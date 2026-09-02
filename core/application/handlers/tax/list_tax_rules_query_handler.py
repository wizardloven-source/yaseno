# core/application/handlers/tax/list_tax_rules_query_handler.py
"""
List Tax Rules Query Handler - معالج استعلام قائمة القواعد الضريبية
"""

import logging
from typing import List

from core.domain.tax.value_objects import TaxType, TaxJurisdiction
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class ListTaxRulesQueryHandler(BaseTaxQueryHandler):
    """
    معالج استعلام لجلب قائمة القواعد الضريبية مع خيارات التصفية
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None) -> List:
        """
        تنفيذ جلب قائمة القواعد الضريبية
        
        Args:
            query: ListTaxRulesQuery
            user_context: سياق المستخدم
        
        Returns:
            List[TaxRule]: قائمة القواعد الضريبية
        """
        logger.debug(f"Listing tax rules: type={query.tax_type}, jurisdiction={query.jurisdiction}")
        
        with self._uow:
            tax_repo = self._uow.taxes
            
            # تطبيق الفلاتر
            if query.tax_type:
                tax_type = TaxType(query.tax_type)
                rules = tax_repo.get_by_tax_type(tax_type)
            elif query.jurisdiction:
                jurisdiction = TaxJurisdiction(query.jurisdiction)
                rules = tax_repo.get_by_jurisdiction(jurisdiction)
            else:
                rules = tax_repo.get_all(include_inactive=query.include_inactive)
            
            # Pagination
            start = query.offset
            end = query.offset + query.limit
            paginated_rules = rules[start:end]
            
            logger.info(f"Found {len(paginated_rules)} tax rules (total: {len(rules)})")
            return paginated_rules