# domain/centers/events.py (ملف جديد)
"""Cost & Profit Centers Events - أحداث مراكز التكلفة والربح"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import CenterId, CenterCode, CenterType


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class CenterCreatedEvent(BaseDomainEvent):
    center_id: CenterId
    center_code: CenterCode
    center_name: str
    center_type: CenterType
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.center.created"


@dataclass(frozen=True)
class CenterUpdatedEvent(BaseDomainEvent):
    center_id: CenterId
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.center.updated"


@dataclass(frozen=True)
class CenterActivatedEvent(BaseDomainEvent):
    center_id: CenterId
    center_code: CenterCode
    center_name: str
    activated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.center.activated"


@dataclass(frozen=True)
class CenterSuspendedEvent(BaseDomainEvent):
    center_id: CenterId
    center_code: CenterCode
    center_name: str
    suspended_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.center.suspended"


@dataclass(frozen=True)
class CenterClosedEvent(BaseDomainEvent):
    center_id: CenterId
    center_code: CenterCode
    center_name: str
    closed_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.center.closed"


@dataclass(frozen=True)
class CenterArchivedEvent(BaseDomainEvent):
    center_id: CenterId
    center_code: CenterCode
    center_name: str
    archived_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.center.archived"


@dataclass(frozen=True)
class CenterBudgetUpdatedEvent(BaseDomainEvent):
    center_id: CenterId
    center_code: CenterCode
    center_name: str
    old_budget: Decimal
    new_budget: Decimal
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.budget.updated"


@dataclass(frozen=True)
class CenterBudgetExceededEvent(BaseDomainEvent):
    center_id: CenterId
    center_code: CenterCode
    center_name: str
    budget_limit: Decimal
    actual_usage: Decimal
    exceeded_by: Decimal
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.budget.exceeded"


@dataclass(frozen=True)
class AllocationPostedEvent(BaseDomainEvent):
    allocation_id: str
    source_center: str
    total_amount: Decimal
    posted_by: str
    journal_entry_id: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.allocation.posted"


@dataclass(frozen=True)
class AllocationCancelledEvent(BaseDomainEvent):
    allocation_id: str
    source_center: str
    cancelled_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "centers.allocation.cancelled"