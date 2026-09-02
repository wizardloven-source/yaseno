# core/domain/customers/events.py
"""Domain Events for Customers Context"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import CustomerId, CustomerCode, CustomerStatus


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CustomerCreatedEvent(BaseDomainEvent):
    customer_id: CustomerId
    customer_code: CustomerCode
    customer_name: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "customers.customer.created"


@dataclass(frozen=True)
class CustomerUpdatedEvent(BaseDomainEvent):
    customer_id: CustomerId
    customer_code: CustomerCode
    customer_name: str
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "customers.customer.updated"


@dataclass(frozen=True)
class CustomerDeletedEvent(BaseDomainEvent):
    customer_id: CustomerId
    customer_code: CustomerCode
    customer_name: str
    deleted_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "customers.customer.deleted"