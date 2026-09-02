# api.py
"""
YAseen ERP - FastAPI REST API
النسخة الكاملة والمتكاملة - تدعم جميع وحدات النظام
الإصدار: 3.0.0
"""

import sys
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime, date, timedelta
from datetime import date as date_type
from typing import List, Optional, Dict, Any
import uuid
import logging

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Depends, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator
import uvicorn


def filter_fields(data: dict, allowed_fields: list[str]) -> dict:
    """Filter a dictionary to only include allowed fields. Prevents mass-assignment."""
    return {k: v for k, v in data.items() if k in allowed_fields}


def _load_or_generate_secret_key() -> str:
    """توليد مفتاح سري آمن وعشوائي وحفظه في ملف محلي (لا يوجد مفتاح افتراضي مكتوب في الكود)."""
    secret_file = Path(__file__).parent / ".jwt_secret"
    if secret_file.exists():
        stored = secret_file.read_text().strip()
        if stored:
            return stored
    import secrets
    generated = secrets.token_urlsafe(48)
    try:
        secret_file.write_text(generated)
    except OSError:
        pass
    logging.getLogger("api.secret").warning(
        "JWT_SECRET_KEY env var not set. Generated a random secret persisted to .jwt_secret. "
        "Set JWT_SECRET_KEY in production."
    )
    return generated

# JWT
from jose import JWTError, jwt
from passlib.context import CryptContext

import time
from collections import defaultdict
from threading import Lock

_rate_limit_lock = Lock()
_rate_requests = defaultdict(list)
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))


def rate_limiter(max_requests: int = RATE_LIMIT_MAX, window_seconds: int = RATE_LIMIT_WINDOW):
    """Sliding-window rate limiter middleware factory."""
    async def dependency(request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        with _rate_limit_lock:
            _rate_requests[ip] = [t for t in _rate_requests[ip] if now - t < window_seconds]
            if len(_rate_requests[ip]) >= max_requests:
                raise HTTPException(status_code=429, detail="طلبات كثيرة جداً. يرجى المحاولة لاحقاً.")
            _rate_requests[ip].append(now)
    return dependency

# =============================================================================
# Bootstrap
# =============================================================================

from core.bootstrap.startup import get_bootstrap, init_bootstrap

try:
    bootstrap = get_bootstrap()
except Exception as e:
    print(f"Bootstrap not initialized: {e}")
    print("Initializing bootstrap with default settings...")
    bootstrap = init_bootstrap(
        database_url=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/erpya"),
        echo_sql=False,
        seed_data=False,
    )

logger = logging.getLogger(__name__)

# =============================================================================
# JWT Configuration
# =============================================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY") or _load_or_generate_secret_key()
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))  # 30 minutes default
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# =============================================================================
# FastAPI App
# =============================================================================

ENV = os.getenv("ENV", "development")

app = FastAPI(
    title="YAseen ERP API",
    description="REST API لتطبيق YAseen ERP المحاسبي - النسخة المتكاملة",
    version="3.0.0",
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} {response.status_code} {duration_ms:.0f}ms")
    return response


# =============================================================================
# Pydantic Models (Pydantic v2)
# =============================================================================

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    remember_me: bool = False


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class JournalLineRequest(BaseModel):
    account_code: str = Field(..., min_length=3, max_length=20)
    debit: Decimal = Field(Decimal("0"), ge=0)
    credit: Decimal = Field(Decimal("0"), ge=0)
    description: Optional[str] = None
    currency: Optional[str] = None
    cost_center: Optional[str] = None
    profit_center: Optional[str] = None
    
    @field_validator("credit")
    @classmethod
    def validate_debit_credit(cls, v, info):
        values = info.data
        debit = values.get("debit", Decimal("0"))
        if debit > 0 and v > 0:
            raise ValueError("لا يمكن أن يكون هناك مدين ودائن في نفس الوقت")
        if debit == 0 and v == 0:
            raise ValueError("يجب أن يكون هناك مدين أو دائن")
        return v


class CreateJournalEntryRequest(BaseModel):
    date: date_type = Field(..., description="تاريخ القيد")
    description: str = Field(..., min_length=3, max_length=500)
    lines: List[JournalLineRequest] = Field(..., min_length=2)
    transaction_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    
    @model_validator(mode="after")
    def validate_balanced(self) -> 'CreateJournalEntryRequest':
        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)
        if total_debit != total_credit:
            raise ValueError(f"القيد غير متوازن. مدين: {total_debit}, دائن: {total_credit}")
        return self


class CreateAccountRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=20, pattern=r"^\d+$")
    name: str = Field(..., min_length=2, max_length=100)
    account_type: str = Field(..., description="asset, liability, equity, revenue, expense")
    parent_code: Optional[str] = None
    description: Optional[str] = None
    currency: str = Field("USD", min_length=3, max_length=3)
    is_active: bool = True


class CreateCustomerRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=20)
    name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    tax_number: Optional[str] = None
    credit_limit: Decimal = Field(Decimal("0"), ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    notes: Optional[str] = None


class CreateInvoiceRequest(BaseModel):
    customer_id: str
    customer_name: str
    currency: str = Field("USD", min_length=3, max_length=3)
    payment_type: str = "cash"
    payment_currency: str = "USD"
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    fund_id: Optional[str] = None
    lines: List[dict] = Field(default_factory=list)
    notes: Optional[str] = None


class InvoiceLineRequest(BaseModel):
    product_code: str
    product_name: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    notes: Optional[str] = None


class PostInvoiceRequest(BaseModel):
    force: bool = False


class CancelInvoiceRequest(BaseModel):
    reason: Optional[str] = None


class ReturnInvoiceRequest(BaseModel):
    reason: str = Field(..., min_length=2)


class CreatePaymentRequest(BaseModel):
    payment_type: str  # receive, pay, transfer
    payment_method: str  # cash, check, transfer
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    fund_id: str
    customer_id: Optional[str] = None
    supplier_id: Optional[str] = None
    invoice_id: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None


class TrialBalanceRequest(BaseModel):
    as_of_date: date
    include_zero_balance: bool = False
    currency: str = Field("USD", min_length=3, max_length=3)


class IncomeStatementRequest(BaseModel):
    start_date: date
    end_date: date
    currency: str = Field("USD", min_length=3, max_length=3)


class BalanceSheetRequest(BaseModel):
    as_of_date: date
    currency: str = Field("USD", min_length=3, max_length=3)


class CreateProductRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    unit_price: Decimal = Field(Decimal("0"), ge=0)
    tax_rate: Decimal = Field(Decimal("0"), ge=0, le=100)
    description: Optional[str] = None
    category: Optional[str] = None
    stock_quantity: int = Field(0, ge=0)
    low_stock_threshold: int = Field(10, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)


class CreateSupplierRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    tax_number: Optional[str] = None
    credit_limit: Decimal = Field(Decimal("0"), ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    notes: Optional[str] = None


class PurchaseOrderLineRequest(BaseModel):
    product_code: str
    product_name: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class CreatePurchaseOrderRequest(BaseModel):
    supplier_id: str = Field(..., min_length=1)
    supplier_name: Optional[str] = None
    currency: str = Field("USD", min_length=3, max_length=3)
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    lines: List[PurchaseOrderLineRequest] = Field(..., min_length=1)


class CreateFundRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    account_code: str = Field(..., min_length=1, max_length=20)
    fund_type: str = "main"
    currency: str = Field("USD", min_length=3, max_length=3)
    opening_balance: Decimal = Field(Decimal("0"))


class FundTransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    description: Optional[str] = None


# =============================================================================
# JWT Utilities
# =============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


_ROLE_DISPLAY = {
    "admin": "مدير النظام",
    "accountant": "محاسب",
    "auditor": "مدقق",
    "financial_analyst": "محلل مالي",
    "user": "مستخدم",
}


def _user_primary_role(user) -> str:
    roles = getattr(user, 'roles', None)
    if roles:
        first = roles[0]
        name = first.name if hasattr(first, 'name') else first
        return name or 'user'
    return 'user'


def _user_primary_role_display(user) -> str:
    role = _user_primary_role(user)
    return _ROLE_DISPLAY.get(role, role)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.utcnow()
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.utcnow()
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# Dependencies
# =============================================================================

def get_uow():
    try:
        with bootstrap.uow() as uow:
            return uow
    except Exception as e:
        logger.error(f"Error getting UOW: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = verify_token(token)
        
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user_id = payload.get("sub")
        username = payload.get("username")
        roles = payload.get("roles", [])
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        from core.domain.auth.value_objects import UserId
        from uuid import UUID as _UUID
        try:
            parsed_user_id = UserId.from_string(user_id) if isinstance(user_id, str) else user_id
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        with bootstrap.uow() as uow:
            user_repo = uow.users
            user = user_repo.get_by_id(parsed_user_id)
            
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")
            
            if not user.is_active:
                raise HTTPException(status_code=403, detail="User is inactive")
            
            user_dict = {
                "id": str(user.id.value),
                "username": user.username,
                "email": user.email,
                "roles": [r.name for r in user.roles],
                "permissions": sorted({p.code for r in user.roles for p in r.permissions}),
                "is_super_admin": user.is_super_admin,
            }
            
            # ✅ ضبط سياق المستخدم الحالي (request-scoped) لتفعيل
            # @require_permission في المعالجات بدون أي سياق تجريبي
            from core.application.security.authorization import (
                UserContext,
                set_current_user_context,
            )
            set_current_user_context(UserContext(
                user_id=user_dict["id"],
                username=user_dict["username"],
                roles=set(user_dict["roles"]),
                permissions=set(user_dict["permissions"]),
                is_super_admin=user_dict["is_super_admin"],
            ))
            
            return user_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# =============================================================================
# 1. HEALTH CHECK
# =============================================================================

@app.get("/api/health", response_model=ApiResponse)
async def health_check():
    return ApiResponse(
        success=True,
        message="الخادم يعمل بشكل صحيح",
        data={"status": "healthy", "version": "3.0.0"}
    )


@app.get("/api/health/db", response_model=ApiResponse)
async def health_check_db(uow=Depends(get_uow)):
    try:
        with uow:
            from sqlalchemy import text
            result = uow.session.execute(text("SELECT 1"))
            return ApiResponse(
                success=True,
                message="قاعدة البيانات متصلة بشكل صحيح",
                data={"status": "connected"}
            )
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return ApiResponse(
            success=False,
            message=f"فشل الاتصال بقاعدة البيانات: {str(e)}",
            errors=[str(e)]
        )


# =============================================================================
# 2. AUTHENTICATION
# =============================================================================

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, rate_limit: None = Depends(rate_limiter(10, 60))):
    with bootstrap.uow() as uow:
        user_repo = uow.users
        user = user_repo.get_by_username(request.username)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="اسم المستخدم أو كلمة المرور غير صحيحة",
            )
        
        if not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="اسم المستخدم أو كلمة المرور غير صحيحة",
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="الحساب معطل",
            )
        
        token_data = {
            "sub": str(user.id.value),
            "username": user.username,
            "roles": [r.name for r in user.roles],
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        user.last_login = datetime.utcnow()
        user_repo.save(user)
        uow.commit()
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": str(user.id.value),
                "username": user.username,
                "email": user.email,
                "roles": [r.name for r in user.roles],
            }
        )


@app.post("/api/auth/refresh")
async def refresh_token(request: dict, rate_limit: None = Depends(rate_limiter(10, 60))):
    try:
        data = filter_fields(request, ["token"])
        token = data.get("token")
        if not token:
            raise HTTPException(status_code=400, detail="Token is required")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user_id = payload.get("sub")
        username = payload.get("username")
        roles = payload.get("roles", [])
        
        new_access_token = create_access_token({
            "sub": user_id,
            "username": username,
            "roles": roles,
        })
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    return current_user


@app.post("/api/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    return {"message": "تم تسجيل الخروج بنجاح"}


@app.post("/api/auth/change-password")
async def change_password(request: dict, current_user: dict = Depends(get_current_user), rate_limit: None = Depends(rate_limiter(10, 60))):
    data = filter_fields(request, ["old_password", "new_password"])
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="كلمة المرور القديمة والجديدة مطلوبتان")
    
    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 6 أحرف على الأقل")
    
    with bootstrap.uow() as uow:
        user_repo = uow.users
        user = user_repo.get_by_id(current_user["id"])
        
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="كلمة المرور الحالية غير صحيحة")
        
        user.password_hash = get_password_hash(new_password)
        user.updated_by = current_user["username"]
        user_repo.save(user)
        uow.commit()
        
        return {"message": "تم تغيير كلمة المرور بنجاح"}


# =============================================================================
# 3. ACCOUNTING - Journal Entries
# =============================================================================

