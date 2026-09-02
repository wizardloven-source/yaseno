# core/application/handlers/payments/get_customer_payments_query_handler.py
"""
Get Customer Payments Query Handler - استعلام لجلب دفعات العميل
"""

import logging
from typing import List

from core.domain.payments.interfaces import IPaymentRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import GetCustomerPaymentsQuery
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class GetCustomerPaymentsQueryHandler(BaseQueryHandler[GetCustomerPaymentsQuery, List[PaymentDTO]]):
    """
    معالج استعلام لجلب دفعات العميل
    
    يقوم بجلب جميع دفعات عميل معين مع خيارات التصفية والترقيم.
    """
    
    def __init__(self, payment_repo: IPaymentRepository):
        self._payment_repo = payment_repo
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetCustomerPaymentsQuery) -> List[PaymentDTO]:
        """
        تنفيذ جلب دفعات العميل
        
        Args:
            query: استعلام جلب دفعات العميل
        
        Returns:
            List[PaymentDTO]: قائمة دفعات العميل
        """
        logger.debug(f"Fetching payments for customer: {query.customer_id}")
        
        # جلب دفعات العميل
        payments = self._payment_repo.list_by_customer(
            customer_id=query.customer_id,
            limit=query.limit,
            offset=query.offset
        )
        
        logger.info(f"Found {len(payments)} payments for customer {query.customer_id}")
        
        return [payment_to_dto(payment) for payment in payments]