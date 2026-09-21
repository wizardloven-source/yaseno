"""
Domain Events for Sales Cycle
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DomainEvent:
    """Base class for domain events"""
    event_id: str = field(default_factory=lambda: str(__import__('uuid').uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)
    aggregate_id: Optional[str] = None
    aggregate_type: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_type": self.__class__.__name__,
        }


# Quotation Events
@dataclass
class QuotationCreatedEvent(DomainEvent):
    quotation_number: str
    customer_id: str
    grand_total: float
    currency: str
    created_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


@dataclass
class QuotationSentEvent(DomainEvent):
    quotation_number: str
    customer_id: str
    sent_date: datetime
    sent_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


@dataclass
class QuotationAcceptedEvent(DomainEvent):
    quotation_number: str
    customer_id: str
    accepted_date: datetime
    grand_total: float
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


@dataclass
class QuotationRejectedEvent(DomainEvent):
    quotation_number: str
    customer_id: str
    rejected_date: datetime
    reason: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


@dataclass
class QuotationConvertedEvent(DomainEvent):
    quotation_number: str
    order_number: str
    converted_date: datetime
    converted_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


# Order Events
@dataclass
class OrderCreatedEvent(DomainEvent):
    order_number: str
    customer_id: str
    grand_total: float
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    created_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class StockReservationCreated(DomainEvent):
    """تم حجز المخزون بعد تأكيد أمر البيع"""
    order_number: str
    order_id: str
    customer_id: str
    reserved_total: float
    reserved_lines: int
    reservation_status: str = "reserved"

    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class OrderCompletedEvent(DomainEvent):
    """اكتمل الأمر: تمت الفاتورة بالكامل من كميات مسلّمة"""
    order_number: str
    order_id: str
    customer_id: str
    completed_date: datetime
    total_invoiced: float = 0.0

    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class OrderConfirmedEvent(DomainEvent):
    order_number: str
    customer_id: str
    confirmed_date: datetime
    confirmed_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class OrderShippedEvent(DomainEvent):
    order_number: str
    tracking_number: str
    carrier: Optional[str]
    shipped_date: datetime
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class ShippingItemShipped(DomainEvent):
    """تم شحن بند من بند الشحنة - يقلل الحجز ويحدّث كميات الشحنة"""
    shipping_id: str
    shipping_number: str
    order_id: str
    order_number: str
    product_id: str
    product_code: str
    shipped_quantity: float
    shipped_date: datetime

    def __post_init__(self):
        self.aggregate_type = "SalesShipping"
        self.aggregate_id = self.shipping_number


@dataclass
class OrderDeliveredEvent(DomainEvent):
    order_number: str
    customer_id: str
    delivered_date: datetime
    received_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class OrderCancelledEvent(DomainEvent):
    order_number: str
    customer_id: str
    cancelled_date: datetime
    reason: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


# Delivery Note Events
@dataclass
class DeliveryNoteCreatedEvent(DomainEvent):
    delivery_number: str
    order_number: str
    customer_id: str
    total_items: int
    created_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "DeliveryNote"
        self.aggregate_id = self.delivery_number


@dataclass
class DeliveryCompletedEvent(DomainEvent):
    delivery_number: str
    order_number: str
    customer_id: str
    completed_date: datetime
    received_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "DeliveryNote"
        self.aggregate_id = self.delivery_number


@dataclass
class DeliveryFailedEvent(DomainEvent):
    delivery_number: str
    order_number: str
    failed_date: datetime
    reason: str
    
    def __post_init__(self):
        self.aggregate_type = "DeliveryNote"
        self.aggregate_id = self.delivery_number
