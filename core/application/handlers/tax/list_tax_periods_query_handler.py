# core/application/handlers/tax/list_tax_periods_query_handler.py
"""
List Tax Periods Query Handler - معالج استعلام قائمة الفترات الضريبية
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class ListTaxPeriodsQueryHandler(BaseTaxQueryHandler):
    """
    معالج استعلام لجلب قائمة الفترات الضريبية
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None) -> List:
        """
        تنفيذ جلب قائمة الفترات الضريبية
        
        Args:
            query: ListTaxPeriodsQuery
            user_context: سياق المستخدم
        
        Returns:
            List[TaxPeriod]: قائمة الفترات الضريبية
        """
        logger.debug(f"Listing tax periods: year={query.year}, status={query.status}")
        
        with self._uow:
            period_repo = self._uow.tax_periods
            
            if query.year:
                periods = period_repo.get_by_year(query.year)
            elif query.status == "open":
                periods = period_repo.get_open_periods()
            elif query.status == "closed":
                periods = period_repo.get_closed_periods()
            else:
                periods = period_repo.get_by_year(2024)  # افتراضي
        
            # Pagination
            start = query.offset
            end = query.offset + query.limit
            paginated_periods = periods[start:end]
            
            logger.info(f"Found {len(paginated_periods)} tax periods (total: {len(periods)})")
            return paginated_periods