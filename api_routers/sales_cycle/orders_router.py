# api_routers/sales_cycle/orders_router.py
"""
Sales Orders API Router - أوامر البيع
"""

import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text

from api_routers.shared import bootstrap, logger, ApiResponse, get_current_user
from api_routers.sales_cycle.dtos import (
    CreateOrderRequest,
    UpdateOrderRequest,
    CancelOrderRequest,
    CreateInvoiceFromOrderRequest,
)
from api_routers.sales_cycle.utils import (
    get_customer_info,
    next_document_number,
)
from api_routers.sales_cycle.service import create_order, update_order_status_after_delivery
from api_routers.sales_cycle.picking_service import (
    InsufficientStockError,
    reserve_order_items,
    release_order_reservations,
    create_picking_list,
    cancel_order_picking_lists,
)
from core.application.security.authorization import get_current_user_context

router = APIRouter(prefix="", tags=["sales-orders"])

PERM = {
    "create": "sales.create_order",
    "update": "sales.update_order",
    "confirm": "sales.confirm_order",
    "cancel": "sales.cancel_order",
    "invoice": "sales.create_invoice",
}


def _check_perm(perm: str):
    _ctx = get_current_user_context()
    if _ctx and not _ctx.has_permission(perm):
        raise HTTPException(status_code=403, detail="ليس لديك الصلاحية المطلوبة")


