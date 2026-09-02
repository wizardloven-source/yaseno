# core/application/handlers/workflow/reassign_request_handler.py
"""
Reassign Request Handler - معالج إعادة تعيين طلب إلى مراجع آخر
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import ReassignRequestCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class ReassignRequestHandler(BaseHandler[ReassignRequestCommand, ApprovalRequestDTO]):
    """
    معالج إعادة تعيين طلب إلى مراجع آخر
    
    ✅ مصحح: استخدام Lazy Initialization
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    def _get_service(self) -> WorkflowService:
        return WorkflowService(
            workflow_repo=self._uow.workflows,
            request_repo=self._uow.approval_requests
        )

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ReassignRequestCommand, user_context: UserContext) -> ApprovalRequestDTO:
        """
        تنفيذ إعادة تعيين الطلب
        
        Args:
            command: أمر إعادة تعيين الطلب
            user_context: سياق المستخدم
        
        Returns:
            ApprovalRequestDTO: بيانات الطلب بعد إعادة التعيين
        """
        logger.info(f"Reassigning request: {command.request_id} to {command.new_approver_id}")

        with self._uow:
            service = self._get_service()
            # إعادة تعيين الطلب (يجب إضافة هذه الدالة في WorkflowService)
            request = service.reassign_request(
                request_id=command.request_id,
                new_approver_id=command.new_approver_id,
                reassigned_by=user_context.user_id,
                reason=command.reason
            )
            self._commit()

        logger.info(f"Request reassigned: {request.id} to {command.new_approver_id}")

        return request_to_dto(request)