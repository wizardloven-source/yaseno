# core/application/handlers/tax/get_tax_exemption_query_handler.py
"""
Get Tax Exemption Query Handler - معالج استعلام جلب إعفاء ضريبي
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetTaxExemptionQueryHandler(BaseTaxQueryHandler):
    """
    معالج استعلام لجلب إعفاء ضريبي واحد بواسطة المعرف
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ جلب إعفاء ضريبي
        
        Args:
            query: GetTaxExemptionQuery
            user_context: سياق المستخدم
        
        Returns:
            TaxExemption: الإعفاء الضريبي أو None
        """
        logger.debug(f"Fetching tax exemption: {query.exemption_id}")
        
        with self._uow:
            exemption_repo = self._uow.tax_exemptions
            exemption = exemption_repo.get_by_id(query.exemption_id)
            
            if not exemption:
                logger.warning(f"Tax exemption not found: {query.exemption_id}")
                return None
            
            return exemption