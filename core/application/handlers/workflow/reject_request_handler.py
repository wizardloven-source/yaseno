# core/application/handlers/workflow/reject_request_handler.py
"""
Reject Request Handler - معالج رفض طلب
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import RejectRequestCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class RejectRequestHandler(BaseHandler[RejectRequestCommand, ApprovalRequestDTO]):
    """
    معالج رفض طلب
    
    يقوم برفض طلب الموافقة مع ذكر السبب.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._service = WorkflowService(
            workflow_repo=uow.workflows,
            request_repo=uow.approval_requests
        )

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: RejectRequestCommand, user_context: UserContext) -> ApprovalRequestDTO:
        """
        تنفيذ رفض الطلب
        
        Args:
            command: أمر رفض الطلب
            user_context: سياق المستخدم
        
        Returns:
            ApprovalRequestDTO: بيانات الطلب بعد الرفض
        """
        logger.info(f"Rejecting request: {command.request_id} by {command.approver_name}")

        with self._uow:
            service = WorkflowService(
                workflow_repo=self._uow.workflows,
                request_repo=self._uow.approval_requests
            )
            request = service.reject_request(
                request_id=command.request_id,
                approver_id=user_context.user_id,
                approver_name=user_context.username,
                reason=command.reason
            )
            self._commit()

        logger.info(f"Request rejected: {request.id}")

        return request_to_dto(request)