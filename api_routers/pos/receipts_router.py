# api_routers/pos/receipts_router.py
"""
Point of Sale (POS) Receipts - إيصالات نقطة البيع
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from api_routers.pos.dtos import (
    CreatePosReceiptRequest,
    ReturnPosReceiptRequest,
    VoidPosReceiptRequest,
)
from api_routers.pos.pos_service import (
    create_pos_receipt,
    reverse_pos_receipt,
    list_pos_receipts,
    get_pos_receipt,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["pos-receipts"])

PERM = {
    "sell": "pos.sell",
    "credit_sale": "pos.credit_sale",
    "apply_discount": "pos.apply_discount",
    "return": "pos.return",
    "void": "pos.void_receipt",
    "view": "pos.view_sales",
}


def _check_perm(perm: str):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission(perm):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")


def _actor(current_user: dict) -> str:
    return str(current_user.get("id") or "system")


def _has_discount(request: CreatePosReceiptRequest) -> bool:
    return any(
        (getattr(l, "discount_percent", 0) or 0) > 0 or (getattr(l, "discount_amount", 0) or 0) > 0
        for l in request.lines
    )


@router.post("/api/pos/receipts", response_model=ApiResponse)
async def create_receipt(
    request: CreatePosReceiptRequest,
    current_user: dict = Depends(get_current_user),
):
    if request.tender_type == "credit":
        _check_perm(PERM["credit_sale"])
    else:
        _check_perm(PERM["sell"])
    if _has_discount(request):
        _check_perm(PERM["apply_discount"])

    try:
        with bootstrap.uow() as uow:
            result = create_pos_receipt(
                uow,
                session_id=request.session_id,
                customer_id=request.customer_id,
                currency=request.currency,
                tender_type=request.tender_type,
                lines_data=[l.model_dump() for l in request.lines],
                tenders=request.tenders,
                idempotency_key=request.idempotency_key,
                client_reference=request.client_reference,
                device_id=request.device_id,
                fund_id=request.fund_id,
                notes=request.notes,
                created_by=_actor(current_user),
            )
            uow.commit()
            if result.get("idempotent"):
                message = "تم إعادة إيصال البيع (معرّف مكرر)"
            else:
                message = "تم إنشاء إيصال البيع بنجاح"
            return ApiResponse(success=True, message=message, data=result)
    except Exception as e:
        logger.error(f"Error creating POS receipt: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/pos/receipts", response_model=ApiResponse)
async def all_receipts(
    session_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            data = list_pos_receipts(
                uow,
                session_id=session_id,
                customer_id=customer_id,
                status=status,
                q=q,
                skip=skip,
                limit=limit,
            )
            return ApiResponse(success=True, message="تم جلب إيصالات نقطة البيع", data=data)
    except Exception as e:
        logger.error(f"Error listing POS receipts: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/pos/receipts/{receipt_id}", response_model=ApiResponse)
async def receipt_detail(
    receipt_id: str,
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            data = get_pos_receipt(uow, receipt_id)
            return ApiResponse(success=True, message="تم جلب تفاصيل الإيصال", data=data)
    except Exception as e:
        logger.error(f"Error getting POS receipt: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/pos/receipts/{receipt_id}/return", response_model=ApiResponse)
async def return_receipt(
    receipt_id: str,
    request: ReturnPosReceiptRequest,
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["return"])
    try:
        with bootstrap.uow() as uow:
            result = reverse_pos_receipt(
                uow,
                receipt_id=receipt_id,
                reason=request.reason,
                refund_tender=request.refund_tender,
                created_by=_actor(current_user),
                return_line_specs=[l.model_dump() for l in request.items],
                is_void=False,
            )
            uow.commit()
            return ApiResponse(
                success=True,
                message="تم إرجاع المبيع بنجاح",
                data=result,
            )
    except Exception as e:
        logger.error(f"Error returning POS receipt: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/pos/receipts/{receipt_id}/void", response_model=ApiResponse)
async def void_receipt(
    receipt_id: str,
    request: VoidPosReceiptRequest,
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["void"])
    try:
        with bootstrap.uow() as uow:
            result = reverse_pos_receipt(
                uow,
                receipt_id=receipt_id,
                reason=request.reason,
                refund_tender="cash",
                created_by=_actor(current_user),
                return_line_specs=None,
                is_void=True,
            )
            uow.commit()
            return ApiResponse(
                success=True,
                message="تم إلغاء الإيصال بنجاح",
                data=result,
            )
    except Exception as e:
        logger.error(f"Error voiding POS receipt: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])