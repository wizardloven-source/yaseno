"""
Settings Router - Basic Units, Currency, Sites, Centers, Settings, Branches,
Roles & Permissions, Fiscal Periods, Year-end Closing, Notifications, Audit Log, Opening Balances
"""

import uuid
from decimal import Decimal
from datetime import datetime, date, timedelta
from datetime import date as date_type
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field, field_validator, model_validator

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user

router = APIRouter(prefix="", tags=["settings"])


# =============================================================================
# PYDANTIC MODELS
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


# ---------- Roles & Permissions ----------

class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_admin: bool = False
    permission_ids: List[str] = []


class UpdateRoleRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    is_admin: Optional[bool] = None
    permission_ids: Optional[List[str]] = None


# ---------- Fiscal Periods ----------

class CreatePeriodRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    start_date: str = Field(..., description="YYYY-MM-DD")
    end_date: str = Field(..., description="YYYY-MM-DD")


# ---------- Year-end Closing ----------

class CloseYearRequest(BaseModel):
    retained_earnings_code: str = Field(..., min_length=3, max_length=20)


# ---------- Opening Balances ----------

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


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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


# =============================================================================
# 13. BASIC UNITS - Currency, Sites, Centers, Settings, Branches
# =============================================================================


# =============================================================================
# CURRENCY ENDPOINTS - نقاط نهاية العملات
# =============================================================================

@router.post("/api/currency", response_model=ApiResponse)
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


@router.get("/api/currency", response_model=ApiResponse)
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


@router.get("/api/currency/base", response_model=ApiResponse)
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


@router.get("/api/currency/by-code/{code}", response_model=ApiResponse)
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


@router.get("/api/currency/exchange-rate", response_model=ApiResponse)
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


@router.get("/api/currency/{currency_id}", response_model=ApiResponse)
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


@router.put("/api/currency/{currency_id}", response_model=ApiResponse)
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


@router.delete("/api/currency/{currency_id}", response_model=ApiResponse)
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


@router.post("/api/currency/{currency_id}/base", response_model=ApiResponse)
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


@router.post("/api/currency/{currency_id}/exchange-rate", response_model=ApiResponse)
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

@router.post("/api/sites", response_model=ApiResponse)
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


@router.get("/api/sites", response_model=ApiResponse)
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


@router.get("/api/sites/default", response_model=ApiResponse)
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


@router.get("/api/sites/search", response_model=ApiResponse)
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


@router.get("/api/sites/combo", response_model=ApiResponse)
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


@router.get("/api/sites/{site_id}/statistics", response_model=ApiResponse)
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


@router.get("/api/sites/{site_id}", response_model=ApiResponse)
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


@router.put("/api/sites/{site_id}", response_model=ApiResponse)
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


@router.delete("/api/sites/{site_id}", response_model=ApiResponse)
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


@router.post("/api/sites/{site_id}/default", response_model=ApiResponse)
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

@router.post("/api/centers", response_model=ApiResponse)
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


@router.get("/api/centers", response_model=ApiResponse)
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


@router.get("/api/centers/tree", response_model=ApiResponse)
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


@router.get("/api/centers/{center_code}/summary", response_model=ApiResponse)
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


@router.get("/api/centers/{center_id}", response_model=ApiResponse)
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


@router.put("/api/centers/{center_id}", response_model=ApiResponse)
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


@router.delete("/api/centers/{center_id}", response_model=ApiResponse)
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


@router.post("/api/centers/{center_id}/activate", response_model=ApiResponse)
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


@router.post("/api/centers/{center_id}/suspend", response_model=ApiResponse)
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


@router.post("/api/centers/{center_id}/close", response_model=ApiResponse)
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


@router.post("/api/centers/allocations", response_model=ApiResponse)
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


@router.post("/api/centers/allocations/{allocation_id}/post", response_model=ApiResponse)
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

@router.get("/api/settings", response_model=ApiResponse)
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


@router.get("/api/settings/ui", response_model=ApiResponse)
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


@router.put("/api/settings/ui", response_model=ApiResponse)
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


@router.put("/api/settings", response_model=ApiResponse)
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

@router.post("/api/customers/{customer_id}/branches", response_model=ApiResponse)
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


@router.get("/api/branches", response_model=ApiResponse)
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


