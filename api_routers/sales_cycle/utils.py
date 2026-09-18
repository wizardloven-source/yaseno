# api_routers/sales_cycle/utils.py
"""
Sales Cycle Helpers - أدوات مساعدة لدورة المبيعات
"""

from datetime import date
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import text


# =============================================================================
# الحسابات المالية
# =============================================================================

def item_totals(
    quantity: Any,
    unit_price: Any,
    discount_percent: Any = 0,
    tax_percent: Any = 0,
) -> Dict[str, Decimal]:
    """حساب مجاميع عنصر (قبل الخصم، الخصم، بعد الخصم، الضريبة، الإجمالي)"""
    qty = Decimal(str(quantity or 0))
    price = Decimal(str(unit_price or 0))
    disc = Decimal(str(discount_percent or 0))
    tax = Decimal(str(tax_percent or 0))

    subtotal = qty * price
    discount_amount = subtotal * (disc / Decimal(100))
    amount_after_discount = subtotal - discount_amount
    tax_amount = amount_after_discount * (tax / Decimal(100))
    total = amount_after_discount + tax_amount

    return {
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "amount_after_discount": amount_after_discount,
        "tax_amount": tax_amount,
        "total": total,
    }


def document_totals(
    line_totals: List[Dict[str, Any]],
    global_discount_amount: Any = 0,
    shipping_cost: Any = 0,
) -> Dict[str, Decimal]:
    """
    حساب مجاميع المستند بالكامل
    يخصم `global_discount_amount` من إجمالي العناصر ثم يضيف الضريبة والشحن.
    """
    subtotal = sum((t["subtotal"] for t in line_totals), Decimal("0"))
    items_discount = sum((t["discount_amount"] for t in line_totals), Decimal("0"))
    global_disc = Decimal(str(global_discount_amount or 0))
    total_discount = items_discount + global_disc
    amount_after_discount = subtotal - total_discount
    total_tax = sum((t["tax_amount"] for t in line_totals), Decimal("0"))
    ship = Decimal(str(shipping_cost or 0))
    grand_total = amount_after_discount + total_tax + ship

    return {
        "subtotal": subtotal,
        "total_discount": total_discount,
        "amount_after_discount": amount_after_discount,
        "total_tax": total_tax,
        "grand_total": grand_total,
    }


# =============================================================================
# توليد الأرقام التسلسلية
# =============================================================================

def next_document_number(uow, prefix: str, table: str, column: str) -> str:
    """
    توليد رقم تسلسلي للمستند بالصيغة: PREFIX-YYYY-NNNN
    مثال: QT-2026-0001
    """
    year = date.today().year
    row = uow.session.execute(
        text(
            "SELECT COALESCE(MAX(CAST(COALESCE(NULLIF(SPLIT_PART({col}, '-', 3), ''), '0') AS INTEGER)), 0) AS m "
            "FROM {table} WHERE {col} LIKE :prefix".format(table=table, col=column)
        ),
        {"prefix": prefix + "-%"},
    ).mappings().first()
    seq = int(row["m"] or 0) + 1 if row else 1
    return f"{prefix}-{year}-{seq:04d}"


# =============================================================================
# استعلامات مساعدة
# =============================================================================

def get_customer_info(uow, customer_id: str) -> Optional[Dict[str, Any]]:
    """جلب بيانات العميل (الاسم/العملة/العنوان) من المستودع"""
    try:
        customer = uow.customers.get_by_id(customer_id)
    except Exception:
        return None
    if not customer:
        return None
    data = {
        "id": str(customer.id) if hasattr(customer, "id") else customer_id,
        "name": customer.name if hasattr(customer, "name") else "",
        "currency": getattr(customer, "currency", "USD") or "USD",
    }
    if hasattr(customer, "address") and customer.address:
        addr = customer.address
        data["address"] = {
            "street": getattr(addr, "street", ""),
            "city": getattr(addr, "city", ""),
            "state": getattr(addr, "state", ""),
            "postal_code": getattr(addr, "postal_code", ""),
            "country": getattr(addr, "country", ""),
        }
    return data


def get_product_info(uow, product_id: str) -> Optional[Dict[str, Any]]:
    """جلب بيانات المنتج (الكود/الاسم/السعر/الضريبة/الوحدة)"""
    try:
        from core.domain.products.value_objects import ProductId
        product = uow.products.get_by_id(ProductId.from_string(product_id))
    except Exception:
        return None
    if not product:
        return None
    return {
        "id": str(product.id.value),
        "code": str(product.code),
        "name": product.name,
        "unit_price": float(product.unit_price.amount),
        "currency": product.unit_price.currency,
        "tax_rate": float(product.tax_rate),
        "unit": getattr(product, "unit", "") or "pcs",
    }


def get_product_code(uow, product_id: str) -> str:
    """استخراج كود المنتج فقط"""
    info = get_product_info(uow, product_id)
    return info["code"] if info else ""


# =============================================================================
# بناء مجاميع صفوف القوائم
# =============================================================================

def serialize_line(row: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    """تحويل صف من قاعدة البيانات إلى قاموس عادي"""
    return {k: row.get(k) for k in keys}