# api_routers/sales_cycle/picking_router.py
"""
Picking Lists API Router - قوائم الانتقاء (M3.1)
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from api_routers.sales_cycle.dtos import (
    PickPickingRequest,
    CancelPickingRequest,
)
from api_routers.sales_cycle.picking_service import (
    _get_picking,
    _serialize_picking,
    _serialize_picking_item,
    pick_picking_list,
    pack_picking_list,
    cancel_picking_list,
    cancel_order_picking_lists,
    get_product_availability,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["sales-picking"])

PERM = {
    "view": "sales.view_picking",
    "pick": "sales.pick_picking",
    "pack": "sales.pack_picking",
    "cancel": "sales.cancel_picking",
}


def _check_perm(perm: str):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission(perm):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")


@router.get("/api/sales/picking-lists", response_model=ApiResponse)
async def list_picking_lists(
    order_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            where = []
            params: dict = {}
            if order_id:
                where.append("order_id = :order_id")
                params["order_id"] = order_id
            if status:
                where.append("status = :status")
                params["status"] = status
            if q:
                where.append("(customer_name ILIKE :q OR picking_number ILIKE :q "
                             "OR order_number ILIKE :q)")
                params["q"] = f"%{q}%"

            where_sql = (" WHERE " + " AND ".join(where)) if where else ""
            total = uow.session.execute(
                text(f"SELECT COUNT(*) AS c FROM sales_picking_lists{where_sql}"),
                params,
            ).mappings().first()["c"]

            params["skip"] = skip
            params["limit"] = limit
            rows = uow.session.execute(
                text(f"""
                    SELECT * FROM sales_picking_lists{where_sql}
                    ORDER BY created_at DESC LIMIT :limit OFFSET :skip
                """),
                params,
            ).mappings().all()

            return ApiResponse(success=True, message="تم جلب قوائم الانتقاء",
                               data={"items": [_serialize_picking(r) for r in rows],
                                     "total": total, "skip": skip, "limit": limit})
    except Exception as e:
        logger.error(f"Error listing picking lists: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/picking-lists/{picking_id}", response_model=ApiResponse)
async def get_picking_list(picking_id: str, current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            found = _get_picking(uow, picking_id)
            if not found:
                return ApiResponse(success=False, message="قائمة الانتقاء غير موجودة")
            row, items = found
            item_list = [_serialize_picking_item(i) for i in items]
            for item in item_list:
                try:
                    item["availability"] = get_product_availability(
                        uow, item["product_id"]
                    )
                except Exception:
                    item["availability"] = None
            return ApiResponse(success=True, data=_serialize_picking(row, item_list))
    except Exception as e:
        logger.error(f"Error getting picking list: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/picking-lists/{picking_id}/pick", response_model=ApiResponse)
async def pick_picking(picking_id: str, request: PickPickingRequest,
                       current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["pick"])
    try:
        with bootstrap.uow() as uow:
            lines = [
                {"order_item_id": ln.order_item_id,
                 "picked_quantity": float(ln.picked_quantity),
                 "notes": ln.notes}
                for ln in request.items
            ]
            result = pick_picking_list(
                uow,
                picking_id=picking_id,
                lines=lines,
                warehouse_id=request.warehouse_id,
                created_by=current_user.get("username", "system"),
            )
            uow.commit()
            return ApiResponse(success=True, message="تم تسجيل الانتقاء بنجاح",
                               data=result)
    except Exception as e:
        logger.error(f"Error picking items: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/picking-lists/{picking_id}/pack", response_model=ApiResponse)
async def pack_picking(picking_id: str, current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["pack"])
    try:
        with bootstrap.uow() as uow:
            pack_picking_list(uow, picking_id=picking_id,
                              created_by=current_user.get("username", "system"))
            uow.commit()
            return ApiResponse(success=True, message="تم تغليف قائمة الانتقاء بنجاح",
                               data={"id": picking_id, "status": "packed"})
    except Exception as e:
        logger.error(f"Error packing picking list: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/picking-lists/{picking_id}/cancel", response_model=ApiResponse)
async def cancel_picking(picking_id: str, request: CancelPickingRequest,
                         current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["cancel"])
    try:
        with bootstrap.uow() as uow:
            cancel_picking_list(uow, picking_id=picking_id, reason=request.reason)
            uow.commit()
            return ApiResponse(success=True, message="تم إلغاء قائمة الانتقاء",
                               data={"id": picking_id, "status": "cancelled"})
    except Exception as e:
        logger.error(f"Error cancelling picking list: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/orders/{order_id}/picking/cancel", response_model=ApiResponse)
async def cancel_order_pickings(order_id: str, request: CancelPickingRequest,
                                current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["cancel"])
    try:
        with bootstrap.uow() as uow:
            count = cancel_order_picking_lists(uow, order_id=order_id, reason=request.reason)
            uow.commit()
            return ApiResponse(success=True,
                               message="تم إلغاء قوائم الانتقاء المفتوحة للأمر",
                               data={"cancelled": count})
    except Exception as e:
        logger.error(f"Error cancelling order picking lists: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])