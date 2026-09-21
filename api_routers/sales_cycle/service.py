# api_routers/sales_cycle/service.py
"""
Sales Cycle Shared Services - خدمات مشتركة لأوامر البيع وإشعارات التسليم
"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import text
from uuid import uuid4

from api_routers.sales_cycle.utils import (
    item_totals,
    document_totals,
    next_document_number,
)


def _jsonb(value: Optional[Dict[str, Any]]) -> Optional[str]:
    """تحويل قاموس إلى نص JSON جاهز للإدخال في عمود JSONB"""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def _build_serialized_lines(uow, lines: List[dict], include_product: bool = True) -> List[dict]:
    """
    استكمال بيانات الأسطر (كود/اسم المنتج + الحسابات المالية)
    كل سطر يحتوي: product_id, quantity, unit_price, discount_percent, tax_percent, unit, notes
    """
    from api_routers.sales_cycle.utils import get_product_info

    result = []
    for raw in lines:
        product_id = raw["product_id"]
        info = get_product_info(uow, product_id) if include_product else None
        if info is None and include_product:
            raise ValueError(f"المنتج {product_id} غير موجود")

        unit_price = float(raw.get("unit_price") or (info and info.get("unit_price")) or 0)
        tax_percent = float(raw.get("tax_percent") if raw.get("tax_percent") is not None
                            else (info and info.get("tax_rate")) or 0)
        quantity = float(raw.get("quantity", 1))
        discount_percent = float(raw.get("discount_percent", 0))

        totals = item_totals(quantity, unit_price, discount_percent, tax_percent)
        result.append({
            "product_id": str(product_id),
            "product_code": (info or {}).get("code", ""),
            "product_name": (info or {}).get("name", ""),
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_percent": discount_percent,
            "tax_percent": tax_percent,
            "unit": raw.get("unit") or (info or {}).get("unit") or "pcs",
            "notes": raw.get("notes") or "",
            **totals,
        })
    return result


def create_order(
    uow,
    customer_id: str,
    customer_name: str,
    currency: str,
    created_by: str,
    *,
    lines: List[dict],
    order_date=None,
    expected_delivery_date=None,
    quotation_id: Optional[str] = None,
    priority: str = "normal",
    global_discount_percent=0,
    global_discount_amount=0,
    shipping_cost=0,
    shipping_method=None,
    tracking_number=None,
    carrier=None,
    payment_terms=None,
    due_date=None,
    billing_address=None,
    shipping_address=None,
    notes=None,
    internal_notes=None,
    branch_id=None,
) -> Dict[str, Any]:
    """
    إنشاء أمر بيع جديد مع سطوره وإرجاع (id, order_number, grand_total)
    """
    serialized = _build_serialized_lines(uow, lines)
    totals = document_totals(
        serialized,
        global_discount_amount=global_discount_amount,
        shipping_cost=shipping_cost,
    )

    if global_discount_percent:
        global_discount_amount = float(
            totals["amount_after_discount"]
            + totals["total_tax"]
            + float(shipping_cost or 0)
        ) * float(global_discount_percent) / 100

    order_id = str(uuid4())
    order_number = next_document_number(uow, "SO", "sales_orders", "order_number")
    order_date = order_date or datetime.now().date()

    uow.session.execute(
        text("""
            INSERT INTO sales_orders (
                id, order_number, customer_id, customer_name, currency,
                source_type, source_id, quotation_id, order_date,
                expected_delivery_date, status, priority,
                global_discount_percent, global_discount_amount,
                subtotal, total_discount, amount_after_discount, total_tax,
                shipping_cost, grand_total, shipping_method, tracking_number,
                carrier, payment_terms, due_date, billing_address, shipping_address,
                notes, internal_notes, branch_id, created_by
            ) VALUES (
                :id, :order_number, :customer_id, :customer_name, :currency,
                :source_type, :source_id, :quotation_id, :order_date,
                :expected_delivery_date, 'draft', :priority,
                :gdp, :gda, :subtotal, :total_discount, :amount_after_discount,
                :total_tax, :shipping_cost, :grand_total, :shipping_method,
                :tracking_number, :carrier, :payment_terms, :due_date,
                CAST(:billing_address AS jsonb), CAST(:shipping_address AS jsonb),
                :notes, :internal_notes, :branch_id, :created_by
            )
        """),
        {
            "id": order_id,
            "order_number": order_number,
            "customer_id": str(customer_id),
            "customer_name": customer_name,
            "currency": currency,
            "source_type": "quotation" if quotation_id else None,
            "source_id": quotation_id,
            "quotation_id": quotation_id,
            "order_date": order_date,
            "expected_delivery_date": expected_delivery_date,
            "priority": priority,
            "gdp": float(global_discount_percent or 0),
            "gda": float(global_discount_amount or 0),
            "subtotal": float(totals["subtotal"]),
            "total_discount": float(totals["total_discount"]),
            "amount_after_discount": float(totals["amount_after_discount"]),
            "total_tax": float(totals["total_tax"]),
            "shipping_cost": float(shipping_cost or 0),
            "grand_total": float(totals["grand_total"]),
            "shipping_method": shipping_method,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "payment_terms": payment_terms,
            "due_date": due_date,
            "billing_address": _jsonb(billing_address),
            "shipping_address": _jsonb(shipping_address),
            "notes": notes,
            "internal_notes": internal_notes,
            "branch_id": branch_id,
            "created_by": created_by,
        },
    )

    for item in serialized:
        uow.session.execute(
            text("""
                INSERT INTO order_items (
                    id, order_id, product_id, product_code, product_name,
                    quantity, unit_price, discount_percent, tax_percent, unit,
                    delivered_quantity, returned_quantity, notes,
                    subtotal, discount_amount, amount_after_discount,
                    tax_amount, total
                ) VALUES (
                    :id, :order_id, :product_id, :product_code, :product_name,
                    :quantity, :unit_price, :discount_percent, :tax_percent, :unit,
                    0, 0, :notes, :subtotal, :discount_amount,
                    :amount_after_discount, :tax_amount, :total
                )
            """),
            {
                "id": str(uuid4()),
                "order_id": order_id,
                "product_id": item["product_id"],
                "product_code": item["product_code"],
                "product_name": item["product_name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "discount_percent": item["discount_percent"],
                "tax_percent": item["tax_percent"],
                "unit": item["unit"],
                "notes": item["notes"],
                "subtotal": float(item["subtotal"]),
                "discount_amount": float(item["discount_amount"]),
                "amount_after_discount": float(item["amount_after_discount"]),
                "tax_amount": float(item["tax_amount"]),
                "total": float(item["total"]),
            },
        )

    return {"id": order_id, "order_number": order_number,
            "grand_total": float(totals["grand_total"])}


def update_order_status_after_delivery(uow, order_id: str) -> str:
    """
    إعادة حساب حالة الأمر بعد تسليم جزئي/كامل
    يُرجع الحالة الجديدة
    """
    rows = uow.session.execute(
        text("""
            SELECT COALESCE(SUM(quantity), 0) AS ordered,
                   COALESCE(SUM(delivered_quantity), 0) AS delivered
            FROM order_items WHERE order_id = :order_id
        """),
        {"order_id": order_id},
    ).mappings().first()

    ordered = float(rows["ordered"] or 0)
    delivered = float(rows["delivered"] or 0)

    if ordered <= 0:
        new_status = "delivered"
    elif delivered >= ordered:
        new_status = "delivered"
    elif delivered > 0:
        new_status = "partially_delivered"
    else:
        new_status = "confirmed"

    uow.session.execute(
        text("UPDATE sales_orders SET status = :status, updated_at = NOW() WHERE id = :id"),
        {"status": new_status, "id": order_id},
    )

    fully = ordered > 0 and delivered >= ordered - 0.001
    uow.session.execute(
        text("UPDATE sales_orders SET fully_delivered = :fd, updated_at = NOW() "
             "WHERE id = :id"),
        {"fd": fully, "id": order_id},
    )
    return new_status


def get_auto_invoice_on_delivery(uow) -> bool:
    """
    يقرأ إعداد auto_invoice_on_delivery من جدول الإعدادات.
    القيمة الافتراضية: مفعّل (تُنشأ مسودة فاتورة تلقائياً عند اكتمال التسليم).
    """
    try:
        row = uow.session.execute(
            text("SELECT value FROM settings WHERE key = :k LIMIT 1"),
            {"k": "auto_invoice_on_delivery"},
        ).mappings().first()
        if row is None:
            return True
        return str(row["value"]).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return True


def set_auto_invoice_on_delivery(uow, enabled: bool) -> None:
    """يراجع إعداد auto_invoice_on_delivery (إدراج/تحديث)."""
    uow.session.execute(
        text("""
            INSERT INTO settings (key, value, category, is_json, created_at, updated_at)
            VALUES (:k, :v, 'sales', FALSE, NOW(), NOW())
            ON CONFLICT (key) DO UPDATE SET value = :v, updated_at = NOW()
        """),
        {"k": "auto_invoice_on_delivery", "v": "true" if enabled else "false"},
    )


def create_invoice_draft_from_delivery(
    uow, order_id: str, delivery_id: str, created_by: str
) -> Optional[Dict[str, Any]]:
    """
    مصنع الفاتورة من التسليم (Delivery → Invoice Draft Factory).
    يُنشئ مسودة فاتورة من الكميات المسلّمة فعلياً، يربطها بإشعار التسليم
    (invoice_deliveries)، ويحدّث معلومات الفاتورة على الأمر.
    لا تُرحَّل الفاتورة هنا (تظل draft حتى ترحيلها عبر /post).
    لا يُنشئ شيئاً إذا كان الأمر مفتوحاً عليه فاتورة سابقة.
    """
    order = uow.session.execute(
        text("SELECT * FROM sales_orders WHERE id = :id"),
        {"id": order_id},
    ).mappings().first()
    if not order:
        raise ValueError("أمر البيع غير موجود")

    if order.get("invoice_id"):
        return None

    items = uow.session.execute(
        text("SELECT * FROM delivery_items WHERE delivery_id = :did ORDER BY id"),
        {"did": delivery_id},
    ).mappings().all()
    if not items:
        return None

    from api_routers.shared import bootstrap
    from core.application.invoicing.commands import (
        CreateInvoiceCommand, AddInvoiceLineCommand,
    )

    command_bus = bootstrap.container.resolve("command_bus")
    currency = order["currency"] or "USD"

    # فاتورة التسليم لا تملك صندوقاً؛ لذلك نستخدم البيع الآجل (ذمم) افتراضياً
    # ما لم تكن شروط الدفع شيك/تحويل.
    payment_type = (order.get("payment_terms") or "").strip().lower()
    if payment_type not in ("credit", "check", "transfer"):
        payment_type = "credit"

    create_cmd = CreateInvoiceCommand(
        customer_id=str(order["customer_id"]),
        customer_name=order["customer_name"],
        site_id=None,
        site_name=None,
        currency=currency,
        payment_type=payment_type,
        payment_currency=currency,
        fund_id=None,
        notes=(order.get("notes") or ""),
        created_by=created_by,
    )
    result = command_bus.dispatch(create_cmd)

    invoice_id = None
    if isinstance(result, dict):
        invoice_id = result.get("id")
    elif hasattr(result, "id"):
        invoice_id = result.id
    if not invoice_id:
        raise ValueError("فشل إنشاء مسودة الفاتورة من التسليم")

    total_amount = Decimal("0")
    for it in items:
        qty = Decimal(str(it["delivered_quantity"] or 0))
        if qty <= 0:
            continue
        unit_price = _delivery_line_unit_price(uow, order_id, str(it["product_id"]))
        total_amount += unit_price * qty
        line_cmd = AddInvoiceLineCommand(
            invoice_id=invoice_id,
            product_code=it["product_code"] or "",
            product_name=it["product_name"],
            quantity=qty,
            unit_price=unit_price,
            currency=currency,
            notes="فاتورة تلقائية من إشعار التسليم " + str(it["id"]),
        )
        command_bus.dispatch(line_cmd)

        # تحديث الكمية المفوتَرة على بند الأمر
        uow.session.execute(
            text("""
                UPDATE order_items SET invoiced_qty = COALESCE(invoiced_qty, 0) + :qty,
                    updated_at = NOW()
                WHERE order_id = :oid AND CAST(product_id AS TEXT) = :pid
            """),
            {"qty": float(qty), "oid": order_id, "pid": str(it["product_id"])},
        )

    # ربط الفاتورة بإشعار التسليم
    uow.session.execute(
        text("""
            INSERT INTO invoice_deliveries (id, invoice_id, delivery_id, order_id, created_by)
            VALUES (:id, :inv, :did, :oid, :cb)
        """),
        {"id": str(uuid4()), "inv": invoice_id, "did": delivery_id,
         "oid": order_id, "cb": created_by},
    )

    # بناء قائمة معرّفات الفواتير في بايثون (أأمن من عمليات jsonb النصية)
    inv_row = uow.session.execute(
        text("SELECT number FROM invoices WHERE id = :inv"),
        {"inv": invoice_id},
    ).mappings().first()
    invoice_number = inv_row["number"] if inv_row else None

    existing = uow.session.execute(
        text("SELECT invoice_ids FROM sales_orders WHERE id = :oid"),
        {"oid": order_id},
    ).mappings().first()
    ids = existing["invoice_ids"] if existing else None
    if isinstance(ids, str):
        try:
            ids = json.loads(ids)
        except Exception:
            ids = []
    if not isinstance(ids, list):
        ids = []
    if invoice_id not in ids:
        ids.append(invoice_id)

    uow.session.execute(
        text("""
            UPDATE sales_orders SET
                invoice_id = :inv,
                invoice_number = :num,
                invoiced_date = NOW(),
                invoiced_amount = :amount,
                invoice_ids = CAST(:ids AS jsonb),
                payment_status = 'invoiced',
                updated_at = NOW()
            WHERE id = :oid
        """),
        {"inv": invoice_id, "num": invoice_number, "amount": float(total_amount),
         "ids": json.dumps(ids), "oid": order_id},
    )

    mark_order_invoiced(uow, order_id)
    return {"id": invoice_id, "amount": float(total_amount)}


def _delivery_line_unit_price(uow, order_id: str, product_id: str) -> Decimal:
    """استرجاع سعر الوحدة من بند الأمر للمنتج."""
    row = uow.session.execute(
        text("SELECT unit_price FROM order_items WHERE order_id = :oid "
             "AND CAST(product_id AS TEXT) = :pid LIMIT 1"),
        {"oid": order_id, "pid": product_id},
    ).mappings().first()
    return Decimal(str(row["unit_price"] or 0)) if row else Decimal("0")


def mark_order_invoiced(uow, order_id: str) -> None:
    """
    بعد ربط فاتورة بالأمر: يحدّث reservation_status (invoiced)
    ويعيد حساب اكتمال الأمر (كل البنود مفوترَة ومسلَّمة → completed).
    """
    rows = uow.session.execute(
        text("""
            SELECT COALESCE(SUM(quantity), 0) AS ordered,
                   COALESCE(SUM(invoiced_qty), 0) AS invoiced,
                   COALESCE(SUM(delivered_quantity), 0) AS delivered
            FROM order_items WHERE order_id = :oid
        """),
        {"oid": order_id},
    ).mappings().first()

    ordered = float(rows["ordered"] or 0)
    invoiced = float(rows["invoiced"] or 0)
    delivered = float(rows["delivered"] or 0)

    reservation_status = "invoiced"
    completed = ordered > 0 and invoiced >= ordered - 0.001
    if completed:
        reservation_status = "completed"

    uow.session.execute(
        text("UPDATE sales_orders SET reservation_status = :rs, updated_at = NOW() "
             "WHERE id = :oid"),
        {"rs": reservation_status, "oid": order_id},
    )

    if completed:
        try:
            from core.domain.sales_cycle.events import OrderCompletedEvent
            event = OrderCompletedEvent(
                order_number=str(order_id),
                order_id=order_id,
                customer_id="",
                completed_date=datetime.now(),
                total_invoiced=float(invoiced),
            )
            from api_routers.shared import bootstrap
            event_bus = bootstrap.container.resolve("event_bus")
            event_bus.dispatch(event)
        except Exception:
            pass

    return completed


def get_delivery_status_weights() -> Dict[str, int]:
    return {"draft": 0, "scheduled": 1, "in_transit": 2, "delivered": 3, "failed": -1, "cancelled": -2}