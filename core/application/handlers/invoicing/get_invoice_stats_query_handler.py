"""
Get Invoice Stats Query Handler - استعلام لإحصائيات الفواتير
"""

import logging
from typing import Optional
from datetime import date

from core.domain.invoicing.interfaces import IInvoiceRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.invoicing.commands import GetInvoiceStatsQuery
from core.application.invoicing.dtos import InvoiceStatisticsDTO

logger = logging.getLogger(__name__)


class GetInvoiceStatsQueryHandler(BaseQueryHandler[GetInvoiceStatsQuery, InvoiceStatisticsDTO]):
    """معالج استعلام لإحصائيات الفواتير"""
    
    def __init__(self, invoice_repo: IInvoiceRepository):
        self._invoice_repo = invoice_repo
    
    def handle(self, query: GetInvoiceStatsQuery) -> InvoiceStatisticsDTO:
        """تنفيذ استعلام إحصائيات الفواتير"""
        stats = self._invoice_repo.get_statistics(
            from_date=query.from_date.date() if query.from_date else None,
            to_date=query.to_date.date() if query.to_date else None
        )
        
        return InvoiceStatisticsDTO(
            total_count=stats.total_count,
            total_amount=stats.total_amount,
            total_tax=stats.total_tax,
            total_with_tax=stats.total_with_tax,
            draft_count=stats.draft_count,
            posted_count=stats.posted_count,
            cancelled_count=stats.cancelled_count,
            currency=stats.currency if hasattr(stats, 'currency') else "USD",
            by_currency=stats.by_currency,
            by_payment_type=stats.by_payment_type,
            average_amount=stats.average_amount,
            min_amount=stats.min_amount,
            max_amount=stats.max_amount
        )