# core/application/handlers/roles/delete_role_handler.py
"""Delete Role Handler - معالج حذف دور"""

import logging

from core.domain.auth.value_objects import RoleId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class DeleteRoleHandler(BaseHandler):
    """معالج حذف دور"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MANAGE_USERS)
    def handle(self, command, user_context: UserContext):
        """تنفيذ حذف دور"""
        with self._uow:
            role_repo = self._uow.roles
            
            role = role_repo.get_by_id(RoleId.from_string(command.role_id))
            if not role:
                return {
                    "success": False,
                    "message": f"Role '{command.role_id}' not found"
                }
            
            # منع حذف الأدوار الافتراضية
            if role.name in ["admin", "accountant", "auditor"]:
                return {
                    "success": False,
                    "message": f"Cannot delete system role: {role.name}"
                }
            
            # حذف الدور
            result = role_repo.delete(role.id)
            self._commit()
            
            logger.info(f"Role deleted: {role.name} by {user_context.user_id}")
            
            return {
                "success": result,
                "message": f"Role '{role.name}' deleted successfully"
            }