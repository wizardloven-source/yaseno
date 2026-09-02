# core/application/handlers/workflow/deactivate_workflow_handler.py
"""
Deactivate Workflow Handler - معالج تعطيل سير العمل
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import DeactivateWorkflowCommand
from core.application.workflow.dtos import WorkflowDTO
from core.application.workflow.converters import workflow_to_dto

logger = logging.getLogger(__name__)


class DeactivateWorkflowHandler(BaseHandler[DeactivateWorkflowCommand, WorkflowDTO]):
    """
    معالج تعطيل سير العمل
    
    ✅ مصحح: استخدام Lazy Initialization
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    def _get_service(self) -> WorkflowService:
        return WorkflowService(
            workflow_repo=self._uow.workflows,
            request_repo=self._uow.approval_requests
        )

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: DeactivateWorkflowCommand, user_context: UserContext) -> WorkflowDTO:
        """
        تنفيذ تعطيل سير العمل
        
        Args:
            command: أمر تعطيل سير العمل
            user_context: سياق المستخدم
        
        Returns:
            WorkflowDTO: بيانات سير العمل بعد التعطيل
        """
        logger.info(f"Deactivating workflow: {command.workflow_id}")

        with self._uow:
            service = self._get_service()
            workflow = service.deactivate_workflow(
                workflow_id=command.workflow_id,
                deactivated_by=user_context.user_id
            )
            self._commit()

        logger.info(f"Workflow deactivated: {workflow.code}")

        return workflow_to_dto(workflow)