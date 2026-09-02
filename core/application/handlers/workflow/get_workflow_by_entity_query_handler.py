# core/application/handlers/workflow/get_workflow_by_entity_query_handler.py
"""
Get Workflow By Entity Query Handler - ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط³ظٹط± ط¹ظ…ظ„ ظ„ظ†ظˆط¹ ظƒظٹط§ظ†
"""

import logging

from core.domain.workflow.value_objects import WorkflowEntityType
from core.domain.workflow.interfaces import IWorkflowRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import GetWorkflowByEntityQuery
from core.application.workflow.dtos import WorkflowDTO
from core.application.workflow.converters import workflow_to_dto

logger = logging.getLogger(__name__)


class GetWorkflowByEntityQueryHandler(BaseQueryHandler[GetWorkflowByEntityQuery, WorkflowDTO]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط³ظٹط± ط¹ظ…ظ„ ظ„ظ†ظˆط¹ ظƒظٹط§ظ†
    """

    def __init__(self, workflow_repo: IWorkflowRepository):
        self._workflow_repo = workflow_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetWorkflowByEntityQuery, user_context: UserContext = None) -> WorkflowDTO:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ط³ظٹط± ط§ظ„ط¹ظ…ظ„ ظ„ظ†ظˆط¹ ط§ظ„ظƒظٹط§ظ†
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ط¬ظ„ط¨ ط³ظٹط± ط§ظ„ط¹ظ…ظ„ ظ„ظ†ظˆط¹ ط§ظ„ظƒظٹط§ظ†
        
        Returns:
            WorkflowDTO: ط¨ظٹط§ظ†ط§طھ ط³ظٹط± ط§ظ„ط¹ظ…ظ„ ط£ظˆ None
        """
        logger.debug(f"Fetching workflow for entity type: {query.entity_type}")

        # طھط­ظˆظٹظ„ ظ†ظˆط¹ ط§ظ„ظƒظٹط§ظ†
        type_map = {
            'invoice': WorkflowEntityType.INVOICE,
            'payment': WorkflowEntityType.PAYMENT,
            'journal_entry': WorkflowEntityType.JOURNAL_ENTRY,
            'purchase_order': WorkflowEntityType.PURCHASE_ORDER,
            'sales_order': WorkflowEntityType.SALES_ORDER,
            'expense': WorkflowEntityType.EXPENSE,
            'budget': WorkflowEntityType.BUDGET,
            'contract': WorkflowEntityType.CONTRACT,
            'user': WorkflowEntityType.USER,
            'custom': WorkflowEntityType.CUSTOM
        }
        entity_type = type_map.get(query.entity_type, WorkflowEntityType.CUSTOM)

        workflow = self._workflow_repo.get_by_entity_type(entity_type)

        if not workflow:
            logger.warning(f"No workflow found for entity type: {query.entity_type}")
            return None

        return workflow_to_dto(workflow)
