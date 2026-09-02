# core/domain/workflow/entities.py - الإصدار النهائي

"""
Approval Workflow Entities - كيانات سير عمل الموافقات
"""

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4
from decimal import Decimal

# ✅ استيراد من value_objects فقط
from .value_objects import (
    WorkflowId, RequestId, WorkflowStatus, RequestStatus,
    ApprovalAction, WorkflowEntityType, ApprovalStep,
    ApprovalRecord, RequestHistory
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Workflow:
    """AGGREGATE ROOT - سير العمل"""
    id: WorkflowId = field(default_factory=lambda: WorkflowId(str(uuid4())))
    name: str = ""
    code: str = ""
    description: Optional[str] = None
    entity_type: WorkflowEntityType = WorkflowEntityType.CUSTOM
    status: WorkflowStatus = WorkflowStatus.DRAFT
    
    steps: List[ApprovalStep] = field(default_factory=list)
    current_step_index: int = 0
    
    is_mandatory: bool = False
    auto_approve_threshold: Optional[Decimal] = None
    auto_approve_after_days: Optional[int] = None
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"
    
    @property
    def is_active(self) -> bool:
        return self.status == WorkflowStatus.ACTIVE
    
    @property
    def total_steps(self) -> int:
        return len(self.steps)
    
    @property
    def current_step(self) -> Optional[ApprovalStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def add_step(self, step: ApprovalStep) -> None:
        step = replace(step, order=len(self.steps))
        self.steps.append(step)
        self.updated_at = utc_now()
        self.version += 1
    
    def remove_step(self, step_id: str) -> bool:
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                self.steps.pop(i)
                for j, s in enumerate(self.steps):
                    self.steps[j] = replace(s, order=j)
                self.updated_at = utc_now()
                self.version += 1
                return True
        return False
    
    def activate(self, activated_by: str) -> None:
        if not self.steps:
            raise ValueError("Cannot activate workflow with no steps")
        self.status = WorkflowStatus.ACTIVE
        self.updated_at = utc_now()
        self.updated_by = activated_by
        self.version += 1
    
    def deactivate(self, deactivated_by: str) -> None:
        self.status = WorkflowStatus.INACTIVE
        self.updated_at = utc_now()
        self.updated_by = deactivated_by
        self.version += 1
    
    def archive(self, archived_by: str) -> None:
        self.status = WorkflowStatus.ARCHIVED
        self.updated_at = utc_now()
        self.updated_by = archived_by
        self.version += 1
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events


@dataclass
class ApprovalRequest:
    """
    AGGREGATE ROOT - طلب الموافقة
    
    ⚠️ جميع الحقول الإجبارية أولاً (بدون قيم افتراضية)
    """
    # ========== الحقول الإجبارية ==========
    id: RequestId
    workflow_id: WorkflowId
    entity_type: WorkflowEntityType
    entity_id: str
    requested_by: str
    requested_by_name: str
    title: str
    entity_data: Dict[str, Any]
    
    # ========== الحقول الاختيارية ==========
    requested_at: datetime = field(default_factory=utc_now)
    status: RequestStatus = RequestStatus.DRAFT
    current_step_index: int = 0
    description: Optional[str] = None
    priority: str = "normal"
    due_date: Optional[datetime] = None
    amount: Optional[Decimal] = None
    currency: str = "USD"
    approvals: List[ApprovalRecord] = field(default_factory=list)
    history: List[RequestHistory] = field(default_factory=list)
    approved_by: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_by_name: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def is_pending(self) -> bool:
        return self.status in [RequestStatus.PENDING, RequestStatus.IN_REVIEW]
    
    @property
    def is_approved(self) -> bool:
        return self.status == RequestStatus.APPROVED
    
    @property
    def is_rejected(self) -> bool:
        return self.status == RequestStatus.REJECTED
    
    @property
    def is_cancelled(self) -> bool:
        return self.status == RequestStatus.CANCELLED
    
    @property
    def is_draft(self) -> bool:
        return self.status == RequestStatus.DRAFT
    
    @property
    def is_expired(self) -> bool:
        return self.status == RequestStatus.EXPIRED
    
    @property
    def can_approve(self) -> bool:
        return self.status in [RequestStatus.PENDING, RequestStatus.IN_REVIEW]
    
    @property
    def current_step(self) -> Optional[ApprovalStep]:
        return None
    
    @property
    def approval_count(self) -> int:
        return len(self.approvals)
    
    @property
    def approved_count(self) -> int:
        return len([a for a in self.approvals if a.is_approved])
    
    @property
    def rejected_count(self) -> int:
        return len([a for a in self.approvals if a.is_rejected])
    
    @property
    def is_completed(self) -> bool:
        return self.status in [RequestStatus.APPROVED, RequestStatus.REJECTED, RequestStatus.CANCELLED]
    
    def submit(self, submitted_by: str) -> None:
        if self.status != RequestStatus.DRAFT:
            raise ValueError(f"Cannot submit request in status '{self.status.value}'")
        
        self.status = RequestStatus.PENDING
        self.requested_by = submitted_by
        self.requested_at = utc_now()
        self.version += 1
        
        self._add_history(
            action="submit",
            performed_by=submitted_by,
            from_status=RequestStatus.DRAFT.value,
            to_status=RequestStatus.PENDING.value,
            comment="تم تقديم الطلب للموافقة"
        )
        
        from .events import RequestSubmittedEvent
        self._events.append(RequestSubmittedEvent(
            request_id=self.id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            title=self.title,
            submitted_by=submitted_by
        ))
    
    def approve(self, approver_id: str, approver_name: str, comment: Optional[str] = None) -> None:
        if not self.can_approve:
            raise ValueError(f"Cannot approve request in status '{self.status.value}'")
        
        record = ApprovalRecord(
            approver_id=approver_id,
            approver_name=approver_name,
            action=ApprovalAction.APPROVE,
            comment=comment,
            approved_at=utc_now()
        )
        self.approvals.append(record)
        
        if self._is_fully_approved():
            self.status = RequestStatus.APPROVED
            self.approved_by = approver_id
            self.approved_by_name = approver_name
            self.approved_at = utc_now()
            
            self._add_history(
                action="approve",
                performed_by=approver_id,
                from_status=RequestStatus.IN_REVIEW.value,
                to_status=RequestStatus.APPROVED.value,
                comment=comment
            )
            
            from .events import RequestApprovedEvent
            self._events.append(RequestApprovedEvent(
                request_id=self.id,
                entity_type=self.entity_type,
                entity_id=self.entity_id,
                approved_by=approver_id,
                approved_at=self.approved_at
            ))
        else:
            self.status = RequestStatus.IN_REVIEW
            self._add_history(
                action="approve",
                performed_by=approver_id,
                from_status=RequestStatus.PENDING.value,
                to_status=RequestStatus.IN_REVIEW.value,
                comment=f"تمت الموافقة من قبل {approver_name} - قيد المراجعة"
            )
        
        self.version += 1
    
    def reject(self, approver_id: str, approver_name: str, reason: str) -> None:
        if not self.can_approve:
            raise ValueError(f"Cannot reject request in status '{self.status.value}'")
        
        self.status = RequestStatus.REJECTED
        self.rejected_by = approver_id
        self.rejected_by_name = approver_name
        self.rejected_at = utc_now()
        self.rejection_reason = reason
        self.version += 1
        
        record = ApprovalRecord(
            approver_id=approver_id,
            approver_name=approver_name,
            action=ApprovalAction.REJECT,
            comment=reason,
            rejected_at=utc_now()
        )
        self.approvals.append(record)
        
        self._add_history(
            action="reject",
            performed_by=approver_id,
            from_status=RequestStatus.PENDING.value,
            to_status=RequestStatus.REJECTED.value,
            comment=reason
        )
        
        from .events import RequestRejectedEvent
        self._events.append(RequestRejectedEvent(
            request_id=self.id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            rejected_by=approver_id,
            reason=reason
        ))
    
    def cancel(self, cancelled_by: str, reason: Optional[str] = None) -> None:
        if self.is_completed:
            raise ValueError(f"Cannot cancel completed request")
        
        self.status = RequestStatus.CANCELLED
        self.version += 1
        
        self._add_history(
            action="cancel",
            performed_by=cancelled_by,
            from_status=self.status.value,
            to_status=RequestStatus.CANCELLED.value,
            comment=reason
        )
        
        from .events import RequestCancelledEvent
        self._events.append(RequestCancelledEvent(
            request_id=self.id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            cancelled_by=cancelled_by,
            reason=reason
        ))
    
    def escalate(self, escalated_by: str, reason: Optional[str] = None) -> None:
        if not self.can_approve:
            raise ValueError(f"Cannot escalate request in status '{self.status.value}'")
        
        self.status = RequestStatus.IN_REVIEW
        self.version += 1
        
        self._add_history(
            action="escalate",
            performed_by=escalated_by,
            from_status=RequestStatus.PENDING.value,
            to_status=RequestStatus.IN_REVIEW.value,
            comment=reason
        )
        
        from .events import RequestEscalatedEvent
        self._events.append(RequestEscalatedEvent(
            request_id=self.id,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            escalated_by=escalated_by,
            reason=reason
        ))
    
    def expire(self) -> None:
        if not self.is_pending:
            return
        
        self.status = RequestStatus.EXPIRED
        self.version += 1
        
        self._add_history(
            action="expire",
            performed_by="system",
            from_status=RequestStatus.PENDING.value,
            to_status=RequestStatus.EXPIRED.value,
            comment="انتهت صلاحية الطلب"
        )
    
    def _is_fully_approved(self) -> bool:
        return len(self.approvals) > 0 and self.approved_count > 0
    
    def _add_history(
        self,
        action: str,
        performed_by: str,
        from_status: str,
        to_status: str,
        comment: Optional[str] = None
    ) -> None:
        history = RequestHistory(
            id=str(uuid4()),
            request_id=str(self.id),
            action=action,
            performed_by=performed_by,
            performed_by_name=performed_by,
            performed_at=utc_now(),
            from_status=from_status,
            to_status=to_status,
            comment=comment
        )
        self.history.append(history)
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'workflow_id': str(self.workflow_id),
            'entity_type': self.entity_type.value,
            'entity_id': self.entity_id,
            'status': self.status.value,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'requested_by': self.requested_by,
            'requested_by_name': self.requested_by_name,
            'requested_at': self.requested_at.isoformat(),
            'approved_by': self.approved_by,
            'approved_by_name': self.approved_by_name,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'rejected_by': self.rejected_by,
            'rejected_by_name': self.rejected_by_name,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'rejection_reason': self.rejection_reason,
            'approvals': [
                {
                    'approver_id': a.approver_id,
                    'approver_name': a.approver_name,
                    'action': a.action.value,
                    'comment': a.comment,
                    'approved_at': a.approved_at.isoformat() if a.approved_at else None,
                    'rejected_at': a.rejected_at.isoformat() if a.rejected_at else None
                }
                for a in self.approvals
            ],
            'history': [
                {
                    'id': h.id,
                    'action': h.action,
                    'performed_by': h.performed_by,
                    'performed_at': h.performed_at.isoformat(),
                    'from_status': h.from_status,
                    'to_status': h.to_status,
                    'comment': h.comment
                }
                for h in self.history
            ],
            'version': self.version
        }