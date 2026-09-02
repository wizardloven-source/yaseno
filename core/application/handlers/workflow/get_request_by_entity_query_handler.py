# core/application/handlers/workflow/get_request_by_entity_query_handler.py
"""
Get Request By Entity Query Handler - ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط·ظ„ط¨ ظ„ظƒظٹط§ظ†
"""

import logging

from core.domain.workflow.value_objects import WorkflowEntityType
from core.domain.workflow.interfaces import IApprovalRequestRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import GetRequestByEntityQuery
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class GetRequestByEntityQueryHandler(BaseQueryHandler[GetRequestByEntityQuery, ApprovalRequestDTO]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط·ظ„ط¨ ظ„ظƒظٹط§ظ†
    """

    def __init__(self, request_repo: IApprovalRequestRepository):
        self._request_repo = request_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetRequestByEntityQuery, user_context: UserContext = None) -> ApprovalRequestDTO:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨ ظ„ظ„ظƒظٹط§ظ†
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨ ظ„ظ„ظƒظٹط§ظ†
        
        Returns:
            ApprovalRequestDTO: ط¨ظٹط§ظ†ط§طھ ط·ظ„ط¨ ط§ظ„ظ…ظˆط§ظپظ‚ط© ط£ظˆ None
        """
        logger.debug(f"Fetching request for entity: {query.entity_type}:{query.entity_id}")

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

        request = self._request_repo.get_by_entity(
            entity_type=entity_type,
            entity_id=query.entity_id
        )

        if not request:
            logger.warning(f"No request found for entity: {query.entity_type}:{query.entity_id}")
            return None

        return request_to_dto(request)
