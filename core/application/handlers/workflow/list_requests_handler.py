# core/application/handlers/workflow/list_requests_handler.py
"""
List Requests Handler - ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ‚ط§ط¦ظ…ط© ط·ظ„ط¨ط§طھ ط§ظ„ظ…ظˆط§ظپظ‚ط©
"""

import logging
from typing import List

from core.domain.workflow.value_objects import RequestStatus, WorkflowEntityType
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import ListRequestsQuery
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import requests_to_dto_list

logger = logging.getLogger(__name__)


class ListRequestsHandler(BaseQueryHandler[ListRequestsQuery, List[ApprovalRequestDTO]]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ‚ط§ط¦ظ…ط© ط·ظ„ط¨ط§طھ ط§ظ„ظ…ظˆط§ظپظ‚ط© ظ…ط¹ ط®ظٹط§ط±ط§طھ ط§ظ„طھطµظپظٹط©
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: ListRequestsQuery, user_context: UserContext = None) -> List[ApprovalRequestDTO]:
        """
        طھظ†ظپظٹط° ط¬ظ„ط¨ ظ‚ط§ط¦ظ…ط© ط§ظ„ط·ظ„ط¨ط§طھ
        
        Args:
            query: ط§ط³طھط¹ظ„ط§ظ… ظ‚ط§ط¦ظ…ط© ط§ظ„ط·ظ„ط¨ط§طھ
        
        Returns:
            List[ApprovalRequestDTO]: ظ‚ط§ط¦ظ…ط© ط·ظ„ط¨ط§طھ ط§ظ„ظ…ظˆط§ظپظ‚ط©
        """
        logger.debug(f"Listing requests: type={query.entity_type}, status={query.status}")

        with self._uow:
            request_repo = self._uow.approval_requests

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
                    'draft': RequestStatus.DRAFT,
                    'pending': RequestStatus.PENDING,
                    'in_review': RequestStatus.IN_REVIEW,
                    'approved': RequestStatus.APPROVED,
                    'rejected': RequestStatus.REJECTED,
                    'cancelled': RequestStatus.CANCELLED,
                    'expired': RequestStatus.EXPIRED
                }
                status = status_map.get(query.status)

            # ط¥ط°ط§ طھظ… طھط­ط¯ظٹط¯ ظ…ط±ط§ط¬ط¹طŒ ط§ط³طھط®ط¯ظ… ط§ظ„ظ‚ط§ط¦ظ…ط© ط­ط³ط¨ ط§ظ„ظ…ط±ط§ط¬ط¹
            if query.approver_id:
                requests = request_repo.list_by_approver(
                    approver_id=query.approver_id,
                    status=status,
                    limit=query.limit,
                    offset=query.offset
                )
            elif query.requestor_id:
                requests = request_repo.list_by_requestor(
                    requestor_id=query.requestor_id,
                    status=status,
                    limit=query.limit,
                    offset=query.offset
                )
            elif entity_type:
                requests = request_repo.list_by_entity_type(
                    entity_type=entity_type,
                    status=status,
                    limit=query.limit,
                    offset=query.offset
                )
            elif query.from_date and query.to_date:
                requests = request_repo.list_by_date_range(
                    from_date=query.from_date,
                    to_date=query.to_date,
                    status=status,
                    limit=query.limit,
                    offset=query.offset
                )
            else:
                # ط§ظ„ط­طµظˆظ„ ط¹ظ„ظ‰ ط¬ظ…ظٹط¹ ط§ظ„ط·ظ„ط¨ط§طھ
                requests = request_repo.list_by_entity_type(
                    entity_type=WorkflowEntityType.CUSTOM,
                    status=status,
                    limit=query.limit,
                    offset=query.offset
                )

            logger.info(f"Found {len(requests)} requests")

            return requests_to_dto_list(requests)