@router.get("/api/branches/search", response_model=ApiResponse)
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


@router.get("/api/branches/by-code/{code}", response_model=ApiResponse)
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


@router.get("/api/branches/default", response_model=ApiResponse)
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


@router.get("/api/branches/{branch_id}", response_model=ApiResponse)
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


@router.put("/api/branches/{branch_id}", response_model=ApiResponse)
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


@router.delete("/api/branches/{branch_id}", response_model=ApiResponse)
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


@router.post("/api/branches/{branch_id}/activate", response_model=ApiResponse)
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


@router.post("/api/branches/{branch_id}/deactivate", response_model=ApiResponse)
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


@router.post("/api/branches/{branch_id}/default", response_model=ApiResponse)
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
# ROLES & PERMISSIONS (الأدوار والصلاحيات)
# =============================================================================

@router.get("/api/roles", response_model=ApiResponse)
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


@router.post("/api/roles", response_model=ApiResponse)
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


@router.put("/api/roles/{role_id}", response_model=ApiResponse)
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


@router.delete("/api/roles/{role_id}", response_model=ApiResponse)
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


@router.get("/api/permissions", response_model=ApiResponse)
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


@router.get("/api/permissions/groups", response_model=ApiResponse)
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
# FISCAL PERIODS (الفترات المالية)
# =============================================================================

@router.get("/api/fiscal-periods", response_model=ApiResponse)
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


@router.post("/api/fiscal-periods", response_model=ApiResponse)
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


@router.post("/api/fiscal-periods/{period_id}/close", response_model=ApiResponse)
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


@router.post("/api/fiscal-periods/{period_id}/reopen", response_model=ApiResponse)
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
# YEAR-END CLOSING (إقفال السنة المالية)
# =============================================================================

@router.post("/api/fiscal-periods/{period_id}/close-year", response_model=ApiResponse)
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
# NOTIFICATIONS (الإشعارات)
# =============================================================================

@router.get("/api/notifications", response_model=ApiResponse)
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


@router.get("/api/notifications/unread-count", response_model=ApiResponse)
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


@router.post("/api/notifications/{notif_id}/read", response_model=ApiResponse)
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


@router.post("/api/notifications/read-all", response_model=ApiResponse)
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
# AUDIT LOG (سجل التدقيق)
# =============================================================================

@router.get("/api/audit", response_model=ApiResponse)
async def list_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    performed_by: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
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
                where_clauses.append("operation = :act")
                params["act"] = action
            if performed_by:
                where_clauses.append("user_id = :pb")
                params["pb"] = performed_by
            if date_from:
                where_clauses.append("created_at::date >= :df")
                params["df"] = date_from
            if date_to:
                where_clauses.append("created_at::date <= :dt")
                params["dt"] = date_to
            where_sql = (" AND ".join(where_clauses)) if where_clauses else "1=1"

            count = uow.session.execute(text(
                f"SELECT COUNT(*) FROM audit_logs WHERE {where_sql}"
            ), params).scalar() or 0

            rows = uow.session.execute(text(
                f"SELECT id, entity_type, entity_id, operation, user_id, user_name, "
                f"old_state, new_state, changes, ip_address, created_at "
                f"FROM audit_logs WHERE {where_sql} ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            ), params).mappings().all()

            items = []
            for r in rows:
                details = r["changes"] or r["new_state"] or r["old_state"] or {}
                items.append({
                    "id": str(r["id"]),
                    "entity_type": r["entity_type"],
                    "entity_id": r["entity_id"],
                    "action": r["operation"],
                    "performed_by": r["user_id"],
                    "user_id": r["user_id"],
                    "user_name": r["user_name"] or r["user_id"],
                    "old_values": r["old_state"],
                    "new_values": r["new_state"],
                    "details": details,
                    "ip_address": r["ip_address"],
                    "created_at": str(r["created_at"]) if r["created_at"] else None,
                })
            return ApiResponse(success=True, message="تم جلب سجل التدقيق",
                               data={"items": items, "total": count})
    except Exception as e:
        logger.error(f"Error listing audit log: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


# =============================================================================
# OPENING BALANCES (الأرصدة الافتتاحية)
# =============================================================================

@router.post("/api/opening-balances", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/api/opening-balances", response_model=ApiResponse)
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
