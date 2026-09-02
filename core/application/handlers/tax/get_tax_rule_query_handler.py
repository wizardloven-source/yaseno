# core/application/handlers/tax/get_tax_rule_query_handler.py
"""
Get Tax Rule Query Handler - معالج استعلام جلب قاعدة ضريبية
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetTaxRuleQueryHandler(BaseTaxQueryHandler):
    """
    معالج استعلام لجلب قاعدة ضريبية واحدة بواسطة المعرف
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ جلب قاعدة ضريبية
        
        Args:
            query: GetTaxRuleQuery
            user_context: سياق المستخدم
        
        Returns:
            TaxRule: القاعدة الضريبية أو None
        """
        logger.debug(f"Fetching tax rule: {query.rule_id}")
        
        with self._uow:
            tax_repo = self._uow.taxes
            rule = tax_repo.get_by_id(query.rule_id)
            
            if not rule:
                logger.warning(f"Tax rule not found: {query.rule_id}")
                return None
            
            return rule