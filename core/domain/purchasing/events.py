from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List

from ..shared.value_objects import BaseDomainEvent, Money
from .value_objects import PurchaseOrderId, PurchaseReturnId


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PurchaseOrderCreatedEvent(BaseDomainEvent):
    order_id: PurchaseOrderId
    supplier_id: str
    total_amount: Money
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.order.created"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "order_id": str(self.order_id),
            "supplier_id": self.supplier_id,
            "total_amount": str(self.total_amount.amount),
            "currency": self.total_amount.currency,
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseOrderPostedEvent(BaseDomainEvent):
    order_id: PurchaseOrderId
    order_number: Optional[str]
    journal_entry_id: str
    total_amount: Money
    supplier_id: str
    posted_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.order.posted"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "order_id": str(self.order_id),
            "order_number": self.order_number,
            "journal_entry_id": self.journal_entry_id,
            "total_amount": str(self.total_amount.amount),
            "currency": self.total_amount.currency,
            "supplier_id": self.supplier_id,
            "posted_by": self.posted_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseOrderLineAddedEvent(BaseDomainEvent):
    order_id: PurchaseOrderId
    product_code: str
    product_name: str
    quantity: int
    unit_price: Money
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.order.line_added"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "order_id": str(self.order_id),
            "product_code": self.product_code,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": str(self.unit_price.amount),
            "currency": self.unit_price.currency,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseOrderReceivedEvent(BaseDomainEvent):
    order_id: PurchaseOrderId
    line_id: str
    product_code: str
    quantity: int
    received_by: str
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    expiry_date: Optional[datetime] = None
    location: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.order.received"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "order_id": str(self.order_id),
            "line_id": self.line_id,
            "product_code": self.product_code,
            "quantity": self.quantity,
            "received_by": self.received_by,
            "batch_number": self.batch_number,
            "serial_numbers": self.serial_numbers,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "location": self.location,
            "occurred_at": self.occurred_at.isoformat()
        }


# ========== ✅ Purchase Return Events ==========

@dataclass(frozen=True)
class PurchaseReturnSubmittedEvent(BaseDomainEvent):
    return_id: PurchaseReturnId
    return_number: Optional[str]
    submitted_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.return.submitted"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "return_id": str(self.return_id),
            "return_number": self.return_number,
            "submitted_by": self.submitted_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseReturnApprovedEvent(BaseDomainEvent):
    return_id: PurchaseReturnId
    return_number: Optional[str]
    approved_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.return.approved"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "return_id": str(self.return_id),
            "return_number": self.return_number,
            "approved_by": self.approved_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseReturnShippedEvent(BaseDomainEvent):
    return_id: PurchaseReturnId
    return_number: Optional[str]
    shipped_by: str
    tracking_number: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.return.shipped"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "return_id": str(self.return_id),
            "return_number": self.return_number,
            "shipped_by": self.shipped_by,
            "tracking_number": self.tracking_number,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseReturnReceivedBySupplierEvent(BaseDomainEvent):
    return_id: PurchaseReturnId
    return_number: Optional[str]
    received_at: datetime
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.return.received_by_supplier"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "return_id": str(self.return_id),
            "return_number": self.return_number,
            "received_at": self.received_at.isoformat(),
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseReturnCompletedEvent(BaseDomainEvent):
    return_id: PurchaseReturnId
    return_number: Optional[str]
    debit_note_id: str
    total_amount: Money
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.return.completed"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "return_id": str(self.return_id),
            "return_number": self.return_number,
            "debit_note_id": self.debit_note_id,
            "total_amount": str(self.total_amount.amount),
            "currency": self.total_amount.currency,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseReturnRejectedEvent(BaseDomainEvent):
    return_id: PurchaseReturnId
    return_number: Optional[str]
    reason: str
    rejected_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.return.rejected"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "return_id": str(self.return_id),
            "return_number": self.return_number,
            "reason": self.reason,
            "rejected_by": self.rejected_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class PurchaseReturnCancelledEvent(BaseDomainEvent):
    return_id: PurchaseReturnId
    return_number: Optional[str]
    reason: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "purchasing.return.cancelled"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "return_id": str(self.return_id),
            "return_number": self.return_number,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat()
        }