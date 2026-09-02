"""
Approval Workflow Commands - أوامر سير عمل الموافقات
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


# =============================================================================
# COMMANDS - أوامر إدارة سير العمل
# =============================================================================

@dataclass(frozen=True)
class CreateWorkflowCommand:
    """أمر إنشاء سير عمل جديد"""
    name: str
    code: str
    entity_type: str
    steps: List[Dict[str, Any]]
    description: Optional[str] = None
    is_mandatory: bool = False
    auto_approve_threshold: Optional[Decimal] = None
    auto_approve_after_days: Optional[int] = None
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateWorkflowCommand:
    """أمر تحديث سير العمل"""
    workflow_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    is_mandatory: Optional[bool] = None
    auto_approve_threshold: Optional[Decimal] = None
    auto_approve_after_days: Optional[int] = None
    updated_by: str = "system"
    version: int = 1


@dataclass(frozen=True)
class ActivateWorkflowCommand:
    """أمر تفعيل سير العمل"""
    workflow_id: str
    activated_by: str = "system"


@dataclass(frozen=True)
class DeactivateWorkflowCommand:
    """أمر تعطيل سير العمل"""
    workflow_id: str
    deactivated_by: str = "system"


@dataclass(frozen=True)
class DeleteWorkflowCommand:
    """أمر حذف سير العمل"""
    workflow_id: str
    deleted_by: str = "system"


# =============================================================================
# COMMANDS - أوامر طلبات الموافقة
# =============================================================================

@dataclass(frozen=True)
class CreateApprovalRequestCommand:
    """أمر إنشاء طلب موافقة"""
    entity_type: str
    entity_id: str
    title: str
    description: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "USD"
    priority: str = "normal"
    due_date: Optional[datetime] = None
    entity_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_by: str = "system"


@dataclass(frozen=True)
class SubmitRequestCommand:
    """أمر تقديم طلب للموافقة"""
    request_id: str
    submitted_by: str = "system"


@dataclass(frozen=True)
class ApproveRequestCommand:
    """أمر الموافقة على طلب"""
    request_id: str
    approver_id: str
    approver_name: str
    comment: Optional[str] = None


@dataclass(frozen=True)
class RejectRequestCommand:
    """أمر رفض طلب"""
    request_id: str
    approver_id: str
    approver_name: str
    reason: str


@dataclass(frozen=True)
class CancelRequestCommand:
    """أمر إلغاء طلب"""
    request_id: str
    cancelled_by: str
    reason: Optional[str] = None


@dataclass(frozen=True)
class EscalateRequestCommand:
    """أمر تصعيد طلب"""
    request_id: str
    escalated_by: str
    reason: Optional[str] = None


# ✅ إضافة أوامر جديدة
@dataclass(frozen=True)
class ReassignRequestCommand:
    """
    أمر إعادة تعيين طلب إلى مراجع آخر
    
    يقوم بتغيير المراجع المسؤول عن الطلب.
    """
    request_id: str
    new_approver_id: str
    new_approver_name: Optional[str] = None
    reason: Optional[str] = None
    reassigned_by: str = "system"


@dataclass(frozen=True)
class BatchApproveRequestsCommand:
    """
    أمر الموافقة الجماعية على طلبات متعددة
    
    يقوم بالموافقة على عدة طلبات دفعة واحدة.
    """
    request_ids: List[str]
    comment: Optional[str] = None
    approved_by: str = "system"


@dataclass(frozen=True)
class BatchRejectRequestsCommand:
    """
    أمر الرفض الجماعي لطلبات متعددة
    
    يقوم برفض عدة طلبات دفعة واحدة.
    """
    request_ids: List[str]
    reason: str
    rejected_by: str = "system"


# =============================================================================
# QUERIES - استعلامات
# =============================================================================

@dataclass(frozen=True)
class GetWorkflowQuery:
    """استعلام لجلب سير عمل"""
    workflow_id: str


@dataclass(frozen=True)
class GetWorkflowByEntityQuery:
    """استعلام لجلب سير عمل لنوع كيان"""
    entity_type: str


@dataclass(frozen=True)
class ListWorkflowsQuery:
    """استعلام لقائمة سير العمل"""
    entity_type: Optional[str] = None
    status: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetRequestQuery:
    """استعلام لجلب طلب موافقة"""
    request_id: str


@dataclass(frozen=True)
class GetRequestByEntityQuery:
    """استعلام لجلب طلب لكيان"""
    entity_type: str
    entity_id: str


@dataclass(frozen=True)
class ListRequestsQuery:
    """استعلام لقائمة طلبات الموافقة"""
    entity_type: Optional[str] = None
    status: Optional[str] = None
    requestor_id: Optional[str] = None
    approver_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class ListPendingRequestsQuery:
    """استعلام لقائمة الطلبات المعلقة"""
    entity_type: Optional[str] = None
    approver_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetRequestStatisticsQuery:
    """استعلام لإحصائيات الطلبات"""
    entity_type: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


# ✅ إضافة استعلامات جديدة
@dataclass(frozen=True)
class GetRequestsByApproverQuery:
    """استعلام لجلب الطلبات الموكلة لمراجع معين"""
    approver_id: str
    status: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetRequestsByRequestorQuery:
    """استعلام لجلب الطلبات المقدمة من مقدم معين"""
    requestor_id: str
    status: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Workflow Commands
    "CreateWorkflowCommand",
    "UpdateWorkflowCommand",
    "ActivateWorkflowCommand",
    "DeactivateWorkflowCommand",
    "DeleteWorkflowCommand",
    
    # Request Commands
    "CreateApprovalRequestCommand",
    "SubmitRequestCommand",
    "ApproveRequestCommand",
    "RejectRequestCommand",
    "CancelRequestCommand",
    "EscalateRequestCommand",
    "ReassignRequestCommand",           # ✅ إضافة
    
    # Batch Commands
    "BatchApproveRequestsCommand",      # ✅ إضافة
    "BatchRejectRequestsCommand",       # ✅ إضافة
    
    # Queries
    "GetWorkflowQuery",
    "GetWorkflowByEntityQuery",
    "ListWorkflowsQuery",
    "GetRequestQuery",
    "GetRequestByEntityQuery",
    "ListRequestsQuery",
    "ListPendingRequestsQuery",
    "GetRequestStatisticsQuery",
    "GetRequestsByApproverQuery",       # ✅ إضافة
    "GetRequestsByRequestorQuery",      # ✅ إضافة
]