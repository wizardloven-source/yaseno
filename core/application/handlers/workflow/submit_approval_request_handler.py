# core/application/handlers/workflow/submit_approval_request_handler.py
"""
Submit Approval Request Handler - معالج تقديم طلب للموافقة
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import SubmitRequestCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class SubmitApprovalRequestHandler(BaseHandler[SubmitRequestCommand, ApprovalRequestDTO]):
    """
    معالج تقديم طلب للموافقة
    
    ✅ مصحح: استخدام Lazy Initialization
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    def _get_service(self) -> WorkflowService:
        return WorkflowService(
            workflow_repo=self._uow.workflows,
            request_repo=self._uow.approval_requests
        )

    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: SubmitRequestCommand, user_context: UserContext) -> ApprovalRequestDTO:
        """
        تنفيذ تقديم الطلب
        
        Args:
            command: أمر تقديم الطلب
            user_context: سياق المستخدم
        
        Returns:
            ApprovalRequestDTO: بيانات الطلب بعد التقديم
        """
        logger.info(f"Submitting request: {command.request_id}")

        with self._uow:
            service = self._get_service()
            request = service.submit_request(
                request_id=command.request_id,
                submitted_by=user_context.user_id
            )
            self._commit()

        logger.info(f"Request submitted: {request.id} (Status: {request.status.value})")

        return request_to_dto(request)