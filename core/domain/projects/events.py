# core/domain/projects/events.py (ملف جديد)
"""Projects Domain Events - أحداث مجال المشاريع"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from decimal import Decimal

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import ProjectId, ProjectCode, ProjectStatus


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ProjectCreatedEvent(BaseDomainEvent):
    project_id: ProjectId
    project_code: ProjectCode
    project_name: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "projects.project.created"


@dataclass(frozen=True)
class ProjectUpdatedEvent(BaseDomainEvent):
    project_id: ProjectId
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "projects.project.updated"


@dataclass(frozen=True)
class ProjectStatusChangedEvent(BaseDomainEvent):
    project_id: ProjectId
    project_code: ProjectCode
    project_name: str
    old_status: ProjectStatus
    new_status: ProjectStatus
    reason: Optional[str]
    changed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "projects.project.status_changed"


@dataclass(frozen=True)
class ProjectBudgetUpdatedEvent(BaseDomainEvent):
    project_id: ProjectId
    project_code: ProjectCode
    project_name: str
    old_budget: Decimal
    new_budget: Decimal
    currency: str
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "projects.budget.updated"


@dataclass(frozen=True)
class ProjectExpenseRecordedEvent(BaseDomainEvent):
    project_id: ProjectId
    project_code: ProjectCode
    project_name: str
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    recorded_by: str
    notes: Optional[str]
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "projects.expense.recorded"


@dataclass(frozen=True)
class ProjectBudgetAlertEvent(BaseDomainEvent):
    project_id: ProjectId
    project_code: ProjectCode
    project_name: str
    alert_level: str
    budget_limit: Decimal
    actual_usage: Decimal
    remaining: Decimal
    utilization: Decimal
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "projects.budget.alert"