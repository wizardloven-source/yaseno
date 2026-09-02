# core/application/handlers/workflow/cancel_request_handler.py
"""
Cancel Request Handler - معالج إلغاء طلب
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import CancelRequestCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class CancelRequestHandler(BaseHandler[CancelRequestCommand, ApprovalRequestDTO]):
    """
    معالج إلغاء طلب
    
    يقوم بإلغاء طلب موافقة (فقط إذا كان مسودة أو معلقاً).
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._service = WorkflowService(
            workflow_repo=uow.workflows,
            request_repo=uow.approval_requests
        )

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CancelRequestCommand, user_context: UserContext) -> ApprovalRequestDTO:
        """
        تنفيذ إلغاء الطلب
        
        Args:
            command: أمر إلغاء الطلب
            user_context: سياق المستخدم
        
        Returns:
            ApprovalRequestDTO: بيانات الطلب بعد الإلغاء
        """
        logger.info(f"Cancelling request: {command.request_id}")

        with self._uow:
            service = WorkflowService(
                workflow_repo=self._uow.workflows,
                request_repo=self._uow.approval_requests
            )
            request = service.cancel_request(
                request_id=command.request_id,
                cancelled_by=user_context.user_id,
                reason=command.reason
            )
            self._commit()

        logger.info(f"Request cancelled: {request.id}")

        return request_to_dto(request)