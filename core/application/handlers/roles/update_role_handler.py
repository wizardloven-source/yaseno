# core/application/handlers/roles/update_role_handler.py
"""Update Role Handler - معالج تحديث دور"""

import logging

from core.domain.auth.value_objects import RoleId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.shared.exceptions import ConcurrentModificationError

logger = logging.getLogger(__name__)


class UpdateRoleHandler(BaseHandler):
    """معالج تحديث دور"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MANAGE_USERS)
    def handle(self, command, user_context: UserContext):
        """تنفيذ تحديث دور"""
        with self._uow:
            role_repo = self._uow.roles
            
            role = role_repo.get_by_id(RoleId.from_string(command.role_id))
            if not role:
                raise ValueError(f"Role '{command.role_id}' not found")
            
            # التحقق من الإصدار (Optimistic Locking)
            if role.version != command.version:
                raise ConcurrentModificationError(
                    "Role",
                    command.role_id,
                    command.version,
                    role.version
                )
            
            # تحديث البيانات
            if command.display_name:
                role.display_name = command.display_name
            if command.description is not None:
                role.description = command.description
            if command.is_admin is not None:
                role.is_admin = command.is_admin
            if command.is_active is not None:
                role.is_active = command.is_active
            
            # تحديث الصلاحيات إذا تم تحديدها
            if command.permission_ids is not None:
                role.permissions.clear()
                permission_repo = self._uow.permissions
                for perm_id in command.permission_ids:
                    permission = permission_repo.get_by_id(perm_id)
                    if permission:
                        role.permissions.append(permission)
            
            role.updated_by = user_context.user_id
            role_repo.save(role)
            self._commit()
            
            logger.info(f"Role updated: {role.name} by {user_context.user_id}")
            return role