# core/application/handlers/workflow/list_workflows_query_handler.py
"""
List Workflows Query Handler - ط§ط³طھط¹ظ„ط§ظ… ظ„ظ‚ط§ط¦ظ…ط© ط³ظٹط± ط§ظ„ط¹ظ…ظ„
"""

import logging
from typing import List

from core.domain.workflow.value_objects import WorkflowStatus, WorkflowEntityType
from core.domain.workflow.interfaces import IWorkflowRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import ListWorkflowsQuery
from core.application.workflow.dtos import WorkflowDTO
from core.application.workflow.converters import workflows_to_dto_list

logger = logging.getLogger(__name__)


class ListWorkflowsQueryHandler(BaseQueryHandler[ListWorkflowsQuery, List[WorkflowDTO]]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ„ظ‚ط§ط¦ظ…ط© ط³ظٹط± ط§ظ„ط¹ظ…ظ„
    """

    def __init__(self, workflow_repo: IWorkflowRepository):
        self._workflow_repo = workflow_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: ListWorkflowsQuery, user_context: UserContext = None) -> List[WorkflowDTO]:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ظ‚ط§ط¦ظ…ط© ط³ظٹط± ط§ظ„ط¹ظ…ظ„
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ظ‚ط§ط¦ظ…ط© ط³ظٹط± ط§ظ„ط¹ظ…ظ„
        
        Returns:
            List[WorkflowDTO]: ظ‚ط§ط¦ظ…ط© ط³ظٹط± ط§ظ„ط¹ظ…ظ„
        """
        logger.debug(f"Listing workflows: type={query.entity_type}, status={query.status}")

        # طھط­ظˆظٹظ„ ط§ظ„ظپظ„ط§طھط±
        entity_type = None
        if query.entity_type:
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
            entity_type = type_map.get(query.entity_type)

        status = None
        if query.status:
            status_map = {
                'draft': WorkflowStatus.DRAFT,
                'active': WorkflowStatus.ACTIVE,
                'inactive': WorkflowStatus.INACTIVE,
                'archived': WorkflowStatus.ARCHIVED
            }
            status = status_map.get(query.status)

        workflows = self._workflow_repo.list_all(
            entity_type=entity_type,
            status=status,
            limit=query.limit,
            offset=query.offset
        )

        logger.info(f"Found {len(workflows)} workflows")

        return workflows_to_dto_list(workflows)
