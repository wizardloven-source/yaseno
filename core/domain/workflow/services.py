# core/domain/workflow/services.py - الإصدار المُصحَّح بالكامل

"""
Approval Workflow Services - خدمات سير عمل الموافقات
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4

from .entities import Workflow, ApprovalRequest
from .value_objects import (
    WorkflowId, RequestId, WorkflowStatus, RequestStatus,
    WorkflowEntityType, ApprovalStep, ApprovalAction
)
from .interfaces import IWorkflowRepository, IApprovalRequestRepository


class WorkflowService:
    """
    خدمة سير عمل الموافقات
    
    تدير إنشاء وتنفيذ سير العمل للموافقات على مختلف الكيانات.
    """

    def __init__(
        self,
        workflow_repo: IWorkflowRepository,
        request_repo: IApprovalRequestRepository
    ):
        self._workflow_repo = workflow_repo
        self._request_repo = request_repo

    # =========================================================================
    # إدارة سير العمل
    # =========================================================================

    def create_workflow(
        self,
        name: str,
        code: str,
        entity_type: WorkflowEntityType,
        steps: List[Dict[str, Any]],
        description: Optional[str] = None,
        is_mandatory: bool = False,
        auto_approve_threshold: Optional[Decimal] = None,
        auto_approve_after_days: Optional[int] = None,
        created_by: str = "system"
    ) -> Workflow:
        """إنشاء سير عمل جديد"""
        workflow = Workflow(
            name=name,
            code=code,
            entity_type=entity_type,
            description=description,
            is_mandatory=is_mandatory,
            auto_approve_threshold=auto_approve_threshold,
            auto_approve_after_days=auto_approve_after_days,
            created_by=created_by,
            updated_by=created_by
        )

        # إضافة الخطوات
        for step_data in steps:
            step = ApprovalStep(
                id=str(uuid4()),
                name=step_data.get('name', ''),
                order=step_data.get('order', len(workflow.steps)),
                role=step_data.get('role', ''),
                required_approvals=step_data.get('required_approvals', 1),
                requires_all=step_data.get('requires_all', False),
                is_final=step_data.get('is_final', False),
                timeout_hours=step_data.get('timeout_hours'),
                escalation_role=step_data.get('escalation_role'),
                description=step_data.get('description')
            )
            workflow.add_step(step)

        self._workflow_repo.save(workflow)
        return workflow

    def update_workflow(
        self,
        workflow_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_mandatory: Optional[bool] = None,
        auto_approve_threshold: Optional[Decimal] = None,
        auto_approve_after_days: Optional[int] = None,
        updated_by: str = "system"
    ) -> Workflow:
        """تحديث سير العمل"""
        workflow = self._workflow_repo.get_by_id(WorkflowId(workflow_id))
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        if name:
            workflow.name = name
        if description is not None:
            workflow.description = description
        if is_mandatory is not None:
            workflow.is_mandatory = is_mandatory
        if auto_approve_threshold is not None:
            workflow.auto_approve_threshold = auto_approve_threshold
        if auto_approve_after_days is not None:
            workflow.auto_approve_after_days = auto_approve_after_days

        workflow.updated_at = datetime.now(timezone.utc)
        workflow.updated_by = updated_by
        workflow.version += 1

        self._workflow_repo.save(workflow)
        return workflow

    def activate_workflow(self, workflow_id: str, activated_by: str) -> Workflow:
        """تفعيل سير العمل"""
        workflow = self._workflow_repo.get_by_id(WorkflowId(workflow_id))
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow.activate(activated_by)
        self._workflow_repo.save(workflow)
        return workflow

    def deactivate_workflow(self, workflow_id: str, deactivated_by: str) -> Workflow:
        """تعطيل سير العمل"""
        workflow = self._workflow_repo.get_by_id(WorkflowId(workflow_id))
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow.deactivate(deactivated_by)
        self._workflow_repo.save(workflow)
        return workflow

    def get_workflow_for_entity(self, entity_type: WorkflowEntityType) -> Optional[Workflow]:
        """الحصول على سير العمل المناسب لنوع الكيان"""
        return self._workflow_repo.get_by_entity_type(entity_type)

    # =========================================================================
    # ✅ إدارة طلبات الموافقة - الجزء المُصحَّح
    # =========================================================================

    def create_request(
        self,
        entity_type: WorkflowEntityType,
        entity_id: str,
        title: str,
        requested_by: str,
        requested_by_name: str,
        description: Optional[str] = None,
        amount: Optional[Decimal] = None,
        currency: str = "USD",
        priority: str = "normal",
        due_date: Optional[datetime] = None,
        entity_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        إنشاء طلب موافقة جديد
        
        ✅ مصحح: تمرير جميع الحقول الإجبارية بما فيها id و requested_at
        """
        # الحصول على سير العمل المناسب
        workflow = self._workflow_repo.get_by_entity_type(entity_type)
        if not workflow:
            raise ValueError(f"No workflow found for entity type: {entity_type.value}")

        # ✅ إنشاء الطلب مع جميع الحقول الإجبارية
        request = ApprovalRequest(
            id=RequestId.generate(),  # ✅ توليد معرف
            workflow_id=workflow.id,
            entity_type=entity_type,
            entity_id=entity_id,
            requested_by=requested_by,
            requested_by_name=requested_by_name,
            title=title,
            entity_data=entity_data or {},
            # الحقول الاختيارية
            description=description,
            amount=amount,
            currency=currency,
            priority=priority,
            due_date=due_date,
            metadata=metadata or {},
            requested_at=datetime.now(timezone.utc)  # ✅ تعيين وقت الطلب
        )

        self._request_repo.save(request)
        return request

    def submit_request(self, request_id: str, submitted_by: str) -> ApprovalRequest:
        """تقديم طلب للموافقة"""
        request = self._request_repo.get_by_id(RequestId(request_id))
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        # التحقق من وجود سير عمل
        workflow = self._workflow_repo.get_by_id(request.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {request.workflow_id}")

        # التحقق من المبلغ مقابل حد الموافقة التلقائية
        if (workflow.auto_approve_threshold and 
            request.amount and 
            request.amount <= workflow.auto_approve_threshold):
            # موافقة تلقائية
            request.submit(submitted_by)
            request.approve("system", "System", "Auto-approved")
        else:
            request.submit(submitted_by)

        self._request_repo.save(request)
        return request

    def approve_request(
        self,
        request_id: str,
        approver_id: str,
        approver_name: str,
        comment: Optional[str] = None
    ) -> ApprovalRequest:
        """الموافقة على طلب"""
        request = self._request_repo.get_by_id(RequestId(request_id))
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        request.approve(approver_id, approver_name, comment)
        self._request_repo.save(request)
        return request

    def reject_request(
        self,
        request_id: str,
        approver_id: str,
        approver_name: str,
        reason: str
    ) -> ApprovalRequest:
        """رفض طلب"""
        request = self._request_repo.get_by_id(RequestId(request_id))
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        request.reject(approver_id, approver_name, reason)
        self._request_repo.save(request)
        return request

    def cancel_request(self, request_id: str, cancelled_by: str, reason: Optional[str] = None) -> ApprovalRequest:
        """إلغاء طلب"""
        request = self._request_repo.get_by_id(RequestId(request_id))
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        request.cancel(cancelled_by, reason)
        self._request_repo.save(request)
        return request

    def escalate_request(self, request_id: str, escalated_by: str, reason: Optional[str] = None) -> ApprovalRequest:
        """تصعيد طلب"""
        request = self._request_repo.get_by_id(RequestId(request_id))
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        request.escalate(escalated_by, reason)
        self._request_repo.save(request)
        return request

    def reassign_request(
        self,
        request_id: str,
        new_approver_id: str,
        new_approver_name: Optional[str] = None,
        reason: Optional[str] = None,
        reassigned_by: str = "system"
    ) -> ApprovalRequest:
        """إعادة تعيين الطلب إلى مراجع آخر"""
        request = self._request_repo.get_by_id(RequestId(request_id))
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        if not request.is_pending:
            raise ValueError(f"Cannot reassign request in status '{request.status.value}'")

        request.metadata = dict(request.metadata or {})
        request.metadata['current_approver_id'] = new_approver_id
        if new_approver_name:
            request.metadata['current_approver_name'] = new_approver_name
        request.version += 1

        request._add_history(
            action="reassign",
            performed_by=reassigned_by,
            from_status=request.status.value,
            to_status=request.status.value,
            comment=reason or f"إعادة تعيين إلى {new_approver_name or new_approver_id}"
        )

        from .events import RequestAssignedEvent
        request._events.append(RequestAssignedEvent(
            request_id=request.id,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            assigned_to=new_approver_id,
            assigned_by=reassigned_by
        ))

        self._request_repo.save(request)
        return request

    # =========================================================================
    # استعلامات
    # =========================================================================

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """الحصول على طلب"""
        return self._request_repo.get_by_id(RequestId(request_id))

    def get_request_by_entity(self, entity_type: WorkflowEntityType, entity_id: str) -> Optional[ApprovalRequest]:
        """الحصول على طلب لكيان معين"""
        return self._request_repo.get_by_entity(entity_type, entity_id)

    def get_pending_requests(self, entity_type: Optional[WorkflowEntityType] = None) -> List[ApprovalRequest]:
        """الحصول على الطلبات المعلقة"""
        return self._request_repo.list_pending(entity_type)

    def get_requests_for_approver(
        self,
        approver_id: str,
        status: Optional[RequestStatus] = None
    ) -> List[ApprovalRequest]:
        """الحصول على الطلبات التي يحتاجها مراجع معين"""
        return self._request_repo.list_by_approver(approver_id, status)

    def get_requests_by_requestor(
        self,
        requestor_id: str,
        status: Optional[RequestStatus] = None
    ) -> List[ApprovalRequest]:
        """الحصول على طلبات مقدم معين"""
        return self._request_repo.list_by_requestor(requestor_id, status)

    # =========================================================================
    # مهام الخلفية
    # =========================================================================

    def process_expired_requests(self) -> int:
        """معالجة الطلبات المنتهية صلاحيتها"""
        expired_count = 0
        pending = self._request_repo.list_pending()

        for request in pending:
            if request.due_date and request.due_date < datetime.now(timezone.utc):
                request.expire()
                self._request_repo.save(request)
                expired_count += 1

        return expired_count

    def process_timeout_escalations(self) -> int:
        """معالجة تصعيد الطلبات المتأخرة"""
        escalated_count = 0
        pending = self._request_repo.list_pending()

        for request in pending:
            workflow = self._workflow_repo.get_by_id(request.workflow_id)
            if not workflow or not workflow.current_step:
                continue

            step = workflow.current_step
            if step.timeout_hours:
                timeout_time = request.requested_at + timedelta(hours=step.timeout_hours)
                if timeout_time < datetime.now(timezone.utc):
                    request.escalate("system", f"Auto-escalated after {step.timeout_hours} hours")
                    self._request_repo.save(request)
                    escalated_count += 1

        return escalated_count