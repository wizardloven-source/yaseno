# core/domain/sales/value_objects.py
"""
Sales Value Objects - كائنات القيمة لوحدة المبيعات
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# Sales Quotation Value Objects
# ============================================================================

@dataclass(frozen=True)
class QuotationId:
    """معرف عرض السعر"""
    value: str
    
    def __init__(self, value: Optional[str] = None):
        object.__setattr__(self, 'value', value or str(uuid.uuid4()))
    
    @classmethod
    def generate(cls) -> 'QuotationId':
        return cls(str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value[:8]


@dataclass(frozen=True)
class QuotationNumber:
    """رقم عرض السعر التسلسلي"""
    value: str
    
    def __init__(self, value: str):
        if not value or len(value.strip()) == 0:
            raise ValueError("Quotation number cannot be empty")
        object.__setattr__(self, 'value', value.strip().upper())
    
    @classmethod
    def generate(cls, prefix: str = "QT", sequence: int = 1) -> 'QuotationNumber':
        """توليد رقم عرض سعر تلقائي"""
        return cls(f"{prefix}-{sequence:06d}")
    
    def __str__(self) -> str:
        return self.value


class QuotationStatus(Enum):
    """حالات عرض السعر"""
    DRAFT = "draft"  # مسودة
    SENT = "sent"  # مرسل للعميل
    VIEWED = "viewed"  # شوهد من العميل
    ACCEPTED = "accepted"  # مقبول
    REJECTED = "rejected"  # مرفوض
    EXPIRED = "expired"  # منتهي الصلاحية
    CONVERTED = "converted"  # تم تحويله لأمر بيع


# ============================================================================
# Sales Order Value Objects
# ============================================================================

@dataclass(frozen=True)
class OrderId:
    """معرف أمر البيع"""
    value: str
    
    def __init__(self, value: Optional[str] = None):
        object.__setattr__(self, 'value', value or str(uuid.uuid4()))
    
    @classmethod
    def generate(cls) -> 'OrderId':
        return cls(str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value[:8]


@dataclass(frozen=True)
class OrderNumber:
    """رقم أمر البيع التسلسلي"""
    value: str
    
    def __init__(self, value: str):
        if not value or len(value.strip()) == 0:
            raise ValueError("Order number cannot be empty")
        object.__setattr__(self, 'value', value.strip().upper())
    
    @classmethod
    def generate(cls, prefix: str = "SO", sequence: int = 1) -> 'OrderNumber':
        """توليد رقم أمر بيع تلقائي"""
        return cls(f"{prefix}-{sequence:06d}")
    
    def __str__(self) -> str:
        return self.value


class OrderStatus(Enum):
    """حالات أمر البيع"""
    DRAFT = "draft"  # مسودة
    CONFIRMED = "confirmed"  # مؤكد
    IN_PROGRESS = "in_progress"  # قيد التنفيذ
    PICKING = "picking"  # الجرد
    PICKED = "picked"  # تم الجرد
    PACKING = "packing"  # التعبئة
    PACKED = "packed"  # تم التعبئة
    READY_TO_SHIP = "ready_to_ship"  # جاهز للشحن
    SHIPPED = "shipped"  # تم الشحن
    IN_TRANSIT = "in_transit"  # أثناء النقل
    DELIVERED = "delivered"  # تم التسليم
    PARTIALLY_DELIVERED = "partially_delivered"  # تم التسليم جزئياً
    COMPLETED = "completed"  # مكتمل
    CANCELLED = "cancelled"  # ملغى
    ON_HOLD = "on_hold"  # معلق


# ============================================================================
# Delivery Note Value Objects
# ============================================================================

@dataclass(frozen=True)
class DeliveryId:
    """معرف إشعار التسليم"""
    value: str
    
    def __init__(self, value: Optional[str] = None):
        object.__setattr__(self, 'value', value or str(uuid.uuid4()))
    
    @classmethod
    def generate(cls) -> 'DeliveryId':
        return cls(str(uuid.uuid4()))
    
    def __str__(self) -> str:
        return self.value[:8]


@dataclass(frozen=True)
class DeliveryNumber:
    """رقم إشعار التسليم التسلسلي"""
    value: str
    
    def __init__(self, value: str):
        if not value or len(value.strip()) == 0:
            raise ValueError("Delivery number cannot be empty")
        object.__setattr__(self, 'value', value.strip().upper())
    
    @classmethod
    def generate(cls, prefix: str = "DN", sequence: int = 1) -> 'DeliveryNumber':
        """توليد رقم إشعار تسليم تلقائي"""
        return cls(f"{prefix}-{sequence:06d}")
    
    def __str__(self) -> str:
        return self.value


class DeliveryStatus(Enum):
    """حالات إشعار التسليم"""
    DRAFT = "draft"  # مسودة
    SCHEDULED = "scheduled"  # مجدول
    SHIPPED = "shipped"  # تم الشحن (alias for IN_TRANSIT)
    IN_TRANSIT = "in_transit"  # أثناء النقل
    DELIVERED = "delivered"  # تم التسليم
    PARTIALLY_DELIVERED = "partially_delivered"  # تم التسليم جزئياً
    RETURNED = "returned"  # تم الإرجاع
    CANCELLED = "cancelled"  # ملغى


# ============================================================================
# Common Value Objects
# ============================================================================

@dataclass(frozen=True)
class CustomerReference:
    """مرجع العميل"""
    customer_id: str
    branch_id: Optional[str] = None
    
    def __str__(self) -> str:
        if self.branch_id:
            return f"{self.customer_id}:{self.branch_id}"
        return self.customer_id


@dataclass(frozen=True)
class SalesPersonReference:
    """مرجع موظف المبيعات"""
    employee_id: str
    name: Optional[str] = None


@dataclass(frozen=True)
class ShippingAddress:
    """عنوان الشحن"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone: Optional[str] = None
    notes: Optional[str] = None
    
    def __str__(self) -> str:
        return f"{self.street}, {self.city}, {self.state} {self.postal_code}, {self.country}"


@dataclass(frozen=True)
class PaymentTerms:
    """شروط الدفع"""
    days: int = 0  # عدد الأيام
    discount_percent: Decimal = Decimal('0')  # خصم الدفع المبكر
    discount_days: int = 0  # أيام خصم الدفع المبكر
    
    @property
    def has_discount(self) -> bool:
        return self.discount_percent > 0 and self.discount_days > 0
