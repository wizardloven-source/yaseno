# core/application/handlers/workflow/get_approval_request_query_handler.py
"""
Get Approval Request Query Handler - ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط·ظ„ط¨ ظ…ظˆط§ظپظ‚ط©
"""

import logging

from core.domain.workflow.value_objects import RequestId
from core.domain.workflow.interfaces import IApprovalRequestRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import GetRequestQuery
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class GetApprovalRequestQueryHandler(BaseQueryHandler[GetRequestQuery, ApprovalRequestDTO]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ„ط¬ظ„ط¨ ط·ظ„ط¨ ظ…ظˆط§ظپظ‚ط©
    """

    def __init__(self, request_repo: IApprovalRequestRepository):
        self._request_repo = request_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetRequestQuery, user_context: UserContext = None) -> ApprovalRequestDTO:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ط·ظ„ط¨ ط§ظ„ظ…ظˆط§ظپظ‚ط©
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ط¬ظ„ط¨ ط·ظ„ط¨ ط§ظ„ظ…ظˆط§ظپظ‚ط©
        
        Returns:
            ApprovalRequestDTO: ط¨ظٹط§ظ†ط§طھ ط·ظ„ط¨ ط§ظ„ظ…ظˆط§ظپظ‚ط© ط£ظˆ None
        """
        logger.debug(f"Fetching approval request: {query.request_id}")

        request = self._request_repo.get_by_id(RequestId(query.request_id))

        if not request:
            logger.warning(f"Approval request not found: {query.request_id}")
            return None

        return request_to_dto(request)
