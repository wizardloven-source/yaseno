# core/application/handlers/workflow/get_workflow_query_handler.py
"""
Get Workflow Query Handler - ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط³ظٹط± ط¹ظ…ظ„
"""

import logging

from core.domain.workflow.value_objects import WorkflowId
from core.domain.workflow.interfaces import IWorkflowRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import GetWorkflowQuery
from core.application.workflow.dtos import WorkflowDTO
from core.application.workflow.converters import workflow_to_dto

logger = logging.getLogger(__name__)


class GetWorkflowQueryHandler(BaseQueryHandler[GetWorkflowQuery, WorkflowDTO]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط³ظٹط± ط¹ظ…ظ„
    """

    def __init__(self, workflow_repo: IWorkflowRepository):
        self._workflow_repo = workflow_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetWorkflowQuery, user_context: UserContext = None) -> WorkflowDTO:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ط³ظٹط± ط§ظ„ط¹ظ…ظ„
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ط¬ظ„ط¨ ط³ظٹط± ط§ظ„ط¹ظ…ظ„
        
        Returns:
            WorkflowDTO: ط¨ظٹط§ظ†ط§طھ ط³ظٹط± ط§ظ„ط¹ظ…ظ„ ط£ظˆ None
        """
        logger.debug(f"Fetching workflow: {query.workflow_id}")

        workflow = self._workflow_repo.get_by_id(WorkflowId(query.workflow_id))

        if not workflow:
            logger.warning(f"Workflow not found: {query.workflow_id}")
            return None

        return workflow_to_dto(workflow)
