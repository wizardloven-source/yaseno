# core/application/handlers/payments/get_fund_payments_query_handler.py
"""
Get Fund Payments Query Handler - استعلام لجلب دفعات صندوق معين
"""

import logging
from typing import List

from core.domain.payments.interfaces import IPaymentRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import GetFundPaymentsQuery
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class GetFundPaymentsQueryHandler(BaseQueryHandler[GetFundPaymentsQuery, List[PaymentDTO]]):
    """
    معالج استعلام لجلب دفعات صندوق معين
    """

    def __init__(self, payment_repo: IPaymentRepository):
        self._payment_repo = payment_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetFundPaymentsQuery) -> List[PaymentDTO]:
        """
        تنفيذ جلب دفعات الصندوق
        
        Args:
            query: استعلام جلب دفعات الصندوق
        
        Returns:
            List[PaymentDTO]: قائمة دفعات الصندوق
        """
        logger.debug(f"Fetching payments for fund: {query.fund_id}")

        payments = self._payment_repo.list_by_fund(
            fund_id=query.fund_id,
            from_date=query.from_date,
            to_date=query.to_date,
            limit=query.limit,
            offset=query.offset
        )

        logger.info(f"Found {len(payments)} payments for fund {query.fund_id}")

        return [payment_to_dto(payment) for payment in payments]