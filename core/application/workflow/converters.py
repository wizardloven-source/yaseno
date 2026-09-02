# core/application/workflow/converters.py
"""
Approval Workflow Converters - محولات سير عمل الموافقات
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal

from core.domain.workflow.entities import Workflow, ApprovalRequest
from core.domain.workflow.value_objects import (
    WorkflowStatus, RequestStatus, WorkflowEntityType,
    ApprovalAction, ApprovalStep, ApprovalRecord, RequestHistory
)

from .dtos import (
    WorkflowDTO,
    ApprovalStepDTO,
    ApprovalRequestDTO,
    ApprovalRecordDTO,
    RequestHistoryDTO,
    RequestStatisticsDTO
)


# =============================================================================
# دوال مساعدة
# =============================================================================

def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, 'value'):
        return str(value.value)
    return str(value)


def _safe_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return Decimal('0')


def _safe_datetime(value: Any):
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value
    return value


# =============================================================================
# Workflow Converters
# =============================================================================

def step_to_dto(step: ApprovalStep) -> ApprovalStepDTO:
    """تحويل ApprovalStep إلى DTO"""
    if not step:
        return None

    return ApprovalStepDTO(
        id=step.id,
        name=step.name,
        order=step.order,
        role=step.role,
        required_approvals=step.required_approvals,
        requires_all=step.requires_all,
        is_final=step.is_final,
        timeout_hours=step.timeout_hours,
        escalation_role=step.escalation_role,
        description=step.description
    )


def steps_to_dto_list(steps: List[ApprovalStep]) -> List[ApprovalStepDTO]:
    """تحويل قائمة ApprovalSteps إلى DTOs"""
    if not steps:
        return []
    return [step_to_dto(s) for s in steps if s]


def workflow_to_dto(workflow: Workflow) -> WorkflowDTO:
    """تحويل Workflow إلى DTO"""
    if not workflow:
        return None

    return WorkflowDTO(
        id=_safe_str(workflow.id),
        name=workflow.name,
        code=workflow.code,
        entity_type=workflow.entity_type.value,
        status=workflow.status.value,
        steps=steps_to_dto_list(workflow.steps),
        is_mandatory=workflow.is_mandatory,
        auto_approve_threshold=workflow.auto_approve_threshold,
        auto_approve_after_days=workflow.auto_approve_after_days,
        description=workflow.description,
        created_at=workflow.created_at,
        created_by=workflow.created_by,
        updated_at=workflow.updated_at,
        updated_by=workflow.updated_by,
        version=workflow.version
    )


def workflows_to_dto_list(workflows: List[Workflow]) -> List[WorkflowDTO]:
    """تحويل قائمة Workflows إلى DTOs"""
    if not workflows:
        return []
    return [workflow_to_dto(w) for w in workflows if w]


# =============================================================================
# ApprovalRequest Converters
# =============================================================================

def approval_record_to_dto(record: ApprovalRecord) -> ApprovalRecordDTO:
    """تحويل ApprovalRecord إلى DTO"""
    if not record:
        return None

    return ApprovalRecordDTO(
        approver_id=record.approver_id,
        approver_name=record.approver_name,
        action=record.action.value,
        comment=record.comment,
        approved_at=record.approved_at,
        rejected_at=record.rejected_at
    )


def approval_records_to_dto_list(records: List[ApprovalRecord]) -> List[ApprovalRecordDTO]:
    """تحويل قائمة ApprovalRecords إلى DTOs"""
    if not records:
        return []
    return [approval_record_to_dto(r) for r in records if r]


def request_history_to_dto(history: RequestHistory) -> RequestHistoryDTO:
    """تحويل RequestHistory إلى DTO"""
    if not history:
        return None

    return RequestHistoryDTO(
        id=history.id,
        action=history.action,
        performed_by=history.performed_by,
        performed_by_name=history.performed_by_name,
        performed_at=history.performed_at,
        from_status=history.from_status,
        to_status=history.to_status,
        comment=history.comment
    )


def request_history_to_dto_list(history: List[RequestHistory]) -> List[RequestHistoryDTO]:
    """تحويل قائمة RequestHistory إلى DTOs"""
    if not history:
        return []
    return [request_history_to_dto(h) for h in history if h]


def request_to_dto(request: ApprovalRequest) -> ApprovalRequestDTO:
    """تحويل ApprovalRequest إلى DTO"""
    if not request:
        return None

    return ApprovalRequestDTO(
        id=_safe_str(request.id),
        workflow_id=_safe_str(request.workflow_id),
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
        approvals=approval_records_to_dto_list(request.approvals),
        history=request_history_to_dto_list(request.history),
        metadata=request.metadata,
        version=request.version
    )


def requests_to_dto_list(requests: List[ApprovalRequest]) -> List[ApprovalRequestDTO]:
    """تحويل قائمة ApprovalRequests إلى DTOs"""
    if not requests:
        return []
    return [request_to_dto(r) for r in requests if r]


# =============================================================================
# Statistics Converters
# =============================================================================

def statistics_to_dto(
    total_count: int,
    status_counts: Dict[str, int],
    total_amount: Decimal = Decimal('0'),
    approved_amount: Decimal = Decimal('0'),
    rejected_amount: Decimal = Decimal('0'),
    currency: str = "USD",
    by_entity_type: Optional[Dict[str, int]] = None,
    by_priority: Optional[Dict[str, int]] = None,
    average_approval_time_hours: Optional[float] = None,
    approval_rate: Optional[float] = None
) -> RequestStatisticsDTO:
    """تحويل إحصائيات الطلبات إلى DTO"""
    return RequestStatisticsDTO(
        total_count=total_count,
        draft_count=status_counts.get('draft', 0),
        pending_count=status_counts.get('pending', 0),
        in_review_count=status_counts.get('in_review', 0),
        approved_count=status_counts.get('approved', 0),
        rejected_count=status_counts.get('rejected', 0),
        cancelled_count=status_counts.get('cancelled', 0),
        expired_count=status_counts.get('expired', 0),
        total_amount=total_amount,
        approved_amount=approved_amount,
        rejected_amount=rejected_amount,
        currency=currency,
        by_entity_type=by_entity_type or {},
        by_priority=by_priority or {},
        average_approval_time_hours=average_approval_time_hours,
        approval_rate=approval_rate
    )


# =============================================================================
# دوال إضافية
# =============================================================================

def request_to_dict(request: ApprovalRequest) -> Dict[str, Any]:
    """تحويل ApprovalRequest إلى قاموس (للاستخدام في API)"""
    if not request:
        return {}

    return {
        'id': _safe_str(request.id),
        'workflow_id': _safe_str(request.workflow_id),
        'entity_type': request.entity_type.value,
        'entity_id': request.entity_id,
        'status': request.status.value,
        'title': request.title,
        'description': request.description,
        'priority': request.priority,
        'amount': float(request.amount) if request.amount else None,
        'currency': request.currency,
        'due_date': request.due_date.isoformat() if request.due_date else None,
        'requested_by': request.requested_by,
        'requested_by_name': request.requested_by_name,
        'requested_at': request.requested_at.isoformat(),
        'approved_by': request.approved_by,
        'approved_by_name': request.approved_by_name,
        'approved_at': request.approved_at.isoformat() if request.approved_at else None,
        'rejected_by': request.rejected_by,
        'rejected_by_name': request.rejected_by_name,
        'rejected_at': request.rejected_at.isoformat() if request.rejected_at else None,
        'rejection_reason': request.rejection_reason,
        'approvals': [
            {
                'approver_id': a.approver_id,
                'approver_name': a.approver_name,
                'action': a.action.value,
                'comment': a.comment,
                'approved_at': a.approved_at.isoformat() if a.approved_at else None
            }
            for a in request.approvals
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
            for h in request.history
        ],
        'metadata': request.metadata,
        'version': request.version
    }


def workflow_to_dict(workflow: Workflow) -> Dict[str, Any]:
    """تحويل Workflow إلى قاموس (للاستخدام في API)"""
    if not workflow:
        return {}

    return {
        'id': _safe_str(workflow.id),
        'name': workflow.name,
        'code': workflow.code,
        'entity_type': workflow.entity_type.value,
        'status': workflow.status.value,
        'steps': [
            {
                'id': s.id,
                'name': s.name,
                'order': s.order,
                'role': s.role,
                'required_approvals': s.required_approvals,
                'requires_all': s.requires_all,
                'is_final': s.is_final,
                'timeout_hours': s.timeout_hours,
                'escalation_role': s.escalation_role,
                'description': s.description
            }
            for s in workflow.steps
        ],
        'is_mandatory': workflow.is_mandatory,
        'auto_approve_threshold': float(workflow.auto_approve_threshold) if workflow.auto_approve_threshold else None,
        'auto_approve_after_days': workflow.auto_approve_after_days,
        'description': workflow.description,
        'created_at': workflow.created_at.isoformat(),
        'created_by': workflow.created_by,
        'updated_at': workflow.updated_at.isoformat(),
        'updated_by': workflow.updated_by,
        'version': workflow.version
    }


__all__ = [
    # Workflow
    'step_to_dto',
    'steps_to_dto_list',
    'workflow_to_dto',
    'workflows_to_dto_list',
    'workflow_to_dict',
    
    # Request
    'approval_record_to_dto',
    'approval_records_to_dto_list',
    'request_history_to_dto',
    'request_history_to_dto_list',
    'request_to_dto',
    'requests_to_dto_list',
    'request_to_dict',
    
    # Statistics
    'statistics_to_dto',
]