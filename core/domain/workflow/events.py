# core/domain/workflow/events.py
"""
Approval Workflow Events - أحداث سير عمل الموافقات
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import RequestId, WorkflowId, WorkflowEntityType


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# أحداث سير العمل
# =============================================================================

@dataclass(frozen=True)
class WorkflowCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء سير عمل جديد"""
    workflow_id: WorkflowId
    name: str
    code: str
    entity_type: WorkflowEntityType
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.created"


@dataclass(frozen=True)
class WorkflowActivatedEvent(BaseDomainEvent):
    """يُرفع عند تفعيل سير العمل"""
    workflow_id: WorkflowId
    name: str
    code: str
    activated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.activated"


@dataclass(frozen=True)
class WorkflowDeactivatedEvent(BaseDomainEvent):
    """يُرفع عند تعطيل سير العمل"""
    workflow_id: WorkflowId
    name: str
    code: str
    deactivated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.deactivated"


# =============================================================================
# أحداث طلب الموافقة
# =============================================================================

@dataclass(frozen=True)
class RequestSubmittedEvent(BaseDomainEvent):
    """يُرفع عند تقديم طلب للموافقة"""
    request_id: RequestId
    entity_type: WorkflowEntityType
    entity_id: str
    title: str
    submitted_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.request.submitted"


@dataclass(frozen=True)
class RequestApprovedEvent(BaseDomainEvent):
    """يُرفع عند الموافقة على الطلب"""
    request_id: RequestId
    entity_type: WorkflowEntityType
    entity_id: str
    approved_by: str
    approved_at: datetime
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.request.approved"


@dataclass(frozen=True)
class RequestRejectedEvent(BaseDomainEvent):
    """يُرفع عند رفض الطلب"""
    request_id: RequestId
    entity_type: WorkflowEntityType
    entity_id: str
    rejected_by: str
    reason: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.request.rejected"


@dataclass(frozen=True)
class RequestCancelledEvent(BaseDomainEvent):
    """يُرفع عند إلغاء الطلب"""
    request_id: RequestId
    entity_type: WorkflowEntityType
    entity_id: str
    cancelled_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.request.cancelled"


@dataclass(frozen=True)
class RequestEscalatedEvent(BaseDomainEvent):
    """يُرفع عند تصعيد الطلب"""
    request_id: RequestId
    entity_type: WorkflowEntityType
    entity_id: str
    escalated_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.request.escalated"


@dataclass(frozen=True)
class RequestExpiredEvent(BaseDomainEvent):
    """يُرفع عند انتهاء صلاحية الطلب"""
    request_id: RequestId
    entity_type: WorkflowEntityType
    entity_id: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.request.expired"


@dataclass(frozen=True)
class RequestAssignedEvent(BaseDomainEvent):
    """يُرفع عند تعيين طلب إلى مراجع"""
    request_id: RequestId
    entity_type: WorkflowEntityType
    entity_id: str
    assigned_to: str
    assigned_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "workflow.request.assigned"


# =============================================================================
# تصدير جميع الأحداث
# =============================================================================

__all__ = [
    "WorkflowCreatedEvent",
    "WorkflowActivatedEvent",
    "WorkflowDeactivatedEvent",
    "RequestSubmittedEvent",
    "RequestApprovedEvent",
    "RequestRejectedEvent",
    "RequestCancelledEvent",
    "RequestEscalatedEvent",
    "RequestExpiredEvent",
    "RequestAssignedEvent",
]