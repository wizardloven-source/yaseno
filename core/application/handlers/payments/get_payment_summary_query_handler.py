# core/application/handlers/payments/get_payment_summary_query_handler.py
"""
Get Payment Summary Query Handler - معالج استعلام لجلب ملخص الدفعات
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentQueryHandler
from core.application.payments.commands import GetPaymentSummaryQuery
from core.application.payments.dtos import PaymentSummaryDTO
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class GetPaymentSummaryQueryHandler(BasePaymentQueryHandler[GetPaymentSummaryQuery, PaymentSummaryDTO]):
    """
    معالج استعلام لجلب ملخص الدفعات
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetPaymentSummaryQuery) -> PaymentSummaryDTO:
        with self._uow:
            repo = self._uow.payments
            
            summary_data = repo.get_summary(
                from_date=query.from_date,
                to_date=query.to_date
            )
            
            return PaymentSummaryDTO(
                total_received=summary_data.get('total_received', 0),
                total_paid=summary_data.get('total_paid', 0),
                net_balance=summary_data.get('net_balance', 0),
                total_count=summary_data.get('total_count', 0),
                pending_count=summary_data.get('pending_count', 0),
                completed_count=summary_data.get('completed_count', 0),
                cancelled_count=summary_data.get('cancelled_count', 0),
                currency=summary_data.get('currency', 'USD')
            )