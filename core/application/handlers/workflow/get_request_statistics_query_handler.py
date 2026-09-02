# core/application/handlers/workflow/get_request_statistics_query_handler.py
"""
Get Request Statistics Query Handler - ط§ط³طھط¹ظ„ط§ظ… ظ„ط¥ط­طµط§ط¦ظٹط§طھ ط§ظ„ط·ظ„ط¨ط§طھ
"""

import logging
from typing import Dict, Any
from decimal import Decimal

from core.domain.workflow.value_objects import WorkflowEntityType, RequestStatus
from core.domain.workflow.interfaces import IApprovalRequestRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import GetRequestStatisticsQuery
from core.application.workflow.dtos import RequestStatisticsDTO
from core.application.workflow.converters import statistics_to_dto

logger = logging.getLogger(__name__)


class GetRequestStatisticsQueryHandler(BaseQueryHandler[GetRequestStatisticsQuery, RequestStatisticsDTO]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ„ط¥ط­طµط§ط¦ظٹط§طھ ط§ظ„ط·ظ„ط¨ط§طھ
    """

    def __init__(self, request_repo: IApprovalRequestRepository):
        self._request_repo = request_repo

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetRequestStatisticsQuery, user_context: UserContext = None) -> RequestStatisticsDTO:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ط¥ط­طµط§ط¦ظٹط§طھ ط§ظ„ط·ظ„ط¨ط§طھ
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ط¥ط­طµط§ط¦ظٹط§طھ ط§ظ„ط·ظ„ط¨ط§طھ
        
        Returns:
            RequestStatisticsDTO: ط¥ط­طµط§ط¦ظٹط§طھ ط§ظ„ط·ظ„ط¨ط§طھ
        """
        logger.debug(f"Fetching request statistics: type={query.entity_type}")

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

        # ط¬ظ„ط¨ ط¥ط­طµط§ط¦ظٹط§طھ ط§ظ„ط·ظ„ط¨ط§طھ
        total_count = 0
        status_counts = {}
        total_amount = Decimal('0')
        approved_amount = Decimal('0')
        rejected_amount = Decimal('0')
        by_entity_type = {}
        by_priority = {}

        # ظپظٹ ظ†ط¸ط§ظ… ط­ظ‚ظٹظ‚ظٹطŒ ط³ظٹطھظ… ط¬ظ„ط¨ ظ‡ط°ظ‡ ط§ظ„ط¨ظٹط§ظ†ط§طھ ظ…ظ† ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ
        # ظ‡ظ†ط§ ظ†ط³طھط®ط¯ظ… ط¯ظˆط§ظ„ ط§ظ„ظ…ط³طھظˆط¯ط¹ ط§ظ„ظ…طھط§ط­ط©

        # ظ…ط«ط§ظ„: ط­ط³ط§ط¨ ط¹ط¯ط¯ ط§ظ„ط·ظ„ط¨ط§طھ ط­ط³ط¨ ط§ظ„ط­ط§ظ„ط©
        for status in RequestStatus:
            count = self._request_repo.count_by_status(status)
            if count > 0:
                status_counts[status.value] = count
                total_count += count

        return statistics_to_dto(
            total_count=total_count,
            status_counts=status_counts,
            total_amount=total_amount,
            approved_amount=approved_amount,
            rejected_amount=rejected_amount,
            currency="USD",
            by_entity_type=by_entity_type,
            by_priority=by_priority
        )
