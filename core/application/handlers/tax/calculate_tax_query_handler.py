# core/application/handlers/tax/calculate_tax_query_handler.py
"""
Calculate Tax Query Handler - معالج استعلام حساب الضريبة
"""

import logging
from decimal import Decimal

from core.domain.tax.services import TaxEngine
from core.domain.tax.value_objects import TaxContext

from .base_handler import BaseTaxQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class CalculateTaxQueryHandler(BaseTaxQueryHandler):
    """
    معالج استعلام حساب الضريبة
    
    يقوم بحساب الضريبة لمبلغ معين في سياق محدد
    """
    
    def __init__(self, tax_engine: TaxEngine):
        self._tax_engine = tax_engine
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ حساب الضريبة
        
        Args:
            query: CalculateTaxQuery
            user_context: سياق المستخدم
        
        Returns:
            TaxCalculationResult: نتيجة حساب الضريبة
        """
        logger.debug(f"Calculating tax: amount={query.amount}, currency={query.currency}")
        
        # إنشاء سياق الضريبة
        context = TaxContext(
            product_code=query.product_code,
            product_category=query.product_category,
            customer_id=query.customer_id,
            customer_group=query.customer_group,
            customer_tax_number=query.customer_tax_number,
            customer_country=query.customer_country,
            invoice_id=query.invoice_id,
            invoice_date=query.invoice_date,
            currency=query.currency,
            site_id=query.site_id,
            site_country=query.site_country,
            site_region=query.site_region,
            amount=Decimal(str(query.amount)),
            is_tax_inclusive=query.is_tax_inclusive,
            metadata=query.metadata or {}
        )
        
        # حساب الضريبة
        result = self._tax_engine.calculate_tax(
            amount=Decimal(str(query.amount)),
            context=context
        )
        
        logger.info(f"Tax calculated: {result.tax_amount} {result.currency}")
        return result