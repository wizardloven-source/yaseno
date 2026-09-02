# core/application/handlers/tax/update_tax_rule_handler.py
"""
Update Tax Rule Handler - معالج تحديث قاعدة ضريبية
"""

import logging
from decimal import Decimal

from core.domain.tax.value_objects import TaxType, TaxCalculationType, TaxJurisdiction
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from .base_handler import BaseTaxHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class UpdateTaxRuleHandler(BaseTaxHandler):
    """
    معالج تحديث قاعدة ضريبية موجودة
    
    يستخدم Optimistic Locking عبر الـ version
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ تحديث قاعدة ضريبية
        
        Args:
            command: UpdateTaxRuleCommand
            user_context: سياق المستخدم
        
        Returns:
            TaxRule: القاعدة الضريبية المحدثة
        """
        logger.info(f"Updating tax rule: {command.rule_id}")
        
        with self._uow:
            tax_repo = self._uow.taxes
            
            # جلب القاعدة
            rule = tax_repo.get_by_id(command.rule_id)
            if not rule:
                raise ValueError(f"Tax rule '{command.rule_id}' not found")
            
            # التحقق من الإصدار (Optimistic Locking)
            if rule.version != command.version:
                raise ConcurrentModificationError(
                    "TaxRule",
                    command.rule_id,
                    command.version,
                    rule.version
                )
            
            # تحديث البيانات
            updated_by = user_context.user_id if user_context else command.updated_by
            
            rule.update(
                name=command.name,
                description=command.description,
                rate=Decimal(str(command.rate)) if command.rate is not None else None,
                calculation_type=TaxCalculationType(command.calculation_type) if command.calculation_type else None,
                valid_to=command.valid_to,
                is_active=command.is_active,
                updated_by=updated_by
            )
            
            # حفظ التغييرات
            tax_repo.save(rule)
            self._commit()
            
            logger.info(f"Tax rule updated: {rule.code} (version {rule.version})")
            return rule