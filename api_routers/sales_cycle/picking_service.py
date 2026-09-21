# api_routers/sales_cycle/picking_service.py
"""
M3.1 Sales Cycle - Picking & Shipping Service
حجز المخزون + قوائم الانتقاء + الشحنات

يتكامل مع دورة المبيعات الحالية:
  - الحجز عند تأكيد أمر البيع (confirm)
  - تحرير الحجز عند الإلغاء أو اكتمال التسليم
  - قائمتا انتقاء وشحن مرتبطتان بالأمر
"""

import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import text

from api_routers.sales_cycle.utils import next_document_number


# -----------------------------------------------------------------------------
# استثناءات
# -----------------------------------------------------------------------------

class InsufficientStockError(ValueError):
    """نقص الكمية المتاحة لحجز مخزون أمر بيع"""

    def __init__(self, details: List[Dict[str, Any]]):
        self.details = details
        super().__init__(self.to_message())

    def to_message(self) -> str:
        lines = []
        for d in self.details:
            lines.append(
                f"{d.get('product_name', d.get('product_id'))}: المطلوب "
                f"{d.get('required')} والمتاح {d.get('available')}"
            )
        return "كمية غير كافية في المخزون: " + " | ".join(lines)


# الحالات التي يُعتبر فيها حجز الأمر نشطاً
RESERVED_ACTIVE_STATUSES_EXPR = "status NOT IN ('draft', 'cancelled', 'delivered')"


# -----------------------------------------------------------------------------
# أدوات مساعدة
# -----------------------------------------------------------------------------

