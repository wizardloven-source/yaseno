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
    quotation_number: str = ""
    customer_id: str = ""
    grand_total: float = 0.0
    currency: str = "USD"
    created_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


@dataclass
class QuotationSentEvent(DomainEvent):
    quotation_number: str = ""
    customer_id: str = ""
    sent_date: Optional[datetime] = None
    sent_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


@dataclass
class QuotationAcceptedEvent(DomainEvent):
    quotation_number: str = ""
    customer_id: str = ""
    accepted_date: Optional[datetime] = None
    grand_total: float = 0.0
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


@dataclass
class QuotationRejectedEvent(DomainEvent):
    quotation_number: str = ""
    customer_id: str = ""
    rejected_date: Optional[datetime] = None
    reason: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


@dataclass
class QuotationConvertedEvent(DomainEvent):
    quotation_number: str = ""
    order_number: str = ""
    converted_date: Optional[datetime] = None
    converted_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesQuotation"
        self.aggregate_id = self.quotation_number


# Order Events
@dataclass
class OrderCreatedEvent(DomainEvent):
    order_number: str = ""
    customer_id: str = ""
    grand_total: float = 0.0
    source_type: Optional[str] = None
    source_id: Optional[str] = None
    created_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class OrderConfirmedEvent(DomainEvent):
    order_number: str = ""
    customer_id: str = ""
    confirmed_date: Optional[datetime] = None
    confirmed_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class OrderShippedEvent(DomainEvent):
    order_number: str = ""
    tracking_number: str = ""
    carrier: Optional[str] = None
    shipped_date: Optional[datetime] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class OrderDeliveredEvent(DomainEvent):
    order_number: str = ""
    customer_id: str = ""
    delivered_date: Optional[datetime] = None
    received_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


@dataclass
class OrderCancelledEvent(DomainEvent):
    order_number: str = ""
    customer_id: str = ""
    cancelled_date: Optional[datetime] = None
    reason: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "SalesOrder"
        self.aggregate_id = self.order_number


# Delivery Note Events
@dataclass
class DeliveryNoteCreatedEvent(DomainEvent):
    delivery_number: str = ""
    order_number: str = ""
    customer_id: str = ""
    total_items: int = 0
    created_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "DeliveryNote"
        self.aggregate_id = self.delivery_number


@dataclass
class DeliveryCompletedEvent(DomainEvent):
    delivery_number: str = ""
    order_number: str = ""
    customer_id: str = ""
    completed_date: Optional[datetime] = None
    received_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_type = "DeliveryNote"
        self.aggregate_id = self.delivery_number


@dataclass
class DeliveryFailedEvent(DomainEvent):
    delivery_number: str = ""
    order_number: str = ""
    failed_date: Optional[datetime] = None
    reason: str = ""
    
    def __post_init__(self):
        self.aggregate_type = "DeliveryNote"
        self.aggregate_id = self.delivery_number
