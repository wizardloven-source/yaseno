# core/application/handlers/tax/update_tax_exemption_handler.py
"""
Update Tax Exemption Handler - معالج تحديث إعفاء ضريبي
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from .base_handler import BaseTaxHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class UpdateTaxExemptionHandler(BaseTaxHandler):
    """
    معالج تحديث إعفاء ضريبي موجود
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ تحديث إعفاء ضريبي
        
        Args:
            command: UpdateTaxExemptionCommand
            user_context: سياق المستخدم
        
        Returns:
            TaxExemption: الإعفاء الضريبي المحدث
        """
        logger.info(f"Updating tax exemption: {command.exemption_id}")
        
        with self._uow:
            exemption_repo = self._uow.tax_exemptions
            
            # جلب الإعفاء
            exemption = exemption_repo.get_by_id(command.exemption_id)
            if not exemption:
                raise ValueError(f"Tax exemption '{command.exemption_id}' not found")
            
            # التحقق من الإصدار
            if exemption.version != command.version:
                raise ConcurrentModificationError(
                    "TaxExemption",
                    command.exemption_id,
                    command.version,
                    exemption.version
                )
            
            updated_by = user_context.user_id if user_context else command.updated_by
            
            # تحديث البيانات
            if command.name:
                exemption.name = command.name
            if command.description is not None:
                exemption.description = command.description
            if command.customer_ids is not None:
                exemption.customer_ids = command.customer_ids
            if command.customer_groups is not None:
                exemption.customer_groups = command.customer_groups
            if command.product_codes is not None:
                exemption.product_codes = command.product_codes
            if command.product_categories is not None:
                exemption.product_categories = command.product_categories
            if command.countries is not None:
                exemption.countries = command.countries
            if command.valid_to is not None:
                exemption.valid_to = command.valid_to
            if command.threshold_amount is not None:
                exemption.threshold_amount = command.threshold_amount
            if command.is_active is not None:
                exemption.is_active = command.is_active
            
            exemption.updated_by = updated_by
            exemption.version += 1
            
            # حفظ التغييرات
            exemption_repo.save(exemption)
            self._commit()
            
            logger.info(f"Tax exemption updated: {exemption.code} (version {exemption.version})")
            return exemption