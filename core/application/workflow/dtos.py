# core/application/workflow/dtos.py
"""
Approval Workflow DTOs - كائنات نقل البيانات لسير عمل الموافقات
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


@dataclass
class ApprovalStepDTO:
    """خطوة في سير العمل - DTO"""
    id: str
    name: str
    order: int
    role: str
    required_approvals: int = 1
    requires_all: bool = False
    is_final: bool = False
    timeout_hours: Optional[int] = None
    escalation_role: Optional[str] = None
    description: Optional[str] = None


@dataclass
class WorkflowDTO:
    """سير العمل - DTO"""
    id: str
    name: str
    code: str
    entity_type: str
    status: str
    steps: List[ApprovalStepDTO]
    is_mandatory: bool
    auto_approve_threshold: Optional[Decimal] = None
    auto_approve_after_days: Optional[int] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=datetime.now)
    updated_by: str = "system"
    version: int = 1

    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"

    @property
    def total_steps(self) -> int:
        return len(self.steps)


@dataclass
class ApprovalRecordDTO:
    """سجل الموافقة - DTO"""
    approver_id: str
    approver_name: str
    action: str
    comment: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None


@dataclass
class RequestHistoryDTO:
    """سجل تاريخ الطلب - DTO"""
    id: str
    action: str
    performed_by: str
    performed_by_name: str
    performed_at: datetime
    from_status: str
    to_status: str
    comment: Optional[str] = None


@dataclass
class ApprovalRequestDTO:
    """
    طلب الموافقة - DTO
    
    ⚠️ ملاحظة: جميع الحقول الإجبارية (بدون قيم افتراضية) 
    يجب أن تأتي قبل الحقول الاختيارية (ذات القيم الافتراضية)
    """
    
    # ========== الحقول الإجبارية (بدون قيم افتراضية) ==========
    id: str
    workflow_id: str
    entity_type: str
    entity_id: str
    status: str
    title: str
    
    # معلومات مقدم الطلب (إجبارية)
    requested_by: str
    requested_by_name: str
    requested_at: datetime
    
    # معلومات الموافقة/الرفض (اختيارية ولكن تبقى إجبارية في الهيكل)
    approved_by: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    rejected_by: Optional[str] = None
    rejected_by_name: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # ========== الحقول الاختيارية (بقيم افتراضية) ==========
    description: Optional[str] = None
    priority: str = "normal"
    amount: Optional[Decimal] = None
    currency: str = "USD"
    due_date: Optional[datetime] = None
    
    # القوائم (مع قيم افتراضية)
    approvals: List[ApprovalRecordDTO] = field(default_factory=list)
    history: List[RequestHistoryDTO] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1

    # ========== الخصائص المساعدة ==========
    
    @property
    def is_pending(self) -> bool:
        return self.status in ["pending", "in_review"]

    @property
    def is_approved(self) -> bool:
        return self.status == "approved"

    @property
    def is_rejected(self) -> bool:
        return self.status == "rejected"

    @property
    def is_cancelled(self) -> bool:
        return self.status == "cancelled"

    @property
    def is_expired(self) -> bool:
        return self.status == "expired"

    @property
    def display_name(self) -> str:
        return f"{self.title} ({self.entity_type})"

    @property
    def is_completed(self) -> bool:
        return self.status in ["approved", "rejected", "cancelled"]

    @property
    def can_approve(self) -> bool:
        return self.status in ["pending", "in_review"]
    
    @property
    def approval_count(self) -> int:
        return len(self.approvals)
    
    @property
    def approved_count(self) -> int:
        return len([a for a in self.approvals if a.action == "approve"])
    
    @property
    def rejected_count(self) -> int:
        return len([a for a in self.approvals if a.action == "reject"])


@dataclass
class RequestStatisticsDTO:
    """إحصائيات طلبات الموافقة - DTO"""
    total_count: int
    draft_count: int
    pending_count: int
    in_review_count: int
    approved_count: int
    rejected_count: int
    cancelled_count: int
    expired_count: int
    
    total_amount: Decimal = Decimal('0')
    approved_amount: Decimal = Decimal('0')
    rejected_amount: Decimal = Decimal('0')
    currency: str = "USD"
    
    by_entity_type: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)
    
    average_approval_time_hours: Optional[float] = None
    approval_rate: Optional[float] = None
    
    # ========== الخصائص المساعدة ==========
    
    @property
    def completion_rate(self) -> float:
        """نسبة الطلبات المكتملة"""
        completed = self.approved_count + self.rejected_count + self.cancelled_count
        if self.total_count == 0:
            return 0.0
        return (completed / self.total_count) * 100
    
    @property
    def pending_rate(self) -> float:
        """نسبة الطلبات المعلقة"""
        pending = self.pending_count + self.in_review_count
        if self.total_count == 0:
            return 0.0
        return (pending / self.total_count) * 100
    
    @property
    def total_amount_formatted(self) -> str:
        return f"{self.total_amount:,.2f} {self.currency}"
    
    @property
    def approved_amount_formatted(self) -> str:
        return f"{self.approved_amount:,.2f} {self.currency}"


# ========== دالة مساعدة لإنشاء DTO من Entity ==========

def request_to_dto(request) -> ApprovalRequestDTO:
    """
    تحويل كيان ApprovalRequest إلى DTO
    
    Args:
        request: كيان ApprovalRequest من Domain Layer
    
    Returns:
        ApprovalRequestDTO: كائن نقل البيانات
    """
    if not request:
        return None
    
    return ApprovalRequestDTO(
        id=str(request.id),
        workflow_id=str(request.workflow_id),
        entity_type=request.entity_type.value,
        entity_id=request.entity_id,
        status=request.status.value,
        title=request.title,
        description=request.description,
        priority=request.priority,
        amount=request.amount,
        currency=request.currency,
        due_date=request.due_date,
        requested_by=request.requested_by,
        requested_by_name=request.requested_by_name,
        requested_at=request.requested_at,
        approved_by=request.approved_by,
        approved_by_name=request.approved_by_name,
        approved_at=request.approved_at,
        rejected_by=request.rejected_by,
        rejected_by_name=request.rejected_by_name,
        rejected_at=request.rejected_at,
        rejection_reason=request.rejection_reason,
        approvals=[
            ApprovalRecordDTO(
                approver_id=a.approver_id,
                approver_name=a.approver_name,
                action=a.action.value,
                comment=a.comment,
                approved_at=a.approved_at,
                rejected_at=a.rejected_at
            )
            for a in request.approvals
        ],
        history=[
            RequestHistoryDTO(
                id=h.id,
                action=h.action,
                performed_by=h.performed_by,
                performed_by_name=h.performed_by_name,
                performed_at=h.performed_at,
                from_status=h.from_status,
                to_status=h.to_status,
                comment=h.comment
            )
            for h in request.history
        ],
        metadata=request.metadata,
        version=request.version
    )


__all__ = [
    "ApprovalStepDTO",
    "WorkflowDTO",
    "ApprovalRecordDTO",
    "RequestHistoryDTO",
    "ApprovalRequestDTO",
    "RequestStatisticsDTO",
    "request_to_dto",
]