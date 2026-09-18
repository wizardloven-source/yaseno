# api_routers/sales_cycle/deliveries_router.py
"""
Delivery Notes API Router - إشعارات التسليم
"""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from api_routers.sales_cycle.dtos import (
    CreateDeliveryRequest,
    CompleteDeliveryRequest,
    FailDeliveryRequest,
    DeliveryLineRequest,
)
from api_routers.sales_cycle.utils import next_document_number
from api_routers.sales_cycle.service import update_order_status_after_delivery
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["sales-deliveries"])

PERM = {
    "create": "sales.create_delivery",
    "complete": "sales.complete_delivery",
    "cancel": "sales.cancel_delivery",
}


def _check_perm(perm: str):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission(perm):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")


def _serialize_delivery(row, items=None) -> dict:
    data = {
        "id": row["id"],
        "delivery_number": row["delivery_number"],
        "order_id": row["order_id"],
        "order_number": row["order_number"],
        "customer_id": str(row["customer_id"]),
        "customer_name": row["customer_name"],
        "delivery_date": row["delivery_date"].isoformat() if row.get("delivery_date") else None,
        "scheduled_date": row["scheduled_date"].isoformat() if row.get("scheduled_date") else None,
        "actual_delivery_time": row["actual_delivery_time"].isoformat()
                                if row.get("actual_delivery_time") else None,
        "status": row["status"],
        "carrier": row.get("carrier"),
        "vehicle_number": row.get("vehicle_number"),
        "driver_name": row.get("driver_name"),
        "driver_phone": row.get("driver_phone"),
        "delivery_address": row.get("delivery_address"),
        "received_by": row.get("received_by"),
        "received_by_title": row.get("received_by_title"),
        "received_date": row["received_date"].isoformat() if row.get("received_date") else None,
        "failure_reason": row.get("failure_reason"),
        "notes": row.get("notes"),
        "branch_id": row.get("branch_id"),
        "created_by": row.get("created_by"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }
    if items is not None:
        data["items"] = items
    return data


def _serialize_delivery_item(row) -> dict:
    return {
        "id": row["id"],
        "product_id": str(row["product_id"]),
        "product_code": row["product_code"],
        "product_name": row["product_name"],
        "ordered_quantity": float(row["ordered_quantity"] or 0),
        "delivered_quantity": float(row["delivered_quantity"] or 0),
        "unit": row["unit"],
        "notes": row["notes"],
    }


def _get_delivery(uow, delivery_id: str):
    row = uow.session.execute(
        text("SELECT * FROM delivery_notes WHERE id = :id"),
        {"id": delivery_id},
    ).mappings().first()
    if not row:
        return None
    items = uow.session.execute(
        text("SELECT * FROM delivery_items WHERE delivery_id = :did ORDER BY id"),
        {"did": delivery_id},
    ).mappings().all()
    return row, [_serialize_delivery_item(i) for i in items]


def create_delivery_record(uow, order_id: str, lines: Optional[list],
                           created_by: str, **kwargs) -> dict:
    """
    إنشاء إشعار تسليم من أمر بيع (يستخدم داخلياً ومن روتير الأوامر)
    لا يُحدث الكميات المسلّمة عند الإنشاء - فقط عند الاكتمال
    """
    order_row = uow.session.execute(
        text("SELECT * FROM sales_orders WHERE id = :id"),
        {"id": order_id},
    ).mappings().first()
    if not order_row:
        raise ValueError("أمر البيع غير موجود")

    if lines is None:
        items = uow.session.execute(
            text("SELECT * FROM order_items WHERE order_id = :oid ORDER BY id"),
            {"oid": order_id},
        ).mappings().all()
        lines = [{
            "product_id": str(i["product_id"]),
            "quantity": float(i["quantity"]) - float(i["delivered_quantity"] or 0),
        } for i in items if float(i["quantity"]) - float(i["delivered_quantity"] or 0) > 0]

    delivery_id = str(uuid4())
    delivery_number = next_document_number(uow, "DN", "delivery_notes", "delivery_number")

    delivery_address = kwargs.get("delivery_address")
    uow.session.execute(
        text("""
            INSERT INTO delivery_notes (
                id, delivery_number, order_id, order_number, customer_id,
                customer_name, delivery_date, scheduled_date, status,
                carrier, vehicle_number, driver_name, driver_phone,
                delivery_address, notes, branch_id, created_by
            ) VALUES (
                :id, :delivery_number, :order_id, :order_number, :customer_id,
                :customer_name, :delivery_date, :scheduled_date, 'draft',
                :carrier, :vehicle_number, :driver_name, :driver_phone,
                :delivery_address::jsonb, :notes, :branch_id, :created_by
            )
        """),
        {
            "id": delivery_id,
            "delivery_number": delivery_number,
            "order_id": order_id,
            "order_number": order_row["order_number"],
            "customer_id": str(order_row["customer_id"]),
            "customer_name": order_row["customer_name"],
            "delivery_date": kwargs.get("delivery_date") or datetime.now().date(),
            "scheduled_date": kwargs.get("scheduled_date"),
            "carrier": kwargs.get("carrier"),
            "vehicle_number": kwargs.get("vehicle_number"),
            "driver_name": kwargs.get("driver_name"),
            "driver_phone": kwargs.get("driver_phone"),
            "delivery_address": json.dumps(delivery_address, ensure_ascii=False)
                                if delivery_address else None,
            "notes": kwargs.get("notes"),
            "branch_id": kwargs.get("branch_id"),
            "created_by": created_by,
        },
    )

    for ln in lines:
        num = ln.get("quantity", ln.get("delivered_quantity", 1))
        prod = uow.session.execute(
            text("SELECT product_code, product_name, unit FROM order_items "
                 "WHERE order_id = :oid AND CAST(product_id AS TEXT) = :pid LIMIT 1"),
            {"oid": order_id, "pid": str(ln["product_id"])},
        ).mappings().first()
        uow.session.execute(
            text("""
                INSERT INTO delivery_items (
                    id, delivery_id, product_id, product_code, product_name,
                    ordered_quantity, delivered_quantity, unit, notes
                ) VALUES (
                    :id, :did, :product_id, :product_code, :product_name,
                    :ordered_quantity, :delivered_quantity, :unit, :notes
                )
            """),
            {
                "id": str(uuid4()),
                "did": delivery_id,
                "product_id": str(ln["product_id"]),
                "product_code": (prod["product_code"] if prod else ""),
                "product_name": (prod["product_name"] if prod else ""),
                "ordered_quantity": float(ln.get("ordered_quantity", 0)),
                "delivered_quantity": float(num),
                "unit": (prod["unit"] if prod else "pcs"),
                "notes": ln.get("notes"),
            },
        )

    return {"id": delivery_id, "delivery_number": delivery_number}


@router.post("/api/sales/deliveries", response_model=ApiResponse)
async def create_delivery(request: CreateDeliveryRequest,
                          current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["create"])
    try:
        with bootstrap.uow() as uow:
            order_row = uow.session.execute(
                text("SELECT * FROM sales_orders WHERE id = :id"),
                {"id": request.order_id},
            ).mappings().first()
            if not order_row:
                return ApiResponse(success=False, message="أمر البيع غير موجود",
                                   errors=["أمر البيع غير موجود"])
            if order_row["status"] not in ("confirmed", "in_progress",
                                           "partially_delivered"):
                return ApiResponse(success=False,
                                   message="لا يمكن إنشاء تسليم في الحالة الحالية")

            # التحقق من الكميات مقابل المتبقي غير المسلّم
            if request.lines:
                for ln in request.lines:
                    remaining = uow.session.execute(
                        text("""
                            SELECT quantity, delivered_quantity FROM order_items
                            WHERE order_id = :oid AND CAST(product_id AS TEXT) = :pid
                        """),
                        {"oid": request.order_id, "pid": str(ln.product_id)},
                    ).mappings().first()
                    if not remaining:
                        return ApiResponse(success=False,
                                           message=f"المنتج {ln.product_id} غير موجود في الأمر")
                    rem = float(remaining["quantity"]) - float(remaining["delivered_quantity"] or 0)
                    if float(ln.quantity) > rem:
                        return ApiResponse(
                            success=False,
                            message=f"الكمية المطلوبة ({ln.quantity}) تتجاوز المتبقي "
                                    f"غير المُسلَّم ({rem})",
                        )

            lines = [
                {"product_id": ln.product_id, "quantity": ln.quantity,
                 "notes": ln.notes}
                for ln in (request.lines or [])
            ] if request.lines else None

            delivery = create_delivery_record(
                uow, order_id=request.order_id, lines=lines,
                created_by=current_user.get("username", "system"),
                delivery_date=request.delivery_date,
                scheduled_date=request.scheduled_date,
                carrier=request.carrier,
                vehicle_number=request.vehicle_number,
                driver_name=request.driver_name,
                driver_phone=request.driver_phone,
                delivery_address=request.delivery_address,
                notes=request.notes,
            )
            uow.commit()
            return ApiResponse(success=True, message="تم إنشاء إشعار التسليم بنجاح",
                               data={"id": delivery["id"],
                                     "delivery_number": delivery["delivery_number"]})
    except Exception as e:
        logger.error(f"Error creating delivery: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/deliveries", response_model=ApiResponse)
async def list_deliveries(
    order_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user),
):
    try:
        with bootstrap.uow() as uow:
            where = []
            params: dict = {}
            if order_id:
                where.append("order_id = :order_id")
                params["order_id"] = order_id
            if customer_id:
                where.append("customer_id = :customer_id")
                params["customer_id"] = customer_id
            if status:
                where.append("status = :status")
                params["status"] = status
            if from_date:
                where.append("delivery_date >= :from_date")
                params["from_date"] = from_date
            if to_date:
                where.append("delivery_date <= :to_date")
                params["to_date"] = to_date
            if q:
                where.append("(customer_name ILIKE :q OR delivery_number ILIKE :q "
                             "OR order_number ILIKE :q)")
                params["q"] = f"%{q}%"

            where_sql = (" WHERE " + " AND ".join(where)) if where else ""
            total = uow.session.execute(
                text(f"SELECT COUNT(*) AS c FROM delivery_notes{where_sql}"),
                params,
            ).mappings().first()["c"]

            params["skip"] = skip
            params["limit"] = limit
            rows = uow.session.execute(
                text(f"""
                    SELECT * FROM delivery_notes{where_sql}
                    ORDER BY created_at DESC LIMIT :limit OFFSET :skip
                """),
                params,
            ).mappings().all()

            return ApiResponse(success=True, message="تم جلب إشعارات التسليم",
                               data={"items": [_serialize_delivery(r) for r in rows],
                                     "total": total, "skip": skip, "limit": limit})
    except Exception as e:
        logger.error(f"Error listing deliveries: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/deliveries/statistics", response_model=ApiResponse)
