# core/application/handlers/payments/get_payment_query_handler.py
"""
Get Payment Query Handler - معالج استعلام لجلب دفعة واحدة
"""

import logging

from core.domain.payments.value_objects import PaymentId
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentQueryHandler
from core.application.payments.commands import GetPaymentQuery
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class GetPaymentQueryHandler(BasePaymentQueryHandler[GetPaymentQuery, PaymentDTO]):
    """
    معالج استعلام لجلب دفعة واحدة بواسطة المعرف
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetPaymentQuery) -> PaymentDTO:
        with self._uow:
            repo = self._uow.payments
            
            payment = repo.get_by_id(PaymentId.from_string(query.payment_id))
            if not payment:
                return None
            
            logger.debug(f"Retrieved payment: {payment.code}")
            return payment_to_dto(payment)