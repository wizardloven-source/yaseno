# core/application/handlers/tax/create_tax_rule_handler.py
"""
Create Tax Rule Handler - معالج إنشاء قاعدة ضريبية جديدة
"""

import logging
from decimal import Decimal
from datetime import date

from core.domain.tax.entities import TaxRule
from core.domain.tax.value_objects import (
    TaxId, TaxCode, TaxRate, TaxType, TaxCalculationType, TaxJurisdiction
)
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class CreateTaxRuleHandler(BaseTaxHandler):
    """
    معالج إنشاء قاعدة ضريبية جديدة
    
    مسؤولياته:
        1. التحقق من عدم وجود كود مكرر
        2. إنشاء كيان القاعدة الضريبية
        3. الحفظ عبر Repository
        4. إرجاع القاعدة الجديدة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ إنشاء قاعدة ضريبية جديدة
        
        Args:
            command: CreateTaxRuleCommand
            user_context: سياق المستخدم
        
        Returns:
            TaxRule: القاعدة الضريبية المنشأة
        """
        logger.info(f"Creating tax rule: {command.code} - {command.name}")
        
        with self._uow:
            tax_repo = self._uow.taxes
            
            # التحقق من عدم وجود كود مكرر
            existing = tax_repo.get_by_code(command.code)
            if existing:
                raise ValueError(f"Tax rule with code '{command.code}' already exists")
            
            # إنشاء القاعدة
            rule = TaxRule.create(
                code=command.code,
                name=command.name,
                rate=Decimal(str(command.rate)),
                tax_type=TaxType(command.tax_type),
                calculation_type=TaxCalculationType(command.calculation_type),
                jurisdiction=TaxJurisdiction(command.jurisdiction),
                description=command.description,
                is_default=command.is_default,
                is_mandatory=command.is_mandatory,
                valid_from=command.valid_from or date.today(),
                valid_to=command.valid_to,
                created_by=user_context.user_id if user_context else "system"
            )
            
            # حفظ في قاعدة البيانات
            tax_repo.save(rule)
            self._commit()
            
            logger.info(f"Tax rule created: {rule.code} (ID: {rule.id})")
            return rule