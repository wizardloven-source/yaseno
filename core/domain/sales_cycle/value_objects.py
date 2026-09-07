"""
Value Objects for Sales Cycle Domain
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


class QuotationStatus(str, Enum):
    """حالات عرض السعر"""
    DRAFT = "draft"  # مسودة
    SENT = "sent"  # تم الإرسال للعميل
    VIEWED = "viewed"  # شاهده العميل
    ACCEPTED = "accepted"  # مقبول
    REJECTED = "rejected"  # مرفوض
    EXPIRED = "expired"  # منتهي الصلاحية
    CONVERTED = "converted"  # تم تحويله لأمر بيع


class OrderStatus(str, Enum):
    """حالات أمر البيع"""
    DRAFT = "draft"  # مسودة
    CONFIRMED = "confirmed"  # مؤكد
    IN_PROGRESS = "in_progress"  # قيد التنفيذ
    PICKING = "picking"  # جاري التحضير
    PACKING = "packing"  # جاري التغليف
    READY_TO_SHIP = "ready_to_ship"  # جاهز للشحن
    SHIPPED = "shipped"  # تم الشحن
    IN_TRANSIT = "in_transit"  # أثناء النقل
    OUT_FOR_DELIVERY = "out_for_delivery"  # خارج للتسليم
    DELIVERED = "delivered"  # تم التسليم
    PARTIALLY_DELIVERED = "partially_delivered"  # تم التسليم جزئياً
    CANCELLED = "cancelled"  # ملغى
    ON_HOLD = "on_hold"  # معلق
    RETURNED = "returned"  # تم الإرجاع
    COMPLETED = "completed"  # مكتمل


class DeliveryStatus(str, Enum):
    """حالات إشعار التسليم"""
    DRAFT = "draft"  # مسودة
    PENDING = "pending"  # قيد الانتظار
    SCHEDULED = "scheduled"  # مجدول
    IN_TRANSIT = "in_transit"  # أثناء النقل
    DELIVERED = "delivered"  # تم التسليم
    PARTIALLY_DELIVERED = "partially_delivered"  # تم التسليم جزئياً
    FAILED = "failed"  # فشل التسليم
    RETURNED = "returned"  # تم الإرجاع
    CANCELLED = "cancelled"  # ملغى


@dataclass(frozen=True)
class Money:
    """قيمة نقدية مع عملة"""
    amount: float
    currency: str = "SAR"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("المبلغ لا يمكن أن يكون سالباً")
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("لا يمكن جمع عملات مختلفة")
        return Money(self.amount + other.amount, self.currency)
    
    def __mul__(self, factor: float) -> 'Money':
        return Money(self.amount * factor, self.currency)
    
    def to_dict(self) -> dict:
        return {"amount": self.amount, "currency": self.currency}


@dataclass(frozen=True)
class Address:
    """عنوان متكامل"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "SA"
    building_number: Optional[str] = None
    unit_number: Optional[str] = None
    district: Optional[str] = None
    
    def format_address(self) -> str:
        """تنسيق العنوان كنص واحد"""
        parts = [
            self.street,
            self.district,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ", ".join(p for p in parts if p)
    
    def to_dict(self) -> dict:
        return {
            "street": self.street,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "building_number": self.building_number,
            "unit_number": self.unit_number,
            "district": self.district,
        }
