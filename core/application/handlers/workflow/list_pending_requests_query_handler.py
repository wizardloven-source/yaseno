# core/application/handlers/workflow/list_pending_requests_query_handler.py
"""
List Pending Requests Query Handler - ط§ط³طھط¹ظ„ط§ظ… ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ط¹ظ„ظ‚ط©
"""

import logging
from typing import List

from core.domain.workflow.value_objects import WorkflowEntityType
from core.domain.workflow.interfaces import IApprovalRequestRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import ListPendingRequestsQuery
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import requests_to_dto_list

logger = logging.getLogger(__name__)


class ListPendingRequestsQueryHandler(BaseQueryHandler[ListPendingRequestsQuery, List[ApprovalRequestDTO]]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ„ظ‚ط§ط¦ظ…ط© ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ط¹ظ„ظ‚ط©
    """

    def __init__(self, request_repo: IApprovalRequestRepository):
        self._request_repo = request_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: ListPendingRequestsQuery, user_context: UserContext = None) -> List[ApprovalRequestDTO]:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ظ‚ط§ط¦ظ…ط© ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ط¹ظ„ظ‚ط©
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ظ‚ط§ط¦ظ…ط© ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ط¹ظ„ظ‚ط©
        
        Returns:
            List[ApprovalRequestDTO]: ظ‚ط§ط¦ظ…ط© ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ط¹ظ„ظ‚ط©
        """
        logger.debug(f"Listing pending requests: type={query.entity_type}")

        # طھط­ظˆظٹظ„ ظ†ظˆط¹ ط§ظ„ظƒظٹط§ظ†
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

        # ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ط¹ظ„ظ‚ط©
        if query.approver_id:
            requests = self._request_repo.list_by_approver(
                approver_id=query.approver_id,
                status=None,
                limit=query.limit,
                offset=query.offset
            )
            # طھطµظپظٹط© ط§ظ„ظ…ط¹ظ„ظ‚ط© ظپظ‚ط·
            requests = [r for r in requests if r.is_pending]
        else:
            requests = self._request_repo.list_pending(
                entity_type=entity_type,
                limit=query.limit,
                offset=query.offset
            )

        logger.info(f"Found {len(requests)} pending requests")

        return requests_to_dto_list(requests)