def _serialize_order(row, items=None) -> dict:
    data = {
        "id": row["id"],
        "order_number": row["order_number"],
        "customer_id": str(row["customer_id"]),
        "customer_name": row["customer_name"],
        "currency": row["currency"],
        "source_type": row.get("source_type"),
        "source_id": row.get("source_id"),
        "quotation_id": row.get("quotation_id"),
        "order_date": row["order_date"].isoformat() if row.get("order_date") else None,
        "expected_delivery_date": row["expected_delivery_date"].isoformat()
                                  if row.get("expected_delivery_date") else None,
        "actual_delivery_date": row["actual_delivery_date"].isoformat()
                                if row.get("actual_delivery_date") else None,
        "status": row["status"],
        "priority": row["priority"],
        "global_discount_percent": float(row["global_discount_percent"] or 0),
        "global_discount_amount": float(row["global_discount_amount"] or 0),
        "subtotal": float(row["subtotal"] or 0),
        "total_discount": float(row["total_discount"] or 0),
        "amount_after_discount": float(row["amount_after_discount"] or 0),
        "total_tax": float(row["total_tax"] or 0),
        "shipping_cost": float(row["shipping_cost"] or 0),
        "grand_total": float(row["grand_total"] or 0),
        "shipping_method": row.get("shipping_method"),
        "tracking_number": row.get("tracking_number"),
        "carrier": row.get("carrier"),
        "payment_status": row.get("payment_status", "pending"),
        "payment_terms": row.get("payment_terms"),
        "due_date": row["due_date"].isoformat() if row.get("due_date") else None,
        "invoice_id": row.get("invoice_id"),
        "invoice_number": row.get("invoice_number"),
        "invoiced_date": row["invoiced_date"].isoformat() if row.get("invoiced_date") else None,
        "invoiced_amount": float(row["invoiced_amount"] or 0),
        "billing_address": row.get("billing_address"),
        "shipping_address": row.get("shipping_address"),
        "notes": row.get("notes"),
        "internal_notes": row.get("internal_notes"),
        "branch_id": row.get("branch_id"),
        "created_by": row.get("created_by"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "delivery_progress": None,
    }
    if items is not None:
        data["items"] = items
    return data


def _serialize_order_item(row) -> dict:
    return {
        "id": row["id"],
        "product_id": str(row["product_id"]),
        "product_code": row["product_code"],
        "product_name": row["product_name"],
        "quantity": float(row["quantity"]),
        "unit_price": float(row["unit_price"]),
        "discount_percent": float(row["discount_percent"] or 0),
        "tax_percent": float(row["tax_percent"] or 0),
        "unit": row["unit"],
        "delivered_quantity": float(row["delivered_quantity"] or 0),
        "returned_quantity": float(row["returned_quantity"] or 0),
        "reserved_quantity": float(row["reserved_quantity"] or 0) if "reserved_quantity" in row else 0,
        "notes": row["notes"],
        "subtotal": float(row["subtotal"] or 0),
        "discount_amount": float(row["discount_amount"] or 0),
        "amount_after_discount": float(row["amount_after_discount"] or 0),
        "tax_amount": float(row["tax_amount"] or 0),
        "total": float(row["total"] or 0),
    }


def _get_order(uow, order_id: str):
    row = uow.session.execute(
        text("SELECT * FROM sales_orders WHERE id = :id"),
        {"id": order_id},
    ).mappings().first()
    if not row:
        return None
    items = uow.session.execute(
        text("SELECT * FROM order_items WHERE order_id = :oid ORDER BY id"),
        {"oid": order_id},
    ).mappings().all()
    ordered = sum(float(i["quantity"]) for i in items)
    delivered = sum(float(i["delivered_quantity"] or 0) for i in items)
    progress = round(delivered / ordered * 100, 2) if ordered else 0
    return row, [_serialize_order_item(i) for i in items], progress


@router.post("/api/sales/orders", response_model=ApiResponse)
async def create_order_endpoint(request: CreateOrderRequest,
                                current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["create"])
    try:
        with bootstrap.uow() as uow:
            customer = get_customer_info(uow, request.customer_id) \
                if request.customer_id else None
            if not customer:
                return ApiResponse(success=False, message="العميل غير موجود",
                                   errors=["العميل غير موجود"])

            lines = []
            if request.lines:
                lines = [
                    {
                        "product_id": ln.product_id,
                        "quantity": ln.quantity,
                        "unit_price": ln.unit_price,
                        "discount_percent": ln.discount_percent,
                        "tax_percent": ln.tax_percent,
                        "unit": ln.unit,
                        "notes": ln.notes,
                    }
                    for ln in request.lines
                ]

            # إنشاء أمر من عرض سعر مقبول (يتم جلب الأسطر منه)
            if not lines and request.quotation_id:
                quote = uow.session.execute(
                    text("SELECT * FROM sales_quotations WHERE id = :id"),
                    {"id": request.quotation_id},
                ).mappings().first()
                if not quote or quote["status"] not in ("accepted", "converted"):
                    return ApiResponse(success=False,
                                       message="عرض السعر غير موجود أو غير مقبول")
                quote_items = uow.session.execute(
                    text("SELECT * FROM quotation_items WHERE quotation_id = :qid ORDER BY id"),
                    {"qid": request.quotation_id},
                ).mappings().all()
                lines = [
                    {
                        "product_id": str(i["product_id"]),
                        "quantity": float(i["quantity"]),
                        "unit_price": float(i["unit_price"]),
                        "discount_percent": float(i["discount_percent"] or 0),
                        "tax_percent": float(i["tax_percent"] or 0),
                        "unit": i["unit"],
                        "notes": i["notes"],
                    }
                    for i in quote_items
                ]

            if not lines:
                return ApiResponse(success=False, message="يجب تحديد عنصر واحد على الأقل",
                                   errors=["لا توجد عناصر في الأمر"])

            currency = request.currency or customer.get("currency") or "USD"
            order = create_order(
                uow,
                customer_id=request.customer_id,
                customer_name=customer.get("name") or request.customer_name or "",
                currency=currency,
                created_by=current_user.get("username", "system"),
                lines=lines,
                order_date=request.order_date,
                expected_delivery_date=request.expected_delivery_date,
                quotation_id=request.quotation_id,
                priority=request.priority or "normal",
                global_discount_percent=request.global_discount_percent,
                global_discount_amount=request.global_discount_amount,
                shipping_cost=request.shipping_cost,
                shipping_method=request.shipping_method,
                tracking_number=request.tracking_number,
                carrier=request.carrier,
                payment_terms=request.payment_terms,
                due_date=request.due_date,
                billing_address=request.billing_address,
                shipping_address=request.shipping_address,
                notes=request.notes,
                internal_notes=request.internal_notes,
                branch_id=request.branch_id,
            )
            uow.commit()
            return ApiResponse(success=True, message="تم إنشاء أمر البيع بنجاح",
                               data={"id": order["id"], "order_number": order["order_number"]})
    except Exception as e:
        logger.error(f"Error creating order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/orders", response_model=ApiResponse)
async def list_orders(
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
            if customer_id:
                where.append("customer_id = :customer_id")
                params["customer_id"] = customer_id
            if status:
                where.append("status = :status")
                params["status"] = status
            if from_date:
                where.append("order_date >= :from_date")
                params["from_date"] = from_date
            if to_date:
                where.append("order_date <= :to_date")
                params["to_date"] = to_date
            if q:
                where.append("(customer_name ILIKE :q OR order_number ILIKE :q)")
                params["q"] = f"%{q}%"

            where_sql = (" WHERE " + " AND ".join(where)) if where else ""
            total = uow.session.execute(
                text(f"SELECT COUNT(*) AS c FROM sales_orders{where_sql}"),
                params,
            ).mappings().first()["c"]

            params["skip"] = skip
            params["limit"] = limit
            rows = uow.session.execute(
                text(f"""
                    SELECT * FROM sales_orders{where_sql}
                    ORDER BY created_at DESC LIMIT :limit OFFSET :skip
                """),
                params,
            ).mappings().all()

            return ApiResponse(success=True, message="تم جلب أوامر البيع",
                               data={"items": [_serialize_order(r) for r in rows],
                                     "total": total, "skip": skip, "limit": limit})
    except Exception as e:
        logger.error(f"Error listing orders: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/orders/statistics", response_model=ApiResponse)
async def get_statistics(current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            total = uow.session.execute(
                text("SELECT COUNT(*) AS c FROM sales_orders")
            ).mappings().first()["c"]

            by_status_rows = uow.session.execute(
                text("SELECT status, COUNT(*) AS c, COALESCE(SUM(grand_total), 0) AS v "
                     "FROM sales_orders GROUP BY status")
            ).mappings().all()
            by_status = {r["status"]: {"count": r["c"], "value": float(r["v"])}
                         for r in by_status_rows}

            open_value = uow.session.execute(
                text("SELECT COALESCE(SUM(grand_total), 0) AS v FROM sales_orders "
                     "WHERE status NOT IN ('cancelled', 'delivered')")
            ).mappings().first()["v"]

            return ApiResponse(success=True,
                               data={"total": total, "by_status": by_status,
                                     "open_value": float(open_value)})
    except Exception as e:
        logger.error(f"Error getting order statistics: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/sales/orders/{order_id}", response_model=ApiResponse)
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    try:
        with bootstrap.uow() as uow:
            found = _get_order(uow, order_id)
            if not found:
                return ApiResponse(success=False, message="أمر البيع غير موجود")
            row, items, progress = found
            data = _serialize_order(row, items)
            data["delivery_progress"] = progress
            return ApiResponse(success=True, data=data)
    except Exception as e:
        logger.error(f"Error getting order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.patch("/api/sales/orders/{order_id}", response_model=ApiResponse)
async def update_order(order_id: str, request: UpdateOrderRequest,
                       current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["update"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM sales_orders WHERE id = :id"),
                {"id": order_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="أمر البيع غير موجود")
            if row["status"] not in ("draft", "confirmed", "in_progress",
                                     "partially_delivered"):
                return ApiResponse(success=False,
                                   message="لا يمكن تعديل الأمر في الحالة الحالية")

            sets, params = ["updated_at = NOW()"], {"id": order_id}
            field_map = {
                "expected_delivery_date": "expected_delivery_date",
                "priority": "priority",
                "shipping_method": "shipping_method",
                "tracking_number": "tracking_number",
                "carrier": "carrier",
                "payment_terms": "payment_terms",
                "due_date": "due_date",
                "notes": "notes",
                "internal_notes": "internal_notes",
            }
            for attr, col in field_map.items():
                val = getattr(request, attr, None)
                if val is not None:
                    sets.append(f"{col} = :{col}")
                    params[col] = val

            uow.session.execute(
                text(f"UPDATE sales_orders SET {', '.join(sets)} WHERE id = :id"),
                params,
            )
            uow.commit()
            return ApiResponse(success=True, message="تم تحديث أمر البيع بنجاح")
    except Exception as e:
        logger.error(f"Error updating order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/orders/{order_id}/confirm", response_model=ApiResponse)
async def confirm_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """
    تأكيد أمر البيع:
      - حجز المخزون (reserve) - يرفض التأكيد عند نقص الكميات مع إبقاء الحالة
      - إنشاء قائمة انتقاء تلقائية
    """
    _check_perm(PERM["confirm"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM sales_orders WHERE id = :id"),
                {"id": order_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="أمر البيع غير موجود")
            if row["status"] not in ("draft", "in_progress"):
                return ApiResponse(success=False,
                                   message="لا يمكن تأكيد الأمر في الحالة الحالية")

            username = current_user.get("username", "system")
            try:
                reserve_order_items(uow, order_id=order_id, created_by=username)
            except InsufficientStockError as e:
                return ApiResponse(success=False, message=str(e), errors=[
                    {
                        "product_id": d["product_id"],
                        "product_name": d["product_name"],
                        "required": d["required"],
                        "available": d["available"],
                    }
                    for d in e.details
                ])

            uow.session.execute(
                text("UPDATE sales_orders SET status = 'confirmed', updated_at = NOW() "
                     "WHERE id = :id"),
                {"id": order_id},
            )
            picking = create_picking_list(uow, order_id=order_id, created_by=username)
            uow.commit()
            return ApiResponse(
                success=True,
                message="تم تأكيد أمر البيع وحجز المخزون بنجاح",
                data={"id": order_id, "status": "confirmed",
                      "picking_list": picking},
            )
    except Exception as e:
        logger.error(f"Error confirming order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/orders/{order_id}/ship", response_model=ApiResponse)
async def ship_order(order_id: str, current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["update"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM sales_orders WHERE id = :id"),
                {"id": order_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="أمر البيع غير موجود")
            if row["status"] not in ("confirmed", "in_progress"):
                return ApiResponse(success=False,
                                   message="يجب تأكيد الأمر قبل الشحن")
            uow.session.execute(
                text("UPDATE sales_orders SET status = 'in_progress', updated_at = NOW() "
                     "WHERE id = :id"),
                {"id": order_id},
            )
            uow.commit()
            return ApiResponse(success=True, message="تم تسجيل الشحن بنجاح")
    except Exception as e:
        logger.error(f"Error shipping order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/orders/{order_id}/deliver", response_model=ApiResponse)
async def deliver_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """
    تسليم الطلبية - إنشاء إشعار تسليم للكميات المتبقية غير المسلّمة
    """
    _check_perm(PERM["update"])
    try:
        from api_routers.sales_cycle.deliveries_router import create_delivery_record

        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM sales_orders WHERE id = :id"),
                {"id": order_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="أمر البيع غير موجود")
            if row["status"] not in ("confirmed", "in_progress", "partially_delivered"):
                return ApiResponse(success=False,
                                   message="يجب تأكيد الأمر قبل التسليم")

            order_obj = _get_order(uow, order_id)
            if not order_obj:
                return ApiResponse(success=False, message="أمر البيع غير موجود")
            _, items, _ = order_obj

            remaining = []
            for it in items:
                rem = float(it["quantity"]) - float(it["delivered_quantity"])
                if rem > 0:
                    remaining.append({"product_id": it["product_id"], "quantity": rem})

            if not remaining:
                return ApiResponse(success=False, message="تم تسليم كامل كميات الأمر")

            delivery = create_delivery_record(
                uow, order_id=order_id, lines=remaining,
                created_by=current_user.get("username", "system"),
            )
            uow.commit()
            return ApiResponse(
                success=True,
                message="تم إنشاء إشعار التسليم بنجاح",
                data={"id": delivery["id"], "delivery_number": delivery["delivery_number"]},
            )
    except Exception as e:
        logger.error(f"Error delivering order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/orders/{order_id}/cancel", response_model=ApiResponse)
async def cancel_order(order_id: str, request: CancelOrderRequest,
                       current_user: dict = Depends(get_current_user)):
    _check_perm(PERM["cancel"])
    try:
        with bootstrap.uow() as uow:
            row = uow.session.execute(
                text("SELECT id, status FROM sales_orders WHERE id = :id"),
                {"id": order_id},
            ).mappings().first()
            if not row:
                return ApiResponse(success=False, message="أمر البيع غير موجود")
            if row["status"] in ("cancelled", "delivered"):
                return ApiResponse(success=False,
                                   message="لا يمكن إلغاء الأمر في الحالة الحالية")
            reason = (request.reason or "").strip()
            uow.session.execute(
                text("UPDATE sales_orders SET status = 'cancelled', "
                     "notes = COALESCE(NULLIF(:reason, ''), notes), updated_at = NOW() "
                     "WHERE id = :id"),
                {"id": order_id, "reason": reason},
            )
            released = release_order_reservations(uow, order_id=order_id)
            cancelled_pickings = cancel_order_picking_lists(uow, order_id=order_id,
                                                            reason=reason)
            uow.commit()
            return ApiResponse(
                success=True,
                message="تم إلغاء أمر البيع وتحرير المخزون المحجوز",
                data={"id": order_id, "status": "cancelled",
                      "reservations_released": released,
                      "picking_lists_cancelled": cancelled_pickings},
            )
    except Exception as e:
        logger.error(f"Error cancelling order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/sales/orders/{order_id}/invoice", response_model=ApiResponse)
async def create_invoice_from_order(
    order_id: str, request: CreateInvoiceFromOrderRequest,
    current_user: dict = Depends(get_current_user),
):
    _check_perm(PERM["invoice"])
    try:
        from core.application.invoicing.commands import (
            CreateInvoiceCommand, AddInvoiceLineCommand,
        )
        from decimal import Decimal

        command_bus = bootstrap.container.resolve("command_bus")

        with bootstrap.uow() as uow:
            found = _get_order(uow, order_id)
            if not found:
                return ApiResponse(success=False, message="أمر البيع غير موجود")
            row, items, _ = found
            if row["status"] in ("draft", "cancelled"):
                return ApiResponse(success=False,
                                   message="يجب تأكيد الأمر قبل إصدار الفاتورة")
            if row.get("invoice_id"):
                return ApiResponse(success=False,
                                   message="تم إصدار فاتورة لهذا الأمر مسبقاً")

            qty_on = request.quantity_on or "delivered"
            total_amount = Decimal("0")
            for it in items:
                qty = (float(it["delivered_quantity"]) if qty_on == "delivered"
                       and float(it["delivered_quantity"]) > 0
                       else float(it["quantity"]))
                total_amount += Decimal(str(it["unit_price"] * qty))

            create_cmd = CreateInvoiceCommand(
                customer_id=str(row["customer_id"]),
                customer_name=row["customer_name"],
                site_id=None,
                site_name=None,
                currency=request.payment_currency or row["currency"],
                payment_type=request.payment_type or "cash",
                payment_currency=request.payment_currency or row["currency"],
                fund_id=request.fund_id,
                notes=request.notes or (row.get("notes") or ""),
                created_by=current_user.get("username", "system"),
            )
            result = command_bus.dispatch(create_cmd)

            invoice_id = None
            if isinstance(result, dict):
                invoice_id = result.get("id")
            elif hasattr(result, "id"):
                invoice_id = result.id

            for it in items:
                qty = (float(it["delivered_quantity"]) if qty_on == "delivered"
                       and float(it["delivered_quantity"]) > 0
                       else float(it["quantity"]))
                if qty <= 0:
                    continue
                line_cmd = AddInvoiceLineCommand(
                    invoice_id=invoice_id,
                    product_code=it["product_code"] or "",
                    product_name=it["product_name"],
                    quantity=Decimal(str(qty)),
                    unit_price=Decimal(str(it["unit_price"])),
                    currency=request.payment_currency or row["currency"],
                    notes=it.get("notes") or "",
                )
                command_bus.dispatch(line_cmd)

                uow.session.execute(
                    text("""
                        UPDATE order_items SET invoiced_qty =
                            COALESCE(invoiced_qty, 0) + :qty, updated_at = NOW()
                        WHERE order_id = :oid AND CAST(product_id AS TEXT) = :pid
                    """),
                    {"qty": float(qty), "oid": order_id, "pid": str(it["product_id"])},
                )

            uow.session.execute(
                text("UPDATE sales_orders SET invoice_id = :invoice_id, "
                     "invoiced_date = NOW(), invoiced_amount = :amount, "
                     "payment_status = 'invoiced', updated_at = NOW() WHERE id = :id"),
                {"invoice_id": invoice_id, "amount": float(total_amount), "id": order_id},
            )
            ids = uow.session.execute(
                text("SELECT invoice_ids FROM sales_orders WHERE id = :oid"),
                {"oid": order_id},
            ).mappings().first()
            existing_ids = ids["invoice_ids"] if ids else None
            if isinstance(existing_ids, str):
                try:
                    existing_ids = json.loads(existing_ids)
                except Exception:
                    existing_ids = []
            if not isinstance(existing_ids, list):
                existing_ids = []
            if invoice_id not in existing_ids:
                existing_ids.append(invoice_id)
            uow.session.execute(
                text("UPDATE sales_orders SET invoice_ids = CAST(:ids AS jsonb), "
                     "updated_at = NOW() WHERE id = :oid"),
                {"ids": json.dumps(existing_ids), "oid": order_id},
            )
            try:
                from api_routers.sales_cycle.service import mark_order_invoiced
                mark_order_invoiced(uow, order_id)
            except Exception:
                pass
            uow.commit()
            return ApiResponse(success=True, message="تم إصدار الفاتورة بنجاح",
                               data={"invoice_id": invoice_id,
                                     "lines_added": len(items)})
    except Exception as e:
        logger.error(f"Error creating invoice from order: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])