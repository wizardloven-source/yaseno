# core/application/handlers/workflow/delete_workflow_handler.py
"""
Delete Workflow Handler - معالج حذف سير العمل
"""

import logging

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import DeleteWorkflowCommand

logger = logging.getLogger(__name__)


class DeleteWorkflowHandler(BaseHandler[DeleteWorkflowCommand, dict]):
    """
    معالج حذف سير العمل
    
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
    def handle(self, command: DeleteWorkflowCommand, user_context: UserContext) -> dict:
        """
        تنفيذ حذف سير العمل
        
        Args:
            command: أمر حذف سير العمل
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Deleting workflow: {command.workflow_id}")

        with self._uow:
            service = self._get_service()
            
            # التحقق من وجود سير العمل
            workflow = self._uow.workflows.get_by_id(command.workflow_id)
            if not workflow:
                return {
                    "success": False,
                    "message": f"Workflow {command.workflow_id} not found",
                    "workflow_id": command.workflow_id
                }
            
            # حذف سير العمل
            result = self._uow.workflows.delete(workflow.id)
            self._commit()

        if result:
            logger.info(f"Workflow deleted: {command.workflow_id}")
            return {
                "success": True,
                "message": f"Workflow {command.workflow_id} deleted successfully",
                "workflow_id": command.workflow_id
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete workflow {command.workflow_id}",
                "workflow_id": command.workflow_id
            }