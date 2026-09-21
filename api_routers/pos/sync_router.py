# api_routers/pos/sync_router.py
"""
Point of Sale (POS) Sync - مزامنة الأجهزة (المزامنة الحركية للعمل دون اتصال)
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from api_routers.pos.pos_service import (
    sync_pos_receipts,
    retry_sync_operation,
    list_sync_operations,
)
from api_routers.pos.dtos import SyncReceiptsRequest
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["pos-sync"])

PERM = {
    "sell": "pos.sell",
    "view": "pos.view_sales",
}


def _check_perm(perm: str):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission(perm):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")


def _actor(current_user: dict) -> str:
    return str(current_user.get("id") or "system")


@router.post("/api/pos/sync/receipts", response_model=ApiResponse)
async def sync_receipts(
    request: SyncReceiptsRequest,
    current_user: dict = Depends(get_current_user),
):
    """مزامنة دفعة إيصالات البيع من الجهاز"""
    _check_perm(PERM["sell"])
    try:
        device_id = request.receipts[0].device_id if request.receipts else None
        with bootstrap.uow() as uow:
            results = sync_pos_receipts(
                uow,
                receipts=[r.model_dump() for r in request.receipts],
                device_id=device_id,
                created_by=_actor(current_user),
            )
            uow.commit()
            synced = sum(1 for r in results if r.get("item_status") == "synced")
            conflicts = sum(1 for r in results if r.get("item_status") == "conflict")
            failed = sum(1 for r in results if r.get("item_status") == "failed")
            return ApiResponse(
                success=True,
                message=f"تمت المزامنة: {synced} مُدمج، {conflicts} تعارض، {failed} فشل",
                data={"results": results, "synced": synced, "conflicts": conflicts, "failed": failed},
            )
    except Exception as e:
        logger.error(f"Error syncing POS receipts: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/pos/sync/operations", response_model=ApiResponse)
async def all_sync_operations(
    status: Optional[str] = Query(None),
    device_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            data = list_sync_operations(
                uow, status=status, device_id=device_id, skip=skip, limit=limit
            )
            return ApiResponse(
                success=True,
                message="تم جلب عمليات المزامنة",
                data=data,
            )
    except Exception as e:
        logger.error(f"Error listing sync operations: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/pos/sync/operations/{operation_id}/retry", response_model=ApiResponse)
async def retry_sync(
    operation_id: str,
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["sell"])
    try:
        with bootstrap.uow() as uow:
            result = retry_sync_operation(uow, operation_id, created_by=_actor(current_user))
            uow.commit()
            if result.get("success"):
                message = "تمت إعادة المزامنة بنجاح"
            else:
                message = f"فشلت إعادة المزامنة: {result.get('error', result.get('conflict_code', ''))}"
            return ApiResponse(
                success=result.get("success", False),
                message=message,
                data=result,
            )
    except Exception as e:
        logger.error(f"Error retrying sync operation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])