# core/infrastructure/db/postgres/workflow_repository.py
"""
Approval Workflow Repository - مستودع سير عمل الموافقات
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update, delete, and_, or_, func, desc
from sqlalchemy.orm import Session

from core.domain.workflow.entities import Workflow, ApprovalRequest
from core.domain.workflow.value_objects import (
    WorkflowId, RequestId, WorkflowStatus, RequestStatus, WorkflowEntityType
)
from core.domain.workflow.interfaces import IWorkflowRepository, IApprovalRequestRepository
from core.shared.exceptions import ConcurrentModificationError

from ..models.workflow_model import WorkflowModel, ApprovalRequestModel


# =============================================================================
# دوال التحويل - Workflow
# =============================================================================

def _model_to_domain_workflow(model: WorkflowModel) -> Workflow:
    """تحويل ORM Model إلى Domain Entity - Workflow"""
    if not model:
        return None

    workflow = Workflow(
        id=WorkflowId(str(model.id)),
        name=model.name,
        code=model.code,
        description=model.description,
        entity_type=WorkflowEntityType(model.entity_type),
        status=WorkflowStatus(model.status),
        is_mandatory=model.is_mandatory,
        auto_approve_threshold=model.auto_approve_threshold,
        auto_approve_after_days=model.auto_approve_after_days,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )

    # إعادة بناء الخطوات
    from core.domain.workflow.value_objects import ApprovalStep
    for step_data in model.steps:
        step = ApprovalStep(
            id=step_data.get('id', ''),
            name=step_data.get('name', ''),
            order=step_data.get('order', 0),
            role=step_data.get('role', ''),
            required_approvals=step_data.get('required_approvals', 1),
            requires_all=step_data.get('requires_all', False),
            is_final=step_data.get('is_final', False),
            timeout_hours=step_data.get('timeout_hours'),
            escalation_role=step_data.get('escalation_role'),
            description=step_data.get('description')
        )
        workflow.steps.append(step)

    workflow.current_step_index = model.current_step_index

    return workflow


def _domain_to_model_workflow(workflow: Workflow) -> WorkflowModel:
    """تحويل Domain Entity إلى ORM Model - Workflow"""
    return WorkflowModel(
        id=UUID(str(workflow.id)),
        name=workflow.name,
        code=workflow.code,
        description=workflow.description,
        entity_type=workflow.entity_type.value,
        status=workflow.status.value,
        steps=[
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
        current_step_index=workflow.current_step_index,
        is_mandatory=workflow.is_mandatory,
        auto_approve_threshold=workflow.auto_approve_threshold,
        auto_approve_after_days=workflow.auto_approve_after_days,
        created_at=workflow.created_at,
        created_by=workflow.created_by,
        updated_at=workflow.updated_at,
        updated_by=workflow.updated_by,
        version=workflow.version
    )


# =============================================================================
# دوال التحويل - ApprovalRequest (المُصحَّحة)
# =============================================================================

def _model_to_domain_request(model: ApprovalRequestModel) -> ApprovalRequest:
    """تحويل ORM Model إلى Domain Entity - ApprovalRequest"""
    if not model:
        return None

    request = ApprovalRequest(
        id=RequestId(str(model.id)),
        workflow_id=WorkflowId(str(model.workflow_id)),
        entity_type=WorkflowEntityType(model.entity_type),
        entity_id=model.entity_id,
        entity_data=model.entity_data,
        status=RequestStatus(model.status),
        current_step_index=model.current_step_index,
        title=model.title,
        description=model.description,
        priority=model.priority,
        due_date=model.due_date,
        amount=model.amount,
        currency=model.currency,
        requested_by=model.requested_by,
        requested_by_name=model.requested_by_name,
        requested_at=model.requested_at,
        approved_by=model.approved_by,
        approved_by_name=model.approved_by_name,
        approved_at=model.approved_at,
        rejected_by=model.rejected_by,
        rejected_by_name=model.rejected_by_name,
        rejected_at=model.rejected_at,
        rejection_reason=model.rejection_reason,
        metadata=model.extra_data or {},  # ✅ تم التعديل
        version=model.version
    )

    # إعادة بناء الموافقات
    from core.domain.workflow.value_objects import ApprovalRecord, ApprovalAction
    for rec_data in model.approvals:
        record = ApprovalRecord(
            approver_id=rec_data.get('approver_id', ''),
            approver_name=rec_data.get('approver_name', ''),
            action=ApprovalAction(rec_data.get('action', 'approve')),
            comment=rec_data.get('comment'),
            approved_at=rec_data.get('approved_at'),
            rejected_at=rec_data.get('rejected_at')
        )
        request.approvals.append(record)

    return request


def _domain_to_model_request(request: ApprovalRequest) -> ApprovalRequestModel:
    """تحويل Domain Entity إلى ORM Model - ApprovalRequest"""
    return ApprovalRequestModel(
        id=UUID(str(request.id)),
        workflow_id=UUID(str(request.workflow_id)),
        entity_type=request.entity_type.value,
        entity_id=request.entity_id,
        entity_data=request.entity_data,
        status=request.status.value,
        current_step_index=request.current_step_index,
        title=request.title,
        description=request.description,
        priority=request.priority,
        due_date=request.due_date,
        amount=request.amount,
        currency=request.currency,
        approvals=[
            {
                'approver_id': a.approver_id,
                'approver_name': a.approver_name,
                'action': a.action.value,
                'comment': a.comment,
                'approved_at': a.approved_at.isoformat() if a.approved_at else None,
                'rejected_at': a.rejected_at.isoformat() if a.rejected_at else None
            }
            for a in request.approvals
        ],
        history=[
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
        extra_data=request.metadata,  # ✅ تم التعديل
        version=request.version
    )


# =============================================================================
# Workflow Repository
# =============================================================================

class PostgresWorkflowRepository(IWorkflowRepository):
    """تطبيق PostgreSQL لمستودع سير العمل"""

    def __init__(self, session: Session):
        self._session = session

    def save(self, workflow: Workflow) -> None:
        """حفظ سير العمل مع Optimistic Locking"""
        existing = self._session.execute(
            select(WorkflowModel).where(WorkflowModel.id == UUID(str(workflow.id)))
        ).scalar_one_or_none()

        if existing:
            now = datetime.now(timezone.utc)
            new_version = existing.version + 1

            result = self._session.execute(
                update(WorkflowModel)
                .where(
                    WorkflowModel.id == UUID(str(workflow.id)),
                    WorkflowModel.version == workflow.version
                )
                .values(
                    name=workflow.name,
                    code=workflow.code,
                    description=workflow.description,
                    entity_type=workflow.entity_type.value,
                    status=workflow.status.value,
                    steps=[
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
                    current_step_index=workflow.current_step_index,
                    is_mandatory=workflow.is_mandatory,
                    auto_approve_threshold=workflow.auto_approve_threshold,
                    auto_approve_after_days=workflow.auto_approve_after_days,
                    updated_at=now,
                    updated_by=workflow.updated_by,
                    version=new_version
                )
            )

            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "Workflow",
                    str(workflow.id),
                    workflow.version,
                    existing.version
                )

            workflow.version = new_version

        else:
            model = _domain_to_model_workflow(workflow)
            self._session.add(model)
            self._session.flush()
            workflow.version = 1

    def get_by_id(self, workflow_id: WorkflowId) -> Optional[Workflow]:
        """الحصول على سير عمل بواسطة المعرف"""
        model = self._session.execute(
            select(WorkflowModel).where(WorkflowModel.id == UUID(str(workflow_id)))
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain_workflow(model)

    def get_by_code(self, code: str) -> Optional[Workflow]:
        """الحصول على سير عمل بواسطة الكود"""
        model = self._session.execute(
            select(WorkflowModel).where(WorkflowModel.code == code)
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain_workflow(model)

    def get_by_entity_type(self, entity_type: WorkflowEntityType) -> Optional[Workflow]:
        """الحصول على سير عمل لنوع كيان معين"""
        model = self._session.execute(
            select(WorkflowModel)
            .where(
                and_(
                    WorkflowModel.entity_type == entity_type.value,
                    WorkflowModel.status == 'active'
                )
            )
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain_workflow(model)

    def list_all(
        self,
        entity_type: Optional[WorkflowEntityType] = None,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Workflow]:
        """قائمة سير العمل"""
        query = select(WorkflowModel)

        if entity_type:
            query = query.where(WorkflowModel.entity_type == entity_type.value)

        if status:
            query = query.where(WorkflowModel.status == status.value)

        query = query.order_by(WorkflowModel.code).limit(limit).offset(offset)

        models = self._session.execute(query).scalars().all()

        return [_model_to_domain_workflow(m) for m in models]

    def delete(self, workflow_id: WorkflowId) -> bool:
        """حذف سير العمل"""
        workflow = self.get_by_id(workflow_id)
        if not workflow or workflow.status == WorkflowStatus.ACTIVE:
            return False

        result = self._session.execute(
            delete(WorkflowModel).where(WorkflowModel.id == UUID(str(workflow_id)))
        )
        self._session.flush()

        return result.rowcount > 0


# =============================================================================
# ApprovalRequest Repository
# =============================================================================

class PostgresApprovalRequestRepository(IApprovalRequestRepository):
    """تطبيق PostgreSQL لمستودع طلبات الموافقة"""

    def __init__(self, session: Session):
        self._session = session

    def save(self, request: ApprovalRequest) -> None:
        """حفظ طلب الموافقة"""
        existing = self._session.execute(
            select(ApprovalRequestModel).where(ApprovalRequestModel.id == UUID(str(request.id)))
        ).scalar_one_or_none()

        if existing:
            model = _domain_to_model_request(request)
            model.id = existing.id
            self._session.merge(model)
        else:
            model = _domain_to_model_request(request)
            self._session.add(model)

        self._session.flush()

    def get_by_id(self, request_id: RequestId) -> Optional[ApprovalRequest]:
        """الحصول على طلب بواسطة المعرف"""
        model = self._session.execute(
            select(ApprovalRequestModel).where(ApprovalRequestModel.id == UUID(str(request_id)))
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain_request(model)

    def get_by_entity(self, entity_type: WorkflowEntityType, entity_id: str) -> Optional[ApprovalRequest]:
        """الحصول على طلب لكيان معين"""
        model = self._session.execute(
            select(ApprovalRequestModel)
            .where(
                and_(
                    ApprovalRequestModel.entity_type == entity_type.value,
                    ApprovalRequestModel.entity_id == entity_id
                )
            )
            .order_by(desc(ApprovalRequestModel.requested_at))
            .limit(1)
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain_request(model)

    def list_by_entity_type(
        self,
        entity_type: WorkflowEntityType,
        status: Optional[RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة طلبات حسب نوع الكيان"""
        query = select(ApprovalRequestModel).where(
            ApprovalRequestModel.entity_type == entity_type.value
        )

        if status:
            query = query.where(ApprovalRequestModel.status == status.value)

        query = query.order_by(desc(ApprovalRequestModel.requested_at)).limit(limit).offset(offset)

        models = self._session.execute(query).scalars().all()

        return [_model_to_domain_request(m) for m in models]

    def list_by_approver(
        self,
        approver_id: str,
        status: Optional[RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة طلبات مراجعة من قبل مستخدم معين"""
        query = select(ApprovalRequestModel)

        # البحث في سجل الموافقات
        query = query.where(
            ApprovalRequestModel.approvals.contains([{'approver_id': approver_id}])
        )

        if status:
            query = query.where(ApprovalRequestModel.status == status.value)

        query = query.order_by(desc(ApprovalRequestModel.requested_at)).limit(limit).offset(offset)

        models = self._session.execute(query).scalars().all()

        return [_model_to_domain_request(m) for m in models]

    def list_by_requestor(
        self,
        requestor_id: str,
        status: Optional[RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة طلبات مقدم من قبل مستخدم معين"""
        query = select(ApprovalRequestModel).where(
            ApprovalRequestModel.requested_by == requestor_id
        )

        if status:
            query = query.where(ApprovalRequestModel.status == status.value)

        query = query.order_by(desc(ApprovalRequestModel.requested_at)).limit(limit).offset(offset)

        models = self._session.execute(query).scalars().all()

        return [_model_to_domain_request(m) for m in models]

    def list_pending(
        self,
        entity_type: Optional[WorkflowEntityType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة الطلبات المعلقة"""
        query = select(ApprovalRequestModel).where(
            ApprovalRequestModel.status.in_(['pending', 'in_review'])
        )

        if entity_type:
            query = query.where(ApprovalRequestModel.entity_type == entity_type.value)

        query = query.order_by(desc(ApprovalRequestModel.requested_at)).limit(limit).offset(offset)

        models = self._session.execute(query).scalars().all()

        return [_model_to_domain_request(m) for m in models]

    def list_by_date_range(
        self,
        from_date: datetime,
        to_date: datetime,
        status: Optional[RequestStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """قائمة طلبات في نطاق زمني"""
        query = select(ApprovalRequestModel).where(
            and_(
                ApprovalRequestModel.requested_at >= from_date,
                ApprovalRequestModel.requested_at <= to_date
            )
        )

        if status:
            query = query.where(ApprovalRequestModel.status == status.value)

        query = query.order_by(desc(ApprovalRequestModel.requested_at)).limit(limit).offset(offset)

        models = self._session.execute(query).scalars().all()

        return [_model_to_domain_request(m) for m in models]

    def count_by_status(self, status: RequestStatus) -> int:
        """حساب عدد الطلبات حسب الحالة"""
        result = self._session.execute(
            select(func.count()).select_from(ApprovalRequestModel)
            .where(ApprovalRequestModel.status == status.value)
        ).scalar()

        return result or 0

    def delete(self, request_id: RequestId) -> bool:
        """حذف طلب (فقط إذا كان مسودة)"""
        request = self.get_by_id(request_id)
        if not request or request.status != RequestStatus.DRAFT:
            return False

        result = self._session.execute(
            delete(ApprovalRequestModel).where(ApprovalRequestModel.id == UUID(str(request_id)))
        )
        self._session.flush()

        return result.rowcount > 0