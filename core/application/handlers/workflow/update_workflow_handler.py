# core/application/handlers/workflow/update_workflow_handler.py
"""
Update Workflow Handler - معالج تحديث سير العمل
"""

import logging
from decimal import Decimal

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import UpdateWorkflowCommand
from core.application.workflow.dtos import WorkflowDTO
from core.application.workflow.converters import workflow_to_dto

logger = logging.getLogger(__name__)


class UpdateWorkflowHandler(BaseHandler[UpdateWorkflowCommand, WorkflowDTO]):
    """
    معالج تحديث سير العمل
    
    ✅ مصحح: استخدام Lazy Initialization للوصول إلى الـ Repositories
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    def _get_service(self) -> WorkflowService:
        return WorkflowService(
            workflow_repo=self._uow.workflows,
            request_repo=self._uow.approval_requests
        )

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: UpdateWorkflowCommand, user_context: UserContext) -> WorkflowDTO:
        """
        تنفيذ تحديث سير العمل
        
        Args:
            command: أمر تحديث سير العمل
            user_context: سياق المستخدم
        
        Returns:
            WorkflowDTO: بيانات سير العمل المحدث
        """
        logger.info(f"Updating workflow: {command.workflow_id}")

        with self._uow:
            service = self._get_service()
            workflow = service.update_workflow(
                workflow_id=command.workflow_id,
                name=command.name,
                description=command.description,
                is_mandatory=command.is_mandatory,
                auto_approve_threshold=command.auto_approve_threshold,
                auto_approve_after_days=command.auto_approve_after_days,
                updated_by=user_context.user_id
            )
            self._commit()

        logger.info(f"Workflow updated: {workflow.code} (ID: {workflow.id})")

        return workflow_to_dto(workflow)