async def get_statistics(current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            total = uow.session.execute(
                text("SELECT COUNT(*) AS c FROM delivery_notes")
            ).mappings().first()["c"]

            by_status_rows = uow.session.execute(
                text("SELECT status, COUNT(*) AS c FROM delivery_notes GROUP BY status")
            ).mappings().all()
            by_status = {r["status"]: r["c"] for r in by_status_rows}

            pending = uow.session.execute(
                text("SELECT COUNT(*) AS c FROM delivery_notes "
                     "WHERE status NOT IN ('delivered', 'cancelled', 'failed')")
            ).mappings().first()["c"]

            return ApiResponse(success=True,
                               data={"total": total, "by_status": by_status,
                                     "pending": pending})
    except Exception as e:
        logger.error(f"Error getting delivery statistics: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/deliveries/{delivery_id}", response_model=ApiResponse)
async def get_delivery(delivery_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            found = _get_delivery(uow, delivery_id)
            if not found:
                return ApiResponse(success=False, message="إشعار التسليم غير موجود")
            row, items = found
            return ApiResponse(success=True, data=_serialize_delivery(row, items))
    except Exception as e:
        logger.error(f"Error getting delivery: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/deliveries/{delivery_id}/complete", response_model=ApiResponse)
async def complete_delivery(delivery_id: str, request: CompleteDeliveryRequest,
                            current_user: dict = Depends(get_current_user)):
    """
    اكتمال التسليم:
    يحدّث كميات order_items.delivered_quantity و حالة الأمر -
    لا يخصم المخزون (يُخصم عند ترحيل الفاتورة عبر post_invoice_handler)
    """
    _check_perm(PERM["complete"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT * FROM delivery_notes WHERE id = :id"),
                {"id": delivery_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="إشعار التسليم غير موجود")
            if row["status"] in ("delivered", "failed", "cancelled"):
                return ApiResponse(success=False,
                                   message="لا يمكن إكمال تسليم في الحالة الحالية")

            items = uow.session.execute(
                text("SELECT * FROM delivery_items WHERE delivery_id = :did ORDER BY id"),
                {"did": delivery_id},
            ).mappings().all()
            if not items:
                return ApiResponse(success=False, message="إشعار التسليم بدون عناصر")

            # التحقق النهائي من الكميات قبل الإكمال
            for it in items:
                remaining = uow.session.execute(
                    text("""
                        SELECT quantity, delivered_quantity FROM order_items
                        WHERE order_id = :oid AND CAST(product_id AS TEXT) = :pid
                    """),
                    {"oid": row["order_id"], "pid": str(it["product_id"])},
                ).mappings().first()
                if remaining:
                    rem = float(remaining["quantity"]) - float(remaining["delivered_quantity"] or 0)
                    qty = float(it["delivered_quantity"] or 0)
                    if qty > rem:
                        return ApiResponse(
                            success=False,
                            message=f"الكمية ({qty}) لمنتج {it['product_name']} "
                                    f"تتجاوز المتبقي غير المُسلَّم ({rem})",
                        )
                uow.session.execute(
                    text("""
                        UPDATE order_items SET delivered_quantity =
                            delivered_quantity + :qty, updated_at = NOW()
                        WHERE order_id = :oid AND CAST(product_id AS TEXT) = :pid
                    """),
                    {"qty": float(it["delivered_quantity"] or 0),
                     "oid": row["order_id"], "pid": str(it["product_id"])},
                )

            new_status = update_order_status_after_delivery(uow, row["order_id"])
            uow.session.execute(
                text("""
                    UPDATE delivery_notes SET status = 'delivered',
                        received_by = :received_by, received_by_title = :title,
                        actual_delivery_time = COALESCE(:instant, NOW()),
                        received_date = NOW(), notes = COALESCE(NULLIF(:notes, ''), notes),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "received_by": request.received_by,
                    "title": request.received_by_title,
                    "instant": request.actual_delivery_time or datetime.now(),
                    "notes": request.notes or "",
                    "id": delivery_id,
                },
            )
            if new_status == "delivered":
                uow.session.execute(
                    text("UPDATE sales_orders SET actual_delivery_date = CURRENT_DATE, "
                         "updated_at = NOW() WHERE id = :id"),
                    {"id": row["order_id"]},
                )
            uow.commit()
            return ApiResponse(success=True, message="تم اكتمال التسليم بنجاح",
                               data={"order_status": new_status})
    except Exception as e:
        logger.error(f"Error completing delivery: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/deliveries/{delivery_id}/fail", response_model=ApiResponse)
async def fail_delivery(delivery_id: str, request: FailDeliveryRequest,
                        current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["complete"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM delivery_notes WHERE id = :id"),
                {"id": delivery_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="إشعار التسليم غير موجود")
            if row["status"] in ("delivered", "failed", "cancelled"):
                return ApiResponse(success=False,
                                   message="لا يمكن تغيير حالة التسليم الآن")
            uow.session.execute(
                text("UPDATE delivery_notes SET status = 'failed', "
                     "failure_reason = :reason, updated_at = NOW() WHERE id = :id"),
                {"reason": (request.reason or "").strip(), "id": delivery_id},
            )
            uow.commit()
            return ApiResponse(success=True, message="تم تسجيل فشل التسليم")
    except Exception as e:
        logger.error(f"Error failing delivery: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/deliveries/{delivery_id}/cancel", response_model=ApiResponse)
async def cancel_delivery(delivery_id: str, current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["cancel"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM delivery_notes WHERE id = :id"),
                {"id": delivery_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="إشعار التسليم غير موجود")
            if row["status"] in ("delivered", "failed", "cancelled"):
                return ApiResponse(success=False,
                                   message="لا يمكن إلغاء تسليم في الحالة الحالية")
            uow.session.execute(
                text("UPDATE delivery_notes SET status = 'cancelled', updated_at = NOW() "
                     "WHERE id = :id"),
                {"id": delivery_id},
            )
            uow.commit()
            return ApiResponse(success=True, message="تم إلغاء إشعار التسليم")
    except Exception as e:
        logger.error(f"Error cancelling delivery: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])