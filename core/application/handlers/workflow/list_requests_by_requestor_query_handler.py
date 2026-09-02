# core/application/handlers/workflow/list_requests_by_requestor_query_handler.py
"""
List Requests By Requestor Query Handler - ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ظ‚ط¯ظ…ط© ظ…ظ† ظ…ظ‚ط¯ظ… ظ…ط¹ظٹظ†
"""

import logging
from typing import List

from core.domain.workflow.value_objects import RequestStatus
from core.domain.workflow.interfaces import IApprovalRequestRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import GetRequestsByRequestorQuery
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import requests_to_dto_list

logger = logging.getLogger(__name__)


class ListRequestsByRequestorQueryHandler(BaseQueryHandler[GetRequestsByRequestorQuery, List[ApprovalRequestDTO]]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ظ‚ط¯ظ…ط© ظ…ظ† ظ…ظ‚ط¯ظ… ظ…ط¹ظٹظ†
    """

    def __init__(self, request_repo: IApprovalRequestRepository):
        self._request_repo = request_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetRequestsByRequestorQuery, user_context: UserContext = None) -> List[ApprovalRequestDTO]:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ظ‚ط¯ظ…ط© ظ…ظ† ط§ظ„ظ…ظ‚ط¯ظ…
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨ط§طھ ط§ظ„ظ…ظ‚ط¯ظ…ط© ظ…ظ† ط§ظ„ظ…ظ‚ط¯ظ…
        
        Returns:
            List[ApprovalRequestDTO]: ظ‚ط§ط¦ظ…ط© ط§ظ„ط·ظ„ط¨ط§طھ
        """
        logger.debug(f"Fetching requests from requestor: {query.requestor_id}")

        # طھط­ظˆظٹظ„ ط§ظ„ط­ط§ظ„ط©
        status = None
        if query.status:
            status_map = {
                'draft': RequestStatus.DRAFT,
                'pending': RequestStatus.PENDING,
                'in_review': RequestStatus.IN_REVIEW,
                'approved': RequestStatus.APPROVED,
                'rejected': RequestStatus.REJECTED,
                'cancelled': RequestStatus.CANCELLED,
                'expired': RequestStatus.EXPIRED
            }
            status = status_map.get(query.status)

        requests = self._request_repo.list_by_requestor(
            requestor_id=query.requestor_id,
            status=status,
            limit=query.limit,
            offset=query.offset
        )

        logger.info(f"Found {len(requests)} requests from requestor {query.requestor_id}")

        return requests_to_dto_list(requests)
