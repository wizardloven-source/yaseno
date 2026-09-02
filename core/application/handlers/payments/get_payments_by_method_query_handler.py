# core/application/handlers/payments/get_payments_by_method_query_handler.py
"""
Get Payments By Method Query Handler - استعلام لجلب دفعات حسب طريقة الدفع
"""

import logging
from typing import List

from core.domain.payments.value_objects import PaymentMethod
from core.domain.payments.interfaces import IPaymentRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import GetPaymentsByMethodQuery
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class GetPaymentsByMethodQueryHandler(BaseQueryHandler[GetPaymentsByMethodQuery, List[PaymentDTO]]):
    """
    معالج استعلام لجلب دفعات حسب طريقة الدفع
    """

    def __init__(self, payment_repo: IPaymentRepository):
        self._payment_repo = payment_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetPaymentsByMethodQuery) -> List[PaymentDTO]:
        """
        تنفيذ جلب دفعات حسب طريقة الدفع
        
        Args:
            query: استعلام جلب دفعات حسب طريقة الدفع
        
        Returns:
            List[PaymentDTO]: قائمة الدفعات
        """
        logger.debug(f"Fetching payments by method: {query.payment_method}")

        try:
            method = PaymentMethod(query.payment_method)
        except ValueError:
            logger.warning(f"Invalid payment method: {query.payment_method}")
            return []

        payments = self._payment_repo.list_by_method(
            method=method,
            limit=query.limit,
            offset=query.offset
        )

        # تصفية حسب التاريخ
        if query.from_date:
            payments = [p for p in payments if p.date.date() >= query.from_date]
        if query.to_date:
            payments = [p for p in payments if p.date.date() <= query.to_date]

        logger.info(f"Found {len(payments)} payments with method {query.payment_method}")

        return [payment_to_dto(payment) for payment in payments]