def _jsonb(value: Optional[Dict[str, Any]]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def get_product_on_hand(uow, product_id: str) -> float:
    """
    الكمية الفعلية في المخزون (On Hand):
      - تُحسب من دفتر حركات المخزون stock_movements (المرجع المعتمد).
      - إذا لم يوجد أي حركة للمنتج، نعود إلى products.stock_quantity.
    """
    rows = uow.session.execute(
        text("""
            SELECT COALESCE(SUM(CASE WHEN movement_type IN
                       ('purchase', 'return', 'adjustment_in', 'transfer_in')
                       THEN quantity ELSE 0 END), 0) -
                   COALESCE(SUM(CASE WHEN movement_type IN
                       ('sale', 'adjustment_out', 'transfer_out', 'damage', 'expired')
                       THEN quantity ELSE 0 END), 0) AS on_hand
            FROM stock_movements
            WHERE entity_type = 'product' AND entity_id = :pid
        """),
        {"pid": product_id},
    ).mappings().first()

    if not rows:
        return 0.0

    try:
        cnt = uow.session.execute(
            text("SELECT COUNT(*) AS c FROM stock_movements "
                 "WHERE entity_type = 'product' AND entity_id = :pid"),
            {"pid": product_id},
        ).mappings().first()["c"]
    except Exception:
        cnt = 1

    if cnt == 0:
        prod = uow.session.execute(
            text("SELECT stock_quantity FROM products WHERE CAST(id AS TEXT) = :pid"),
            {"pid": product_id},
        ).mappings().first()
        return float(prod["stock_quantity"] or 0) if prod else 0.0

    return float(rows["on_hand"] or 0)


def get_reserved_quantity(uow, product_id: str, exclude_order_id: Optional[str] = None) -> float:
    """إجمالي الكميات المحجوزة للمنتج عبر أوامر البيع النشطة."""
    where = "oi.reserved_quantity > 0"
    params: Dict[str, Any] = {"pid": product_id}
    if exclude_order_id:
        where += " AND oi.order_id != :exclude"
        params["exclude"] = exclude_order_id

    row = uow.session.execute(
        text(f"""
            SELECT COALESCE(SUM(oi.reserved_quantity), 0) AS r
            FROM order_items oi
            WHERE oi.product_id = :pid AND {where}
              AND oi.order_id IN (
                  SELECT id FROM sales_orders WHERE {RESERVED_ACTIVE_STATUSES_EXPR}
              )
        """),
        params,
    ).mappings().first()
    return float(row["r"] or 0) if row else 0.0


def get_product_availability(uow, product_id: str,
                             exclude_order_id: Optional[str] = None) -> Dict[str, float]:
    """الكمية المتاحة = الفعلية - المحجوزة (باستثناء الأمر الحالي اختيارياً)."""
    on_hand = get_product_on_hand(uow, product_id)
    reserved = get_reserved_quantity(uow, product_id, exclude_order_id)
    return {
        "on_hand": round(on_hand, 3),
        "reserved": round(reserved, 3),
        "available": round(on_hand - reserved, 3),
    }


# -----------------------------------------------------------------------------
# الحجز / التحرير
# -----------------------------------------------------------------------------

def reserve_order_items(uow, order_id: str, created_by: str) -> Dict[str, Any]:
    """
    حجز كميات الأمر في order_items.reserved_quantity.
    يرفع InsufficientStockError عند عدم كفاية المخزون (دون حفظ أي تغيير).
    """
    items = uow.session.execute(
        text("SELECT * FROM order_items WHERE order_id = :oid ORDER BY id"),
        {"oid": order_id},
    ).mappings().all()
    if not items:
        raise ValueError("أمر البيع لا يحتوي على عناصر")

    shortages = []
    updates = []
    for it in items:
        remaining = float(it["quantity"]) - float(it["delivered_quantity"] or 0)
        if remaining <= 0:
            continue
        availability = get_product_availability(
            uow, str(it["product_id"]), exclude_order_id=order_id
        )
        if availability["available"] < remaining - 0.001:
            shortages.append({
                "product_id": str(it["product_id"]),
                "product_name": it["product_name"],
                "required": remaining,
                "available": availability["available"],
            })
        else:
            updates.append((str(it["id"]), remaining))

    if shortages:
        raise InsufficientStockError(shortages)

    for item_id, qty in updates:
        uow.session.execute(
            text("UPDATE order_items SET reserved_quantity = :qty, updated_at = NOW() "
                 "WHERE id = :id"),
            {"qty": qty, "id": item_id},
        )

    uow.session.execute(
        text("UPDATE sales_orders SET reservation_status = 'reserved', updated_at = NOW() "
             "WHERE id = :oid"),
        {"oid": order_id},
    )

    return {
        "order_id": order_id,
        "reserved_lines": len(updates),
        "reserved_total": round(sum(q for _, q in updates), 2),
    }


def release_order_reservations(uow, order_id: str) -> int:
    """تحرير كل الحجوزات الخاصة بالأمر."""
    res = uow.session.execute(
        text("UPDATE order_items SET reserved_quantity = 0, updated_at = NOW() "
             "WHERE order_id = :oid"),
        {"oid": order_id},
    )
    uow.session.execute(
        text("UPDATE sales_orders SET reservation_status = 'released', updated_at = NOW() "
             "WHERE id = :oid"),
        {"oid": order_id},
    )
    return res.rowcount or 0


def release_delivered_quantity(uow, order_id: str, product_id: str, qty: float) -> None:
    """
    تحرير الجزء المسلّم من الحجز عند اكتمال التسليم.
    """
    if qty <= 0:
        return
    uow.session.execute(
        text("""
            UPDATE order_items SET reserved_quantity =
                GREATEST(reserved_quantity - :qty, 0), updated_at = NOW()
            WHERE order_id = :oid AND CAST(product_id AS TEXT) = :pid
        """),
        {"qty": qty, "oid": order_id, "pid": product_id},
    )


# -----------------------------------------------------------------------------
# قوائم الانتقاء
# -----------------------------------------------------------------------------

def create_picking_list(uow, order_id: str, created_by: str,
                        warehouse_id: Optional[str] = None) -> Dict[str, Any]:
    """إنشاء قائمة انتقاء تلقائياً بعد تأكيد الأمر (بكميات البنود المتبقية)."""
    order = uow.session.execute(
        text("SELECT * FROM sales_orders WHERE id = :id"),
        {"id": order_id},
    ).mappings().first()
    if not order:
        raise ValueError("أمر البيع غير موجود")

    picking_id = str(uuid4())
    picking_number = next_document_number(
        uow, "PK", "sales_picking_lists", "picking_number"
    )

    uow.session.execute(
        text("""
            INSERT INTO sales_picking_lists (
                id, picking_number, order_id, order_number, customer_id,
                customer_name, status, warehouse_id, created_by
            ) VALUES (
                :id, :picking_number, :order_id, :order_number, :customer_id,
                :customer_name, 'pending', :warehouse_id, :created_by
            )
        """),
        {
            "id": picking_id,
            "picking_number": picking_number,
            "order_id": order_id,
            "order_number": order["order_number"],
            "customer_id": str(order["customer_id"]),
            "customer_name": order["customer_name"],
            "warehouse_id": warehouse_id,
            "created_by": created_by,
        },
    )

    items = uow.session.execute(
        text("SELECT * FROM order_items WHERE order_id = :oid ORDER BY id"),
        {"oid": order_id},
    ).mappings().all()

    for it in items:
        requested = float(it["quantity"]) - float(it["delivered_quantity"] or 0)
        if requested <= 0:
            continue
        uow.session.execute(
            text("""
                INSERT INTO sales_picking_items (
                    id, picking_list_id, order_item_id, product_id, product_code,
                    product_name, requested_quantity, picked_quantity, unit, warehouse_id
                ) VALUES (
                    :id, :pl_id, :order_item_id, :product_id, :product_code,
                    :product_name, :requested_quantity, 0, :unit, :warehouse_id
                )
            """),
            {
                "id": str(uuid4()),
                "pl_id": picking_id,
                "order_item_id": str(it["id"]),
                "product_id": str(it["product_id"]),
                "product_code": it["product_code"],
                "product_name": it["product_name"],
                "requested_quantity": requested,
                "unit": it["unit"] or "pcs",
                "warehouse_id": warehouse_id,
            },
        )

    return {"id": picking_id, "picking_number": picking_number}


def _get_picking(uow, picking_id: str):
    row = uow.session.execute(
        text("SELECT * FROM sales_picking_lists WHERE id = :id"),
        {"id": picking_id},
    ).mappings().first()
    if not row:
        return None
    items = uow.session.execute(
        text("SELECT * FROM sales_picking_items "
             "WHERE picking_list_id = :pid ORDER BY id"),
        {"pid": picking_id},
    ).mappings().all()
    return row, items


def _serialize_picking(row, items=None) -> Dict[str, Any]:
    data = {
        "id": row["id"],
        "picking_number": row["picking_number"],
        "order_id": row["order_id"],
        "order_number": row["order_number"],
        "customer_id": str(row["customer_id"]),
        "customer_name": row["customer_name"],
        "status": row["status"],
        "warehouse_id": row.get("warehouse_id"),
        "picker_id": row.get("picker_id"),
        "cancellation_reason": row.get("cancellation_reason"),
        "created_by": row.get("created_by"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }
    if items is not None:
        data["items"] = items
    return data


def _serialize_picking_item(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "order_item_id": row["order_item_id"],
        "product_id": str(row["product_id"]),
        "product_code": row["product_code"],
        "product_name": row["product_name"],
        "requested_quantity": float(row["requested_quantity"] or 0),
        "picked_quantity": float(row["picked_quantity"] or 0),
        "unit": row["unit"] or "pcs",
        "warehouse_id": row.get("warehouse_id"),
        "notes": row.get("notes"),
    }


def pick_picking_list(uow, picking_id: str, lines: List[Dict[str, Any]],
                      warehouse_id: Optional[str] = None,
                      created_by: str = "system") -> Dict[str, Any]:
    """
    تسجيل الكميات المنتقاة. يتحقق ألا تتجاوز الكمية المطلوبة،
    ويحدّث حالة القائمة إلى 'picking'.
    """
    row = uow.session.execute(
        text("SELECT * FROM sales_picking_lists WHERE id = :id"),
        {"id": picking_id},
    ).mappings().first()
    if not row:
        raise ValueError("قائمة الانتقاء غير موجودة")
    if row["status"] in ("shipped", "cancelled"):
        raise ValueError("لا يمكن الانتقال على قائمة انتهت حالتها")
    if not lines:
        raise ValueError("يجب تحديد عنصر واحد على الأقل")

    if warehouse_id:
        uow.session.execute(
            text("UPDATE sales_picking_lists SET warehouse_id = :wid, "
                 "updated_at = NOW() WHERE id = :id"),
            {"wid": warehouse_id, "id": picking_id},
        )
        uow.session.execute(
            text("UPDATE sales_picking_items SET warehouse_id = :wid "
                 "WHERE picking_list_id = :pid"),
            {"wid": warehouse_id, "pid": picking_id},
        )

    for ln in lines:
        order_item_id = ln.get("order_item_id") or ln.get("id")
        picked = float(ln.get("picked_quantity") or 0)
        pit = uow.session.execute(
            text("SELECT * FROM sales_picking_items "
                 "WHERE picking_list_id = :pid AND order_item_id = :oiid"),
            {"pid": picking_id, "oiid": order_item_id},
        ).mappings().first()
        if not pit:
            raise ValueError(f"المنتج المرتبط بالبند {order_item_id} غير موجود في القائمة")
        if picked > float(pit["requested_quantity"]) + 0.001:
            raise ValueError(
                f"الكمية المنتقاة ({picked}) تتجاوز المطلوب ({pit['requested_quantity']}) "
                f"للمنتج {pit['product_name']}"
            )
        uow.session.execute(
            text("UPDATE sales_picking_items SET picked_quantity = :qty "
                 "WHERE id = :id"),
            {"qty": picked, "id": str(pit["id"])},
        )

    uow.session.execute(
        text("UPDATE sales_picking_lists SET status = 'picking', "
             "picker_id = :picker, updated_at = NOW() WHERE id = :id"),
        {"picker": created_by, "id": picking_id},
    )
    return {"id": picking_id, "status": "picking"}


def pack_picking_list(uow, picking_id: str, created_by: str = "system") -> None:
    row = uow.session.execute(
        text("SELECT status FROM sales_picking_lists WHERE id = :id"),
        {"id": picking_id},
    ).mappings().first()
    if not row:
        raise ValueError("قائمة الانتقاء غير موجودة")
    if row["status"] in ("packed", "shipped", "cancelled"):
        raise ValueError("لا يمكن التغليف في الحالة الحالية")
    uow.session.execute(
        text("UPDATE sales_picking_lists SET status = 'packed', updated_at = NOW() "
             "WHERE id = :id"),
        {"id": picking_id},
    )


def cancel_picking_list(uow, picking_id: str, reason: Optional[str] = None) -> None:
    row = uow.session.execute(
        text("SELECT status FROM sales_picking_lists WHERE id = :id"),
        {"id": picking_id},
    ).mappings().first()
    if not row:
        raise ValueError("قائمة الانتقاء غير موجودة")
    if row["status"] in ("shipped", "cancelled"):
        raise ValueError("لا يمكن إلغاء قائمة انتهت حالتها")
    uow.session.execute(
        text("UPDATE sales_picking_lists SET status = 'cancelled', "
             "cancellation_reason = :reason, updated_at = NOW() WHERE id = :id"),
        {"id": picking_id, "reason": reason},
    )


def cancel_order_picking_lists(uow, order_id: str, reason: Optional[str] = None) -> int:
    res = uow.session.execute(
        text("UPDATE sales_picking_lists SET status = 'cancelled', "
             "cancellation_reason = :reason, updated_at = NOW() "
             "WHERE order_id = :oid AND status NOT IN ('shipped', 'cancelled')"),
        {"oid": order_id, "reason": reason},
    )
    return res.rowcount or 0


# -----------------------------------------------------------------------------
# الشحنات
# -----------------------------------------------------------------------------

def create_shipping(uow, picking_id: str, created_by: str, **data) -> Dict[str, Any]:
    """
    إنشاء شحنة من قائمة انتقاء: تُنقل الكميات المنتقاة إلى الشحنة،
    وتُحدّث حالة القائمة إلى 'shipped'.
    """
    found = _get_picking(uow, picking_id)
    if not found:
        raise ValueError("قائمة الانتقاء غير موجودة")
    picking, pitems = found
    if picking["status"] not in ("picking", "packed"):
        raise ValueError("يجب انتقاء القائمة قبل الشحن")
    pitems = [p for p in pitems if float(p["picked_quantity"] or 0) > 0]
    if not pitems:
        raise ValueError("قائمة الانتقاء بدون كميات منتقاة")

    shipping_id = str(uuid4())
    shipping_number = next_document_number(uow, "SH", "sales_shipping", "shipping_number")

    uow.session.execute(
        text("""
            INSERT INTO sales_shipping (
                id, shipping_number, order_id, order_number, picking_list_id,
                customer_id, customer_name, status, carrier, tracking_number,
                shipping_method, shipping_cost, destination_address,
                estimated_arrival, notes, created_by
            ) VALUES (
                :id, :shipping_number, :order_id, :order_number, :picking_list_id,
                :customer_id, :customer_name, 'created', :carrier, :tracking_number,
                :shipping_method, :shipping_cost,
                CAST(:destination_address AS jsonb),
                :estimated_arrival, :notes, :created_by
            )
        """),
        {
            "id": shipping_id,
            "shipping_number": shipping_number,
            "order_id": picking["order_id"],
            "order_number": picking["order_number"],
            "picking_list_id": picking_id,
            "customer_id": str(picking["customer_id"]),
            "customer_name": picking["customer_name"],
            "carrier": data.get("carrier"),
            "tracking_number": data.get("tracking_number"),
            "shipping_method": data.get("shipping_method"),
            "shipping_cost": float(data.get("shipping_cost") or 0),
            "destination_address": _jsonb(data.get("destination_address")),
            "estimated_arrival": data.get("estimated_arrival"),
            "notes": data.get("notes"),
            "created_by": created_by,
        },
    )

    for pit in pitems:
        uow.session.execute(
            text("""
                INSERT INTO sales_shipping_items (
                    id, shipping_id, picking_item_id, product_id, product_code,
                    product_name, packed_quantity, shipped_quantity, unit
                ) VALUES (
                    :id, :shipping_id, :picking_item_id, :product_id, :product_code,
                    :product_name, :packed_quantity, :packed_quantity, :unit
                )
            """),
            {
                "id": str(uuid4()),
                "shipping_id": shipping_id,
                "picking_item_id": str(pit["id"]),
                "product_id": str(pit["product_id"]),
                "product_code": pit["product_code"],
                "product_name": pit["product_name"],
                "packed_quantity": float(pit["picked_quantity"]),
                "unit": pit["unit"] or "pcs",
            },
        )

    uow.session.execute(
        text("UPDATE sales_picking_lists SET status = 'shipped', updated_at = NOW() "
             "WHERE id = :id"),
        {"id": picking_id},
    )

    return {"id": shipping_id, "shipping_number": shipping_number}


def _get_shipping(uow, shipping_id: str):
    row = uow.session.execute(
        text("SELECT * FROM sales_shipping WHERE id = :id"),
        {"id": shipping_id},
    ).mappings().first()
    if not row:
        return None
    items = uow.session.execute(
        text("SELECT * FROM sales_shipping_items WHERE shipping_id = :sid ORDER BY id"),
        {"sid": shipping_id},
    ).mappings().all()
    return row, items


def _serialize_shipping(row, items=None) -> Dict[str, Any]:
    data = {
        "id": row["id"],
        "shipping_number": row["shipping_number"],
        "order_id": row["order_id"],
        "order_number": row["order_number"],
        "picking_list_id": row.get("picking_list_id"),
        "customer_id": str(row["customer_id"]),
        "customer_name": row["customer_name"],
        "status": row["status"],
        "carrier": row.get("carrier"),
        "tracking_number": row.get("tracking_number"),
        "shipping_method": row.get("shipping_method"),
        "shipping_cost": float(row["shipping_cost"] or 0),
        "destination_address": row.get("destination_address"),
        "estimated_arrival": row["estimated_arrival"].isoformat()
                              if row.get("estimated_arrival") else None,
        "shipped_at": row["shipped_at"].isoformat() if row.get("shipped_at") else None,
        "delivered_at": row["delivered_at"].isoformat() if row.get("delivered_at") else None,
        "notes": row.get("notes"),
        "created_by": row.get("created_by"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
    }
    if items is not None:
        data["items"] = items
    return data


def _serialize_shipping_item(row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "picking_item_id": row.get("picking_item_id"),
        "product_id": str(row["product_id"]),
        "product_code": row["product_code"],
        "product_name": row["product_name"],
        "packed_quantity": float(row["packed_quantity"] or 0),
        "shipped_quantity": float(row["shipped_quantity"] or 0),
        "unit": row["unit"] or "pcs",
    }


def confirm_shipping(uow, shipping_id: str, created_by: str) -> None:
    """
    تأكيد الشحنة: الحالة → shipped، ترقية حالة الأمر إلى in_progress
    وتسجيل بيانات الناقل/التتبع لدى الأمر إن لم تكن موجودة.
    صرف المخزون: يُحرَّر الحجز مقابل الكميات المشحونة ويُحدَّث picked_qty.
    """
    row = uow.session.execute(
        text("SELECT * FROM sales_shipping WHERE id = :id"),
        {"id": shipping_id},
    ).mappings().first()
    if not row:
        raise ValueError("الشحنة غير موجودة")
    if row["status"] in ("shipped", "delivered", "cancelled"):
        raise ValueError("لا يمكن تأكيد شحنة في الحالة الحالية")

    uow.session.execute(
        text("UPDATE sales_shipping SET status = 'shipped', shipped_at = NOW(), "
             "updated_at = NOW() WHERE id = :id"),
        {"id": shipping_id},
    )

    uow.session.execute(
        text("""
            UPDATE sales_orders SET
                status = CASE WHEN status IN ('draft', 'confirmed') THEN 'in_progress'
                              ELSE status END,
                carrier = COALESCE(NULLIF(carrier, ''), :carrier, carrier),
                tracking_number = COALESCE(NULLIF(tracking_number, ''), :tracking, tracking_number),
                shipping_method = COALESCE(NULLIF(shipping_method, ''), :method, shipping_method),
                updated_at = NOW()
            WHERE id = :order_id
        """),
        {
            "order_id": row["order_id"],
            "carrier": row.get("carrier"),
            "tracking": row.get("tracking_number"),
            "method": row.get("shipping_method"),
        },
    )

    dispatch_shipping_inventory(uow, shipping_id=shipping_id, order_id=row["order_id"])


def dispatch_shipping_inventory(uow, shipping_id: str, order_id: str) -> Dict[str, Any]:
    """
    صرف المخزون عند تأكيد الشحنة (Inventory Dispatch):
      - لكل بند مشحون: يحرّر الحجز (reserved_quantity) مقابل الكمية المشحونة
        (لأن الشحنة خرجت من المخزن وستتحول إلى فاتورة).
      - يحدّث picked_qty الكلي على بند الأمر.
      - يحدّث reservation_status للأمر (partially_shipped / shipped).
    لا يُنشئ حركة مخزون 'sale' هنا: حركة البيع تُنشأ عند ترحيل الفاتورة
    (post_invoice_handler) لتجنب الازدواجية.
    """
    items = uow.session.execute(
        text("SELECT * FROM sales_shipping_items WHERE shipping_id = :sid ORDER BY id"),
        {"sid": shipping_id},
    ).mappings().all()
    if not items:
        return {"shipped_lines": 0, "released_total": 0.0}

    released_total = 0.0
    shipped_product_rows = []
    for it in items:
        shipped = float(it["shipped_quantity"] or 0)
        if shipped <= 0:
            continue
        res = uow.session.execute(
            text("""
                UPDATE order_items SET reserved_quantity =
                    GREATEST(reserved_quantity - :qty, 0),
                    picked_qty = COALESCE(picked_qty, 0) + :qty,
                    updated_at = NOW()
                WHERE order_id = :oid AND CAST(product_id AS TEXT) = :pid
            """),
            {"qty": shipped, "oid": order_id, "pid": str(it["product_id"])},
        )
        if res.rowcount:
            released_total += shipped
        shipped_product_rows.append({
            "product_id": str(it["product_id"]),
            "product_code": it["product_code"],
            "product_name": it["product_name"],
            "shipped_quantity": shipped,
        })

    # تحديد حالة حجز الأمر بناءً على ما شُحن مقابل المطلوب
    stats = uow.session.execute(
        text("""
            SELECT COALESCE(SUM(quantity), 0) AS ordered,
                   COALESCE(SUM(picked_qty), 0) AS shipped
            FROM order_items WHERE order_id = :oid
        """),
        {"oid": order_id},
    ).mappings().first()
    ordered = float(stats["ordered"] or 0)
    shipped = float(stats["shipped"] or 0)
    reservation_status = "shipped"
    if ordered > 0 and shipped < ordered - 0.001:
        reservation_status = "partially_shipped"
    uow.session.execute(
        text("UPDATE sales_orders SET reservation_status = :rs, updated_at = NOW() "
             "WHERE id = :oid"),
        {"rs": reservation_status, "oid": order_id},
    )

    return {
        "shipped_lines": len(shipped_product_rows),
        "released_total": round(released_total, 2),
        "reservation_status": reservation_status,
    }