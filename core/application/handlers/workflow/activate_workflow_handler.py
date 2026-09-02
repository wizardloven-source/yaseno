# core/application/handlers/workflow/activate_workflow_handler.py
"""
Activate Workflow Handler - معالج تفعيل سير العمل
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import ActivateWorkflowCommand
from core.application.workflow.dtos import WorkflowDTO
from core.application.workflow.converters import workflow_to_dto

logger = logging.getLogger(__name__)


class ActivateWorkflowHandler(BaseHandler[ActivateWorkflowCommand, WorkflowDTO]):
    """
    معالج تفعيل سير العمل
    
    ✅ مصحح: استخدام Lazy Initialization للوصول إلى الـ Repositories
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        # ✅ Lazy Initialization
    def _get_service(self) -> WorkflowService:
        return WorkflowService(
            workflow_repo=self._uow.workflows,
            request_repo=self._uow.approval_requests
        )

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: ActivateWorkflowCommand, user_context: UserContext) -> WorkflowDTO:
        """
        تنفيذ تفعيل سير العمل
        
        Args:
            command: أمر تفعيل سير العمل
            user_context: سياق المستخدم
        
        Returns:
            WorkflowDTO: بيانات سير العمل بعد التفعيل
        """
        logger.info(f"Activating workflow: {command.workflow_id}")

        with self._uow:
            service = self._get_service()
            workflow = service.activate_workflow(
                workflow_id=command.workflow_id,
                activated_by=user_context.user_id
            )
            self._commit()

        logger.info(f"Workflow activated: {workflow.code}")

        return workflow_to_dto(workflow)