"""
YAseen ERP - Shared Configuration
JWT, Bootstrap, App, CORS, Middleware
"""
import sys
import os
import time
import logging
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from threading import Lock

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if _env_path.exists():
    load_dotenv(_env_path)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
import bcrypt as _bcrypt

logger = logging.getLogger(__name__)

# =============================================================================
# Bootstrap
# =============================================================================
from core.bootstrap.startup import get_bootstrap, init_bootstrap

try:
    bootstrap = get_bootstrap()
except Exception as e:
    print(f"Bootstrap not initialized: {e}")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is required.")
    bootstrap = init_bootstrap(
        database_url=db_url,
        echo_sql=os.getenv("ECHO_SQL", "false").lower() == "true",
        seed_data=os.getenv("SEED_DATA", "false").lower() == "true",
    )

# =============================================================================
# JWT Configuration
# =============================================================================

def _load_or_generate_secret_key() -> str:
    secret_file = Path(__file__).resolve().parent.parent.parent / ".jwt_secret"
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

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY") or _load_or_generate_secret_key()
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

def _verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


class _PwdContext:
    """Minimal drop-in for passlib.CryptContext used only for verify/hash."""
    def verify(self, plain: str, hashed: str) -> bool:
        return _verify_password(plain, hashed)
    def hash(self, password: str) -> str:
        return _hash_password(password)


pwd_context = _PwdContext()

from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# =============================================================================
# FastAPI App
# =============================================================================

ENV = os.getenv("ENV", "development")

app = FastAPI(
    title="YAseen ERP API",
    description="REST API لتطبيق YAseen ERP المحاسبي",
    version="3.0.0",
    docs_url="/docs" if ENV != "production" else None,
    redoc_url="/redoc" if ENV != "production" else None,
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization", "Content-Type", "Accept",
        "Origin", "X-Requested-With", "Idempotency-Key",
    ],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} {response.status_code} {duration_ms:.0f}ms")
    return response

# =============================================================================
# Rate Limiter
# =============================================================================

_rate_limit_lock = Lock()
_rate_requests = defaultdict(list)
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

SENSITIVE_ENDPOINT_LIMITS = {
    "/api/auth/login": (10, 60),
    "/api/auth/refresh": (20, 60),
    "/api/auth/change-password": (5, 60),
    "/api/payments": (30, 60),
    "/api/invoices": (30, 60),
    "/api/journal-entries": (50, 60),
}

_last_cleanup = time.time()

def _cleanup_old_entries():
    now = time.time()
    with _rate_limit_lock:
        keys_to_delete = []
        for ip in _rate_requests:
            _rate_requests[ip] = [t for t in _rate_requests[ip] if now - t < 300]
            if not _rate_requests[ip]:
                keys_to_delete.append(ip)
        for ip in keys_to_delete:
            del _rate_requests[ip]

def rate_limiter(max_requests: int = RATE_LIMIT_MAX, window_seconds: int = RATE_LIMIT_WINDOW):
    from fastapi import HTTPException
    async def dependency(request: Request):
        global _last_cleanup
        if time.time() - _last_cleanup > 300:
            _cleanup_old_entries()
            _last_cleanup = time.time()
        ip = request.client.host if request.client else "unknown"
        path = request.url.path
        if path in SENSITIVE_ENDPOINT_LIMITS:
            endpoint_max, endpoint_window = SENSITIVE_ENDPOINT_LIMITS[path]
        else:
            endpoint_max, endpoint_window = max_requests, window_seconds
        key = f"{ip}:{path}"
        now = time.time()
        with _rate_limit_lock:
            _rate_requests[key] = [t for t in _rate_requests[key] if now - t < endpoint_window]
            if len(_rate_requests[key]) >= endpoint_max:
                retry_after = int(endpoint_window - (now - _rate_requests[key][0]))
                raise HTTPException(
                    status_code=429,
                    detail=f"طلبات كثيرة جداً. يرجى المحاولة بعد {retry_after} ثانية.",
                    headers={"Retry-After": str(retry_after)},
                )
            _rate_requests[key].append(now)
    return dependency

