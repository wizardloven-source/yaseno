# api_routers/sales_cycle/shipping_router.py
"""
Shipping API Router - الشحنات (M3.1)
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from api_routers.sales_cycle.dtos import CreateShippingRequest
from api_routers.sales_cycle.picking_service import (
    _get_shipping,
    _serialize_shipping,
    _serialize_shipping_item,
    create_shipping,
    confirm_shipping,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["sales-shipping"])

PERM = {
    "view": "sales.view_shipping",
    "create": "sales.create_shipping",
    "confirm": "sales.confirm_shipping",
}


def _check_perm(perm: str):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission(perm):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")


@router.post("/api/sales/picking-lists/{picking_id}/ship", response_model=ApiResponse)
async def ship_from_picking(picking_id: str, request: CreateShippingRequest,
                            current_user: dict = Depends(get_current_user)):
    """
    إنشاء شحنة من قائمة انتقاء مجهزة (الكميات المنتقاة تنتقل إلى الشحنة).
    """
    _check_perm(PERM["create"])
    try:
        with bootstrap.uow() as uow:
            shipping = create_shipping(
                uow,
                picking_id=picking_id,
                created_by=current_user.get("username", "system"),
                carrier=request.carrier,
                tracking_number=request.tracking_number,
                shipping_method=request.shipping_method,
                shipping_cost=float(request.shipping_cost),
                estimated_arrival=request.estimated_arrival,
                destination_address=request.destination_address,
                notes=request.notes,
            )
            uow.commit()
            return ApiResponse(success=True, message="تم إنشاء الشحنة بنجاح",
                               data={"id": shipping["id"],
                                     "shipping_number": shipping["shipping_number"],
                                     "status": "created"})
    except Exception as e:
        logger.error(f"Error creating shipping: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/shippings", response_model=ApiResponse)
async def list_shippings(
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
                where.append("(customer_name ILIKE :q OR shipping_number ILIKE :q "
                             "OR tracking_number ILIKE :q OR order_number ILIKE :q)")
                params["q"] = f"%{q}%"

            where_sql = (" WHERE " + " AND ".join(where)) if where else ""
            total = uow.session.execute(
                text(f"SELECT COUNT(*) AS c FROM sales_shipping{where_sql}"),
                params,
            ).mappings().first()["c"]

            params["skip"] = skip
            params["limit"] = limit
            rows = uow.session.execute(
                text(f"""
                    SELECT * FROM sales_shipping{where_sql}
                    ORDER BY created_at DESC LIMIT :limit OFFSET :skip
                """),
                params,
            ).mappings().all()

            return ApiResponse(success=True, message="تم جلب الشحنات",
                               data={"items": [_serialize_shipping(r) for r in rows],
                                     "total": total, "skip": skip, "limit": limit})
    except Exception as e:
        logger.error(f"Error listing shippings: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/shippings/{shipping_id}", response_model=ApiResponse)
async def get_shipping(shipping_id: str, current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["view"])
    try:
        with bootstrap.uow() as uow:
            found = _get_shipping(uow, shipping_id)
            if not found:
                return ApiResponse(success=False, message="الشحنة غير موجودة")
            row, items = found
            return ApiResponse(success=True,
                               data=_serialize_shipping(
                                   row, [_serialize_shipping_item(i) for i in items]))
    except Exception as e:
        logger.error(f"Error getting shipping: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/shippings/{shipping_id}/confirm", response_model=ApiResponse)
async def confirm_shipping_route(shipping_id: str,
                                 current_user: dict = Depends(get_current_user)):
    """
    تأكيد الشحنة: تُرصد الشحنة كخارجة (status = shipped) وتُرقی حالة الأمر
    إلى in_progress مع تسجيل بيانات الناقل/التتبع.
    """
    _check_perm(PERM["confirm"])
    try:
        with bootstrap.uow() as uow:
            confirm_shipping(uow, shipping_id=shipping_id,
                             created_by=current_user.get("username", "system"))
            uow.commit()
            return ApiResponse(success=True, message="تم تأكيد الشحنة بنجاح",
                               data={"id": shipping_id, "status": "shipped"})
    except Exception as e:
        logger.error(f"Error confirming shipping: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])