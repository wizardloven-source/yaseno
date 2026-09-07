# core/domain/sales/events.py
"""
Sales Domain Events - أحداث المجال لدورة المبيعات
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class SalesEvent:
    """فئة أساسية لأحداث المبيعات"""
    aggregate_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now())
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Quotation Events
# ============================================================================

@dataclass
class QuotationCreated(SalesEvent):
    """تم إنشاء عرض سعر جديد"""
    quotation_number: str = ""
    customer_id: str = ""
    total_amount: float = 0.0


@dataclass
class QuotationSent(SalesEvent):
    """تم إرسال عرض السعر للعميل"""
    quotation_number: str = ""
    sent_at: Optional[datetime] = None
    sent_by: str = ""


@dataclass
class QuotationAccepted(SalesEvent):
    """تم قبول عرض السعر"""
    quotation_number: str = ""
    accepted_at: Optional[datetime] = None


@dataclass
class QuotationRejected(SalesEvent):
    """تم رفض عرض السعر"""
    quotation_number: str = ""
    rejected_at: Optional[datetime] = None
    reason: str = ""


@dataclass
class QuotationConverted(SalesEvent):
    """تم تحويل عرض السعر إلى أمر بيع"""
    quotation_number: str = ""
    order_id: str = ""
    order_number: str = ""
    converted_at: Optional[datetime] = None


@dataclass
class QuotationExpired(SalesEvent):
    """انتهت صلاحية عرض السعر"""
    quotation_number: str = ""
    expired_at: datetime = field(default_factory=lambda: datetime.now())


# ============================================================================
# Order Events
# ============================================================================

@dataclass
class OrderCreated(SalesEvent):
    """تم إنشاء أمر بيع جديد"""
    order_number: str = ""
    customer_id: str = ""
    source_quotation_id: Optional[str] = None
    total_amount: float = 0.0


@dataclass
class OrderConfirmed(SalesEvent):
    """تم تأكيد أمر البيع"""
    order_number: str = ""
    confirmed_at: Optional[datetime] = None


@dataclass
class OrderPicked(SalesEvent):
    """تم جرد عناصر أمر البيع"""
    order_number: str = ""
    picked_at: Optional[datetime] = None


@dataclass
class OrderPacked(SalesEvent):
    """تم تعبئة عناصر أمر البيع"""
    order_number: str = ""
    packed_at: Optional[datetime] = None


@dataclass
class OrderShipped(SalesEvent):
    """تم شحن أمر البيع"""
    order_number: str = ""
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None


@dataclass
class OrderDelivered(SalesEvent):
    """تم تسليم أمر البيع"""
    order_number: str = ""
    delivered_at: Optional[datetime] = None
    received_by: Optional[str] = None


@dataclass
class OrderCancelled(SalesEvent):
    """تم إلغاء أمر البيع"""
    order_number: str = ""
    cancelled_at: Optional[datetime] = None
    reason: str = ""


@dataclass
class OrderOnHold(SalesEvent):
    """تم تعليق أمر البيع"""
    order_number: str = ""
    on_hold_at: Optional[datetime] = None
    reason: str = ""


@dataclass
class OrderResumed(SalesEvent):
    """تم استئناف أمر البيع المعلق"""
    order_number: str = ""
    resumed_at: Optional[datetime] = None


# ============================================================================
# Delivery Events
# ============================================================================

@dataclass
class DeliveryCreated(SalesEvent):
    """تم إنشاء إشعار تسليم جديد"""
    delivery_number: str = ""
    order_id: Optional[str] = None
    customer_id: str = ""


@dataclass
class DeliveryScheduled(SalesEvent):
    """تم جدولة التسليم"""
    delivery_number: str = ""
    scheduled_date: Optional[datetime] = None


@dataclass
class DeliveryInTransit(SalesEvent):
    """أشعار التسليم أثناء النقل"""
    delivery_number: str = ""
    transit_started_at: Optional[datetime] = None


@dataclass
class DeliveryCompleted(SalesEvent):
    """اكتمل التسليم"""
    delivery_number: str = ""
    completed_at: Optional[datetime] = None
    received_by: Optional[str] = None


@dataclass
class DeliveryReturned(SalesEvent):
    """تم إرجاع إشعار التسليم"""
    delivery_number: str = ""
    returned_at: Optional[datetime] = None
    reason: str = ""


@dataclass
class DeliveryCancelled(SalesEvent):
    """تم إلغاء إشعار التسليم"""
    delivery_number: str = ""
    cancelled_at: Optional[datetime] = None
    reason: str = ""
