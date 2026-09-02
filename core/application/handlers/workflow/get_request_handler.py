# core/application/handlers/workflow/get_request_handler.py
"""
Get Request Handler - ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ط¬ظ„ط¨ ط·ظ„ط¨
"""

import logging

from core.domain.workflow.value_objects import RequestId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import GetRequestQuery
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class GetRequestHandler(BaseQueryHandler[GetRequestQuery, ApprovalRequestDTO]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ط¬ظ„ط¨ ط·ظ„ط¨ ظ…ظˆط§ظپظ‚ط©
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetRequestQuery, user_context: UserContext = None) -> ApprovalRequestDTO:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ط¬ظ„ط¨ ط§ظ„ط·ظ„ط¨
        
        Returns:
            ApprovalRequestDTO: ط¨ظٹط§ظ†ط§طھ ط§ظ„ط·ظ„ط¨ ط£ظˆ None
        """
        logger.debug(f"Fetching request: {query.request_id}")

        with self._uow:
            request_repo = self._uow.approval_requests
            request = request_repo.get_by_id(RequestId(query.request_id))

            if not request:
                logger.warning(f"Request not found: {query.request_id}")
                return None

            return request_to_dto(request)
