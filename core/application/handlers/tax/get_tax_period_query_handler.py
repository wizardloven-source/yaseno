# core/application/handlers/tax/get_tax_period_query_handler.py
"""
Get Tax Period Query Handler - معالج استعلام جلب فترة ضريبية
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetTaxPeriodQueryHandler(BaseTaxQueryHandler):
    """
    معالج استعلام لجلب فترة ضريبية واحدة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ جلب فترة ضريبية
        
        Args:
            query: GetTaxPeriodQuery
            user_context: سياق المستخدم
        
        Returns:
            TaxPeriod: الفترة الضريبية أو None
        """
        logger.debug(f"Fetching tax period: {query.period_id}")
        
        with self._uow:
            period_repo = self._uow.tax_periods
            period = period_repo.get_by_id(query.period_id)
            
            if not period:
                logger.warning(f"Tax period not found: {query.period_id}")
                return None
            
            return period