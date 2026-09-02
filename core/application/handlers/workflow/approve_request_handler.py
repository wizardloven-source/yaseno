# core/application/handlers/workflow/approve_request_handler.py
"""
Approve Request Handler - معالج الموافقة على طلب
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import ApproveRequestCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class ApproveRequestHandler(BaseHandler[ApproveRequestCommand, ApprovalRequestDTO]):
    """
    معالج الموافقة على طلب
    
    يقوم بالموافقة على طلب الموافقة وتحديث حالته.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._service = WorkflowService(
            workflow_repo=uow.workflows,
            request_repo=uow.approval_requests
        )

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ApproveRequestCommand, user_context: UserContext) -> ApprovalRequestDTO:
        """
        تنفيذ الموافقة على الطلب
        
        Args:
            command: أمر الموافقة على الطلب
            user_context: سياق المستخدم
        
        Returns:
            ApprovalRequestDTO: بيانات الطلب بعد الموافقة
        """
        logger.info(f"Approving request: {command.request_id} by {command.approver_name}")

        with self._uow:
            service = WorkflowService(
                workflow_repo=self._uow.workflows,
                request_repo=self._uow.approval_requests
            )
            request = service.approve_request(
                request_id=command.request_id,
                approver_id=user_context.user_id,
                approver_name=user_context.username,
                comment=command.comment
            )
            self._commit()

        logger.info(f"Request approved: {request.id}")

        return request_to_dto(request)