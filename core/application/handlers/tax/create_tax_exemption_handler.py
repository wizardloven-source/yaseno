# core/application/handlers/tax/create_tax_exemption_handler.py
"""
Create Tax Exemption Handler - معالج إنشاء إعفاء ضريبي
"""

import logging
from datetime import date

from core.domain.tax.entities import TaxExemption
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class CreateTaxExemptionHandler(BaseTaxHandler):
    """
    معالج إنشاء إعفاء ضريبي جديد
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ إنشاء إعفاء ضريبي جديد
        
        Args:
            command: CreateTaxExemptionCommand
            user_context: سياق المستخدم
        
        Returns:
            TaxExemption: الإعفاء الضريبي المنشأ
        """
        logger.info(f"Creating tax exemption: {command.code} - {command.name}")
        
        with self._uow:
            exemption_repo = self._uow.tax_exemptions
            
            # التحقق من عدم وجود كود مكرر
            existing = exemption_repo.get_by_code(command.code)
            if existing:
                raise ValueError(f"Tax exemption with code '{command.code}' already exists")
            
            # إنشاء الإعفاء
            exemption = TaxExemption.create(
                code=command.code,
                name=command.name,
                description=command.description,
                customer_ids=command.customer_ids,
                customer_groups=command.customer_groups,
                product_codes=command.product_codes,
                product_categories=command.product_categories,
                countries=command.countries,
                valid_from=command.valid_from or date.today(),
                valid_to=command.valid_to,
                threshold_amount=command.threshold_amount,
                threshold_currency=command.threshold_currency,
                is_automatic=command.is_automatic,
                created_by=user_context.user_id if user_context else "system"
            )
            
            # حفظ في قاعدة البيانات
            exemption_repo.save(exemption)
            self._commit()
            
            logger.info(f"Tax exemption created: {exemption.code} (ID: {exemption.id})")
            return exemption