@app.get("/api/journal-entries", response_model=ApiResponse)
async def list_journal_entries(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    is_posted: Optional[bool] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.journal_entries
            entries = repo.list_all(limit=limit, offset=offset)
            
            if is_posted is not None:
                entries = [e for e in entries if e.is_posted == is_posted]
            if from_date:
                entries = [e for e in entries if e.date >= from_date]
            if to_date:
                entries = [e for e in entries if e.date <= to_date]
            
            total = len(entries)
            
            result = []
            for entry in entries:
                result.append({
                    'id': str(entry.id) if hasattr(entry, 'id') else None,
                    'date': entry.date.isoformat() if hasattr(entry, 'date') else None,
                    'description': entry.description if hasattr(entry, 'description') else '',
                    'is_posted': entry.is_posted if hasattr(entry, 'is_posted') else False,
                    'total_debit': float(entry.total_debit) if hasattr(entry, 'total_debit') else 0,
                    'total_credit': float(entry.total_credit) if hasattr(entry, 'total_credit') else 0,
                    'line_count': len(entry.lines) if hasattr(entry, 'lines') else 0,
                    'version': entry.version if hasattr(entry, 'version') else 1,
                })
            
            return ApiResponse(
                success=True,
                message="تم جلب القيود بنجاح",
                data={
                    'items': result,
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total,
                }
            )
    except Exception as e:
        logger.error(f"Error listing journal entries: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/journal-entries/{entry_id}", response_model=ApiResponse)
async def get_journal_entry(entry_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            repo = uow.journal_entries
            entry = repo.get_by_id(entry_id)
            
            if not entry:
                return ApiResponse(success=False, message="القيد غير موجود")
            
            result = {
                'id': str(entry.id),
                'date': entry.date.isoformat(),
                'description': entry.description,
                'is_posted': entry.is_posted,
                'total_debit': float(entry.total_debit),
                'total_credit': float(entry.total_credit),
                'lines': [
                    {
                        'line_id': str(line.line_id),
                        'account_code': str(line.account_code),
                        'account_name': line.account_name if hasattr(line, 'account_name') else '',
                        'debit': float(line.debit.amount),
                        'credit': float(line.credit.amount),
                        'description': line.description if hasattr(line, 'description') else '',
                    }
                    for line in entry.lines
                ],
                'notes': entry.notes if hasattr(entry, 'notes') else None,
                'version': entry.version,
                'created_at': entry.created_at.isoformat() if hasattr(entry, 'created_at') else None,
                'created_by': entry.created_by if hasattr(entry, 'created_by') else None,
            }
            
            return ApiResponse(success=True, message="تم جلب القيد بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error getting journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/journal-entries", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_journal_entry(request: CreateJournalEntryRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.accounting.commands import CreateJournalEntryCommand
        
        command = CreateJournalEntryCommand(
            date=request.date,
            description=request.description,
            lines=[
                {
                    "account_code": line.account_code,
                    "debit": line.debit,
                    "credit": line.credit,
                    "description": line.description,
                    "currency": line.currency,
                    "cost_center": line.cost_center,
                    "profit_center": line.profit_center,
                }
                for line in request.lines
            ],
            transaction_type=request.transaction_type,
            reference_id=request.reference_id,
            notes=request.notes,
            created_by=current_user["username"],
        )
        
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(command)
        
        return ApiResponse(success=True, message="تم إنشاء القيد بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error creating journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/journal-entries/{entry_id}/post", response_model=ApiResponse)
async def post_journal_entry(entry_id: str, force: bool = Query(False), current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        from core.application.accounting.commands import PostJournalEntryCommand
        
        # التحقق من أن الفترة المالية غير مقفلة قبل الترحيل
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT entry_date FROM journal_entries WHERE id::text = :eid"),
                {"eid": entry_id}
            ).mappings().first()
            if row is None:
                return ApiResponse(success=False, message="القيد غير موجود", errors=["entry not found"])
            entry_date = row["entry_date"]
            if entry_date is not None:
                entry_date = entry_date.date() if hasattr(entry_date, "date") else entry_date
            else:
                entry_date = date.today()
            closed = uow.session.execute(
                text("SELECT is_closed FROM fiscal_periods "
                     "WHERE start_date <= :d AND end_date >= :d AND is_closed = TRUE LIMIT 1"),
                {"d": entry_date}
            ).scalar()
            if closed:
                is_admin = bool(
                    current_user.get("is_super_admin")
                    or any(r in current_user.get("roles", []) for r in ("admin", "super_admin"))
                )
                if not force or not is_admin:
                    return ApiResponse(success=False, message="لا يمكن الترحيل في فترة مالية مقفلة")
        
        command = PostJournalEntryCommand(
            entry_id=entry_id,
            posted_by=current_user["username"],
            force=force,
        )
        
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(command)
        
        return ApiResponse(success=True, message="تم ترحيل القيد بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error posting journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/journal-entries/{entry_id}/reverse", response_model=ApiResponse)
async def reverse_journal_entry(entry_id: str, reason: str = Query(...), current_user: dict = Depends(get_current_user)):
    try:
        from core.application.accounting.commands import ReverseJournalEntryCommand
        
        command = ReverseJournalEntryCommand(
            entry_id=entry_id,
            reason=reason,
            reversed_by=current_user["username"],
        )
        
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(command)
        
        return ApiResponse(success=True, message="تم عكس القيد بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error reversing journal entry: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 4. ACCOUNTING - Accounts
# =============================================================================

@app.get("/api/accounts", response_model=ApiResponse)
async def list_accounts(
    account_type: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.accounts
            accounts = repo.get_all_accounts(account_type=account_type, include_inactive=include_inactive)
            
            result = []
            for acc in accounts:
                result.append({
                    'code': str(acc.code) if hasattr(acc, 'code') else '',
                    'name': acc.name if hasattr(acc, 'name') else '',
                    'account_type': acc.account_type if hasattr(acc, 'account_type') else '',
                    'is_active': acc.is_active if hasattr(acc, 'is_active') else True,
                    'currency': acc.currency if hasattr(acc, 'currency') else 'USD',
                    'parent_code': str(acc.parent_code) if hasattr(acc, 'parent_code') and acc.parent_code else None,
                    'description': acc.description if hasattr(acc, 'description') else None,
                })
            
            return ApiResponse(success=True, message="تم جلب الحسابات بنجاح", data={'accounts': result})
    except Exception as e:
        logger.error(f"Error listing accounts: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/accounts", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_account(request: CreateAccountRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.accounts.commands import CreateAccountCommand
        
        command = CreateAccountCommand(
            code=request.code,
            name=request.name,
            account_type=request.account_type,
            parent_code=request.parent_code,
            description=request.description,
            currency=request.currency,
            is_active=request.is_active,
            created_by=current_user["username"],
        )
        
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(command)
        
        return ApiResponse(success=True, message="تم إنشاء الحساب بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error creating account: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 5. CUSTOMERS
# =============================================================================

@app.get("/api/customers", response_model=ApiResponse)
async def list_customers(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.customers
            
            if status_filter:
                customers = repo.list_by_status(status_filter, limit=limit)
            else:
                customers = repo.list_all(limit=limit, offset=offset)
            
            result = []
            for customer in customers:
                result.append({
                    'id': str(customer.id) if hasattr(customer, 'id') else None,
                    'code': str(customer.code) if hasattr(customer, 'code') else '',
                    'name': customer.name if hasattr(customer, 'name') else '',
                    'status': customer.status.value if hasattr(customer, 'status') else 'active',
                    'email': customer.contact_info.email if hasattr(customer, 'contact_info') else None,
                    'phone': customer.contact_info.phone if hasattr(customer, 'contact_info') else None,
                    'credit_limit': float(customer.credit_limit) if hasattr(customer, 'credit_limit') else 0,
                    'currency': customer.currency if hasattr(customer, 'currency') else 'USD',
                })
            
            return ApiResponse(
                success=True,
                message="تم جلب العملاء بنجاح",
                data={'items': result, 'total': len(result)}
            )
    except Exception as e:
        logger.error(f"Error listing customers: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/customers", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(request: CreateCustomerRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.customers.entities import Customer
        from core.domain.customers.value_objects import CustomerCode, ContactInfo, Address
        
        with bootstrap.uow() as uow:
            existing = uow.customers.get_by_code(CustomerCode(request.code))
            if existing:
                return ApiResponse(success=False, message=f"كود العميل '{request.code}' مستخدم مسبقاً", errors=[f"كود العميل '{request.code}' مستخدم مسبقاً"])
        
        customer = Customer.create(
            code=CustomerCode(request.code),
            name=request.name,
            contact_info=ContactInfo(
                email=request.email,
                phone=request.phone,
                mobile=request.mobile
            ),
            address=Address(
                street=request.street,
                city=request.city,
                country=request.country
            ),
            tax_number=request.tax_number,
            credit_limit=request.credit_limit,
            currency=request.currency,
            notes=request.notes,
            created_by=current_user["username"]
        )
        
        with bootstrap.uow() as uow:
            repo = uow.customers
            repo.save(customer)
            uow.commit()
        
        return ApiResponse(
            success=True,
            message="تم إنشاء العميل بنجاح",
            data={'id': str(customer.id), 'code': str(customer.code), 'name': customer.name}
        )
    except Exception as e:
        logger.error(f"Error creating customer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 6. AGING REPORTS (Customers / Suppliers)
# =============================================================================

@app.get("/api/customers/aging", response_model=ApiResponse)
async def customer_aging_report(
    as_of_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        as_of = as_of_date or date.today()
        with bootstrap.uow() as uow:
            rows = uow.session.execute(text(
                "SELECT i.customer_id AS cid, COALESCE(c.name, '') AS name, "
                "COALESCE(SUM(i.total_amount), 0) AS invoiced, "
                "COALESCE((SELECT SUM(p.amount) FROM payments p "
                "          WHERE p.customer_id = i.customer_id AND p.payment_type = 'receive' "
                "            AND p.status NOT IN ('cancelled','rejected')), 0) AS paid "
                "FROM invoices i LEFT JOIN customers c ON c.id::text = i.customer_id "
                "WHERE i.status = 'posted' "
                "GROUP BY i.customer_id, c.name"
            )).mappings().all()

            items = []
            for r in rows:
                invoiced = Decimal(r['invoiced'])
                paid = Decimal(r['paid'])
                if invoiced - paid <= 0:
                    continue
                inv_rows = uow.session.execute(text(
                    "SELECT invoice_date, total_amount FROM invoices "
                    "WHERE customer_id = :cid AND status = 'posted' "
                    "ORDER BY invoice_date"
                ), {"cid": r['cid']}).mappings().all()

                remaining = [Decimal(str(i['total_amount'])) for i in inv_rows]
                to_allocate = paid
                idx = 0
                while to_allocate > 0 and idx < len(remaining):
                    if remaining[idx] > 0:
                        take = min(remaining[idx], to_allocate)
                        remaining[idx] -= take
                        to_allocate -= take
                    idx += 1

                cur_b = Decimal('0'); d30 = Decimal('0'); d60 = Decimal('0'); d90 = Decimal('0')
                for inv, rem in zip(inv_rows, remaining):
                    if rem <= 0:
                        continue
                    days = (as_of - inv['invoice_date'].date()).days
                    if days <= 30:
                        cur_b += rem
                    elif days <= 60:
                        d30 += rem
                    elif days <= 90:
                        d60 += rem
                    else:
                        d90 += rem

                items.append({
                    'customer_id': r['cid'],
                    'name': r['name'],
                    'current': float(cur_b),
                    'd30': float(d30),
                    'd60': float(d60),
                    'd90': float(d90),
                    'total': float(cur_b + d30 + d60 + d90),
                })
            return ApiResponse(success=True, message="تم جلب تقرير أعمار العملاء بنجاح",
                               data={'as_of': as_of.isoformat(), 'items': items})
    except Exception as e:
        logger.error(f"Error getting customer aging report: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/suppliers/aging", response_model=ApiResponse)
async def supplier_aging_report(
    as_of_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        as_of = as_of_date or date.today()
        with bootstrap.uow() as uow:
            rows = uow.session.execute(text(
                "SELECT po.supplier_id AS sid, COALESCE(s.name, '') AS name, "
                "COALESCE(SUM(po.total_amount), 0) AS ordered, "
                "COALESCE((SELECT SUM(p.amount) FROM payments p "
                "          WHERE p.supplier_id = po.supplier_id AND p.payment_type = 'pay' "
                "            AND p.status NOT IN ('cancelled','rejected')), 0) AS paid "
                "FROM purchase_orders po LEFT JOIN suppliers s ON s.id::text = po.supplier_id "
                "WHERE po.status IN ('posted','partially_received','fully_received') "
                "GROUP BY po.supplier_id, s.name"
            )).mappings().all()

            items = []
            for r in rows:
                ordered = Decimal(r['ordered'])
                paid = Decimal(r['paid'])
                if ordered - paid <= 0:
                    continue
                po_rows = uow.session.execute(text(
                    "SELECT order_date, total_amount FROM purchase_orders "
                    "WHERE supplier_id = :sid AND status IN ('posted','partially_received','fully_received') "
                    "ORDER BY order_date"
                ), {"sid": r['sid']}).mappings().all()

                remaining = [Decimal(str(i['total_amount'])) for i in po_rows]
                to_allocate = paid
                idx = 0
                while to_allocate > 0 and idx < len(remaining):
                    if remaining[idx] > 0:
                        take = min(remaining[idx], to_allocate)
                        remaining[idx] -= take
                        to_allocate -= take
                    idx += 1

                cur_b = Decimal('0'); d30 = Decimal('0'); d60 = Decimal('0'); d90 = Decimal('0')
                for po, rem in zip(po_rows, remaining):
                    if rem <= 0:
                        continue
                    days = (as_of - po['order_date'].date()).days
                    if days <= 30:
                        cur_b += rem
                    elif days <= 60:
                        d30 += rem
                    elif days <= 90:
                        d60 += rem
                    else:
                        d90 += rem

                items.append({
                    'supplier_id': r['sid'],
                    'name': r['name'],
                    'current': float(cur_b),
                    'd30': float(d30),
                    'd60': float(d60),
                    'd90': float(d90),
                    'total': float(cur_b + d30 + d60 + d90),
                })
            return ApiResponse(success=True, message="تم جلب تقرير أعمار الموردين بنجاح",
                               data={'as_of': as_of.isoformat(), 'items': items})
    except Exception as e:
        logger.error(f"Error getting supplier aging report: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 6. INVOICES
# =============================================================================

@app.get("/api/invoices", response_model=ApiResponse)
async def list_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.invoices
            
            if status_filter:
                invoices = repo.list_by_status(status_filter, limit=limit)
            else:
                invoices = repo.list_all(limit=limit, offset=offset)
            
            result = []
            for inv in invoices:
                result.append({
                    'id': str(inv.id) if hasattr(inv, 'id') else None,
                    'number': str(inv.number) if hasattr(inv, 'number') else None,
                    'date': inv.date.isoformat() if hasattr(inv, 'date') else None,
                    'customer_name': inv.customer_name if hasattr(inv, 'customer_name') else '',
                    'total': float(inv.total.amount) if hasattr(inv, 'total') else 0,
                    'currency': inv.currency if hasattr(inv, 'currency') else 'USD',
                    'status': inv.status.value if hasattr(inv, 'status') else 'draft',
                })
            
            return ApiResponse(success=True, message="تم جلب الفواتير بنجاح", data={'items': result})
    except Exception as e:
        logger.error(f"Error listing invoices: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/invoices", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(request: CreateInvoiceRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import CreateInvoiceCommand, AddInvoiceLineCommand

        command_bus = bootstrap.container.resolve("command_bus")

        create_cmd = CreateInvoiceCommand(
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            site_id=request.site_id,
            site_name=request.site_name,
            currency=request.currency,
            payment_type=request.payment_type,
            payment_currency=request.payment_currency,
            fund_id=request.fund_id,
            notes=request.notes or "",
            created_by=current_user["username"],
        )
        result = command_bus.dispatch(create_cmd)

        invoice_id = None
        if isinstance(result, dict):
            invoice_id = result.get('id')
        elif hasattr(result, 'id'):
            invoice_id = result.id

        for line in request.lines:
            line_cmd = AddInvoiceLineCommand(
                invoice_id=invoice_id,
                product_code=line.get('product_code') or '',
                product_name=line.get('product_name') or '',
                quantity=Decimal(str(line.get('quantity', 0))),
                unit_price=Decimal(str(line.get('unit_price', 0))),
                currency=line.get('currency', request.currency),
                notes=line.get('notes') or '',
            )
            command_bus.dispatch(line_cmd)

        return ApiResponse(success=True, message="تم إنشاء الفاتورة بنجاح",
                           data={'id': invoice_id, 'lines_added': len(request.lines)})
    except Exception as e:
        logger.error(f"Error creating invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/invoices/{invoice_id}", response_model=ApiResponse)
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.invoicing.value_objects import InvoiceId
        from uuid import UUID as _UUID
        with bootstrap.uow() as uow:
            invoice = uow.invoices.get_by_id(InvoiceId(_UUID(invoice_id)))
            if not invoice:
                return ApiResponse(success=False, message="الفاتورة غير موجودة")
            data = {
                'id': str(invoice.id.value),
                'number': str(invoice.number) if invoice.number else None,
                'date': invoice.date.isoformat(),
                'customer_id': invoice.customer_id,
                'customer_name': invoice.customer_name,
                'site_id': invoice.site_id,
                'site_name': invoice.site_name,
                'currency': invoice.currency,
                'payment_currency': getattr(invoice, 'payment_currency', invoice.currency),
                'payment_type': invoice.payment_type.value if hasattr(invoice.payment_type, 'value') else str(invoice.payment_type),
                'fund_id': invoice.fund_id,
                'status': invoice.status.value if hasattr(invoice.status, 'value') else str(invoice.status),
                'subtotal': float(invoice.subtotal.amount),
                'tax_amount': float(invoice.tax_amount.amount),
                'total': float(invoice.total.amount),
                'journal_entry_id': invoice.journal_entry_id,
                'notes': invoice.notes,
                'lines': [
                    {
                        'line_id': line.line_id,
                        'product_code': line.product_code,
                        'product_name': line.product_name,
                        'quantity': float(line.quantity),
                        'unit_price': float(line.unit_price.amount),
                        'total': float(line.total.amount),
                        'currency': line.unit_price.currency,
                        'notes': line.notes,
                    }
                    for line in invoice.lines
                ],
                'version': invoice.version,
            }
            return ApiResponse(success=True, message="تم جلب الفاتورة بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/invoices/{invoice_id}/post", response_model=ApiResponse)
async def post_invoice(invoice_id: str, request: PostInvoiceRequest = None, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import PostInvoiceCommand

        if request is None:
            request = PostInvoiceRequest(force=False)

        # ⚠️ تجاوز التحقق من المخزون عبر handler مباشر (وضع التجاوز)
        if request.force:
            from core.application.handlers.invoicing.post_invoice_handler import PostInvoiceHandler
            with bootstrap.container.scope() as scope:
                handler = scope.resolve("post_invoice_handler")
                handler.set_force_post(True)
                command = PostInvoiceCommand(
                    invoice_id=invoice_id,
                    posted_by=current_user["username"],
                )
                result = handler.handle(command)
            return ApiResponse(success=True, message="تم ترحيل الفاتورة بنجاح", data=result)

        command_bus = bootstrap.container.resolve("command_bus")
        command = PostInvoiceCommand(
            invoice_id=invoice_id,
            posted_by=current_user["username"],
        )
        result = command_bus.dispatch(command)

        # معالجة نتيجة الفشل
        if isinstance(result, dict) and result.get('success') is False:
            if result.get('requires_confirmation'):
                return ApiResponse(
                    success=False,
                    message=result.get('message', 'تحقق من المخزون مطلوب'),
                    data={'requires_confirmation': True, 'inventory_check': result.get('inventory_check')},
                    errors=[result.get('confirmation_message', '')],
                )
            return ApiResponse(
                success=False,
                message=result.get('message', 'فشل ترحيل الفاتورة'),
                data=result,
                errors=result.get('errors') or [result.get('message', '')],
            )

        return ApiResponse(success=True, message="تم ترحيل الفاتورة بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error posting invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/invoices/{invoice_id}/lines", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def add_invoice_line(invoice_id: str, request: InvoiceLineRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import AddInvoiceLineCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = AddInvoiceLineCommand(
            invoice_id=invoice_id,
            product_code=request.product_code,
            product_name=request.product_name,
            quantity=request.quantity,
            unit_price=request.unit_price,
            currency=request.currency,
            notes=request.notes or "",
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إضافة السطر بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error adding invoice line: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.patch("/api/invoices/{invoice_id}/lines/{line_id}", response_model=ApiResponse)
async def update_invoice_line(invoice_id: str, line_id: str, request: InvoiceLineRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import UpdateInvoiceLineCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateInvoiceLineCommand(
            invoice_id=invoice_id,
            line_id=line_id,
            quantity=request.quantity,
            unit_price=request.unit_price,
            notes=request.notes or "",
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث السطر بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error updating invoice line: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/invoices/{invoice_id}/lines/{line_id}", response_model=ApiResponse)
async def remove_invoice_line(invoice_id: str, line_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import RemoveInvoiceLineCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = RemoveInvoiceLineCommand(invoice_id=invoice_id, line_id=line_id)
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم حذف السطر بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error removing invoice line: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/invoices/{invoice_id}/cancel", response_model=ApiResponse)
async def cancel_invoice(invoice_id: str, request: CancelInvoiceRequest = None, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import CancelInvoiceCommand
        reason = request.reason if request else None
        command_bus = bootstrap.container.resolve("command_bus")
        command = CancelInvoiceCommand(
            invoice_id=invoice_id,
            reason=reason,
            cancelled_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إلغاء الفاتورة بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error cancelling invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/invoices/{invoice_id}/return", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def return_invoice(invoice_id: str, request: ReturnInvoiceRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.invoicing.commands import ReturnInvoiceCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = ReturnInvoiceCommand(
            invoice_id=invoice_id,
            reason=request.reason,
            created_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء فاتورة المرتجع بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error returning invoice: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 7. PRODUCTS
# =============================================================================

@app.get("/api/products", response_model=ApiResponse)
async def list_products(
    include_inactive: bool = Query(False),
    category: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            products = uow.products.list_all(
                include_inactive=include_inactive,
                category=category,
                limit=limit,
                offset=offset,
            )
            if q:
                ql = q.lower()
                products = [p for p in products if ql in str(p.code).lower() or ql in (p.name or '').lower()]
            result = []
            for p in products:
                result.append({
                    'id': str(p.id.value),
                    'code': str(p.code),
                    'name': p.name,
                    'unit_price': float(p.unit_price.amount),
                    'currency': p.unit_price.currency,
                    'tax_rate': float(p.tax_rate),
                    'category': p.category,
                    'stock_quantity': p.stock_quantity,
                    'low_stock_threshold': p.low_stock_threshold,
                    'status': p.status.value if hasattr(p.status, 'value') else str(p.status),
                })
            return ApiResponse(success=True, message="تم جلب المنتجات بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing products: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/products", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_product(request: CreateProductRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.products.entities import Product
        from core.domain.products.value_objects import ProductCode
        from core.domain.shared.value_objects import Money

        with bootstrap.uow() as uow:
            existing = uow.products.get_by_code(ProductCode(request.code))
            if existing:
                return ApiResponse(success=False, message=f"كود المنتج '{request.code}' مستخدم مسبقاً", errors=[f"كود المنتج '{request.code}' مستخدم مسبقاً"])

        product = Product.create(
            code=ProductCode(request.code),
            name=request.name,
            unit_price=Money(request.unit_price, request.currency),
            tax_rate=request.tax_rate,
            description=request.description,
            category=request.category,
            stock_quantity=request.stock_quantity,
            low_stock_threshold=request.low_stock_threshold,
            created_by=current_user["username"],
        )
        with bootstrap.uow() as uow:
            uow.products.save(product)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء المنتج بنجاح",
                           data={'id': str(product.id.value), 'code': str(product.code), 'name': product.name})
    except Exception as e:
        logger.error(f"Error creating product: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/products/low-stock", response_model=ApiResponse)
async def get_low_stock_products(
    threshold: int = Query(10, ge=1),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.products
            all_products = repo.get_all() if hasattr(repo, 'get_all') else []
            result = []
            for p in all_products:
                if getattr(p, 'stock_quantity', 0) <= threshold:
                    result.append({
                        'id': str(getattr(p, 'id', '')),
                        'code': str(getattr(p, 'code', '')),
                        'name': getattr(p, 'name', ''),
                        'stock_quantity': getattr(p, 'stock_quantity', 0),
                    })
            return ApiResponse(success=True, message="تم جلب المنتجات منخفضة المخزون بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error getting low stock products: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/products/{product_id}", response_model=ApiResponse)
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.products.value_objects import ProductId
        with bootstrap.uow() as uow:
            product = uow.products.get_by_id(ProductId.from_string(product_id))
            if not product:
                return ApiResponse(success=False, message="المنتج غير موجود")
            data = {
                'id': str(product.id.value),
                'code': str(product.code),
                'name': product.name,
                'unit_price': float(product.unit_price.amount),
                'currency': product.unit_price.currency,
                'tax_rate': float(product.tax_rate),
                'description': product.description,
                'category': product.category,
                'stock_quantity': product.stock_quantity,
                'low_stock_threshold': product.low_stock_threshold,
                'status': product.status.value if hasattr(product.status, 'value') else str(product.status),
                'version': product.version,
            }
            return ApiResponse(success=True, message="تم جلب المنتج بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting product: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 7. SUPPLIERS
# =============================================================================

@app.get("/api/suppliers", response_model=ApiResponse)
async def list_suppliers(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.suppliers
            from core.domain.suppliers.value_objects import SupplierStatus
            suppliers = repo.list_all(
                status=SupplierStatus(status_filter) if status_filter else None,
                limit=limit,
                offset=offset,
            )
            result = []
            for s in suppliers:
                result.append({
                    'id': str(s.id.value),
                    'code': str(s.code),
                    'name': s.name,
                    'status': s.status.value if hasattr(s.status, 'value') else str(s.status),
                    'email': s.contact_info.email if hasattr(s, 'contact_info') else None,
                    'phone': s.contact_info.phone if hasattr(s, 'contact_info') else None,
                    'credit_limit': float(s.credit_limit) if hasattr(s, 'credit_limit') else 0,
                    'currency': s.currency if hasattr(s, 'currency') else 'USD',
                })
            return ApiResponse(success=True, message="تم جلب الموردين بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing suppliers: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/suppliers", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_supplier(request: CreateSupplierRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.suppliers.entities import Supplier
        from core.domain.suppliers.value_objects import SupplierCode, ContactInfo, Address

        supplier = Supplier.create(
            code=SupplierCode(request.code),
            name=request.name,
            contact_info=ContactInfo(email=request.email, phone=request.phone, mobile=request.mobile),
            address=Address(street=request.street, city=request.city, country=request.country),
            tax_number=request.tax_number,
            credit_limit=request.credit_limit,
            currency=request.currency,
            notes=request.notes,
            created_by=current_user["username"],
        )
        with bootstrap.uow() as uow:
            uow.suppliers.save(supplier)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء المورد بنجاح",
                           data={'id': str(supplier.id.value), 'code': str(supplier.code), 'name': supplier.name})
    except Exception as e:
        logger.error(f"Error creating supplier: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/suppliers/{supplier_id}", response_model=ApiResponse)
async def get_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.suppliers.value_objects import SupplierId
        with bootstrap.uow() as uow:
            supplier = uow.suppliers.get_by_id(SupplierId.from_string(supplier_id))
            if not supplier:
                return ApiResponse(success=False, message="المورد غير موجود")
            data = {
                'id': str(supplier.id.value),
                'code': str(supplier.code),
                'name': supplier.name,
                'status': supplier.status.value if hasattr(supplier.status, 'value') else str(supplier.status),
                'email': supplier.contact_info.email if hasattr(supplier, 'contact_info') else None,
                'phone': supplier.contact_info.phone if hasattr(supplier, 'contact_info') else None,
                'tax_number': supplier.tax_number,
                'credit_limit': float(supplier.credit_limit) if hasattr(supplier, 'credit_limit') else 0,
                'currency': supplier.currency if hasattr(supplier, 'currency') else 'USD',
                'notes': supplier.notes,
                'version': supplier.version,
            }
            return ApiResponse(success=True, message="تم جلب المورد بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting supplier: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 8. PURCHASE ORDERS
# =============================================================================

@app.get("/api/purchase-orders", response_model=ApiResponse)
async def list_purchase_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            repo = uow.purchase_orders
            from core.domain.purchasing.value_objects import PurchaseOrderStatus
            if status_filter:
                orders = repo.list_by_status(PurchaseOrderStatus(status_filter), limit=limit, offset=offset)
            else:
                orders = repo.list_by_filters(limit=limit, offset=offset)
            result = []
            for o in orders:
                result.append({
                    'id': str(o.id.value),
                    'number': str(o.number) if o.number else None,
                    'date': o.date.isoformat(),
                    'supplier_id': o.supplier_id,
                    'supplier_name': o.supplier_name,
                    'status': o.status.value if hasattr(o.status, 'value') else str(o.status),
                    'currency': o.currency,
                    'total': float(o.total.amount),
                })
            return ApiResponse(success=True, message="تم جلب أوامر الشراء بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing purchase orders: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/purchase-orders", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(request: CreatePurchaseOrderRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.purchasing.entities import PurchaseOrder, PurchaseLine
        from core.domain.shared.value_objects import Money

        supplier_name = request.supplier_name or ""
        if not supplier_name:
            try:
                from core.domain.suppliers.value_objects import SupplierId
                with bootstrap.uow() as uow:
                    supplier = uow.suppliers.get_by_id(SupplierId.from_string(request.supplier_id))
                    if supplier:
                        supplier_name = supplier.name
            except Exception:
                pass

        order = PurchaseOrder(
            supplier_id=request.supplier_id,
            supplier_name=supplier_name,
            currency=request.currency,
            notes=request.notes,
            created_by=current_user["username"],
        )
        if request.expected_delivery_date:
            from datetime import datetime as _dt
            order.expected_delivery_date = _dt.combine(request.expected_delivery_date, _dt.min.time())
        for line_req in request.lines:
            line = PurchaseLine(
                product_code=line_req.product_code,
                product_name=line_req.product_name,
                quantity=line_req.quantity,
                unit_price=Money(line_req.unit_price, request.currency),
                notes=line_req.notes or "",
            )
            order.add_line(line)

        with bootstrap.uow() as uow:
            uow.purchase_orders.save(order)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء أمر الشراء بنجاح",
                           data={'id': str(order.id.value), 'status': 'draft'})
    except Exception as e:
        logger.error(f"Error creating purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/purchase-orders/{order_id}", response_model=ApiResponse)
async def get_purchase_order(order_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.purchasing.value_objects import PurchaseOrderId
        with bootstrap.uow() as uow:
            order = uow.purchase_orders.get_by_id(PurchaseOrderId.from_string(order_id))
            if not order:
                return ApiResponse(success=False, message="أمر الشراء غير موجود")
            data = {
                'id': str(order.id.value),
                'number': str(order.number) if order.number else None,
                'date': order.date.isoformat(),
                'supplier_id': order.supplier_id,
                'supplier_name': order.supplier_name,
                'status': order.status.value if hasattr(order.status, 'value') else str(order.status),
                'currency': order.currency,
                'total': float(order.total.amount),
                'lines': [
                    {
                        'product_code': ln.product_code,
                        'product_name': ln.product_name,
                        'quantity': float(ln.quantity),
                        'unit_price': float(ln.unit_price.amount),
                        'received_quantity': float(ln.received_quantity),
                    }
                    for ln in order.lines
                ],
                'version': order.version,
            }
            return ApiResponse(success=True, message="تم جلب أمر الشراء بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class ReceivePurchaseOrderRequest(BaseModel):
    batch_numbers: Optional[Dict[str, str]] = None
    serial_numbers: Optional[Dict[str, List[str]]] = None
    expiry_dates: Optional[Dict[str, datetime]] = None
    locations: Optional[Dict[str, str]] = None


@app.post("/api/purchase-orders/{order_id}/post", response_model=ApiResponse)
async def post_purchase_order(order_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.purchasing.commands import PostPurchaseOrderCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = PostPurchaseOrderCommand(
            order_id=order_id,
            posted_by=current_user["username"],
        )
        result = command_bus.dispatch(command)

        if isinstance(result, dict) and result.get('success') is False:
            return ApiResponse(
                success=False,
                message=result.get('message', 'فشل ترحيل أمر الشراء'),
                data=result,
                errors=result.get('errors') or [result.get('message', '')],
            )
        return ApiResponse(success=True, message="تم ترحيل أمر الشراء بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error posting purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/purchase-orders/{order_id}/receive", response_model=ApiResponse)
async def receive_purchase_order(order_id: str, request: ReceivePurchaseOrderRequest = None,
                                 current_user: dict = Depends(get_current_user)):
    try:
        from core.application.purchasing.commands import ReceivePurchaseOrderCommand
        if request is None:
            request = ReceivePurchaseOrderRequest()
        command_bus = bootstrap.container.resolve("command_bus")
        command = ReceivePurchaseOrderCommand(
            order_id=order_id,
            received_by=current_user["username"],
            batch_numbers=request.batch_numbers,
            serial_numbers=request.serial_numbers,
            expiry_dates=request.expiry_dates,
            locations=request.locations,
        )
        result = command_bus.dispatch(command)

        if isinstance(result, dict) and result.get('success') is False:
            return ApiResponse(
                success=False,
                message=result.get('message', 'فشل استلام أمر الشراء'),
                data=result,
                errors=result.get('errors') or [result.get('message', '')],
            )
        data = {
            'id': getattr(result, 'id', None),
            'number': getattr(result, 'number', None),
            'status': getattr(result, 'status', None),
            'is_fully_received': result.is_fully_received if hasattr(result, 'is_fully_received') else None,
            'stock_movements': getattr(result, 'stock_movements', []),
            'lines': [
                {
                    'line_id': ln.line_id,
                    'product_code': ln.product_code,
                    'quantity': float(ln.quantity),
                    'received_quantity': float(ln.received_quantity),
                    'is_fully_received': ln.is_fully_received,
                }
                for ln in result.lines
            ],
        }
        return ApiResponse(success=True, message="تم استلام أمر الشراء بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error receiving purchase order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 9. PAYMENTS
# =============================================================================

@app.get("/api/payments", response_model=ApiResponse)
async def list_payments(
    payment_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            filters = {"limit": limit, "offset": offset}
            if payment_type:
                filters["payment_type"] = payment_type
            if status_filter:
                filters["status"] = status_filter
            payments = uow.payments.list_by_filters(filters)
            result = []
            for p in payments:
                result.append({
                    'id': str(p.id.value),
                    'code': str(p.code) if hasattr(p.code, 'value') else str(p.code),
                    'date': p.date.isoformat(),
                    'payment_type': p.payment_type.value if hasattr(p.payment_type, 'value') else str(p.payment_type),
                    'payment_method': p.payment_method.value if hasattr(p.payment_method, 'value') else str(p.payment_method),
                    'amount': float(p.amount.amount),
                    'currency': p.currency if hasattr(p, 'currency') else 'USD',
                    'status': p.status.value if hasattr(p.status, 'value') else str(p.status),
                    'customer_name': p.customer_name,
                    'supplier_name': p.supplier_name,
                })
            return ApiResponse(success=True, message="تم جلب المدفوعات بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing payments: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/payments", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(request: CreatePaymentRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.payments.entities import Payment
        from core.domain.payments.value_objects import PaymentType, PaymentMethod
        from core.domain.shared.value_objects import Money

        payment = Payment.create(
            payment_type=PaymentType(request.payment_type),
            amount=Money(request.amount, request.currency),
            payment_method=PaymentMethod(request.payment_method),
            customer_id=request.customer_id,
            supplier_id=request.supplier_id,
            fund_id=request.fund_id,
            notes=request.description or "",
            created_by=current_user["username"],
        )
        with bootstrap.uow() as uow:
            uow.payments.save(payment)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء الدفع بنجاح",
                           data={'id': str(payment.id.value), 'status': 'draft'})
    except Exception as e:
        logger.error(f"Error creating payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/payments/{payment_id}", response_model=ApiResponse)
async def get_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.payments.value_objects import PaymentId
        with bootstrap.uow() as uow:
            payment = uow.payments.get_by_id(PaymentId.from_string(payment_id))
            if not payment:
                return ApiResponse(success=False, message="الدفع غير موجود")
            data = {
                'id': str(payment.id.value),
                'code': str(payment.code),
                'date': payment.date.isoformat(),
                'payment_type': payment.payment_type.value if hasattr(payment.payment_type, 'value') else str(payment.payment_type),
                'payment_method': payment.payment_method.value if hasattr(payment.payment_method, 'value') else str(payment.payment_method),
                'amount': float(payment.amount.amount),
                'currency': payment.currency if hasattr(payment, 'currency') else 'USD',
                'status': payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
                'customer_name': payment.customer_name,
                'supplier_name': payment.supplier_name,
                'notes': payment.notes if hasattr(payment, 'notes') else None,
                'version': payment.version,
            }
            return ApiResponse(success=True, message="تم جلب الدفع بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class PaymentReasonRequest(BaseModel):
    reason: str = ""


@app.post("/api/payments/{payment_id}/submit", response_model=ApiResponse)
async def submit_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.payments.value_objects import PaymentId
        with bootstrap.uow() as uow:
            payment = uow.payments.get_by_id(PaymentId.from_string(payment_id))
            if not payment:
                return ApiResponse(success=False, message="الدفع غير موجود")
            payment.submit(current_user["username"])
            uow.payments.save(payment)
            uow.commit()
        return ApiResponse(success=True, message="تم إرسال الدفع للاعتماد بنجاح",
                           data={'id': payment_id, 'status': 'pending'})
    except Exception as e:
        logger.error(f"Error submitting payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/payments/{payment_id}/approve", response_model=ApiResponse)
async def approve_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import ApprovePaymentCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = ApprovePaymentCommand(
            payment_id=payment_id,
            approved_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم اعتماد الدفع بنجاح",
                           data={'id': str(getattr(result, 'id', payment_id)),
                                 'status': getattr(result, 'status', None)})
    except Exception as e:
        logger.error(f"Error approving payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/payments/{payment_id}/reject", response_model=ApiResponse)
async def reject_payment(payment_id: str, request: PaymentReasonRequest = None,
                         current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import RejectPaymentCommand
        if request is None:
            request = PaymentReasonRequest()
        command_bus = bootstrap.container.resolve("command_bus")
        command = RejectPaymentCommand(
            payment_id=payment_id,
            rejected_by=current_user["username"],
            reason=request.reason,
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم رفض الدفع بنجاح",
                           data={'id': str(getattr(result, 'id', payment_id)),
                                 'status': getattr(result, 'status', None)})
    except Exception as e:
        logger.error(f"Error rejecting payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/payments/{payment_id}/complete", response_model=ApiResponse)
async def complete_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import CompletePaymentCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = CompletePaymentCommand(
            payment_id=payment_id,
            completed_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        data = {
            'id': str(getattr(result, 'id', payment_id)),
            'status': getattr(result, 'status', None),
            'journal_entry_id': getattr(result, 'journal_entry_id', None),
        }
        return ApiResponse(success=True, message="تم إكمال الدفع بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error completing payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/payments/{payment_id}/cancel", response_model=ApiResponse)
async def cancel_payment(payment_id: str, request: PaymentReasonRequest = None,
                         current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import CancelPaymentCommand
        if request is None:
            request = PaymentReasonRequest()
        command_bus = bootstrap.container.resolve("command_bus")
        command = CancelPaymentCommand(
            payment_id=payment_id,
            cancelled_by=current_user["username"],
            reason=request.reason,
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إلغاء الدفع بنجاح",
                           data={'id': str(getattr(result, 'id', payment_id)),
                                 'status': getattr(result, 'status', None)})
    except Exception as e:
        logger.error(f"Error cancelling payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/payments/{payment_id}", response_model=ApiResponse)
async def delete_draft_payment(payment_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.payments.commands import DeleteDraftPaymentCommand
        command_bus = bootstrap.container.resolve("command_bus")
        command = DeleteDraftPaymentCommand(
            payment_id=payment_id,
            deleted_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم حذف الدفع بنجاح",
                           data={'id': payment_id, 'result': result})
    except Exception as e:
        logger.error(f"Error deleting draft payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 10. FUNDS
# =============================================================================

@app.get("/api/funds", response_model=ApiResponse)
async def list_funds(
    fund_type: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            from core.domain.funds.value_objects import FundType
            funds = uow.funds.list_all(
                fund_type=FundType(fund_type) if fund_type else None,
                include_inactive=include_inactive,
                limit=limit,
                offset=offset,
                include_balance=False,
            )
            result = []
            for f in funds:
                result.append({
                    'id': str(f.id.value),
                    'code': str(f.code),
                    'name': f.name,
                    'fund_type': f.fund_type.value if hasattr(f.fund_type, 'value') else str(f.fund_type),
                    'account_code': f.account_code,
                    'currency': f.currency,
                    'status': f.status.value if hasattr(f.status, 'value') else str(f.status),
                })
            return ApiResponse(success=True, message="تم جلب الصناديق بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error listing funds: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/funds", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_fund(request: CreateFundRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.funds.entities import Fund
        from core.domain.funds.value_objects import FundType
        from core.domain.shared.value_objects import Money

        fund = Fund.create(
            code=request.code,
            name=request.name,
            account_code=request.account_code,
            fund_type=FundType(request.fund_type),
            currency=request.currency,
            created_by=current_user["username"],
            opening_balance=Money(request.opening_balance, request.currency) if request.opening_balance else None,
        )
        with bootstrap.uow() as uow:
            uow.funds.save(fund)
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء الصندوق بنجاح",
                           data={'id': str(fund.id.value), 'code': str(fund.code), 'name': fund.name})
    except Exception as e:
        logger.error(f"Error creating fund: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class FundTransactionRequest(BaseModel):
    amount: Decimal
    reason: str = ""
    currency: Optional[str] = None
    reference_id: Optional[str] = None


@app.post("/api/funds/{fund_id}/deposit", response_model=ApiResponse)
async def deposit_to_fund(
    fund_id: str,
    request: FundTransactionRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.funds.commands import DepositToFundCommand
        from core.domain.funds.value_objects import FundId
        command_bus = bootstrap.container.resolve("command_bus")
        command = DepositToFundCommand(
            fund_id=FundId.from_string(fund_id),
            amount=request.amount,
            reason=request.reason,
            currency=request.currency,
            reference_id=request.reference_id,
            created_by=current_user["username"],
        )
        fund = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إيداع المبلغ في الصندوق بنجاح",
                           data={'id': getattr(fund, 'id', None),
                                 'code': getattr(fund, 'code', None),
                                 'balance': getattr(fund, 'balance', None)})
    except Exception as e:
        logger.error(f"Error depositing to fund: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/funds/{fund_id}/withdraw", response_model=ApiResponse)
async def withdraw_from_fund(
    fund_id: str,
    request: FundTransactionRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.funds.commands import WithdrawFromFundCommand
        from core.domain.funds.value_objects import FundId
        command_bus = bootstrap.container.resolve("command_bus")
        command = WithdrawFromFundCommand(
            fund_id=FundId.from_string(fund_id),
            amount=request.amount,
            reason=request.reason,
            currency=request.currency,
            reference_id=request.reference_id,
            created_by=current_user["username"],
        )
        fund = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم سحب المبلغ من الصندوق بنجاح",
                           data={'id': getattr(fund, 'id', None),
                                 'code': getattr(fund, 'code', None),
                                 'balance': getattr(fund, 'balance', None)})
    except Exception as e:
        logger.error(f"Error withdrawing from fund: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/funds/{fund_id}", response_model=ApiResponse)
async def get_fund(fund_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.funds.value_objects import FundId
        with bootstrap.uow() as uow:
            fund = uow.funds.get_by_id(FundId.from_string(fund_id))
            if not fund:
                return ApiResponse(success=False, message="الصندوق غير موجود")
            data = {
                'id': str(fund.id.value),
                'code': str(fund.code),
                'name': fund.name,
                'fund_type': fund.fund_type.value if hasattr(fund.fund_type, 'value') else str(fund.fund_type),
                'account_code': fund.account_code,
                'currency': fund.currency,
                'status': fund.status.value if hasattr(fund.status, 'value') else str(fund.status),
                'version': fund.version,
            }
            return ApiResponse(success=True, message="تم جلب الصندوق بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting fund: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/funds/{fund_id}/balance", response_model=ApiResponse)
async def get_fund_balance(fund_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.funds.value_objects import FundId
        with bootstrap.uow() as uow:
            fund = uow.funds.get_by_id(FundId.from_string(fund_id))
            if not fund:
                return ApiResponse(success=False, message="الصندوق غير موجود")
            balance = uow.funds.get_balance(FundId.from_string(fund_id))
            data = {
                'fund_id': fund_id,
                'currency': balance.currency if hasattr(balance, 'currency') else 'USD',
                'balance': float(balance.amount) if hasattr(balance, 'amount') else 0,
            }
            return ApiResponse(success=True, message="تم جلب رصيد الصندوق بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting fund balance: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class TransferFundsRequest(BaseModel):
    from_fund_id: str
    to_fund_id: str
    amount: Decimal
    reason: str = ""
    from_currency: Optional[str] = None
    to_currency: Optional[str] = None


@app.post("/api/funds/transfer", response_model=ApiResponse)
async def transfer_funds(request: TransferFundsRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.application.funds.commands import TransferBetweenFundsCommand
        from core.domain.funds.value_objects import FundId
        command_bus = bootstrap.container.resolve("command_bus")
        command = TransferBetweenFundsCommand(
            from_fund_id=FundId.from_string(request.from_fund_id),
            to_fund_id=FundId.from_string(request.to_fund_id),
            amount=request.amount,
            reason=request.reason,
            from_currency=request.from_currency,
            to_currency=request.to_currency,
            created_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        if isinstance(result, dict) and result.get('success') is False:
            return ApiResponse(
                success=False,
                message=result.get('message', 'فشل التحويل بين الصناديق'),
                data=result,
                errors=[result.get('error', '')],
            )
        return ApiResponse(success=True, message="تم التحويل بين الصناديق بنجاح", data=result)
    except Exception as e:
        logger.error(f"Error transferring funds: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/funds/{fund_id}/movements", response_model=ApiResponse)
async def get_fund_movements(
    fund_id: str,
    movement_type: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.funds.commands import GetFundMovementsQuery
        from core.domain.funds.value_objects import FundId
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetFundMovementsQuery(
            fund_id=FundId.from_string(fund_id),
            movement_type=movement_type,
            transaction_type=transaction_type,
            limit=limit,
        )
        movements = query_bus.dispatch(query)
        result = []
        for m in movements or []:
            result.append({
                'id': getattr(m, 'id', None),
                'fund_id': getattr(m, 'fund_id', None),
                'movement_type': getattr(m, 'movement_type', None),
                'amount': float(getattr(m, 'amount', 0)),
                'currency': getattr(m, 'currency', None),
                'balance_after': float(getattr(m, 'balance_after', 0)),
                'reason': getattr(m, 'reason', None),
                'reference_id': getattr(m, 'reference_id', None),
                'exchange_rate_used': getattr(m, 'exchange_rate_used', None),
                'from_fund_code': getattr(m, 'from_fund_code', None),
                'to_fund_code': getattr(m, 'to_fund_code', None),
                'created_at': getattr(m, 'created_at', None),
                'created_by': getattr(m, 'created_by', None),
            })
        return ApiResponse(success=True, message="تم جلب حركات الصندوق بنجاح",
                           data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error getting fund movements: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 11. REPORTS
# =============================================================================

@app.get("/api/reports/trial-balance", response_model=ApiResponse)
async def trial_balance_report(
    as_of_date: Optional[date] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    include_zero_balances: bool = Query(True),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text

        def signed_balance(account_type, debit, credit):
            if account_type in ("asset", "expense"):
                return debit - credit
            return credit - debit

        with bootstrap.uow() as uow:
            accounts = uow.accounts.get_all_accounts()
            acct_meta = {
                str(a.code): {
                    'name': a.name if hasattr(a, 'name') else '',
                    'account_type': a.account_type if hasattr(a, 'account_type') else 'asset',
                    'currency': a.currency if hasattr(a, 'currency') else 'USD',
                }
                for a in accounts
            }

            if from_date and to_date:
                if from_date > to_date:
                    return ApiResponse(success=False, message="تاريخ البداية يجب أن يكون قبل تاريخ النهاية")

                movement_rows = uow.session.execute(text(
                    "SELECT a.code AS code, COALESCE(SUM(l.debit_amount), 0) AS debit, "
                    "COALESCE(SUM(l.credit_amount), 0) AS credit "
                    "FROM ledger_entries l JOIN accounts a ON a.id = l.account_id "
                    "WHERE l.entry_date::date >= :from_date AND l.entry_date::date <= :to_date "
                    "GROUP BY a.code"
                ), {"from_date": from_date, "to_date": to_date}).mappings().all()

                opening_rows = uow.session.execute(text(
                    "SELECT a.code AS code, COALESCE(SUM(l.debit_amount), 0) AS debit, "
                    "COALESCE(SUM(l.credit_amount), 0) AS credit "
                    "FROM ledger_entries l JOIN accounts a ON a.id = l.account_id "
                    "WHERE l.entry_date::date < :from_date "
                    "GROUP BY a.code"
                ), {"from_date": from_date}).mappings().all()

                movement = {}
                for r in movement_rows:
                    movement[str(r['code'])] = (Decimal(r['debit']), Decimal(r['credit']))
                opening = {}
                for r in opening_rows:
                    opening[str(r['code'])] = (Decimal(r['debit']), Decimal(r['credit']))

                result = []
                all_codes = set(list(movement.keys()) + list(opening.keys()) + list(acct_meta.keys()))
                for code in sorted(all_codes):
                    op_d, op_c = opening.get(code, (Decimal('0'), Decimal('0')))
                    mv_d, mv_c = movement.get(code, (Decimal('0'), Decimal('0')))
                    meta = acct_meta.get(code, {'name': '', 'account_type': 'asset', 'currency': 'USD'})
                    op_balance = signed_balance(meta['account_type'], op_d, op_c)
                    close_balance = signed_balance(meta['account_type'], op_d + mv_d, op_c + mv_c)
                    if not include_zero_balances and op_balance == 0 and mv_d == 0 and mv_c == 0 and close_balance == 0:
                        continue
                    result.append({
                        'account_code': code,
                        'name': meta['name'],
                        'account_type': meta['account_type'],
                        'currency': meta['currency'],
                        'opening_balance': float(op_balance),
                        'debit': float(mv_d),
                        'credit': float(mv_c),
                        'balance': float(close_balance),
                    })
                totals = {
                    'opening_balance': sum(i['opening_balance'] for i in result),
                    'debit': sum(i['debit'] for i in result),
                    'credit': sum(i['credit'] for i in result),
                    'balance': sum(i['balance'] for i in result),
                }
                return ApiResponse(success=True, message="تم جلب ميزان المراجعة بنجاح",
                                   data={'from_date': from_date.isoformat(), 'to_date': to_date.isoformat(),
                                         'items': result, 'totals': totals, 'total': len(result)})
            else:
                as_of = as_of_date or date.today()
                balances = uow.ledger.get_trial_balance(as_of)
                result = []
                for code, balance in balances.items():
                    code = str(code)
                    meta = acct_meta.get(code, {'name': '', 'account_type': 'asset', 'currency': 'USD'})
                    amt = Decimal(balance.amount)
                    if not include_zero_balances and amt == 0:
                        continue
                    result.append({
                        'account_code': code,
                        'name': meta['name'],
                        'account_type': meta['account_type'],
                        'currency': balance.currency or meta['currency'],
                        'opening_balance': 0.0,
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': float(amt),
                    })
                return ApiResponse(success=True, message="تم جلب ميزان المراجعة بنجاح",
                                   data={'as_of': as_of.isoformat(), 'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error getting trial balance: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/reports/accounts", response_model=ApiResponse)
async def accounts_report(
    include_inactive: bool = Query(False),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            accounts = uow.accounts.get_all_accounts(include_inactive=include_inactive)
            result = [
                {
                    'code': str(a.code),
                    'name': a.name if hasattr(a, 'name') else '',
                    'account_type': a.account_type if hasattr(a, 'account_type') else '',
                }
                for a in accounts
            ]
            return ApiResponse(success=True, message="تم جلب الحسابات بنجاح",
                               data={'items': result, 'total': len(result)})
    except Exception as e:
        logger.error(f"Error getting accounts report: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class IncomeStatementRequest(BaseModel):
    period_start: date
    period_end: date
    currency: str = "USD"
    include_comparative: bool = False


class BalanceSheetRequest(BaseModel):
    as_of_date: date
    currency: str = "USD"


class CashFlowRequest(BaseModel):
    period_start: date
    period_end: date
    currency: str = "USD"
    method: str = "indirect"


@app.post("/api/reports/income-statement", response_model=ApiResponse)
async def income_statement_report(
    request: IncomeStatementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.financial_statements.commands import GenerateIncomeStatementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = GenerateIncomeStatementCommand(
            period_start=request.period_start,
            period_end=request.period_end,
            currency=request.currency,
            include_comparative=request.include_comparative,
            generated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم توليد قائمة الدخل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error generating income statement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/reports/balance-sheet", response_model=ApiResponse)
async def balance_sheet_report(
    request: BalanceSheetRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.financial_statements.commands import GenerateBalanceSheetCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = GenerateBalanceSheetCommand(
            as_of_date=request.as_of_date,
            currency=request.currency,
            generated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم توليد الميزانية العمومية بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error generating balance sheet: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/reports/cash-flow", response_model=ApiResponse)
async def cash_flow_report(
    request: CashFlowRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.financial_statements.commands import GenerateCashFlowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = GenerateCashFlowCommand(
            period_start=request.period_start,
            period_end=request.period_end,
            currency=request.currency,
            method=request.method,
            generated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم توليد قائمة التدفقات النقدية بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error generating cash flow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/reports/financial-statements", response_model=ApiResponse)
async def list_financial_statements(
    statement_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.financial_statements.commands import ListFinancialStatementsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        query = ListFinancialStatementsQuery(statement_type=statement_type, limit=limit)
        items = query_bus.dispatch(query) or []
        return ApiResponse(success=True, message="تم جلب القوائم المالية بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error listing financial statements: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 12. INVENTORY - المخزون
# =============================================================================


class StockMovementRequest(BaseModel):
    entity_type: str
    entity_id: str
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    currency: str = "USD"
    reference_type: str = ""
    reference_id: str = ""
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""


class PurchaseMovementRequest(BaseModel):
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    purchase_order_id: str
    currency: str = "USD"
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""


class SaleMovementRequest(BaseModel):
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    invoice_id: str
    currency: str = "USD"
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    location: Optional[str] = None
    notes: str = ""


class AdjustmentMovementRequest(BaseModel):
    entity_type: str
    entity_id: str
    old_quantity: Decimal
    new_quantity: Decimal
    unit_cost: Decimal
    reason: str
    currency: str = "USD"
    location: Optional[str] = None
    notes: str = ""


class StockBatchRequest(BaseModel):
    entity_type: str
    entity_id: str
    batch_number: str
    quantity: Decimal
    unit_cost: Decimal
    currency: str = "USD"
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""


class ConsumeBatchRequest(BaseModel):
    quantity: Decimal
    reference_type: str
    reference_id: str


class StockTransferRequest(BaseModel):
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    from_location: str
    to_location: str
    currency: str = "USD"
    reference_id: str = ""
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    notes: str = ""


@app.post("/api/inventory/movements", response_model=ApiResponse)
async def create_stock_movement(
    request: StockMovementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateStockMovementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateStockMovementCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            movement_type=request.movement_type,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            currency=request.currency,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            batch_number=request.batch_number,
            serial_numbers=request.serial_numbers,
            expiry_date=request.expiry_date,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء حركة المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating stock movement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/inventory/movements/purchase", response_model=ApiResponse)
async def create_purchase_movement(
    request: PurchaseMovementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreatePurchaseMovementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreatePurchaseMovementCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            purchase_order_id=request.purchase_order_id,
            currency=request.currency,
            batch_number=request.batch_number,
            serial_numbers=request.serial_numbers,
            expiry_date=request.expiry_date,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تسجيل حركة مشتريات بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating purchase movement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/inventory/movements/sale", response_model=ApiResponse)
async def create_sale_movement(
    request: SaleMovementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateSaleMovementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateSaleMovementCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            invoice_id=request.invoice_id,
            currency=request.currency,
            batch_number=request.batch_number,
            serial_numbers=request.serial_numbers,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تسجيل حركة مبيعات بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating sale movement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/inventory/movements/adjustment", response_model=ApiResponse)
async def create_adjustment_movement(
    request: AdjustmentMovementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateAdjustmentMovementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateAdjustmentMovementCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            old_quantity=request.old_quantity,
            new_quantity=request.new_quantity,
            unit_cost=request.unit_cost,
            reason=request.reason,
            currency=request.currency,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تسجيل حركة تسوية المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating adjustment movement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/inventory/{entity_type}/{entity_id}/quantity", response_model=ApiResponse)
async def get_stock_quantity(
    entity_type: str,
    entity_id: str,
    as_of_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import GetStockQuantityQuery
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetStockQuantityQuery(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of_date=as_of_date,
        )
        quantity = query_bus.dispatch(query)
        return ApiResponse(success=True, message="تم جلب كمية المخزون بنجاح",
                           data={'entity_type': entity_type, 'entity_id': entity_id, 'quantity': float(quantity)})
    except Exception as e:
        logger.error(f"Error getting stock quantity: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/inventory/{entity_type}/{entity_id}/movements", response_model=ApiResponse)
async def get_stock_movements(
    entity_type: str,
    entity_id: str,
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    movement_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import GetStockMovementsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetStockMovementsQuery(
            entity_type=entity_type,
            entity_id=entity_id,
            from_date=from_date,
            to_date=to_date,
            movement_type=movement_type,
            limit=limit,
            offset=offset,
        )
        movements = query_bus.dispatch(query) or []
        return ApiResponse(success=True, message="تم جلب حركات المخزون بنجاح",
                           data={'items': jsonable_encoder(movements), 'total': len(movements)})
    except Exception as e:
        logger.error(f"Error getting stock movements: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/inventory/{entity_type}/{entity_id}/valuation", response_model=ApiResponse)
async def get_stock_valuation(
    entity_type: str,
    entity_id: str,
    as_of_date: date = Query(...),
    method: str = Query("fifo"),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import GetStockValuationQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetStockValuationQuery(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of_date=as_of_date,
            method=method,
        )
        valuation = query_bus.dispatch(query)
        return ApiResponse(success=True, message="تم جلب تقييم المخزون بنجاح", data=jsonable_encoder(valuation))
    except Exception as e:
        logger.error(f"Error getting stock valuation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/inventory/low-stock", response_model=ApiResponse)
async def get_low_stock(
    threshold: int = Query(10, ge=0),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import GetLowStockQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetLowStockQuery(threshold=threshold, limit=limit, offset=offset)
        items = query_bus.dispatch(query) or []
        return ApiResponse(success=True, message="تم جلب المنتجات منخفضة المخزون بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error getting low stock: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/inventory/batches", response_model=ApiResponse)
async def create_stock_batch(
    request: StockBatchRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateStockBatchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateStockBatchCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            batch_number=request.batch_number,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            currency=request.currency,
            production_date=request.production_date,
            expiry_date=request.expiry_date,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء دفعة المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating stock batch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/inventory/batches/{batch_id}/consume", response_model=ApiResponse)
async def consume_stock_batch(
    batch_id: str,
    request: ConsumeBatchRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import ConsumeStockBatchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = ConsumeStockBatchCommand(
            batch_id=batch_id,
            quantity=request.quantity,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            consumed_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم استهلاك الدفعة بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error consuming stock batch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/inventory/transfers", response_model=ApiResponse)
async def create_stock_transfer(
    request: StockTransferRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateStockTransferCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateStockTransferCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            from_location=request.from_location,
            to_location=request.to_location,
            currency=request.currency,
            reference_id=request.reference_id,
            batch_number=request.batch_number,
            serial_numbers=request.serial_numbers,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء تحويل المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating stock transfer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/inventory/transfers/{transfer_id}/complete", response_model=ApiResponse)
async def complete_stock_transfer(
    transfer_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CompleteStockTransferCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CompleteStockTransferCommand(transfer_id=transfer_id, completed_by=current_user["username"])
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إكمال تحويل المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error completing stock transfer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 13. BASIC UNITS - الوحدات الأساسية
# (العملات، المواقع، مراكز التكلفة، الإعدادات، فروع العملاء)
# =============================================================================

# ---------- Currency ----------

class CreateCurrencyRequest(BaseModel):
    code: str
    name: str
    symbol: str = ""
    decimal_places: int = 2
    is_base: bool = False


class UpdateCurrencyRequest(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimal_places: Optional[int] = None
    is_active: Optional[bool] = None
    is_base: Optional[bool] = None
    version: int = 1


class SetExchangeRateRequest(BaseModel):
    to_currency_code: str
    rate: float


# ---------- Sites ----------

class CreateSiteRequest(BaseModel):
    code: str
    name: str
    site_type: str = "general"
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    notes: Optional[str] = None
    is_default: bool = False


class UpdateSiteRequest(BaseModel):
    name: Optional[str] = None
    site_type: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    version: int = 1


# ---------- Centers ----------

class CreateCenterRequest(BaseModel):
    code: str
    name: str
    center_type: str
    parent_code: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    department: Optional[str] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: str = "USD"
    description: Optional[str] = None


class UpdateCenterRequest(BaseModel):
    version: int
    name: Optional[str] = None
    center_type: Optional[str] = None
    parent_code: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    department: Optional[str] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class CreateAllocationRequest(BaseModel):
    source_center_code: str
    target_center_codes: List[str]
    amount: Decimal
    period_start: date
    period_end: date
    method: str = "equal"
    percentage: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    weights: Optional[Dict[str, Decimal]] = None
    description: Optional[str] = None


# ---------- Settings ----------

class UpdateUiSettingsRequest(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    font_size: Optional[int] = None
    font_family: Optional[str] = None
    animations_enabled: Optional[bool] = None
    animation_speed: Optional[int] = None
    sidebar_collapsed: Optional[bool] = None
    recent_items_count: Optional[int] = None
    confirm_before_close: Optional[bool] = None
    show_tooltips: Optional[bool] = None
    show_status_bar: Optional[bool] = None
    auto_save_interval: Optional[int] = None


class UpdateAllSettingsRequest(BaseModel):
    ui: Optional[Dict[str, Any]] = None
    invoicing: Optional[Dict[str, Any]] = None
    purchasing: Optional[Dict[str, Any]] = None
    products: Optional[Dict[str, Any]] = None
    customers: Optional[Dict[str, Any]] = None
    suppliers: Optional[Dict[str, Any]] = None
    users: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None
    printer: Optional[Dict[str, Any]] = None
    backup: Optional[Dict[str, Any]] = None


# ---------- Customer Branches ----------

class CreateBranchRequest(BaseModel):
    code: str
    name: str
    customer_name: str
    customer_code: str = ""
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    is_default: bool = False
    notes: Optional[str] = None
    working_hours: Optional[str] = None
    branch_type: str = "store"


class UpdateBranchRequest(BaseModel):
    version: int
    name: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = None
    working_hours: Optional[str] = None
    branch_type: Optional[str] = None
    status: Optional[str] = None


class SetDefaultBranchRequest(BaseModel):
    customer_id: str


# =============================================================================
# CURRENCY ENDPOINTS - نقاط نهاية العملات
# =============================================================================

@app.post("/api/currency", response_model=ApiResponse)
async def create_currency(
    request: CreateCurrencyRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import CreateCurrencyCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateCurrencyCommand(
            code=request.code,
            name=request.name,
            symbol=request.symbol,
            decimal_places=request.decimal_places,
            is_base=request.is_base,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء العملة بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating currency: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/currency", response_model=ApiResponse)
async def list_currencies(
    include_inactive: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import ListCurrenciesQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        items = query_bus.dispatch(ListCurrenciesQuery(
            include_inactive=include_inactive, limit=limit, offset=offset)) or []
        return ApiResponse(success=True, message="تم جلب العملات بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error listing currencies: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/currency/base", response_model=ApiResponse)
async def get_base_currency(current_user: dict = Depends(get_current_user)):
    try:
        from core.application.currency.commands import GetBaseCurrencyQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetBaseCurrencyQuery())
        return ApiResponse(success=True, message="تم جلب العملة الأساسية بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting base currency: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/currency/by-code/{code}", response_model=ApiResponse)
async def get_currency_by_code(
    code: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import GetCurrencyByCodeQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetCurrencyByCodeQuery(code=code))
        return ApiResponse(success=True, message="تم جلب العملة بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting currency by code: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/currency/exchange-rate", response_model=ApiResponse)
async def get_exchange_rate(
    from_currency_code: str = Query(...),
    to_currency_code: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import GetExchangeRateQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetExchangeRateQuery(
            from_currency_code=from_currency_code, to_currency_code=to_currency_code))
        return ApiResponse(success=True, message="تم جلب سعر الصرف بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting exchange rate: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/currency/{currency_id}", response_model=ApiResponse)
async def get_currency(
    currency_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import GetCurrencyQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetCurrencyQuery(currency_id=uuid.UUID(currency_id)))
        return ApiResponse(success=True, message="تم جلب العملة بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting currency: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/currency/{currency_id}", response_model=ApiResponse)
async def update_currency(
    currency_id: str,
    request: UpdateCurrencyRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import UpdateCurrencyCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateCurrencyCommand(
            currency_id=uuid.UUID(currency_id),
            name=request.name,
            symbol=request.symbol,
            decimal_places=request.decimal_places,
            is_active=request.is_active,
            is_base=request.is_base,
            version=request.version,
            updated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث العملة بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error updating currency: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/currency/{currency_id}", response_model=ApiResponse)
async def delete_currency(
    currency_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import DeleteCurrencyCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(DeleteCurrencyCommand(
            currency_id=uuid.UUID(currency_id), deleted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم حذف العملة بنجاح", data=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error deleting currency: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/currency/{currency_id}/base", response_model=ApiResponse)
async def set_base_currency(
    currency_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import SetBaseCurrencyCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(SetBaseCurrencyCommand(
            currency_id=uuid.UUID(currency_id), set_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تعيين العملة الأساسية بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error setting base currency: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/currency/{currency_id}/exchange-rate", response_model=ApiResponse)
async def set_exchange_rate(
    currency_id: str,
    request: SetExchangeRateRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.currency.commands import SetExchangeRateCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(SetExchangeRateCommand(
            from_currency_id=uuid.UUID(currency_id),
            to_currency_code=request.to_currency_code,
            rate=request.rate,
            updated_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم تعيين سعر الصرف بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error setting exchange rate: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# SITES ENDPOINTS - نقاط نهاية المواقع
# =============================================================================

@app.post("/api/sites", response_model=ApiResponse)
async def create_site(
    request: CreateSiteRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import CreateSiteCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateSiteCommand(
            code=request.code,
            name=request.name,
            site_type=request.site_type,
            street=request.street,
            city=request.city,
            country=request.country,
            phone=request.phone,
            mobile=request.mobile,
            email=request.email,
            contact_person=request.contact_person,
            notes=request.notes,
            is_default=request.is_default,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء الموقع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating site: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/sites", response_model=ApiResponse)
async def list_sites(
    site_type: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import ListSitesQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        items = query_bus.dispatch(ListSitesQuery(
            site_type=site_type, include_inactive=include_inactive, limit=limit, offset=offset)) or []
        return ApiResponse(success=True, message="تم جلب المواقع بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error listing sites: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/sites/default", response_model=ApiResponse)
async def get_default_site(current_user: dict = Depends(get_current_user)):
    try:
        from core.application.sites.commands import GetDefaultSiteQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetDefaultSiteQuery())
        return ApiResponse(success=True, message="تم جلب الموقع الافتراضي بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting default site: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/sites/search", response_model=ApiResponse)
async def search_sites(
    q: str = Query(...),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import SearchSitesQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        items = query_bus.dispatch(SearchSitesQuery(search_text=q, limit=limit, offset=offset)) or []
        return ApiResponse(success=True, message="تم البحث عن المواقع بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error searching sites: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/sites/combo", response_model=ApiResponse)
async def get_sites_for_combo(
    include_inactive: bool = Query(False),
    limit: int = Query(1000, ge=1, le=5000),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import GetSitesForComboQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        items = query_bus.dispatch(GetSitesForComboQuery(
            include_inactive=include_inactive, limit=limit)) or []
        return ApiResponse(success=True, message="تم جلب المواقع للقوائم بنجاح", data=jsonable_encoder(items))
    except Exception as e:
        logger.error(f"Error getting sites for combo: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/sites/{site_id}/statistics", response_model=ApiResponse)
async def get_site_statistics(
    site_id: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import GetSiteStatisticsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        stats = query_bus.dispatch(GetSiteStatisticsQuery(
            site_id=uuid.UUID(site_id), from_date=from_date, to_date=to_date))
        return ApiResponse(success=True, message="تم جلب إحصائيات الموقع بنجاح", data=jsonable_encoder(stats))
    except Exception as e:
        logger.error(f"Error getting site statistics: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/sites/{site_id}", response_model=ApiResponse)
async def get_site(
    site_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import GetSiteQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetSiteQuery(site_id=uuid.UUID(site_id)))
        return ApiResponse(success=True, message="تم جلب الموقع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting site: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/sites/{site_id}", response_model=ApiResponse)
async def update_site(
    site_id: str,
    request: UpdateSiteRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import UpdateSiteCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateSiteCommand(
            site_id=uuid.UUID(site_id),
            name=request.name,
            site_type=request.site_type,
            street=request.street,
            city=request.city,
            country=request.country,
            phone=request.phone,
            mobile=request.mobile,
            email=request.email,
            contact_person=request.contact_person,
            notes=request.notes,
            is_active=request.is_active,
            version=request.version,
            updated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث الموقع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error updating site: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/sites/{site_id}", response_model=ApiResponse)
async def delete_site(
    site_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import DeleteSiteCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(DeleteSiteCommand(
            site_id=uuid.UUID(site_id), deleted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم حذف الموقع بنجاح", data=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error deleting site: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/sites/{site_id}/default", response_model=ApiResponse)
async def set_default_site(
    site_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.sites.commands import SetDefaultSiteCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(SetDefaultSiteCommand(
            site_id=uuid.UUID(site_id), set_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تعيين الموقع الافتراضي بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error setting default site: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# CENTERS ENDPOINTS - نقاط نهاية مراكز التكلفة
# =============================================================================

@app.post("/api/centers", response_model=ApiResponse)
async def create_center(
    request: CreateCenterRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import CreateCenterCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateCenterCommand(
            code=request.code,
            name=request.name,
            center_type=request.center_type,
            parent_code=request.parent_code,
            manager_id=request.manager_id,
            manager_name=request.manager_name,
            department=request.department,
            budget_amount=request.budget_amount,
            budget_currency=request.budget_currency,
            description=request.description,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء المركز بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating center: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/centers", response_model=ApiResponse)
async def list_centers(
    center_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    parent_code: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import ListCentersQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        items = query_bus.dispatch(ListCentersQuery(
            center_type=center_type, status=status, parent_code=parent_code,
            include_inactive=include_inactive, limit=limit, offset=offset)) or []
        return ApiResponse(success=True, message="تم جلب المراكز بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error listing centers: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/centers/tree", response_model=ApiResponse)
async def get_center_tree(
    root_code: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import GetCenterTreeQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        tree = query_bus.dispatch(GetCenterTreeQuery(root_code=root_code)) or []
        return ApiResponse(success=True, message="تم جلب شجرة المراكز بنجاح", data=jsonable_encoder(tree))
    except Exception as e:
        logger.error(f"Error getting center tree: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/centers/{center_code}/summary", response_model=ApiResponse)
async def get_center_summary(
    center_code: str,
    from_date: date = Query(...),
    to_date: date = Query(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import GetCenterSummaryQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        summary = query_bus.dispatch(GetCenterSummaryQuery(
            center_code=center_code, from_date=from_date, to_date=to_date))
        return ApiResponse(success=True, message="تم جلب ملخص المركز بنجاح", data=jsonable_encoder(summary))
    except Exception as e:
        logger.error(f"Error getting center summary: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/centers/{center_id}", response_model=ApiResponse)
async def get_center(
    center_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import GetCenterQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetCenterQuery(center_id=center_id))
        return ApiResponse(success=True, message="تم جلب المركز بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting center: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/centers/{center_id}", response_model=ApiResponse)
async def update_center(
    center_id: str,
    request: UpdateCenterRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import UpdateCenterCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateCenterCommand(
            center_id=center_id,
            version=request.version,
            name=request.name,
            center_type=request.center_type,
            parent_code=request.parent_code,
            manager_id=request.manager_id,
            manager_name=request.manager_name,
            department=request.department,
            budget_amount=request.budget_amount,
            budget_currency=request.budget_currency,
            description=request.description,
            notes=request.notes,
            tags=request.tags,
            updated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث المركز بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error updating center: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/centers/{center_id}", response_model=ApiResponse)
async def delete_center(
    center_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import DeleteCenterCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(DeleteCenterCommand(
            center_id=center_id, deleted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم حذف المركز بنجاح", data=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error deleting center: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/centers/{center_id}/activate", response_model=ApiResponse)
async def activate_center(
    center_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import ActivateCenterCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ActivateCenterCommand(
            center_id=center_id, activated_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تفعيل المركز بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error activating center: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/centers/{center_id}/suspend", response_model=ApiResponse)
async def suspend_center(
    center_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import SuspendCenterCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(SuspendCenterCommand(
            center_id=center_id, suspended_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تعليق المركز بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error suspending center: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/centers/{center_id}/close", response_model=ApiResponse)
async def close_center(
    center_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import CloseCenterCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(CloseCenterCommand(
            center_id=center_id, closed_by=current_user["username"]))
        return ApiResponse(success=True, message="تم إغلاق المركز بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error closing center: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/centers/allocations", response_model=ApiResponse)
async def create_allocation(
    request: CreateAllocationRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import CreateAllocationCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateAllocationCommand(
            source_center_code=request.source_center_code,
            target_center_codes=request.target_center_codes,
            amount=request.amount,
            period_start=request.period_start,
            period_end=request.period_end,
            method=request.method,
            percentage=request.percentage,
            fixed_amount=request.fixed_amount,
            weights=request.weights,
            description=request.description,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء التوزيع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating allocation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/centers/allocations/{allocation_id}/post", response_model=ApiResponse)
async def post_allocation(
    allocation_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.centers.commands import PostAllocationCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(PostAllocationCommand(
            allocation_id=allocation_id, posted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم ترحيل التوزيع بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error posting allocation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# SETTINGS ENDPOINTS - نقاط نهاية الإعدادات
# =============================================================================

@app.get("/api/settings", response_model=ApiResponse)
async def get_settings(current_user: dict = Depends(get_current_user)):
    try:
        from core.application.settings.commands import GetSettingsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetSettingsQuery())
        return ApiResponse(success=True, message="تم جلب الإعدادات بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting settings: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/settings/ui", response_model=ApiResponse)
async def get_ui_settings(current_user: dict = Depends(get_current_user)):
    try:
        from core.application.settings.commands import GetUiSettingsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetUiSettingsQuery())
        return ApiResponse(success=True, message="تم جلب إعدادات الواجهة بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting UI settings: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/settings/ui", response_model=ApiResponse)
async def update_ui_settings(
    request: UpdateUiSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.settings.commands import UpdateUiSettingsCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateUiSettingsCommand(
            theme=request.theme,
            language=request.language,
            font_size=request.font_size,
            font_family=request.font_family,
            animations_enabled=request.animations_enabled,
            animation_speed=request.animation_speed,
            sidebar_collapsed=request.sidebar_collapsed,
            recent_items_count=request.recent_items_count,
            confirm_before_close=request.confirm_before_close,
            show_tooltips=request.show_tooltips,
            show_status_bar=request.show_status_bar,
            auto_save_interval=request.auto_save_interval,
            updated_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث إعدادات الواجهة بنجاح", data=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error updating UI settings: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/settings", response_model=ApiResponse)
async def update_all_settings(
    request: UpdateAllSettingsRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.settings.commands import UpdateAllSettingsCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateAllSettingsCommand(
            ui=request.ui,
            invoicing=request.invoicing,
            purchasing=request.purchasing,
            products=request.products,
            customers=request.customers,
            suppliers=request.suppliers,
            users=request.users,
            notifications=request.notifications,
            printer=request.printer,
            backup=request.backup,
            updated_by=current_user["username"],
        )
        result = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث الإعدادات بنجاح", data=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error updating all settings: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# CUSTOMER BRANCHES ENDPOINTS - نقاط نهاية فروع العملاء
# =============================================================================

@app.post("/api/customers/{customer_id}/branches", response_model=ApiResponse)
async def create_customer_branch(
    customer_id: str,
    request: CreateBranchRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.commands import CreateBranchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateBranchCommand(
            code=request.code,
            name=request.name,
            customer_id=customer_id,
            customer_name=request.customer_name,
            customer_code=request.customer_code,
            street=request.street,
            city=request.city,
            country=request.country,
            postal_code=request.postal_code,
            email=request.email,
            phone=request.phone,
            mobile=request.mobile,
            contact_person=request.contact_person,
            latitude=request.latitude,
            longitude=request.longitude,
            tax_number=request.tax_number,
            is_default=request.is_default,
            notes=request.notes,
            working_hours=request.working_hours,
            branch_type=request.branch_type,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء فرع العميل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating customer branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/branches", response_model=ApiResponse)
async def list_branches(
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.queries import ListBranchesQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        result = query_bus.dispatch(ListBranchesQuery(
            customer_id=customer_id, status=status,
            include_deleted=include_deleted, limit=limit, offset=offset))
        data = jsonable_encoder(result)
        if isinstance(data, dict):
            items = data.get('items') or []
        else:
            items = data
        return ApiResponse(success=True, message="تم جلب فروع العملاء بنجاح",
                           data={'items': items, 'total': len(items) if isinstance(items, list) else None})
    except Exception as e:
        logger.error(f"Error listing branches: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/branches/search", response_model=ApiResponse)
async def search_branches(
    q: str = Query(...),
    customer_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.queries import SearchBranchesQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        items = query_bus.dispatch(SearchBranchesQuery(
            search_text=q, customer_id=customer_id, limit=limit, offset=offset)) or []
        return ApiResponse(success=True, message="تم البحث عن فروع العملاء بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error searching branches: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/branches/by-code/{code}", response_model=ApiResponse)
async def get_branch_by_code(
    code: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.queries import GetBranchByCodeQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetBranchByCodeQuery(code=code))
        return ApiResponse(success=True, message="تم جلب فرع العميل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting branch by code: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/branches/default", response_model=ApiResponse)
async def get_default_branch(
    customer_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.queries import GetDefaultBranchQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetDefaultBranchQuery(customer_id=customer_id))
        return ApiResponse(success=True, message="تم جلب الفرع الافتراضي بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting default branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/branches/{branch_id}", response_model=ApiResponse)
async def get_branch(
    branch_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.queries import GetBranchQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        dto = query_bus.dispatch(GetBranchQuery(branch_id=branch_id))
        return ApiResponse(success=True, message="تم جلب فرع العميل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error getting branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/branches/{branch_id}", response_model=ApiResponse)
async def update_branch(
    branch_id: str,
    request: UpdateBranchRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.commands import UpdateBranchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = UpdateBranchCommand(
            branch_id=branch_id,
            version=request.version,
            name=request.name,
            street=request.street,
            city=request.city,
            country=request.country,
            postal_code=request.postal_code,
            email=request.email,
            phone=request.phone,
            mobile=request.mobile,
            contact_person=request.contact_person,
            latitude=request.latitude,
            longitude=request.longitude,
            tax_number=request.tax_number,
            is_default=request.is_default,
            notes=request.notes,
            working_hours=request.working_hours,
            branch_type=request.branch_type,
            status=request.status,
            updated_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تحديث فرع العميل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error updating branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/branches/{branch_id}", response_model=ApiResponse)
async def delete_branch(
    branch_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.commands import DeleteBranchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        result = command_bus.dispatch(DeleteBranchCommand(
            branch_id=branch_id, deleted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم حذف فرع العميل بنجاح", data=jsonable_encoder(result))
    except Exception as e:
        logger.error(f"Error deleting branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/branches/{branch_id}/activate", response_model=ApiResponse)
async def activate_branch(
    branch_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.commands import ActivateBranchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ActivateBranchCommand(
            branch_id=branch_id, activated_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تفعيل فرع العميل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error activating branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/branches/{branch_id}/deactivate", response_model=ApiResponse)
async def deactivate_branch(
    branch_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.commands import DeactivateBranchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(DeactivateBranchCommand(
            branch_id=branch_id, deactivated_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تعطيل فرع العميل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error deactivating branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/branches/{branch_id}/default", response_model=ApiResponse)
async def set_default_branch(
    branch_id: str,
    request: SetDefaultBranchRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.customer_branch.commands import SetDefaultBranchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(SetDefaultBranchCommand(
            branch_id=branch_id, customer_id=request.customer_id, set_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تعيين الفرع الافتراضي بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error setting default branch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# FIXED ASSETS ENDPOINTS - نقاط نهاية الأصول الثابتة
# =============================================================================


class CreateFixedAssetRequest(BaseModel):
    code: str
    name: str
    acquisition_cost: Decimal
    acquisition_date: date
    asset_type: str = "other"
    useful_life_years: int = 5
    salvage_value: Decimal = Decimal('0')
    depreciation_method: str = "straight_line"
    currency: str = "USD"
    category: Optional[str] = None
    location: Optional[str] = None
    responsible_person: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    notes: Optional[str] = None


class PostDepreciationRequest(BaseModel):
    period: int


class DisposeFixedAssetRequest(BaseModel):
    disposal_date: date
    disposal_method: str = "sale"
    sale_amount: Optional[Decimal] = None
    scrap_value: Optional[Decimal] = None
    reason: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None


class RunMonthlyDepreciationRequest(BaseModel):
    as_of_date: Optional[date] = None


@app.post("/api/assets", response_model=ApiResponse)
async def create_fixed_asset(
    request: CreateFixedAssetRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.commands import CreateFixedAssetCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateFixedAssetCommand(
            code=request.code,
            name=request.name,
            acquisition_cost=request.acquisition_cost,
            acquisition_date=request.acquisition_date,
            asset_type=request.asset_type,
            useful_life_years=request.useful_life_years,
            salvage_value=request.salvage_value,
            depreciation_method=request.depreciation_method,
            currency=request.currency,
            category=request.category,
            location=request.location,
            responsible_person=request.responsible_person,
            supplier_id=request.supplier_id,
            supplier_name=request.supplier_name,
            serial_number=request.serial_number,
            barcode=request.barcode,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء الأصل الثابت بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating fixed asset: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/assets", response_model=ApiResponse)
async def list_fixed_assets(
    asset_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.queries import ListFixedAssetsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(ListFixedAssetsQuery(
            asset_type=asset_type, status=status,
            include_inactive=include_inactive, limit=limit, offset=offset))
        return ApiResponse(success=True, message="تم جلب الأصول الثابتة بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error listing fixed assets: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/assets/{asset_id}", response_model=ApiResponse)
async def get_fixed_asset(
    asset_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.queries import GetFixedAssetQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetFixedAssetQuery(asset_id=asset_id))
        if data is None:
            return ApiResponse(success=False, message="الأصل الثابت غير موجود", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب الأصل الثابت بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting fixed asset: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/assets/run-depreciation", response_model=ApiResponse)
async def run_monthly_depreciation(
    request: RunMonthlyDepreciationRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.commands import RunMonthlyDepreciationCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        data = command_bus.dispatch(RunMonthlyDepreciationCommand(
            as_of_date=request.as_of_date, posted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تشغيل الإهلاك الشهري بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error running monthly depreciation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/assets/{asset_id}/depreciation", response_model=ApiResponse)
async def post_depreciation(
    asset_id: str,
    request: PostDepreciationRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.commands import PostDepreciationCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(PostDepreciationCommand(
            asset_id=asset_id, period=request.period, posted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم ترحيل الإهلاك بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error posting depreciation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/assets/{asset_id}/dispose", response_model=ApiResponse)
async def dispose_fixed_asset(
    asset_id: str,
    request: DisposeFixedAssetRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.fixed_assets.commands import DisposeFixedAssetCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(DisposeFixedAssetCommand(
            asset_id=asset_id,
            disposal_date=request.disposal_date,
            disposal_method=request.disposal_method,
            sale_amount=request.sale_amount,
            scrap_value=request.scrap_value,
            reason=request.reason,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            disposed_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم التصرف في الأصل الثابت بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error disposing fixed asset: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# WORKFLOW ENDPOINTS - نقاط نهاية سير العمل والموافقات
# =============================================================================


class WorkflowStepRequest(BaseModel):
    name: str
    order: int = 0
    role: str = ""
    required_approvals: int = 1
    requires_all: bool = False
    is_final: bool = False
    timeout_hours: Optional[int] = None
    escalation_role: Optional[str] = None
    description: Optional[str] = None


class CreateWorkflowRequest(BaseModel):
    name: str
    code: str
    entity_type: str
    steps: List[WorkflowStepRequest]
    description: Optional[str] = None
    is_mandatory: bool = False
    auto_approve_threshold: Optional[Decimal] = None
    auto_approve_after_days: Optional[int] = None


class UpdateWorkflowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_mandatory: Optional[bool] = None
    auto_approve_threshold: Optional[Decimal] = None
    auto_approve_after_days: Optional[int] = None


class CreateApprovalRequestRequest(BaseModel):
    entity_type: str
    entity_id: str
    title: str
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "USD"
    priority: str = "normal"
    due_date: Optional[datetime] = None
    entity_data: Optional[Dict[str, Any]] = None


class ApproveRequestRequest(BaseModel):
    approver_id: str
    approver_name: str = ""
    comment: Optional[str] = None


class RejectRequestRequest(BaseModel):
    approver_id: str
    approver_name: str = ""
    reason: str = ""


class ActionRequestRequest(BaseModel):
    reason: Optional[str] = None


class ReassignRequestRequest(BaseModel):
    new_approver_id: str
    new_approver_name: Optional[str] = None
    reason: Optional[str] = None


class BatchRequestsRequest(BaseModel):
    request_ids: List[str]
    comment: Optional[str] = None
    reason: Optional[str] = None


@app.post("/api/workflows", response_model=ApiResponse)
async def create_workflow(
    request: CreateWorkflowRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import CreateWorkflowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(CreateWorkflowCommand(
            name=request.name,
            code=request.code,
            entity_type=request.entity_type,
            steps=[s.model_dump() for s in request.steps],
            description=request.description,
            is_mandatory=request.is_mandatory,
            auto_approve_threshold=request.auto_approve_threshold,
            auto_approve_after_days=request.auto_approve_after_days,
            created_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم إنشاء سير العمل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/workflows", response_model=ApiResponse)
async def list_workflows(
    entity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ListWorkflowsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(ListWorkflowsQuery(
            entity_type=entity_type, status=status, limit=limit, offset=offset))
        return ApiResponse(success=True, message="تم جلب سير العمل بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error listing workflows: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/workflows/by-entity/{entity_type}", response_model=ApiResponse)
async def get_workflow_by_entity(
    entity_type: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import GetWorkflowByEntityQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetWorkflowByEntityQuery(entity_type=entity_type))
        if data is None:
            return ApiResponse(success=False, message="لا يوجد سير عمل لهذا الكيان", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب سير العمل بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting workflow by entity: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/workflows/{workflow_id}", response_model=ApiResponse)
async def get_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import GetWorkflowQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetWorkflowQuery(workflow_id=workflow_id))
        if data is None:
            return ApiResponse(success=False, message="سير العمل غير موجود", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب سير العمل بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/workflows/{workflow_id}", response_model=ApiResponse)
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import UpdateWorkflowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(UpdateWorkflowCommand(
            workflow_id=workflow_id,
            name=request.name,
            description=request.description,
            is_mandatory=request.is_mandatory,
            auto_approve_threshold=request.auto_approve_threshold,
            auto_approve_after_days=request.auto_approve_after_days,
            updated_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم تحديث سير العمل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error updating workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/workflows/{workflow_id}/activate", response_model=ApiResponse)
async def activate_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ActivateWorkflowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ActivateWorkflowCommand(
            workflow_id=workflow_id, activated_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تفعيل سير العمل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error activating workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/workflows/{workflow_id}/deactivate", response_model=ApiResponse)
async def deactivate_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import DeactivateWorkflowCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(DeactivateWorkflowCommand(
            workflow_id=workflow_id, deactivated_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تعطيل سير العمل بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error deactivating workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/workflows/{workflow_id}", response_model=ApiResponse)
async def delete_workflow(
    workflow_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import DeleteWorkflowCommand
        command_bus = bootstrap.container.resolve("command_bus")
        data = command_bus.dispatch(DeleteWorkflowCommand(
            workflow_id=workflow_id, deleted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم حذف سير العمل بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error deleting workflow: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests", response_model=ApiResponse)
async def create_approval_request(
    request: CreateApprovalRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import CreateApprovalRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(CreateApprovalRequestCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            title=request.title,
            description=request.description,
            amount=request.amount,
            currency=request.currency,
            priority=request.priority,
            due_date=request.due_date,
            entity_data=request.entity_data,
            created_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تم إنشاء طلب الموافقة بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating approval request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/approval-requests/pending", response_model=ApiResponse)
async def list_pending_requests(
    entity_type: Optional[str] = Query(None),
    approver_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ListPendingRequestsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(ListPendingRequestsQuery(
            entity_type=entity_type, approver_id=approver_id, limit=limit, offset=offset))
        return ApiResponse(success=True, message="تم جلب الطلبات المعلقة بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error listing pending requests: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/approval-requests/statistics", response_model=ApiResponse)
async def get_request_statistics(
    entity_type: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import GetRequestStatisticsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetRequestStatisticsQuery(entity_type=entity_type))
        return ApiResponse(success=True, message="تم جلب إحصائيات الطلبات بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting request statistics: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests/batch-approve", response_model=ApiResponse)
async def batch_approve_requests(
    request: BatchRequestsRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import BatchApproveRequestsCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        data = command_bus.dispatch(BatchApproveRequestsCommand(
            request_ids=request.request_ids, comment=request.comment, approved_by=current_user["username"]))
        return ApiResponse(success=True, message="تمت الموافقة الجماعية بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error batch approving requests: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests/batch-reject", response_model=ApiResponse)
async def batch_reject_requests(
    request: BatchRequestsRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import BatchRejectRequestsCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        data = command_bus.dispatch(BatchRejectRequestsCommand(
            request_ids=request.request_ids, reason=request.reason or "", rejected_by=current_user["username"]))
        return ApiResponse(success=True, message="تم الرفض الجماعي بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error batch rejecting requests: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/approval-requests/{request_id}", response_model=ApiResponse)
async def get_approval_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import GetRequestQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        data = query_bus.dispatch(GetRequestQuery(request_id=request_id))
        if data is None:
            return ApiResponse(success=False, message="طلب الموافقة غير موجود", errors=["not_found"])
        return ApiResponse(success=True, message="تم جلب طلب الموافقة بنجاح", data=jsonable_encoder(data))
    except Exception as e:
        logger.error(f"Error getting approval request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests/{request_id}/submit", response_model=ApiResponse)
async def submit_request(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import SubmitRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(SubmitRequestCommand(
            request_id=request_id, submitted_by=current_user["username"]))
        return ApiResponse(success=True, message="تم تقديم الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error submitting request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests/{request_id}/approve", response_model=ApiResponse)
async def approve_request(
    request_id: str,
    request: ApproveRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ApproveRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ApproveRequestCommand(
            request_id=request_id,
            approver_id=request.approver_id or current_user["username"],
            approver_name=request.approver_name,
            comment=request.comment,
        ))
        return ApiResponse(success=True, message="تمت الموافقة على الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error approving request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests/{request_id}/reject", response_model=ApiResponse)
async def reject_request(
    request_id: str,
    request: RejectRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import RejectRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(RejectRequestCommand(
            request_id=request_id,
            approver_id=request.approver_id or current_user["username"],
            approver_name=request.approver_name,
            reason=request.reason,
        ))
        return ApiResponse(success=True, message="تم رفض الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error rejecting request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests/{request_id}/cancel", response_model=ApiResponse)
async def cancel_request(
    request_id: str,
    request: ActionRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import CancelRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(CancelRequestCommand(
            request_id=request_id, cancelled_by=current_user["username"], reason=request.reason))
        return ApiResponse(success=True, message="تم إلغاء الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error cancelling request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests/{request_id}/escalate", response_model=ApiResponse)
async def escalate_request(
    request_id: str,
    request: ActionRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import EscalateRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(EscalateRequestCommand(
            request_id=request_id, escalated_by=current_user["username"], reason=request.reason))
        return ApiResponse(success=True, message="تم تصعيد الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error escalating request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/approval-requests/{request_id}/reassign", response_model=ApiResponse)
async def reassign_request(
    request_id: str,
    request: ReassignRequestRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.workflow.commands import ReassignRequestCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        dto = command_bus.dispatch(ReassignRequestCommand(
            request_id=request_id,
            new_approver_id=request.new_approver_id,
            new_approver_name=request.new_approver_name,
            reason=request.reason,
            reassigned_by=current_user["username"],
        ))
        return ApiResponse(success=True, message="تمت إعادة تعيين الطلب بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error reassigning request: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# MISSING CRUD ENDPOINTS - PUT/DELETE
# =============================================================================

@app.get("/api/auth/users", response_model=ApiResponse)
async def list_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text as sa_text
            rows = uow.session.execute(sa_text(
                "SELECT u.id::text, u.username, u.email, u.full_name, u.is_active, "
                "r.name AS role, r.display_name AS role_display "
                "FROM users u "
                "LEFT JOIN LATERAL (SELECT r2.name, r2.display_name FROM user_roles ur "
                "  JOIN roles r2 ON r2.id = ur.role_id WHERE ur.user_id = u.id ORDER BY r2.name LIMIT 1) r ON TRUE "
                "ORDER BY u.username LIMIT :lim OFFSET :off"
            ), {"lim": limit, "off": offset}).mappings().all()

            count = uow.session.execute(sa_text("SELECT COUNT(*) FROM users")).scalar() or 0
            result = []
            for r in rows:
                names = (r["full_name"] or "").strip().split(" ", 1)
                role = r["role"] or "user"
                result.append({
                    'id': r["id"],
                    'username': r["username"],
                    'email': r["email"] or "",
                    'first_name': names[0] if names else "",
                    'last_name': names[1] if len(names) > 1 else "",
                    'role': role,
                    'role_name': r["role_display"] or _ROLE_DISPLAY.get(role, role),
                    'is_active': r["is_active"],
                })
            return ApiResponse(success=True, message="تم جلب المستخدمين بنجاح",
                               data={'items': result, 'total': count})
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/auth/users", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_user(request: dict, current_user: dict = Depends(get_current_user), rate_limit: None = Depends(rate_limiter(100, 60))):
    try:
        data = filter_fields(request, [
            "username", "email", "first_name", "last_name", "password", "role", "is_active",
        ])
        if not data.get("username"):
            raise HTTPException(status_code=400, detail="username مطلوب")
        if not data.get("password") or len(data["password"]) < 6:
            raise HTTPException(status_code=400, detail="كلمة المرور يجب أن تكون 6 أحرف على الأقل")
        with bootstrap.uow() as uow:
            user_repo = uow.users
            from core.domain.auth.entities import User
            from core.domain.auth.value_objects import UserId
            existing = user_repo.get_by_username(data['username'])
            if existing:
                raise HTTPException(status_code=409, detail="اسم المستخدم موجود مسبقاً")
            new_user = User(
                id=UserId.generate(),
                username=data['username'],
                email=data.get('email', ''),
                full_name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                password_hash=get_password_hash(data.get('password', '')),
                is_active=bool(data.get('is_active', True)),
                is_super_admin=False,
                created_by=current_user["username"],
                updated_by=current_user["username"],
            )
            user_repo.save(new_user)
            uow.commit()
            # تعيين الدور إذا تم إرساله
            role = data.get('role')
            if role:
                try:
                    from sqlalchemy import text as sa_text
                    allowed_roles = ["admin", "accountant", "auditor", "financial_analyst", "user"]
                    if role not in allowed_roles:
                        role = "user"
                    role_row = uow.session.execute(sa_text(
                        "SELECT id FROM roles WHERE name = :name AND is_active = TRUE"
                    ), {"name": role}).first()
                    if role_row:
                        uow.session.execute(sa_text(
                            "INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid) ON CONFLICT DO NOTHING"
                        ), {"uid": str(new_user.id.value), "rid": str(role_row[0])})
                        uow.commit()
                except Exception as role_e:
                    logger.error(f"Error assigning role to user {data.get('username')}: {role_e}")
            return ApiResponse(success=True, message="تم إنشاء المستخدم بنجاح",
                               data={'id': str(new_user.id.value), 'username': new_user.username})
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/auth/users/{user_id}", response_model=ApiResponse)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text as sa_text
            row = uow.session.execute(sa_text(
                "SELECT u.id::text, u.username, u.email, u.full_name, u.is_active, "
                "r.name AS role, r.display_name AS role_display "
                "FROM users u "
                "LEFT JOIN LATERAL (SELECT r2.name, r2.display_name FROM user_roles ur "
                "  JOIN roles r2 ON r2.id = ur.role_id WHERE ur.user_id = u.id ORDER BY r2.name LIMIT 1) r ON TRUE "
                "WHERE u.id::text = :uid"
            ), {"uid": user_id}).mappings().first()
            if not row:
                return ApiResponse(success=False, message="المستخدم غير موجود")
            names = (row["full_name"] or "").strip().split(" ", 1)
            role = row["role"] or "user"
            data = {
                'id': row["id"],
                'username': row["username"],
                'email': row["email"] or "",
                'first_name': names[0] if names else "",
                'last_name': names[1] if len(names) > 1 else "",
                'role': role,
                'role_name': row["role_display"] or _ROLE_DISPLAY.get(role, role),
                'is_active': row["is_active"],
            }
            return ApiResponse(success=True, message="تم جلب المستخدم بنجاح", data=data)
    except Exception as e:
        logger.error(f"Error getting user: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/auth/users/{user_id}", response_model=ApiResponse)
async def update_user(user_id: str, request: dict, current_user: dict = Depends(get_current_user), rate_limit: None = Depends(rate_limiter(100, 60))):
    try:
        data = filter_fields(request, [
            "username", "email", "first_name", "last_name", "password", "role", "is_active",
        ])
        with bootstrap.uow() as uow:
            user_repo = uow.users
            from core.domain.auth.value_objects import UserId as _UserId
            user = user_repo.get_by_id(_UserId.from_string(user_id))
            if not user:
                return ApiResponse(success=False, message="المستخدم غير موجود")
            uid = user.id.value if hasattr(user.id, 'value') else str(user.id)
            if 'username' in data:
                user.username = data['username']
            if 'email' in data:
                user.email = data['email']
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'is_active' in data:
                user.is_active = bool(data['is_active'])
            if 'password' in data and data['password']:
                user.password_hash = get_password_hash(data['password'])
            user.updated_by = current_user["username"]
            user_repo.save(user)
            # تحديث الدور إذا تم إرساله
            if 'role' in data and data['role']:
                from sqlalchemy import text as sa_text
                role_row = uow.session.execute(sa_text(
                    "SELECT id FROM roles WHERE name = :name AND is_active = TRUE"
                ), {"name": data['role']}).first()
                if role_row:
                    uow.session.execute(sa_text(
                        "DELETE FROM user_roles WHERE user_id = :uid"
                    ), {"uid": uid})
                    uow.session.execute(sa_text(
                        "INSERT INTO user_roles (user_id, role_id) VALUES (:uid, :rid) ON CONFLICT DO NOTHING"
                    ), {"uid": uid, "rid": str(role_row[0])})
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث المستخدم بنجاح")
    except Exception as e:
        logger.error(f"Error updating user: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/auth/users/{user_id}", response_model=ApiResponse)
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user), rate_limit: None = Depends(rate_limiter(100, 60))):
    try:
        with bootstrap.uow() as uow:
            user_repo = uow.users
            from core.domain.auth.value_objects import UserId as _UserId
            user = user_repo.get_by_id(_UserId.from_string(user_id))
            if not user:
                return ApiResponse(success=False, message="المستخدم غير موجود")
            user_repo.delete(_UserId.from_string(user_id))
            uow.commit()
            return ApiResponse(success=True, message="تم حذف المستخدم بنجاح")
    except Exception as e:
        logger.error(f"Error deleting user: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/customers/{customer_id}", response_model=ApiResponse)
async def update_customer(customer_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    try:
        data = filter_fields(request, [
            "name", "email", "phone", "status",
        ])
        with bootstrap.uow() as uow:
            repo = uow.customers
            customer = repo.get_by_id(customer_id)
            if not customer:
                return ApiResponse(success=False, message="العميل غير موجود")
            if 'name' in data:
                customer.name = data['name']
            if 'email' in data or 'phone' in data:
                from core.domain.customers.value_objects import ContactInfo
                customer.contact_info = ContactInfo(
                    email=data.get('email', customer.contact_info.email),
                    phone=data.get('phone', customer.contact_info.phone),
                    mobile=customer.contact_info.mobile,
                )
            if 'status' in data:
                from core.domain.shared.value_objects import DomainStatus
                customer.status = DomainStatus(data['status'])
            customer.updated_by = current_user["username"]
            repo.save(customer)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث العميل بنجاح")
    except Exception as e:
        logger.error(f"Error updating customer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/customers/{customer_id}", response_model=ApiResponse)
async def delete_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            repo = uow.customers
            customer = repo.get_by_id(customer_id)
            if not customer:
                return ApiResponse(success=False, message="العميل غير موجود")
            repo.delete(customer_id)
            uow.commit()
            return ApiResponse(success=True, message="تم حذف العميل بنجاح")
    except Exception as e:
        logger.error(f"Error deleting customer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/customers/{customer_id}/status", response_model=ApiResponse)
async def change_customer_status(customer_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    try:
        data = filter_fields(request, ["status"])
        with bootstrap.uow() as uow:
            repo = uow.customers
            customer = repo.get_by_id(customer_id)
            if not customer:
                return ApiResponse(success=False, message="العميل غير موجود")
            from core.domain.shared.value_objects import DomainStatus
            customer.status = DomainStatus(data.get('status', 'active'))
            customer.updated_by = current_user["username"]
            repo.save(customer)
            uow.commit()
            return ApiResponse(success=True, message="تم تغيير حالة العميل بنجاح")
    except Exception as e:
        logger.error(f"Error changing customer status: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/suppliers/{supplier_id}", response_model=ApiResponse)
async def update_supplier(supplier_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    try:
        data = filter_fields(request, [
            "name", "email", "phone",
        ])
        with bootstrap.uow() as uow:
            repo = uow.suppliers
            supplier = repo.get_by_id(supplier_id) if hasattr(repo, 'get_by_id') else None
            if not supplier:
                return ApiResponse(success=False, message="المورد غير موجود")
            if 'name' in data:
                supplier.name = data['name']
            if 'email' in data or 'phone' in data:
                from core.domain.suppliers.value_objects import ContactInfo
                supplier.contact_info = ContactInfo(
                    email=data.get('email', supplier.contact_info.email),
                    phone=data.get('phone', supplier.contact_info.phone),
                    mobile=supplier.contact_info.mobile,
                )
            supplier.updated_by = current_user["username"]
            repo.save(supplier)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث المورد بنجاح")
    except Exception as e:
        logger.error(f"Error updating supplier: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/suppliers/{supplier_id}", response_model=ApiResponse)
async def delete_supplier(supplier_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            repo = uow.suppliers
            repo.delete(supplier_id)
            uow.commit()
            return ApiResponse(success=True, message="تم حذف المورد بنجاح")
    except Exception as e:
        logger.error(f"Error deleting supplier: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/products/{product_id}", response_model=ApiResponse)
async def update_product(product_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    try:
        data = filter_fields(request, [
            "name", "unit_price", "is_active", "stock_quantity", "status",
            "currency", "tax_rate", "description", "category",
        ])
        with bootstrap.uow() as uow:
            repo = uow.products
            product = repo.get_by_id(product_id) if hasattr(repo, 'get_by_id') else None
            if not product:
                return ApiResponse(success=False, message="المنتج غير موجود")
            if 'name' in data:
                product.name = data['name']
            if 'unit_price' in data:
                from decimal import Decimal
                val = data['unit_price']
                if isinstance(val, str):
                    val = Decimal(val)
                elif isinstance(val, (int, float)):
                    val = Decimal(str(val))
                product.unit_price = val
            if 'is_active' in data:
                product.is_active = bool(data['is_active'])
            if 'status' in data:
                from core.domain.products.value_objects import ProductStatus
                status_map = {s.value: s for s in ProductStatus}
                new_status = data['status']
                if new_status in status_map:
                    product.status = status_map[new_status]
                    product.is_active = (new_status == 'active')
            if 'stock_quantity' in data:
                product.stock_quantity = int(data['stock_quantity'])
            if 'tax_rate' in data:
                from decimal import Decimal
                product.tax_rate = Decimal(str(data['tax_rate']))
            if 'description' in data:
                product.description = data['description']
            if 'category' in data:
                product.category = data['category']
            product.updated_by = current_user["username"]
            repo.save(product)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث المنتج بنجاح")
    except Exception as e:
        logger.error(f"Error updating product: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/products/{product_id}/stock", response_model=ApiResponse)
async def update_product_stock(product_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    try:
        data = filter_fields(request, ["quantityChange"])
        with bootstrap.uow() as uow:
            repo = uow.products
            product = repo.get_by_id(product_id) if hasattr(repo, 'get_by_id') else None
            if not product:
                return ApiResponse(success=False, message="المنتج غير موجود")
            quantity_change = data.get('quantityChange', 0)
            product.stock_quantity = getattr(product, 'stock_quantity', 0) + quantity_change
            product.updated_by = current_user["username"]
            repo.save(product)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث المخزون بنجاح")
    except Exception as e:
        logger.error(f"Error updating product stock: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/products/{product_id}", response_model=ApiResponse)
async def delete_product(product_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            repo = uow.products
            repo.delete(product_id)
            uow.commit()
            return ApiResponse(success=True, message="تم حذف المنتج بنجاح")
    except Exception as e:
        logger.error(f"Error deleting product: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.put("/api/funds/{fund_id}", response_model=ApiResponse)
async def update_fund(fund_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    try:
        data = filter_fields(request, [
            "name", "fund_type", "currency",
        ])
        with bootstrap.uow() as uow:
            repo = uow.funds
            fund = repo.get_by_id(fund_id) if hasattr(repo, 'get_by_id') else None
            if not fund:
                return ApiResponse(success=False, message="الصندوق غير موجود")
            if 'name' in data:
                fund.name = data['name']
            if 'fund_type' in data:
                fund.fund_type = data['fund_type']
            if 'currency' in data:
                fund.currency = data['currency']
            fund.updated_by = current_user["username"]
            repo.save(fund)
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث الصندوق بنجاح")
    except Exception as e:
        logger.error(f"Error updating fund: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/funds/{fund_id}", response_model=ApiResponse)
async def delete_fund(fund_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from core.domain.funds.value_objects import FundId
        with bootstrap.uow() as uow:
            repo = uow.funds
            repo.delete(FundId.from_string(fund_id))
            uow.commit()
            return ApiResponse(success=True, message="تم حذف الصندوق بنجاح")
    except Exception as e:
        logger.error(f"Error deleting fund: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 26. OPENING BALANCES (الأرصدة الافتتاحية)
# =============================================================================

class OpeningBalanceLineRequest(BaseModel):
    account_code: str = Field(..., min_length=3, max_length=20)
    debit: Decimal = Field(Decimal("0"), ge=0)
    credit: Decimal = Field(Decimal("0"), ge=0)
    currency: Optional[str] = None

    @field_validator("credit")
    @classmethod
    def _validate_ob_side(cls, v, info):
        debit = info.data.get("debit", Decimal("0"))
        if debit > 0 and v > 0:
            raise ValueError("لا يمكن أن يكون هناك مدين ودائن في نفس الوقت")
        if debit == 0 and v == 0:
            raise ValueError("يجب أن يكون هناك مدين أو دائن")
        return v


class OpeningBalancesRequest(BaseModel):
    opening_date: date_type
    lines: List[OpeningBalanceLineRequest] = Field(..., min_length=1)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _validate_ob_balanced(self) -> 'OpeningBalancesRequest':
        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)
        if total_debit != total_credit:
            raise ValueError(f"الأرصدة الافتتاحية غير متوازنة. مدين: {total_debit}, دائن: {total_credit}")
        return self


def _extract_entry_id(result):
    if result is None:
        return None
    if hasattr(result, "id"):
        return str(result.id)
    if isinstance(result, dict):
        return result.get("id")
    return None


def _find_opening_offset_account(uow):
    from sqlalchemy import text
    row = uow.session.execute(text(
        "SELECT code FROM accounts "
        "WHERE lower(name) LIKE '%opening%' OR name LIKE '%افتتاح%' OR name LIKE '%الافتتاحي%' "
        "ORDER BY code LIMIT 1"
    )).scalar()
    if row:
        return str(row)
    row = uow.session.execute(text(
        "SELECT code FROM accounts WHERE account_type = 'equity' AND is_active = TRUE ORDER BY code LIMIT 1"
    )).scalar()
    if row:
        return str(row)
    return None


@app.post("/api/opening-balances", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_opening_balances(request: OpeningBalancesRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        from core.application.accounting.commands import CreateJournalEntryCommand, PostJournalEntryCommand

        with bootstrap.uow() as uow:
            offset_code = _find_opening_offset_account(uow)
        if not offset_code:
            return ApiResponse(success=False, message="لا يوجد حساب للأرصدة الافتتاحية، قم بإنشاء حساب equity باسم 'أرصدة افتتاحية' أولاً")

        total_credit_offset = sum(line.debit for line in request.lines)
        total_debit_offset = sum(line.credit for line in request.lines)

        lines = []
        for line in request.lines:
            if line.debit > 0:
                lines.append({
                    "account_code": line.account_code,
                    "debit": line.debit,
                    "currency": line.currency,
                    "description": "رصيد افتتاحي",
                })
            if line.credit > 0:
                lines.append({
                    "account_code": line.account_code,
                    "credit": line.credit,
                    "currency": line.currency,
                    "description": "رصيد افتتاحي",
                })
        if total_credit_offset > 0:
            lines.append({"account_code": offset_code, "credit": total_credit_offset, "description": "مقابل الأرصدة الافتتاحية"})
        if total_debit_offset > 0:
            lines.append({"account_code": offset_code, "debit": total_debit_offset, "description": "مقابل الأرصدة الافتتاحية"})

        command = CreateJournalEntryCommand(
            date=request.opening_date,
            description=request.notes or "ترحيل الأرصدة الافتتاحية",
            lines=lines,
            transaction_type="opening_balance",
            reference_id="OPENING-BALANCE",
            created_by=current_user["username"],
        )
        command_bus = bootstrap.container.resolve("command_bus")
        created = command_bus.dispatch(command)
        entry_id = _extract_entry_id(created)
        if not entry_id:
            return ApiResponse(success=False, message="فشل إنشاء قيد الأرصدة الافتتاحية")

        with bootstrap.uow() as uow:
            uow.session.execute(
                text("UPDATE journal_entries SET transaction_type = 'opening_balance', reference = 'OPENING-BALANCE' "
                     "WHERE id::text = :eid"),
                {"eid": entry_id},
            )
            uow.commit()

        posted = False
        try:
            command_bus.dispatch(PostJournalEntryCommand(entry_id=entry_id, posted_by=current_user["username"]))
            posted = True
        except Exception:
            posted = False

        return ApiResponse(success=True, message="تم ترحيل الأرصدة الافتتاحية بنجاح",
                           data={"entry_id": entry_id, "is_posted": posted})
    except Exception as e:
        logger.error(f"Error creating opening balances: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/opening-balances", response_model=ApiResponse)
async def get_opening_balances(current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            row = uow.session.execute(text(
                "SELECT id FROM journal_entries WHERE transaction_type = 'opening_balance' "
                "ORDER BY entry_date DESC, created_at DESC LIMIT 1"
            )).scalar()
            exists = row is not None
            return ApiResponse(success=True, message="تم جلب الأرصدة الافتتاحية بنجاح",
                               data={"exists": exists, "entry_id": str(row) if row else None})
    except Exception as e:
        logger.error(f"Error getting opening balances: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 27. NOTIFICATIONS (الإشعارات)
# =============================================================================

@app.get("/api/notifications", response_model=ApiResponse)
async def list_notifications(current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text
            username = current_user.get("username", "")
            rows = uow.session.execute(text(
                "SELECT id::text, title, message, notification_type, is_read, data, created_at, read_at "
                "FROM notifications WHERE user_id = :uid ORDER BY created_at DESC LIMIT 100"
            ), {"uid": username}).mappings().all()
            items = []
            for r in rows:
                items.append({
                    "id": r["id"],
                    "title": r["title"],
                    "message": r["message"],
                    "type": r["notification_type"],
                    "is_read": r["is_read"],
                    "read": r["is_read"],
                    "data": r["data"],
                    "created_at": str(r["created_at"]) if r["created_at"] else None,
                    "read_at": str(r["read_at"]) if r["read_at"] else None,
                })
            return ApiResponse(success=True, message="تم جلب الإشعارات",
                               data={"items": items, "total": len(items)})
    except Exception as e:
        logger.error(f"Error listing notifications: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/notifications/unread-count", response_model=ApiResponse)
async def notifications_unread_count(current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text
            username = current_user.get("username", "")
            count = uow.session.execute(text(
                "SELECT COUNT(*) FROM notifications WHERE user_id = :uid AND is_read = FALSE"
            ), {"uid": username}).scalar() or 0
            return ApiResponse(success=True, message="ok", data={"count": count, "unread_count": count})
    except Exception as e:
        logger.error(f"Error getting unread count: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/notifications/{notif_id}/read", response_model=ApiResponse)
async def mark_notification_read(notif_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text
            username = current_user.get("username", "")
            uow.session.execute(text(
                "UPDATE notifications SET is_read = TRUE, read_at = NOW() "
                "WHERE id::text = :nid AND user_id = :uid"
            ), {"nid": notif_id, "uid": username})
            uow.commit()
        return ApiResponse(success=True, message="تم التحديد كمقروء")
    except Exception as e:
        logger.error(f"Error marking notification read: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/notifications/read-all", response_model=ApiResponse)
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text
            username = current_user.get("username", "")
            uow.session.execute(text(
                "UPDATE notifications SET is_read = TRUE, read_at = NOW() "
                "WHERE user_id = :uid AND is_read = FALSE"
            ), {"uid": username})
            uow.commit()
        return ApiResponse(success=True, message="تم تحديد الكل كمقروء")
    except Exception as e:
        logger.error(f"Error marking all read: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 28. AUDIT LOG (سجل التدقيق)
# =============================================================================

@app.get("/api/audit", response_model=ApiResponse)
async def list_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    performed_by: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text
            where_clauses = []
            params: Dict[str, Any] = {"lim": limit, "off": offset}
            if entity_type:
                where_clauses.append("entity_type = :et")
                params["et"] = entity_type
            if entity_id:
                where_clauses.append("entity_id = :eid")
                params["eid"] = entity_id
            if action:
                where_clauses.append("action = :act")
                params["act"] = action
            if performed_by:
                where_clauses.append("performed_by = :pb")
                params["pb"] = performed_by
            where_sql = (" AND ".join(where_clauses)) if where_clauses else "1=1"

            count = uow.session.execute(text(
                f"SELECT COUNT(*) FROM audit_log WHERE {where_sql}"
            ), params).scalar() or 0

            rows = uow.session.execute(text(
                f"SELECT id::text, entity_type, entity_id, action, performed_by, "
                f"old_values, new_values, ip_address, created_at "
                f"FROM audit_log WHERE {where_sql} ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            ), params).mappings().all()

            items = []
            for r in rows:
                items.append({
                    "id": r["id"],
                    "entity_type": r["entity_type"],
                    "entity_id": r["entity_id"],
                    "action": r["action"],
                    "performed_by": r["performed_by"],
                    "old_values": r["old_values"],
                    "new_values": r["new_values"],
                    "ip_address": r["ip_address"],
                    "created_at": str(r["created_at"]) if r["created_at"] else None,
                })
            return ApiResponse(success=True, message="تم جلب سجل التدقيق",
                               data={"items": items, "total": count})
    except Exception as e:
        logger.error(f"Error listing audit log: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 30. ROLES & PERMISSIONS (الأدوار والصلاحيات)
# =============================================================================

@app.get("/api/roles", response_model=ApiResponse)
async def list_roles(
    include_inactive: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text as sa_text
            where = "" if include_inactive else "WHERE r.is_active = TRUE"
            rows = uow.session.execute(sa_text(
                f"SELECT r.id::text, r.name, r.display_name, r.description, "
                f"r.is_admin, r.is_active, r.created_at, r.created_by, r.version "
                f"FROM roles r {where} ORDER BY r.name LIMIT :lim OFFSET :off"
            ), {"lim": limit, "off": offset}).mappings().all()

            items = []
            for r in rows:
                perms = uow.session.execute(sa_text(
                    "SELECT p.id::text, p.code, p.name, p.category "
                    "FROM permissions p "
                    "JOIN role_permissions rp ON rp.permission_id = p.id "
                    "WHERE rp.role_id = :rid"
                ), {"rid": r["id"]}).mappings().all()
                items.append({
                    "id": r["id"],
                    "name": r["name"],
                    "display_name": r["display_name"],
                    "description": r["description"],
                    "is_admin": r["is_admin"],
                    "is_active": r["is_active"],
                    "permissions": [dict(p) for p in perms],
                    "created_at": str(r["created_at"]) if r["created_at"] else None,
                    "created_by": r["created_by"],
                    "version": r["version"],
                })

            count = uow.session.execute(sa_text(
                f"SELECT COUNT(*) FROM roles r {where}"
            )).scalar() or 0
            return ApiResponse(success=True, message="تم جلب الأدوار",
                               data={"items": items, "total": count})
    except Exception as e:
        logger.error(f"Error listing roles: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_admin: bool = False
    permission_ids: List[str] = []


@app.post("/api/roles", response_model=ApiResponse)
async def create_role(
    request: CreateRoleRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text as sa_text
        import uuid as _uuid
        with bootstrap.uow() as uow:
            existing = uow.session.execute(sa_text(
                "SELECT id FROM roles WHERE name = :name"
            ), {"name": request.name}).scalar()
            if existing:
                return ApiResponse(success=False, message=f"الدور '{request.name}' موجود مسبقاً")

            role_id = str(_uuid.uuid4())
            uow.session.execute(sa_text(
                "INSERT INTO roles (id, name, display_name, description, is_admin, is_active, created_by, updated_by, version, created_at, updated_at) "
                "VALUES (:id, :name, :dn, :desc, :admin, TRUE, :user, :user, 1, NOW(), NOW())"
            ), {"id": role_id, "name": request.name, "dn": request.display_name or request.name,
                "desc": request.description or "", "admin": request.is_admin,
                "user": current_user.get("username", "system")})

            for pid in request.permission_ids:
                uow.session.execute(sa_text(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid) ON CONFLICT DO NOTHING"
                ), {"rid": role_id, "pid": pid})

            uow.session.commit()
            return ApiResponse(success=True, message=f"تم إنشاء الدور '{request.name}' بنجاح",
                               data={"id": role_id, "name": request.name})
    except Exception as e:
        logger.error(f"Error creating role: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


class UpdateRoleRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_admin: Optional[bool] = None
    permission_ids: Optional[List[str]] = None


@app.put("/api/roles/{role_id}", response_model=ApiResponse)
async def update_role(
    role_id: str,
    request: UpdateRoleRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text as sa_text
        with bootstrap.uow() as uow:
            role = uow.session.execute(sa_text(
                "SELECT id, name, version FROM roles WHERE id::text = :rid"
            ), {"rid": role_id}).mappings().first()
            if not role:
                return ApiResponse(success=False, message="الدور غير موجود")

            new_version = role["version"] + 1
            sets = ["version = :nv", "updated_by = :user"]
            params: dict = {"rid": role_id, "nv": new_version, "user": current_user.get("username", "system")}
            if request.display_name is not None:
                sets.append("display_name = :dn")
                params["dn"] = request.display_name
            if request.description is not None:
                sets.append("description = :desc")
                params["desc"] = request.description
            if request.is_admin is not None:
                sets.append("is_admin = :admin")
                params["admin"] = request.is_admin

            uow.session.execute(sa_text(
                f"UPDATE roles SET {', '.join(sets)} WHERE id::text = :rid AND version = :ov"
            ), {**params, "ov": role["version"]})

            if request.permission_ids is not None:
                uow.session.execute(sa_text(
                    "DELETE FROM role_permissions WHERE role_id = :rid"
                ), {"rid": role_id})
                for pid in request.permission_ids:
                    uow.session.execute(sa_text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:rid, :pid) ON CONFLICT DO NOTHING"
                    ), {"rid": role_id, "pid": pid})

            uow.session.commit()
            return ApiResponse(success=True, message=f"تم تحديث الدور '{role['name']}' بنجاح")
    except Exception as e:
        logger.error(f"Error updating role: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.delete("/api/roles/{role_id}", response_model=ApiResponse)
async def delete_role(
    role_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text as sa_text
        with bootstrap.uow() as uow:
            role = uow.session.execute(sa_text(
                "SELECT id, name FROM roles WHERE id::text = :rid"
            ), {"rid": role_id}).mappings().first()
            if not role:
                return ApiResponse(success=False, message="الدور غير موجود")

            user_count = uow.session.execute(sa_text(
                "SELECT COUNT(*) FROM user_roles WHERE role_id = :rid"
            ), {"rid": role_id}).scalar() or 0
            if user_count > 0:
                return ApiResponse(success=False, message=f"لا يمكن حذف الدور: مستخدمه {user_count} مستخدم(ين)")

            uow.session.execute(sa_text(
                "DELETE FROM role_permissions WHERE role_id = :rid"
            ), {"rid": role_id})
            uow.session.execute(sa_text(
                "DELETE FROM roles WHERE id::text = :rid"
            ), {"rid": role_id})
            uow.session.commit()
            return ApiResponse(success=True, message=f"تم حذف الدور '{role['name']}' بنجاح")
    except Exception as e:
        logger.error(f"Error deleting role: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/permissions", response_model=ApiResponse)
async def list_permissions(
    category: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text as sa_text
            where = "WHERE p.is_active = TRUE"
            params: dict = {"lim": limit, "off": offset}
            if category:
                where += " AND p.category = :cat"
                params["cat"] = category
            rows = uow.session.execute(sa_text(
                f"SELECT p.id::text, p.code, p.name, p.description, p.category "
                f"FROM permissions p {where} ORDER BY p.category, p.code LIMIT :lim OFFSET :off"
            ), params).mappings().all()

            count = uow.session.execute(sa_text(
                f"SELECT COUNT(*) FROM permissions p {where}"
            ), params if not category else {"cat": category}).scalar() or 0

            return ApiResponse(success=True, message="تم جلب الصلاحيات",
                               data={"items": [dict(r) for r in rows], "total": count})
    except Exception as e:
        logger.error(f"Error listing permissions: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/permissions/groups", response_model=ApiResponse)
async def list_permission_groups(
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text as sa_text
            rows = uow.session.execute(sa_text(
                "SELECT category, COUNT(*) as count "
                "FROM permissions WHERE is_active = TRUE "
                "GROUP BY category ORDER BY category"
            )).mappings().all()
            return ApiResponse(success=True, message="تم جلب مجموعات الصلاحيات",
                               data={"items": [dict(r) for r in rows]})
    except Exception as e:
        logger.error(f"Error listing permission groups: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 29. FISCAL PERIODS (الفترات المالية)
# =============================================================================

class CreatePeriodRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")


@app.get("/api/fiscal-periods", response_model=ApiResponse)
async def list_fiscal_periods(current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text
            rows = uow.session.execute(text(
                "SELECT id::text, name, year, period_number, period_type, "
                "start_date, end_date, is_closed, closed_by, closed_at "
                "FROM fiscal_periods ORDER BY year, period_number"
            )).mappings().all()
            items = []
            for r in rows:
                items.append({
                    "id": r["id"],
                    "name": r["name"],
                    "year": r["year"],
                    "period_number": r["period_number"],
                    "period_type": r["period_type"],
                    "start_date": str(r["start_date"].date()) if hasattr(r["start_date"], "date") else str(r["start_date"]),
                    "end_date": str(r["end_date"].date()) if hasattr(r["end_date"], "date") else str(r["end_date"]),
                    "status": "closed" if r["is_closed"] else "open",
                    "is_closed": r["is_closed"],
                    "closed_by": r["closed_by"],
                    "closed_at": str(r["closed_at"]) if r["closed_at"] else None,
                })
            return ApiResponse(success=True, message="تم جلب الفترات المالية",
                               data={"items": items, "total": len(items)})
    except Exception as e:
        logger.error(f"Error listing fiscal periods: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/fiscal-periods", response_model=ApiResponse)
async def create_fiscal_period(request: CreatePeriodRequest, current_user: dict = Depends(get_current_user)):
    try:
        from datetime import date as dt_date
        from sqlalchemy import text
        sd = dt_date.fromisoformat(request.start_date)
        ed = dt_date.fromisoformat(request.end_date)
        if ed < sd:
            return ApiResponse(success=False, message="تاريخ النهاية قبل تاريخ البداية")
        year = sd.year
        pn = sd.month
        with bootstrap.uow() as uow:
            exists = uow.session.execute(text(
                "SELECT id FROM fiscal_periods WHERE year=:y AND period_number=:pn"
            ), {"y": year, "pn": pn}).scalar()
            if exists:
                return ApiResponse(success=False, message=f"الفترة {year}-{pn:02d} موجودة مسبقاً")
            uow.session.execute(text(
                "INSERT INTO fiscal_periods (id, name, year, period_number, period_type, "
                "start_date, end_date, is_closed, is_adjustment, version) "
                "VALUES (gen_random_uuid(), :name, :y, :pn, 'MONTH', :sd, :ed, false, false, 1)"
            ), {"name": request.name, "y": year, "pn": pn, "sd": sd, "ed": ed})
            uow.commit()
        return ApiResponse(success=True, message="تم إنشاء الفترة المالية بنجاح")
    except Exception as e:
        logger.error(f"Error creating fiscal period: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/fiscal-periods/{period_id}/close", response_model=ApiResponse)
async def close_fiscal_period(period_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            period = uow.session.execute(text(
                "SELECT id::text, name, year, period_number, is_closed "
                "FROM fiscal_periods WHERE id::text = :pid"
            ), {"pid": period_id}).mappings().first()
            if not period:
                return ApiResponse(success=False, message="الفترة المالية غير موجودة")
            if period["is_closed"]:
                return ApiResponse(success=False, message="الفترة المالية مقفلة بالفعل")
            period_name = f"{period['year']}-{period['period_number']:02d}"
            closing_service = bootstrap.get_service("closing_service")
            if not closing_service:
                return ApiResponse(success=False, message="Closing service not available")
            result = closing_service.close_period(period_name, current_user.get("username", "system"), force=True)
            if result.success:
                return ApiResponse(success=True, message=f"تم إغلاق الفترة {period_name} بنجاح",
                                   data={"entries_created": result.entries_created})
            return ApiResponse(success=False, message="فشل إغلاق الفترة",
                               errors=result.errors if hasattr(result, 'errors') else [])
    except Exception as e:
        logger.error(f"Error closing fiscal period: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/fiscal-periods/{period_id}/reopen", response_model=ApiResponse)
async def reopen_fiscal_period(period_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            period = uow.session.execute(text(
                "SELECT id::text, name, year, period_number, is_closed "
                "FROM fiscal_periods WHERE id::text = :pid"
            ), {"pid": period_id}).mappings().first()
            if not period:
                return ApiResponse(success=False, message="الفترة المالية غير موجودة")
            if not period["is_closed"]:
                return ApiResponse(success=False, message="الفترة المالية مفتوحة بالفعل")
            period_name = f"{period['year']}-{period['period_number']:02d}"
            closing_service = bootstrap.get_service("closing_service")
            if not closing_service:
                return ApiResponse(success=False, message="Closing service not available")
            result = closing_service.reopen_period(
                period_name, current_user.get("username", "system"), reason="Admin reopen"
            )
            if result.get("success"):
                return ApiResponse(success=True, message=f"تم إعادة فتح الفترة {period_name} بنجاح")
            return ApiResponse(success=False, message=result.get("message", "فشل إعادة الفتح"))
    except Exception as e:
        logger.error(f"Error reopening fiscal period: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 28. YEAR-END CLOSING (إقفال السنة المالية)
# =============================================================================

class CloseYearRequest(BaseModel):
    retained_earnings_code: str = Field(..., min_length=3, max_length=20)


@app.post("/api/fiscal-periods/{period_id}/close-year", response_model=ApiResponse)
async def close_fiscal_year(period_id: str, request: CloseYearRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        from core.application.accounting.commands import CreateJournalEntryCommand, PostJournalEntryCommand

        with bootstrap.uow() as uow:
            period = uow.session.execute(text(
                "SELECT id, fiscal_year_id, year, name, start_date, end_date, is_closed "
                "FROM fiscal_periods WHERE id::text = :pid"
            ), {"pid": period_id}).mappings().first()
            if period is None:
                return ApiResponse(success=False, message="الفترة المالية غير موجودة")
            if period["is_closed"]:
                return ApiResponse(success=False, message="الفترة المالية مقفلة بالفعل")

            year = uow.session.execute(text(
                "SELECT id, code, name, start_date, end_date, status "
                "FROM fiscal_years WHERE id::text = :fyid"
            ), {"fyid": str(period["fiscal_year_id"])}).mappings().first()
            if year is None:
                return ApiResponse(success=False, message="السنة المالية غير موجودة")
            if year["status"] == "closed":
                return ApiResponse(success=False, message="السنة المالية مقفلة بالفعل")

            retained = uow.session.execute(text(
                "SELECT code, name FROM accounts WHERE code = :code"
            ), {"code": request.retained_earnings_code}).mappings().first()
            if retained is None:
                return ApiResponse(success=False, message="حساب الأرباح المحتجزة غير موجود")

            year_start = year["start_date"]
            year_end = year["end_date"] or year["start_date"]
            year_start = year_start.date() if hasattr(year_start, "date") else year_start
            year_end = year_end.date() if hasattr(year_end, "date") else year_end

            rev_rows = uow.session.execute(text(
                "SELECT a.code, COALESCE(SUM(l.credit_amount), 0) AS credit, "
                "COALESCE(SUM(l.debit_amount), 0) AS debit "
                "FROM ledger_entries l JOIN accounts a ON a.id = l.account_id "
                "JOIN journal_entries j ON j.id = l.journal_entry_id "
                "WHERE a.account_type = 'revenue' AND j.is_posted = TRUE "
                "AND COALESCE(j.transaction_type, '') <> 'year_end_closing' "
                "AND l.entry_date::date >= :start AND l.entry_date::date <= :end "
                "GROUP BY a.code"
            ), {"start": year_start, "end": year_end}).mappings().all()

            exp_rows = uow.session.execute(text(
                "SELECT a.code, COALESCE(SUM(l.debit_amount), 0) AS debit, "
                "COALESCE(SUM(l.credit_amount), 0) AS credit "
                "FROM ledger_entries l JOIN accounts a ON a.id = l.account_id "
                "JOIN journal_entries j ON j.id = l.journal_entry_id "
                "WHERE a.account_type = 'expense' AND j.is_posted = TRUE "
                "AND COALESCE(j.transaction_type, '') <> 'year_end_closing' "
                "AND l.entry_date::date >= :start AND l.entry_date::date <= :end "
                "GROUP BY a.code"
            ), {"start": year_start, "end": year_end}).mappings().all()

            lines = []
            summary = []
            total_net = Decimal("0")
            for r in rev_rows:
                bal = Decimal(r["credit"]) - Decimal(r["debit"])
                if bal > 0:
                    lines.append({"account_code": r["code"], "debit": bal, "description": "إقفال السنة - حساب الإيراد"})
                    lines.append({"account_code": request.retained_earnings_code, "credit": bal, "description": "إقفال السنة - الأرباح المحتجزة"})
                    summary.append({"account_code": r["code"], "type": "revenue", "amount": float(bal)})
                    total_net += bal
            for r in exp_rows:
                bal = Decimal(r["debit"]) - Decimal(r["credit"])
                if bal > 0:
                    lines.append({"account_code": r["code"], "credit": bal, "description": "إقفال السنة - حساب المصروف"})
                    lines.append({"account_code": request.retained_earnings_code, "debit": bal, "description": "إقفال السنة - الأرباح المحتجزة"})
                    summary.append({"account_code": r["code"], "type": "expense", "amount": float(bal)})
                    total_net -= bal

            if not lines:
                return ApiResponse(success=False, message="لا توجد إيرادات أو مصروفات مرحلة لإقفالها")

        command = CreateJournalEntryCommand(
            date=year_end,
            description=f"إقفال السنة المالية {year['code']} - {year['name']}",
            lines=lines,
            transaction_type="year_end_closing",
            reference_id=f"CLOSE-YEAR-{period_id[:8]}",
            created_by=current_user["username"],
        )
        command_bus = bootstrap.container.resolve("command_bus")
        created = command_bus.dispatch(command)
        entry_id = _extract_entry_id(created)
        if not entry_id:
            return ApiResponse(success=False, message="فشل إنشاء قيد الإقفال")

        with bootstrap.uow() as uow:
            uow.session.execute(
                text("UPDATE journal_entries SET transaction_type = 'year_end_closing', reference = :ref "
                     "WHERE id::text = :eid"),
                {"ref": f"CLOSE-YEAR-{period_id[:8]}", "eid": entry_id},
            )
            uow.commit()

        posted = False
        try:
            command_bus.dispatch(PostJournalEntryCommand(
                entry_id=entry_id,
                posted_by=current_user["username"],
                force=True,
            ))
            posted = True
        except Exception as e:
            logger.error(f"Error posting closing entry: {e}", exc_info=True)
            return ApiResponse(
                success=False,
                message=f"فشل ترحيل قيد الإقفال: {str(e)}",
                data={"entry_id": entry_id, "is_posted": False},
            )

        # ✅ فقط بعد نجاح الترحيل: قفل فترات السنة + السنة نفسها
        with bootstrap.uow() as uow:
            uow.session.execute(
                text("UPDATE fiscal_periods SET is_closed = TRUE, closed_at = now(), closed_by = :by "
                     "WHERE fiscal_year_id::text = :fyid AND is_closed = FALSE"),
                {"by": current_user["username"], "fyid": str(period["fiscal_year_id"])},
            )
            uow.session.execute(
                text("UPDATE fiscal_years SET status = 'closed', closed_at = now(), closed_by = :by "
                     "WHERE id::text = :fyid"),
                {"by": current_user["username"], "fyid": str(period["fiscal_year_id"])},
            )
            uow.commit()

        return ApiResponse(success=True, message="تم إقفال السنة المالية بنجاح",
                           data={
                               "period_id": period_id,
                               "entry_id": entry_id,
                               "is_posted": posted,
                               "net_income": float(total_net),
                               "entries_created": summary,
                           })
    except Exception as e:
        logger.error(f"Error closing fiscal year: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 28. STATEMENTS (كشوفات الحساب)
# =============================================================================

@app.get("/api/customers/{customer_id}/statement", response_model=ApiResponse)
async def customer_statement(
    customer_id: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        to_date = to_date or date.today()
        with bootstrap.uow() as uow:
            customer = uow.session.execute(text(
                "SELECT id, code, name FROM customers WHERE id::text = :cid"
            ), {"cid": customer_id}).mappings().first()
            if customer is None:
                return ApiResponse(success=False, message="العميل غير موجود")

            inv_rows = uow.session.execute(text(
                "SELECT number, invoice_date, status, total_amount FROM invoices "
                "WHERE customer_id = :cid AND invoice_date::date <= :to ORDER BY invoice_date"
            ), {"cid": customer_id, "to": to_date}).mappings().all()

            pay_rows = uow.session.execute(text(
                "SELECT code, payment_date, amount, status FROM payments "
                "WHERE customer_id = :cid AND payment_type = 'receive' AND payment_date::date <= :to "
                "ORDER BY payment_date"
            ), {"cid": customer_id, "to": to_date}).mappings().all()

            items = []
            for inv in inv_rows:
                if inv["status"] == "cancelled":
                    items.append({"date": inv["invoice_date"], "type": "cancel",
                                  "description": f"إلغاء فاتورة {inv['number']}",
                                  "debit": 0.0, "credit": float(inv["total_amount"]), "reference": inv["number"]})
                elif inv["status"] == "posted":
                    if inv["total_amount"] > 0:
                        items.append({"date": inv["invoice_date"], "type": "invoice",
                                      "description": f"فاتورة {inv['number']}",
                                      "debit": float(inv["total_amount"]), "credit": 0.0, "reference": inv["number"]})
                    else:
                        items.append({"date": inv["invoice_date"], "type": "return",
                                      "description": f"مرتجع فاتورة {inv['number']}",
                                      "debit": 0.0, "credit": abs(float(inv["total_amount"])), "reference": inv["number"]})
            for pay in pay_rows:
                if pay["status"] not in ("cancelled", "rejected"):
                    items.append({"date": pay["payment_date"], "type": "payment",
                                  "description": f"دفعة {pay['code']}",
                                  "debit": 0.0, "credit": float(pay["amount"]), "reference": pay["code"]})

            items.sort(key=lambda x: x["date"])
            opening = sum((Decimal(str(i["debit"])) - Decimal(str(i["credit"]))) for i in items
                          if from_date and i["date"] < from_date)
            filtered = [i for i in items if not from_date or i["date"] >= from_date]

            result_items = []
            if from_date and opening != 0:
                result_items.append({"date": from_date, "type": "opening", "description": "رصيد افتتاحي",
                                     "debit": 0.0, "credit": 0.0, "balance": float(opening)})
            running = opening
            for i in filtered:
                running += Decimal(str(i["debit"])) - Decimal(str(i["credit"]))
                result_items.append({**i, "balance": float(running)})

            return ApiResponse(success=True, message="تم جلب كشف حساب العميل بنجاح",
                               data={
                                   "customer_id": customer_id,
                                   "customer_name": customer["name"],
                                   "from_date": from_date.isoformat() if from_date else None,
                                   "to_date": to_date.isoformat(),
                                   "items": result_items,
                                   "balance": float(running),
                               })
    except Exception as e:
        logger.error(f"Error getting customer statement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/suppliers/{supplier_id}/statement", response_model=ApiResponse)
async def supplier_statement(
    supplier_id: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        to_date = to_date or date.today()
        with bootstrap.uow() as uow:
            supplier = uow.session.execute(text(
                "SELECT id, code, name FROM suppliers WHERE id::text = :sid"
            ), {"sid": supplier_id}).mappings().first()
            if supplier is None:
                return ApiResponse(success=False, message="المورد غير موجود")

            po_rows = uow.session.execute(text(
                "SELECT number, order_date, status, total_amount FROM purchase_orders "
                "WHERE supplier_id = :sid AND order_date::date <= :to ORDER BY order_date"
            ), {"sid": supplier_id, "to": to_date}).mappings().all()

            pay_rows = uow.session.execute(text(
                "SELECT code, payment_date, amount, status FROM payments "
                "WHERE supplier_id = :sid AND payment_type = 'pay' AND payment_date::date <= :to "
                "ORDER BY payment_date"
            ), {"sid": supplier_id, "to": to_date}).mappings().all()

            items = []
            for po in po_rows:
                if po["status"] == "cancelled":
                    items.append({"date": po["order_date"], "type": "cancel",
                                  "description": f"إلغاء أمر شراء {po['number']}",
                                  "debit": 0.0, "credit": float(po["total_amount"]), "reference": po["number"]})
                else:
                    items.append({"date": po["order_date"], "type": "purchase_order",
                                  "description": f"أمر شراء {po['number']}",
                                  "debit": float(po["total_amount"]), "credit": 0.0, "reference": po["number"]})
            for pay in pay_rows:
                if pay["status"] not in ("cancelled", "rejected"):
                    items.append({"date": pay["payment_date"], "type": "payment",
                                  "description": f"دفعة {pay['code']}",
                                  "debit": 0.0, "credit": float(pay["amount"]), "reference": pay["code"]})

            items.sort(key=lambda x: x["date"])
            opening = sum((Decimal(str(i["debit"])) - Decimal(str(i["credit"]))) for i in items
                          if from_date and i["date"] < from_date)
            filtered = [i for i in items if not from_date or i["date"] >= from_date]

            result_items = []
            if from_date and opening != 0:
                result_items.append({"date": from_date, "type": "opening", "description": "رصيد افتتاحي",
                                     "debit": 0.0, "credit": 0.0, "balance": float(opening)})
            running = opening
            for i in filtered:
                running += Decimal(str(i["debit"])) - Decimal(str(i["credit"]))
                result_items.append({**i, "balance": float(running)})

            return ApiResponse(success=True, message="تم جلب كشف حساب المورد بنجاح",
                               data={
                                   "supplier_id": supplier_id,
                                   "supplier_name": supplier["name"],
                                   "from_date": from_date.isoformat() if from_date else None,
                                   "to_date": to_date.isoformat(),
                                   "items": result_items,
                                   "balance": float(running),
                               })
    except Exception as e:
        logger.error(f"Error getting supplier statement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/accounts/{account_code}/statement", response_model=ApiResponse)
async def account_statement(
    account_code: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        to_date = to_date or date.today()
        with bootstrap.uow() as uow:
            acct = uow.session.execute(text(
                "SELECT id, code, name, account_type, currency FROM accounts WHERE code = :code"
            ), {"code": account_code}).mappings().first()
            if acct is None:
                return ApiResponse(success=False, message="الحساب غير موجود")

            rows = uow.session.execute(text(
                "SELECT je.id AS entry_id, je.entry_date AS entry_date, je.description AS description, "
                "jl.debit_amount AS debit, jl.credit_amount AS credit "
                "FROM journal_lines jl "
                "JOIN journal_entries je ON je.id = jl.journal_entry_id "
                "JOIN accounts a ON a.id = jl.account_id "
                "WHERE a.code = :code AND je.is_posted = TRUE AND je.entry_date::date <= :to "
                "ORDER BY je.entry_date, jl.line_order"
            ), {"code": account_code, "to": to_date}).mappings().all()

            account_type = acct["account_type"]

            def signed(d, c):
                d = Decimal(str(d)); c = Decimal(str(c))
                if account_type in ("asset", "expense"):
                    return d - c
                return c - d

            opening = sum(signed(r["debit"], r["credit"]) for r in rows if from_date and r["entry_date"] < from_date)
            filtered = [r for r in rows if not from_date or r["entry_date"] >= from_date]

            items = []
            if from_date and opening != 0:
                items.append({"date": from_date, "entry_id": None, "description": "رصيد افتتاحي",
                              "debit": 0.0, "credit": 0.0, "balance": float(opening)})
            running = opening
            for r in filtered:
                running += signed(r["debit"], r["credit"])
                items.append({
                    "date": r["entry_date"],
                    "entry_id": str(r["entry_id"]),
                    "description": r["description"] or "",
                    "debit": float(r["debit"]),
                    "credit": float(r["credit"]),
                    "balance": float(running),
                })

            return ApiResponse(success=True, message="تم جلب كشف حساب الحساب بنجاح",
                               data={
                                   "account_code": account_code,
                                   "account_name": acct["name"],
                                   "account_type": account_type,
                                   "currency": acct["currency"],
                                   "from_date": from_date.isoformat() if from_date else None,
                                   "to_date": to_date.isoformat(),
                                   "items": items,
                                   "balance": float(running),
                               })
    except Exception as e:
        logger.error(f"Error getting account statement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 29. PAYMENT ALLOCATION (توزيع الدفعات)
# =============================================================================

class AllocatePaymentRequest(BaseModel):
    invoice_id: str
    amount: Decimal = Field(..., gt=0)
    currency: Optional[str] = None
    notes: Optional[str] = None


@app.post("/api/payments/{payment_id}/allocate", response_model=ApiResponse)
async def allocate_payment(payment_id: str, request: AllocatePaymentRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            payment = uow.session.execute(text(
                "SELECT id, code, amount, currency, status FROM payments WHERE id::text = :pid"
            ), {"pid": payment_id}).mappings().first()
            if payment is None:
                return ApiResponse(success=False, message="الدفعة غير موجودة")

            invoice = uow.session.execute(text(
                "SELECT id, number, total_amount, status FROM invoices WHERE id::text = :iid"
            ), {"iid": request.invoice_id}).mappings().first()
            if invoice is None:
                return ApiResponse(success=False, message="الفاتورة غير موجودة")

            currency = request.currency or payment["currency"]
            amount = Decimal(str(request.amount))
            if amount > Decimal(str(payment["amount"])):
                return ApiResponse(success=False, message="مبلغ التوزيع أكبر من مبلغ الدفعة")

            allocation_id = uuid.uuid4()
            uow.session.execute(
                text("INSERT INTO payment_allocations "
                     "(id, payment_id, invoice_id, amount, currency, status, allocated_at, allocated_by, notes) "
                     "VALUES (:id, :pid, :iid, :amount, :currency, 'active', now(), :by, :notes)"),
                {
                    "id": allocation_id,
                    "pid": uuid.UUID(payment_id),
                    "iid": uuid.UUID(request.invoice_id),
                    "amount": amount,
                    "currency": currency,
                    "by": current_user["username"],
                    "notes": request.notes,
                },
            )
            uow.commit()

            return ApiResponse(success=True, message="تم توزيع الدفعة بنجاح",
                               data={
                                   "allocation_id": str(allocation_id),
                                   "payment_id": payment_id,
                                   "invoice_id": request.invoice_id,
                                   "amount": float(amount),
                                   "currency": currency,
                               })
    except Exception as e:
        logger.error(f"Error allocating payment: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 30. BANK RECONCILIATION (التسوية البنكية)
# =============================================================================

def _ensure_reconciliation_tables(uow):
    from sqlalchemy import text
    statements = [
        "CREATE TABLE IF NOT EXISTS bank_statements ("
        " id UUID PRIMARY KEY, account_code VARCHAR(20) NOT NULL, bank_name VARCHAR(200) NOT NULL, "
        " account_number VARCHAR(50) NOT NULL, statement_date DATE NOT NULL, "
        " opening_balance NUMERIC(15,2) NOT NULL DEFAULT 0, closing_balance NUMERIC(15,2) NOT NULL DEFAULT 0, "
        " currency VARCHAR(3) NOT NULL DEFAULT 'USD', file_name VARCHAR(500), file_content TEXT, file_hash VARCHAR(64), "
        " uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(), uploaded_by VARCHAR(100) NOT NULL DEFAULT 'system', "
        " created_at TIMESTAMPTZ NOT NULL DEFAULT now(), statement_metadata JSONB DEFAULT '{}'::jsonb)",
        "CREATE TABLE IF NOT EXISTS reconciliations ("
        " id UUID PRIMARY KEY, bank_statement_id UUID NOT NULL UNIQUE, account_code VARCHAR(20) NOT NULL, "
        " reconciliation_date TIMESTAMPTZ NOT NULL, status VARCHAR(20) NOT NULL DEFAULT 'draft', "
        " reconciliation_type VARCHAR(20) NOT NULL DEFAULT 'bank', "
        " opening_balance NUMERIC(15,2) NOT NULL DEFAULT 0, closing_balance NUMERIC(15,2) NOT NULL DEFAULT 0, "
        " bank_opening_balance NUMERIC(15,2) NOT NULL DEFAULT 0, bank_closing_balance NUMERIC(15,2) NOT NULL DEFAULT 0, "
        " currency VARCHAR(3) NOT NULL DEFAULT 'USD', journal_entry_id UUID, notes TEXT, "
        " created_by VARCHAR(100) NOT NULL DEFAULT 'system', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), "
        " updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_by VARCHAR(100), completed_at TIMESTAMPTZ, "
        " version INTEGER NOT NULL DEFAULT 1, reconciliation_metadata JSONB DEFAULT '{}'::jsonb)",
        "CREATE TABLE IF NOT EXISTS reconciliation_matches ("
        " id UUID PRIMARY KEY, reconciliation_id UUID NOT NULL, bank_line_id VARCHAR(100) NOT NULL, "
        " ledger_entry_id VARCHAR(100) NOT NULL, amount NUMERIC(15,2) NOT NULL, currency VARCHAR(3) NOT NULL DEFAULT 'USD', "
        " status VARCHAR(20) NOT NULL DEFAULT 'matched', matched_by VARCHAR(100) NOT NULL DEFAULT 'system', "
        " matched_at TIMESTAMPTZ NOT NULL DEFAULT now(), match_score INTEGER NOT NULL DEFAULT 0, notes TEXT, "
        " match_metadata JSONB DEFAULT '{}'::jsonb)",
        "CREATE TABLE IF NOT EXISTS reconciliation_items ("
        " id UUID PRIMARY KEY, reconciliation_id UUID NOT NULL, payment_id VARCHAR(100) NOT NULL, "
        " matched BOOLEAN NOT NULL DEFAULT FALSE, amount NUMERIC(15,2) NOT NULL DEFAULT 0, "
        " currency VARCHAR(3) NOT NULL DEFAULT 'USD', created_by VARCHAR(100), created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
    ]
    for stmt in statements:
        uow.session.execute(text(stmt))


class CreateReconciliationRequest(BaseModel):
    account_code: str = Field(..., min_length=3, max_length=20)
    as_of_date: date_type
    statement_balance: Decimal = Field(..., ge=0)
    opening_balance: Decimal = Field(Decimal("0"), ge=0)
    bank_name: Optional[str] = "حساب مصرفي"
    currency: str = "USD"
    notes: Optional[str] = None


class MatchPaymentRequest(BaseModel):
    payment_id: str
    amount: Decimal = Field(..., ge=0)
    currency: Optional[str] = None
    notes: Optional[str] = None


@app.post("/api/reconciliations", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_reconciliation(request: CreateReconciliationRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            account = uow.session.execute(text(
                "SELECT code, name FROM accounts WHERE code = :code"
            ), {"code": request.account_code}).mappings().first()
            if account is None:
                return ApiResponse(success=False, message="الحساب غير موجود")

            bank_statement_id = uuid.uuid4()
            reconciliation_id = uuid.uuid4()
            now_ts = datetime.now()
            uow.session.execute(
                text("INSERT INTO bank_statements "
                     "(id, account_code, bank_name, account_number, statement_date, opening_balance, closing_balance, "
                     " currency, uploaded_at, uploaded_by, created_at) "
                     "VALUES (:id, :account_code, :bank_name, '-', :stmt_date, :opening, :closing, :currency, :now_ts, :by, :now_ts)"),
                {
                    "id": bank_statement_id,
                    "account_code": request.account_code,
                    "bank_name": request.bank_name or "حساب مصرفي",
                    "stmt_date": request.as_of_date,
                    "opening": request.opening_balance,
                    "closing": request.statement_balance,
                    "currency": request.currency,
                    "now_ts": now_ts,
                    "by": current_user["username"],
                },
            )
            uow.session.execute(
                text("INSERT INTO reconciliations "
                     "(id, bank_statement_id, account_code, reconciliation_date, status, reconciliation_type, "
                     " opening_balance, closing_balance, bank_opening_balance, bank_closing_balance, currency, notes, "
                     " created_by, created_at, updated_at, version) "
                     "VALUES (:id, :bsid, :account_code, :rdate, 'draft', 'bank', 0, 0, :bank_opening, :bank_closing, "
                     " :currency, :notes, :by, :now_ts, :now_ts, 1)"),
                {
                    "id": reconciliation_id,
                    "bsid": bank_statement_id,
                    "account_code": request.account_code,
                    "rdate": now_ts,
                    "bank_opening": request.opening_balance,
                    "bank_closing": request.statement_balance,
                    "currency": request.currency,
                    "notes": request.notes,
                    "by": current_user["username"],
                    "now_ts": now_ts,
                },
            )
            uow.commit()

            return ApiResponse(success=True, message="تم إنشاء التسوية البنكية بنجاح",
                               data={
                                   "id": str(reconciliation_id),
                                   "account_code": request.account_code,
                                   "as_of_date": request.as_of_date.isoformat(),
                                   "status": "draft",
                                   "variance": float(Decimal(str(request.statement_balance)) - Decimal(str(request.opening_balance))),
                                   "items": [],
                               })
    except Exception as e:
        logger.error(f"Error creating reconciliation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/reconciliations", response_model=ApiResponse)
async def list_reconciliations(current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            rows = uow.session.execute(text(
                "SELECT r.id, r.account_code, r.reconciliation_date, r.status, r.reconciliation_type, "
                " r.bank_opening_balance, r.bank_closing_balance, r.opening_balance, r.closing_balance, "
                " r.currency, r.created_by, r.created_at, r.completed_at, r.notes, bs.statement_date "
                "FROM reconciliations r JOIN bank_statements bs ON bs.id = r.bank_statement_id "
                "ORDER BY r.created_at DESC"
            )).mappings().all()
            items = []
            for r in rows:
                variance = Decimal(str(r["bank_closing_balance"])) - Decimal(str(r["closing_balance"]))
                items.append({
                    "id": str(r["id"]),
                    "account_code": r["account_code"],
                    "statement_date": r["statement_date"].isoformat() if r["statement_date"] else None,
                    "reconciliation_date": r["reconciliation_date"].isoformat() if r["reconciliation_date"] else None,
                    "status": r["status"],
                    "reconciliation_type": r["reconciliation_type"],
                    "bank_opening_balance": float(r["bank_opening_balance"]),
                    "bank_closing_balance": float(r["bank_closing_balance"]),
                    "opening_balance": float(r["opening_balance"]),
                    "closing_balance": float(r["closing_balance"]),
                    "variance": float(variance),
                    "currency": r["currency"],
                    "created_by": r["created_by"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                    "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                    "notes": r["notes"],
                })
            return ApiResponse(success=True, message="تم جلب التسويات البنكية بنجاح",
                               data={"items": items, "total": len(items)})
    except Exception as e:
        logger.error(f"Error listing reconciliations: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/reconciliations/{reconciliation_id}", response_model=ApiResponse)
async def get_reconciliation(reconciliation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            r = uow.session.execute(text(
                "SELECT r.id, r.account_code, r.reconciliation_date, r.status, r.reconciliation_type, "
                " r.bank_opening_balance, r.bank_closing_balance, r.opening_balance, r.closing_balance, "
                " r.currency, r.created_by, r.created_at, r.completed_at, r.completed_by, r.notes, bs.statement_date "
                "FROM reconciliations r JOIN bank_statements bs ON bs.id = r.bank_statement_id "
                "WHERE r.id::text = :rid"
            ), {"rid": reconciliation_id}).mappings().first()
            if r is None:
                return ApiResponse(success=False, message="التسوية غير موجودة")

            matched_rows = uow.session.execute(text(
                "SELECT bank_line_id, ledger_entry_id, amount, currency, status, matched_by, matched_at, notes "
                "FROM reconciliation_matches WHERE reconciliation_id::text = :rid ORDER BY matched_at"
            ), {"rid": reconciliation_id}).mappings().all()
            items = [{
                "bank_line_id": m["bank_line_id"],
                "ledger_entry_id": m["ledger_entry_id"],
                "payment_id": m["ledger_entry_id"],
                "amount": float(m["amount"]),
                "currency": m["currency"],
                "status": m["status"],
                "matched_by": m["matched_by"],
                "matched_at": m["matched_at"].isoformat() if m["matched_at"] else None,
                "notes": m["notes"],
            } for m in matched_rows]

            suggested = []
            stmt_date = r["statement_date"]
            if stmt_date:
                sug_rows = uow.session.execute(text(
                    "SELECT id, code, payment_date, amount, currency, status FROM payments "
                    "WHERE payment_date::date BETWEEN :from_d AND :to_d ORDER BY payment_date LIMIT 50"
                ), {"from_d": (stmt_date - timedelta(days=30)).isoformat(), "to_d": stmt_date.isoformat()}).mappings().all()
                for s in sug_rows:
                    suggested.append({
                        "payment_id": str(s["id"]),
                        "code": s["code"],
                        "payment_date": s["payment_date"].isoformat() if s["payment_date"] else None,
                        "amount": float(s["amount"]),
                        "currency": s["currency"],
                        "status": s["status"],
                    })

            return ApiResponse(success=True, message="تم جلب التسوية بنجاح",
                               data={
                                   "id": str(r["id"]),
                                   "account_code": r["account_code"],
                                   "statement_date": r["statement_date"].isoformat() if r["statement_date"] else None,
                                   "status": r["status"],
                                   "reconciliation_type": r["reconciliation_type"],
                                   "bank_opening_balance": float(r["bank_opening_balance"]),
                                   "bank_closing_balance": float(r["bank_closing_balance"]),
                                   "opening_balance": float(r["opening_balance"]),
                                   "closing_balance": float(r["closing_balance"]),
                                   "variance": float(Decimal(str(r["bank_closing_balance"])) - Decimal(str(r["closing_balance"]))),
                                   "currency": r["currency"],
                                   "notes": r["notes"],
                                   "created_by": r["created_by"],
                                   "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                                   "completed_by": r["completed_by"],
                                   "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
                                   "items": items,
                                   "suggested_matches": suggested,
                               })
    except Exception as e:
        logger.error(f"Error getting reconciliation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/reconciliations/{reconciliation_id}/match", response_model=ApiResponse)
async def match_reconciliation_item(reconciliation_id: str, request: MatchPaymentRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            r = uow.session.execute(text(
                "SELECT id, status, opening_balance, bank_closing_balance, currency FROM reconciliations "
                "WHERE id::text = :rid"
            ), {"rid": reconciliation_id}).mappings().first()
            if r is None:
                return ApiResponse(success=False, message="التسوية غير موجودة")
            if r["status"] in ("reconciled", "cancelled"):
                return ApiResponse(success=False, message="لا يمكن المطابقة على تسوية مكتملة أو ملغاة")

            payment = uow.session.execute(text(
                "SELECT id, code, amount, currency, status FROM payments WHERE id::text = :pid"
            ), {"pid": request.payment_id}).mappings().first()
            if payment is None:
                return ApiResponse(success=False, message="الدفعة غير موجودة")

            already_matched = uow.session.execute(text(
                "SELECT 1 FROM reconciliation_matches WHERE ledger_entry_id = :pid "
                "AND reconciliation_id::text <> :rid LIMIT 1"
            ), {"pid": request.payment_id, "rid": reconciliation_id}).scalar()
            if already_matched:
                return ApiResponse(success=False, message="الدفعة مطابقة بالفعل لتسوية أخرى")
            already_in_this = uow.session.execute(text(
                "SELECT 1 FROM reconciliation_matches WHERE ledger_entry_id = :pid "
                "AND reconciliation_id::text = :rid LIMIT 1"
            ), {"pid": request.payment_id, "rid": reconciliation_id}).scalar()
            if already_in_this:
                return ApiResponse(success=False, message="الدفعة مطابقة بالفعل لهذه التسوية")

            match_id = uuid.uuid4()
            currency = request.currency or r["currency"] or payment["currency"]
            amount = Decimal(str(request.amount))
            now_ts = datetime.now()

            uow.session.execute(
                text("INSERT INTO reconciliation_matches "
                     "(id, reconciliation_id, bank_line_id, ledger_entry_id, amount, currency, status, matched_by, "
                     " matched_at, match_score, notes) "
                     "VALUES (:id, :rid, :blid, :leid, :amount, :currency, 'matched', :by, :now_ts, 100, :notes)"),
                {
                    "id": match_id,
                    "rid": uuid.UUID(reconciliation_id),
                    "blid": str(payment["code"]) or request.payment_id,
                    "leid": request.payment_id,
                    "amount": amount,
                    "currency": currency,
                    "by": current_user["username"],
                    "now_ts": now_ts,
                    "notes": request.notes,
                },
            )
            uow.session.execute(
                text("INSERT INTO reconciliation_items "
                     "(id, reconciliation_id, payment_id, matched, amount, currency, created_by) "
                     "VALUES (:id, :rid, :pid, TRUE, :amount, :currency, :by)"),
                {
                    "id": match_id,
                    "rid": uuid.UUID(reconciliation_id),
                    "pid": request.payment_id,
                    "amount": amount,
                    "currency": currency,
                    "by": current_user["username"],
                },
            )
            uow.session.execute(
                text("UPDATE reconciliations SET "
                     " closing_balance = opening_balance + COALESCE((SELECT SUM(amount) FROM reconciliation_matches "
                     "   WHERE reconciliation_id = :rid2), 0), "
                     " status = 'in_progress', updated_at = :now_ts WHERE id::text = :rid"),
                {"rid2": uuid.UUID(reconciliation_id), "rid": reconciliation_id, "now_ts": now_ts},
            )
            uow.commit()

            closing = Decimal(str(r["opening_balance"]))
            matched_sum = uow.session.execute(text(
                "SELECT COALESCE(SUM(amount), 0) FROM reconciliation_matches WHERE reconciliation_id::text = :rid"
            ), {"rid": reconciliation_id}).scalar()
            closing += Decimal(str(matched_sum or 0))

            return ApiResponse(success=True, message="تمت مطابقة الدفعة بنجاح",
                               data={
                                   "match_id": str(match_id),
                                   "reconciliation_id": reconciliation_id,
                                   "payment_id": request.payment_id,
                                   "amount": float(amount),
                                   "currency": currency,
                                   "variance": float(Decimal(str(r["bank_closing_balance"])) - closing),
                               })
    except Exception as e:
        logger.error(f"Error matching reconciliation item: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.post("/api/reconciliations/{reconciliation_id}/complete", response_model=ApiResponse)
async def complete_reconciliation(reconciliation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_reconciliation_tables(uow)
            r = uow.session.execute(text(
                "SELECT id, status, opening_balance, closing_balance, bank_closing_balance FROM reconciliations "
                "WHERE id::text = :rid"
            ), {"rid": reconciliation_id}).mappings().first()
            if r is None:
                return ApiResponse(success=False, message="التسوية غير موجودة")
            if r["status"] == "reconciled":
                return ApiResponse(success=False, message="التسوية مكتملة بالفعل")

            now_ts = datetime.now()
            uow.session.execute(
                text("UPDATE reconciliations SET status = 'reconciled', completed_by = :by, completed_at = :now_ts, "
                     " updated_at = :now_ts WHERE id::text = :rid"),
                {"by": current_user["username"], "now_ts": now_ts, "rid": reconciliation_id},
            )
            uow.commit()

            variance = Decimal(str(r["bank_closing_balance"])) - Decimal(str(r["closing_balance"]))
            return ApiResponse(success=True, message="تم إكمال التسوية البنكية بنجاح",
                               data={
                                   "reconciliation_id": reconciliation_id,
                                   "status": "reconciled",
                                   "completed_by": current_user["username"],
                                   "completed_at": now_ts.isoformat(),
                                   "variance": float(variance),
                               })
    except Exception as e:
        logger.error(f"Error completing reconciliation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 31. FX REVALUATION (إعادة تقييم العملات)
# =============================================================================

def _get_fx_rate(uow, base_code, target_code, as_of_date):
    from sqlalchemy import text
    if base_code == target_code:
        return Decimal("1")
    rate = uow.session.execute(text(
        "SELECT er.rate FROM exchange_rates er "
        "JOIN currencies fc ON fc.id = er.from_currency_id AND fc.code = :base "
        "JOIN currencies tc ON tc.id = er.to_currency_id AND tc.code = :target "
        "WHERE er.effective_date <= CAST(:as_of AS timestamptz) "
        "ORDER BY er.effective_date DESC LIMIT 1"
    ), {"base": base_code, "target": target_code, "as_of": as_of_date}).scalar()
    if rate is not None:
        return Decimal(str(rate))
    row = uow.session.execute(text(
        "SELECT exchange_rates FROM currencies WHERE code = :base"
    ), {"base": base_code}).scalar()
    if row:
        val = row.get(target_code)
        if val:
            return Decimal(str(val))
    return None


class RevaluationRequest(BaseModel):
    as_of_date: date_type
    fx_gain_account_code: str = Field(..., min_length=3, max_length=20)
    fx_loss_account_code: str = Field(..., min_length=3, max_length=20)
    currency: Optional[str] = None


@app.post("/api/currency/revaluation", response_model=ApiResponse)
async def run_fx_revaluation(request: RevaluationRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        from core.application.accounting.commands import CreateJournalEntryCommand, PostJournalEntryCommand

        with bootstrap.uow() as uow:
            base_code = uow.session.execute(text(
                "SELECT code FROM currencies WHERE is_base = TRUE LIMIT 1"
            )).scalar()
            base_code = str(base_code) if base_code else "USD"

            gain = uow.session.execute(text(
                "SELECT code FROM accounts WHERE code = :code"
            ), {"code": request.fx_gain_account_code}).scalar()
            loss = uow.session.execute(text(
                "SELECT code FROM accounts WHERE code = :code"
            ), {"code": request.fx_loss_account_code}).scalar()
            if not gain:
                return ApiResponse(success=False, message="حساب أرباح فروق العملة غير موجود")
            if not loss:
                return ApiResponse(success=False, message="حساب خسائر فروق العملة غير موجود")

            rows = uow.session.execute(text(
                "SELECT a.code, a.currency, a.account_type, "
                "COALESCE(SUM(l.debit_amount), 0) AS debit, COALESCE(SUM(l.credit_amount), 0) AS credit "
                "FROM accounts a "
                "LEFT JOIN ledger_entries l ON l.account_id = a.id AND l.entry_date::date <= :as_of "
                "WHERE a.currency IS NOT NULL AND a.currency <> '' AND a.currency <> :base "
                "GROUP BY a.code, a.currency, a.account_type"
            ), {"as_of": request.as_of_date, "base": base_code}).mappings().all()

            lines = []
            summary = []
            skipped = []
            for r in rows:
                balance = Decimal(str(r["debit"])) - Decimal(str(r["credit"]))
                account_type = r["account_type"]
                if account_type in ("liability", "equity", "revenue"):
                    balance = -balance
                if abs(balance) < Decimal("0.01"):
                    continue
                rate = _get_fx_rate(uow, base_code, r["currency"], request.as_of_date)
                if rate is None:
                    skipped.append({"account_code": r["code"], "currency": r["currency"], "reason": "no_rate"})
                    continue
                diff = balance * (rate - Decimal("1"))
                if abs(diff) < Decimal("0.01"):
                    continue
                is_debit_balance = account_type in ("asset", "expense")
                if is_debit_balance:
                    if diff > 0:
                        lines.append({"account_code": r["code"], "debit": abs(diff), "description": "فروق عملة (ربح)"})
                        lines.append({"account_code": request.fx_gain_account_code, "credit": abs(diff), "description": "إعادة تقييم عملة"})
                        summary.append({"account_code": r["code"], "currency": r["currency"], "fx_difference": float(diff), "type": "gain"})
                    else:
                        lines.append({"account_code": r["code"], "credit": abs(diff), "description": "فروق عملة (خسارة)"})
                        lines.append({"account_code": request.fx_loss_account_code, "debit": abs(diff), "description": "إعادة تقييم عملة"})
                        summary.append({"account_code": r["code"], "currency": r["currency"], "fx_difference": float(diff), "type": "loss"})
                else:
                    if diff > 0:
                        lines.append({"account_code": request.fx_loss_account_code, "debit": abs(diff), "description": "إعادة تقييم عملة"})
                        lines.append({"account_code": r["code"], "credit": abs(diff), "description": "فروق عملة (خسارة)"})
                        summary.append({"account_code": r["code"], "currency": r["currency"], "fx_difference": float(diff), "type": "loss"})
                    else:
                        lines.append({"account_code": r["code"], "debit": abs(diff), "description": "فروق عملة (ربح)"})
                        lines.append({"account_code": request.fx_gain_account_code, "credit": abs(diff), "description": "إعادة تقييم عملة"})
                        summary.append({"account_code": r["code"], "currency": r["currency"], "fx_difference": float(diff), "type": "gain"})

            if not lines:
                return ApiResponse(success=True, message="لا توجد فروق عملات لإعادة تقييمها",
                                   data={"as_of_date": request.as_of_date.isoformat(), "base_currency": base_code,
                                         "adjustments": [], "skipped": skipped})

        command = CreateJournalEntryCommand(
            date=request.as_of_date,
            description="إعادة تقييم فروق العملات الأجنبية",
            lines=lines,
            transaction_type="fx_revaluation",
            reference_id=f"FX-REVALUATION-{request.as_of_date.isoformat()}",
            created_by=current_user["username"],
        )
        command_bus = bootstrap.container.resolve("command_bus")
        created = command_bus.dispatch(command)
        entry_id = _extract_entry_id(created)

        with bootstrap.uow() as uow:
            uow.session.execute(
                text("UPDATE journal_entries SET transaction_type = 'fx_revaluation', reference = :ref "
                     "WHERE id::text = :eid"),
                {"ref": f"FX-REVALUATION-{request.as_of_date.isoformat()}", "eid": entry_id},
            )
            uow.commit()

        posted = False
        try:
            command_bus.dispatch(PostJournalEntryCommand(entry_id=entry_id, posted_by=current_user["username"]))
            posted = True
        except Exception:
            posted = False

        return ApiResponse(success=True, message="تم تنفيذ إعادة تقييم العملات بنجاح",
                           data={
                               "as_of_date": request.as_of_date.isoformat(),
                               "base_currency": base_code,
                               "entry_id": entry_id,
                               "is_posted": posted,
                               "adjustments": summary,
                               "skipped": skipped,
                               "total_fx_difference": float(sum(s["fx_difference"] for s in summary)),
                           })
    except Exception as e:
        logger.error(f"Error running FX revaluation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 32. BUDGETS (الميزانيات التقديرية)
# =============================================================================

def _ensure_budget_tables(uow):
    from sqlalchemy import text
    statements = [
        "CREATE TABLE IF NOT EXISTS budgets ("
        " id UUID PRIMARY KEY, name VARCHAR(200) NOT NULL, period_start DATE NOT NULL, period_end DATE NOT NULL, "
        " currency VARCHAR(3) NOT NULL DEFAULT 'USD', status VARCHAR(20) NOT NULL DEFAULT 'active', "
        " created_by VARCHAR(100), created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
        "CREATE TABLE IF NOT EXISTS budget_lines ("
        " id UUID PRIMARY KEY, budget_id UUID NOT NULL, account_code VARCHAR(20) NOT NULL, "
        " amount NUMERIC(15,2) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now())",
    ]
    for stmt in statements:
        uow.session.execute(text(stmt))


class BudgetLineRequest(BaseModel):
    account_code: str = Field(..., min_length=3, max_length=20)
    amount: Decimal = Field(..., ge=0)


class CreateBudgetRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    period_start: date_type
    period_end: date_type
    currency: str = "USD"
    lines: List[BudgetLineRequest] = Field(..., min_length=1)


@app.post("/api/budgets", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_budget(request: CreateBudgetRequest, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        if request.period_start > request.period_end:
            return ApiResponse(success=False, message="تاريخ بداية الميزانية يجب أن يكون قبل تاريخ نهايتها")
        with bootstrap.uow() as uow:
            _ensure_budget_tables(uow)
            for line in request.lines:
                exists = uow.session.execute(text(
                    "SELECT code FROM accounts WHERE code = :code"
                ), {"code": line.account_code}).scalar()
                if not exists:
                    return ApiResponse(success=False, message=f"الحساب {line.account_code} غير موجود")

            budget_id = uuid.uuid4()
            uow.session.execute(
                text("INSERT INTO budgets (id, name, period_start, period_end, currency, status, created_by) "
                     "VALUES (:id, :name, :start, :end, :currency, 'active', :by)"),
                {
                    "id": budget_id,
                    "name": request.name,
                    "start": request.period_start,
                    "end": request.period_end,
                    "currency": request.currency,
                    "by": current_user["username"],
                },
            )
            for line in request.lines:
                uow.session.execute(
                    text("INSERT INTO budget_lines (id, budget_id, account_code, amount) VALUES (:id, :bid, :code, :amount)"),
                    {"id": uuid.uuid4(), "bid": budget_id, "code": line.account_code, "amount": line.amount},
                )
            uow.commit()

            total_budget = sum(line.amount for line in request.lines)
            return ApiResponse(success=True, message="تم إنشاء الميزانية بنجاح",
                               data={
                                   "id": str(budget_id),
                                   "name": request.name,
                                   "period_start": request.period_start.isoformat(),
                                   "period_end": request.period_end.isoformat(),
                                   "currency": request.currency,
                                   "total_budget": float(total_budget),
                                   "lines_count": len(request.lines),
                               })
    except Exception as e:
        logger.error(f"Error creating budget: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/budgets", response_model=ApiResponse)
async def list_budgets(current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_budget_tables(uow)
            rows = uow.session.execute(text(
                "SELECT b.id, b.name, b.period_start, b.period_end, b.currency, b.status, b.created_by, b.created_at, "
                "COALESCE(SUM(bl.amount), 0) AS total_budget, COUNT(bl.id) AS lines_count "
                "FROM budgets b LEFT JOIN budget_lines bl ON bl.budget_id = b.id "
                "GROUP BY b.id ORDER BY b.created_at DESC"
            )).mappings().all()
            items = [{
                "id": str(r["id"]),
                "name": r["name"],
                "period_start": r["period_start"].isoformat(),
                "period_end": r["period_end"].isoformat(),
                "currency": r["currency"],
                "status": r["status"],
                "created_by": r["created_by"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "total_budget": float(r["total_budget"]),
                "lines_count": r["lines_count"],
            } for r in rows]
            return ApiResponse(success=True, message="تم جلب الميزانيات بنجاح",
                               data={"items": items, "total": len(items)})
    except Exception as e:
        logger.error(f"Error listing budgets: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/budgets/{budget_id}", response_model=ApiResponse)
async def get_budget(budget_id: str, current_user: dict = Depends(get_current_user)):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_budget_tables(uow)
            b = uow.session.execute(text(
                "SELECT id, name, period_start, period_end, currency, status, created_by, created_at "
                "FROM budgets WHERE id::text = :bid"
            ), {"bid": budget_id}).mappings().first()
            if b is None:
                return ApiResponse(success=False, message="الميزانية غير موجودة")
            lines = uow.session.execute(text(
                "SELECT id, account_code, amount FROM budget_lines WHERE budget_id::text = :bid ORDER BY account_code"
            ), {"bid": budget_id}).mappings().all()
            return ApiResponse(success=True, message="تم جلب الميزانية بنجاح",
                               data={
                                   "id": str(b["id"]),
                                   "name": b["name"],
                                   "period_start": b["period_start"].isoformat(),
                                   "period_end": b["period_end"].isoformat(),
                                   "currency": b["currency"],
                                   "status": b["status"],
                                   "created_by": b["created_by"],
                                   "created_at": b["created_at"].isoformat() if b["created_at"] else None,
                                   "lines": [{
                                       "id": str(l["id"]),
                                       "account_code": l["account_code"],
                                       "amount": float(l["amount"]),
                                   } for l in lines],
                                   "total_budget": float(sum(l["amount"] for l in lines)),
                               })
    except Exception as e:
        logger.error(f"Error getting budget: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/reports/budget-vs-actual", response_model=ApiResponse)
async def budget_vs_actual_report(
    budget_id: Optional[str] = Query(None),
    period_start: Optional[date] = Query(None),
    period_end: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            _ensure_budget_tables(uow)
            budgets = []
            if budget_id:
                b = uow.session.execute(text(
                    "SELECT id, name, period_start, period_end, currency FROM budgets WHERE id::text = :bid"
                ), {"bid": budget_id}).mappings().first()
                if b is None:
                    return ApiResponse(success=False, message="الميزانية غير موجودة")
                budgets = [b]
            else:
                rows = uow.session.execute(text(
                    "SELECT id, name, period_start, period_end, currency FROM budgets "
                    "WHERE status = 'active' ORDER BY created_at DESC"
                )).mappings().all()
                budgets = rows

            all_reports = []
            for b in budgets:
                p_start = period_start or b["period_start"]
                p_end = period_end or b["period_end"]
                lines = uow.session.execute(text(
                    "SELECT account_code, amount FROM budget_lines WHERE budget_id::text = :bid ORDER BY account_code"
                ), {"bid": str(b["id"])}).mappings().all()

                actual_map = {}
                for l in lines:
                    acct = uow.session.execute(text(
                        "SELECT account_type FROM accounts WHERE code = :code"
                    ), {"code": l["account_code"]}).mappings().first()
                    account_type = acct["account_type"] if acct else "expense"
                    row = uow.session.execute(text(
                        "SELECT COALESCE(SUM(l2.debit_amount), 0) AS debit, COALESCE(SUM(l2.credit_amount), 0) AS credit "
                        "FROM ledger_entries je "
                        "JOIN journal_lines l2 ON l2.journal_entry_id = je.id "
                        "JOIN accounts a ON a.id = l2.account_id "
                        "WHERE a.code = :code AND je.is_posted = TRUE "
                        "AND je.entry_date::date BETWEEN :start AND :end"
                    ), {"code": l["account_code"], "start": p_start, "end": p_end}).mappings().first()
                    debit = Decimal(str(row["debit"]))
                    credit = Decimal(str(row["credit"]))
                    if account_type in ("asset", "expense"):
                        actual = debit - credit
                    else:
                        actual = credit - debit
                    actual_map[l["account_code"]] = actual

                items = []
                for l in lines:
                    budget_amt = Decimal(str(l["amount"]))
                    actual_amt = actual_map.get(l["account_code"], Decimal("0"))
                    variance = budget_amt - actual_amt
                    variance_pct = (variance / budget_amt * Decimal("100")) if budget_amt != 0 else None
                    items.append({
                        "account_code": l["account_code"],
                        "budget": float(budget_amt),
                        "actual": float(actual_amt),
                        "variance": float(variance),
                        "variance_pct": float(variance_pct) if variance_pct is not None else None,
                    })
                all_reports.append({
                    "budget_id": str(b["id"]),
                    "name": b["name"],
                    "currency": b["currency"],
                    "period_start": p_start.isoformat(),
                    "period_end": p_end.isoformat(),
                    "items": items,
                    "total_budget": float(sum(i["budget"] for i in items)),
                    "total_actual": float(sum(i["actual"] for i in items)),
                    "total_variance": float(sum(i["variance"] for i in items)),
                })
            return ApiResponse(success=True, message="تم جلب تقرير الميزانية مقابل الفعلي بنجاح",
                               data={"reports": all_reports})
    except Exception as e:
        logger.error(f"Error getting budget vs actual report: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# 33. FUND LEDGER (دفتر حركة الصندوق)
# =============================================================================

@app.get("/api/funds/{fund_id}/ledger", response_model=ApiResponse)
async def fund_ledger(
    fund_id: str,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from sqlalchemy import text
        with bootstrap.uow() as uow:
            fund = uow.session.execute(text(
                "SELECT id, code, name, currency FROM funds WHERE id::text = :fid"
            ), {"fid": fund_id}).mappings().first()
            if fund is None:
                return ApiResponse(success=False, message="الصندوق غير موجود")

            movements = uow.session.execute(text(
                "SELECT id, movement_type, amount, currency, balance_before, balance_after, reason, "
                "reference_id, created_at, created_by "
                "FROM fund_movements WHERE fund_id::text = :fid ORDER BY created_at"
            ), {"fid": fund_id}).mappings().all()

            filtered = []
            for m in movements:
                m_date = m["created_at"].date() if m["created_at"] else None
                if from_date and m_date and m_date < from_date:
                    continue
                if to_date and m_date and m_date > to_date:
                    continue
                filtered.append(m)

            items = []
            running = Decimal("0")
            if filtered:
                first_before = Decimal(str(filtered[0]["balance_before"] or 0))
                running = first_before
            for m in filtered:
                running += Decimal(str(m["amount"] or 0))
                items.append({
                    "id": str(m["id"]),
                    "date": m["created_at"].isoformat() if m["created_at"] else None,
                    "type": m["movement_type"],
                    "description": m["reason"],
                    "reference_id": m["reference_id"],
                    "amount": float(m["amount"]),
                    "currency": m["currency"] or fund["currency"],
                    "balance_before": float(m["balance_before"] or 0),
                    "balance": float(running),
                    "created_by": m["created_by"],
                })

            return ApiResponse(success=True, message="تم جلب دفتر حركة الصندوق بنجاح",
                               data={
                                   "fund_id": fund_id,
                                   "fund_code": fund["code"],
                                   "fund_name": fund["name"],
                                   "currency": fund["currency"],
                                   "from_date": from_date.isoformat() if from_date else None,
                                   "to_date": to_date.isoformat() if to_date else None,
                                   "items": items,
                                   "closing_balance": float(running),
                                   "movements_count": len(items),
                               })
    except Exception as e:
        logger.error(f"Error getting fund ledger: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@app.get("/api/health")
async def health_check():
    return {"success": True, "message": "Server is healthy"}


@app.get("/api/health/db")
async def database_health_check():
    try:
        with bootstrap.uow() as uow:
            return {"success": True, "message": "Database connection is healthy"}
    except Exception as e:
        return {"success": False, "message": f"Database error: {str(e)}"}


# =============================================================================
# Global Exception Handler
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    if ENV == "production":
        return JSONResponse(status_code=500, content={"success": False, "message": "خطأ داخلي في الخادم"})
    return JSONResponse(status_code=500, content={"success": False, "message": str(exc)})


from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail), "errors": [str(exc.detail)]}
    )


# =============================================================================
# تشغيل الخادم
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    ENV = os.getenv("ENV", "development")
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=(ENV == "development"),
        workers=int(os.getenv("WORKERS", "1")),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )