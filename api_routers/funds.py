from decimal import Decimal
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status, HTTPException
from pydantic import BaseModel, Field

from api_routers.shared import bootstrap, logger, ApiResponse, CreateFundRequest, FundTransactionRequest, get_current_user
from api_routers.shared.dependencies import filter_fields
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["funds"])


class TransferFundsRequest(BaseModel):
    from_fund_id: str
    to_fund_id: str
    amount: Decimal
    reason: str = ""
    from_currency: Optional[str] = None
    to_currency: Optional[str] = None


# =============================================================================
# FUNDS
# =============================================================================

@router.get("/api/funds", response_model=ApiResponse)
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


@router.post("/api/funds", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_fund(request: CreateFundRequest, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("funds.create_fund"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
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


@router.post("/api/funds/{fund_id}/deposit", response_model=ApiResponse)
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


@router.post("/api/funds/{fund_id}/withdraw", response_model=ApiResponse)
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


@router.get("/api/funds/{fund_id}", response_model=ApiResponse)
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


@router.get("/api/funds/{fund_id}/balance", response_model=ApiResponse)
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


@router.post("/api/funds/transfer", response_model=ApiResponse)
async def transfer_funds(request: TransferFundsRequest, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("funds.transfer"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
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


@router.get("/api/funds/{fund_id}/movements", response_model=ApiResponse)
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


@router.put("/api/funds/{fund_id}", response_model=ApiResponse)
async def update_fund(fund_id: str, request: dict, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("funds.update_fund"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
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


@router.delete("/api/funds/{fund_id}", response_model=ApiResponse)
async def delete_fund(fund_id: str, current_user: dict = Depends(get_current_user)):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission("funds.delete_fund"):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")
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
# FUND LEDGER (دفتر حركة الصندوق)
# =============================================================================

@router.get("/api/funds/{fund_id}/ledger", response_model=ApiResponse)
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
