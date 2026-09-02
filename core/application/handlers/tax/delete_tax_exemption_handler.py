# core/application/handlers/tax/delete_tax_exemption_handler.py
"""
Delete Tax Exemption Handler - معالج حذف إعفاء ضريبي
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class DeleteTaxExemptionHandler(BaseTaxHandler):
    """
    معالج حذف إعفاء ضريبي
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ حذف إعفاء ضريبي
        
        Args:
            command: DeleteTaxExemptionCommand
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Deleting tax exemption: {command.exemption_id}")
        
        with self._uow:
            exemption_repo = self._uow.tax_exemptions
            
            # جلب الإعفاء
            exemption = exemption_repo.get_by_id(command.exemption_id)
            if not exemption:
                return {
                    "success": False,
                    "message": f"Tax exemption '{command.exemption_id}' not found",
                    "exemption_id": command.exemption_id
                }
            
            deleted_by = user_context.user_id if user_context else command.deleted_by
            
            # حذف ناعم (تعطيل فقط)
            exemption.is_active = False
            exemption.updated_by = deleted_by
            exemption.version += 1
            
            exemption_repo.save(exemption)
            self._commit()
            
            logger.info(f"Tax exemption deactivated: {exemption.code} by {deleted_by}")
            
            return {
                "success": True,
                "message": f"Tax exemption {exemption.code} deactivated successfully",
                "exemption_id": command.exemption_id
            }