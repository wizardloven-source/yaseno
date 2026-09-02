# core/application/handlers/tax/delete_tax_rule_handler.py
"""
Delete Tax Rule Handler - معالج حذف قاعدة ضريبية
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BaseTaxHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class DeleteTaxRuleHandler(BaseTaxHandler):
    """
    معالج حذف قاعدة ضريبية
    
    ملاحظات:
        1. لا يمكن حذف القاعدة الافتراضية
        2. الحذف هو Soft Delete (تعطيل فقط)
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ حذف قاعدة ضريبية
        
        Args:
            command: DeleteTaxRuleCommand
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Deleting tax rule: {command.rule_id}")
        
        with self._uow:
            tax_repo = self._uow.taxes
            
            # جلب القاعدة
            rule = tax_repo.get_by_id(command.rule_id)
            if not rule:
                return {
                    "success": False,
                    "message": f"Tax rule '{command.rule_id}' not found",
                    "rule_id": command.rule_id
                }
            
            # لا يمكن حذف القاعدة الافتراضية
            if rule.is_default:
                return {
                    "success": False,
                    "message": f"Cannot delete default tax rule: {rule.code}",
                    "rule_id": command.rule_id
                }
            
            deleted_by = user_context.user_id if user_context else command.deleted_by
            
            # حذف ناعم (تعطيل فقط)
            rule.deactivate(deleted_by)
            tax_repo.save(rule)
            self._commit()
            
            logger.info(f"Tax rule deactivated: {rule.code} by {deleted_by}")
            
            return {
                "success": True,
                "message": f"Tax rule {rule.code} deactivated successfully",
                "rule_id": command.rule_id
            }