# =============================================================================
# Idempotency Middleware
# =============================================================================

IDEMPOTENCY_ENDPOINTS = {
    "/api/payments",
    "/api/invoices",
    "/api/journal-entries",
    "/api/purchase-orders",
    "/api/inventory/movements",
    "/api/inventory/transfers",
    "/api/funds/transfer",
}

@app.middleware("http")
async def idempotency_middleware(request: Request, call_next):
    if request.method != "POST":
        return await call_next(request)
    if request.url.path not in IDEMPOTENCY_ENDPOINTS:
        return await call_next(request)

    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        return await call_next(request)

    try:
        with bootstrap.uow() as uow:
            from sqlalchemy import text

            existing = uow.session.execute(
                text("SELECT response_status, response_body, is_processing FROM idempotency_keys WHERE idempotency_key = :key AND expires_at > :now"),
                {"key": idempotency_key, "now": datetime.now(timezone.utc)}
            ).fetchone()

            if existing:
                if existing.is_processing:
                    return JSONResponse(status_code=409, content={"success": False, "message": "Request is being processed"})
                if existing.response_status and existing.response_body:
                    import json
                    return JSONResponse(status_code=existing.response_status, content=json.loads(existing.response_body))

            # Claim the key atomically. If the INSERT conflicts (a concurrent
            # request already claimed this key between our SELECT and INSERT),
            # RETURNING yields no row and we must NOT proceed — replay or 409.
            claimed = uow.session.execute(
                text("""
                    INSERT INTO idempotency_keys (id, idempotency_key, endpoint, is_processing, created_at, expires_at)
                    VALUES (gen_random_uuid(), :key, :endpoint, true, :now, :expires)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING idempotency_key
                """),
                {"key": idempotency_key, "endpoint": request.url.path,
                 "now": datetime.now(timezone.utc), "expires": datetime.now(timezone.utc) + timedelta(hours=24)}
            ).scalar()
            uow.commit()

            if not claimed:
                # A concurrent request won the claim. Return its outcome if
                # already stored, otherwise tell the caller it's in progress.
                concurrent = uow.session.execute(
                    text("SELECT response_status, response_body, is_processing FROM idempotency_keys WHERE idempotency_key = :key"),
                    {"key": idempotency_key}
                ).fetchone()
                if concurrent and concurrent.response_status and concurrent.response_body:
                    import json
                    if not concurrent.is_processing:
                        return JSONResponse(status_code=concurrent.response_status, content=json.loads(concurrent.response_body))
                return JSONResponse(status_code=409, content={"success": False, "message": "Request is being processed"})

    except Exception as e:
        logger.warning(f"Idempotency check failed: {e}")

    response = await call_next(request)

    if idempotency_key and response.status_code < 500:
        try:
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk if isinstance(chunk, bytes) else chunk.encode()

            import json
            with bootstrap.uow() as uow:
                from sqlalchemy import text
                uow.session.execute(
                    text("""
                        UPDATE idempotency_keys
                        SET response_status = :status, response_body = :body, is_processing = false
                        WHERE idempotency_key = :key
                    """),
                    {"status": response.status_code, "body": response_body.decode() if response_body else "{}", "key": idempotency_key}
                )
                uow.commit()

            from fastapi.responses import Response
            return Response(content=response_body, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)
        except Exception as e:
            logger.warning(f"Failed to cache idempotency response: {e}")

    return response

# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())[:8]
    logger.error(f"[{request_id}] Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"success": False, "message": "خطأ داخلي في الخادم", "request_id": request_id})

from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = str(exc.detail)
    if ENV == "production" and exc.status_code == 500:
        detail = "خطأ داخلي في الخادم"
    return JSONResponse(status_code=exc.status_code, content={"success": False, "message": detail, "errors": [detail]})
