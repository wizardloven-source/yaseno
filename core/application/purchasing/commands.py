# core/application/purchasing/commands.py
"""
Purchase Return Commands - أوامر إرجاع المشتريات

✅ محدث: دعم كامل لدورة حياة إرجاع المشتريات
✅ محدث: دعم Debit Note التلقائي
"""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Any


@dataclass
class PurchaseReturnItemCommand:
    """أمر سطر إرجاع مشتريات"""
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    reason: str = ""
    condition: str = "good"  # good, damaged, expired
    batch_number: Optional[str] = None
    serial_numbers: List[str] = field(default_factory=list)
    expiry_date: Optional[datetime] = None
    discount_percent: Decimal = Decimal('0')
    discount_amount: Decimal = Decimal('0')
    tax_rate: Decimal = Decimal('0')


@dataclass
class CreatePurchaseReturnCommand:
    """أمر إنشاء إرجاع مشتريات"""
    purchase_order_id: str
    purchase_order_number: str
    supplier_id: str
    supplier_name: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    warehouse_id: Optional[str] = None
    currency: str = "USD"
    notes: str = ""
    reason: str = ""
    shipping_method: Optional[str] = None
    lines: List[PurchaseReturnItemCommand] = field(default_factory=list)
    created_by: str = ""


@dataclass
class SubmitPurchaseReturnCommand:
    """أمر تقديم إرجاع المشتريات للموافقة"""
    return_id: str
    submitted_by: str


@dataclass
class ApprovePurchaseReturnCommand:
    """أمر الموافقة على إرجاع المشتريات"""
    return_id: str
    approved_by: str


@dataclass
class RejectPurchaseReturnCommand:
    """أمر رفض إرجاع المشتريات"""
    return_id: str
    rejected_by: str
    reason: str


@dataclass
class ShipPurchaseReturnCommand:
    """أمر شحن إرجاع المشتريات للمورد"""
    return_id: str
    shipped_by: str
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None


@dataclass
class ReceiveBySupplierCommand:
    """أمر تأكيد استلام المورد للإرجاع"""
    return_id: str
    received_by: str


@dataclass
class CompletePurchaseReturnCommand:
    """أمر إكمال إرجاع المشتريات وإنشاء Debit Note"""
    return_id: str
    completed_by: str
    auto_create_debit_note: bool = True


@dataclass
class CancelPurchaseReturnCommand:
    """أمر إلغاء إرجاع المشتريات"""
    return_id: str
    cancelled_by: str
    reason: str
