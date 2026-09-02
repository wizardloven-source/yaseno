# core/application/handlers/tax/list_tax_exemptions_query_handler.py
"""
List Tax Exemptions Query Handler - معالج استعلام قائمة الإعفاءات الضريبية
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class ListTaxExemptionsQueryHandler(BaseTaxQueryHandler):
    """
    معالج استعلام لجلب قائمة الإعفاءات الضريبية
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None) -> List:
        """
        تنفيذ جلب قائمة الإعفاءات الضريبية
        
        Args:
            query: ListTaxExemptionsQuery
            user_context: سياق المستخدم
        
        Returns:
            List[TaxExemption]: قائمة الإعفاءات الضريبية
        """
        logger.debug(f"Listing tax exemptions: active_only={query.active_only}")
        
        with self._uow:
            exemption_repo = self._uow.tax_exemptions
            
            if query.active_only:
                exemptions = exemption_repo.get_active_exemptions()
            else:
                exemptions = exemption_repo.get_all(include_inactive=query.include_inactive)
            
            # Pagination
            start = query.offset
            end = query.offset + query.limit
            paginated_exemptions = exemptions[start:end]
            
            logger.info(f"Found {len(paginated_exemptions)} tax exemptions (total: {len(exemptions)})")
            return paginated_exemptions