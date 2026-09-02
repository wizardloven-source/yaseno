# core/application/handlers/workflow/escalate_request_handler.py
"""
Escalate Request Handler - معالج تصعيد طلب
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import EscalateRequestCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class EscalateRequestHandler(BaseHandler[EscalateRequestCommand, ApprovalRequestDTO]):
    """
    معالج تصعيد طلب
    
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
    def handle(self, command: EscalateRequestCommand, user_context: UserContext) -> ApprovalRequestDTO:
        """
        تنفيذ تصعيد الطلب
        
        Args:
            command: أمر تصعيد الطلب
            user_context: سياق المستخدم
        
        Returns:
            ApprovalRequestDTO: بيانات الطلب بعد التصعيد
        """
        logger.info(f"Escalating request: {command.request_id}")

        with self._uow:
            service = self._get_service()
            request = service.escalate_request(
                request_id=command.request_id,
                escalated_by=user_context.user_id,
                reason=command.reason
            )
            self._commit()

        logger.info(f"Request escalated: {request.id}")

        return request_to_dto(request)