# core/application/handlers/payments/get_payment_statistics_query_handler.py
"""
Get Payment Statistics Query Handler - استعلام لجلب إحصائيات الدفعات
"""

import logging
from typing import Dict, Any
from decimal import Decimal

from core.domain.payments.interfaces import IPaymentRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import GetPaymentStatisticsQuery
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class GetPaymentStatisticsQueryHandler(BaseQueryHandler[GetPaymentStatisticsQuery, Dict[str, Any]]):
    """
    معالج استعلام لجلب إحصائيات الدفعات
    """

    def __init__(self, payment_repo: IPaymentRepository):
        self._payment_repo = payment_repo

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetPaymentStatisticsQuery) -> Dict[str, Any]:
        """
        تنفيذ جلب إحصائيات الدفعات
        
        Args:
            query: استعلام إحصائيات الدفعات
        
        Returns:
            Dict[str, Any]: إحصائيات الدفعات
        """
        logger.debug("Fetching payment statistics")

        summary = self._payment_repo.get_summary(
            from_date=query.from_date,
            to_date=query.to_date,
            currency=query.currency
        )

        return {
            "success": True,
            "statistics": summary,
            "currency": query.currency,
            "from_date": query.from_date.isoformat() if query.from_date else None,
            "to_date": query.to_date.isoformat() if query.to_date else None,
        }