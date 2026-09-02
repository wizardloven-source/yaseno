# core/application/handlers/roles/assign_permission_handler.py
"""Assign Permission Handler - معالج تعيين صلاحية لدور"""

import logging

from core.domain.auth.value_objects import RoleId, PermissionId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class AssignPermissionHandler(BaseHandler):
    """معالج تعيين صلاحية لدور"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MANAGE_USERS)
    def handle(self, command, user_context: UserContext):
        """تنفيذ تعيين صلاحية لدور"""
        with self._uow:
            role_repo = self._uow.roles
            permission_repo = self._uow.permissions
            
            role = role_repo.get_by_id(RoleId.from_string(command.role_id))
            if not role:
                raise ValueError(f"Role '{command.role_id}' not found")
            
            permission = permission_repo.get_by_id(PermissionId.from_string(command.permission_id))
            if not permission:
                raise ValueError(f"Permission '{command.permission_id}' not found")
            
            # إضافة الصلاحية إذا لم تكن موجودة
            if permission not in role.permissions:
                role.permissions.append(permission)
                role.updated_by = user_context.user_id
                role_repo.save(role)
                self._commit()
                logger.info(f"Permission {permission.code} assigned to role {role.name}")
                return {"success": True, "message": "Permission assigned successfully"}
            else:
                return {"success": True, "message": "Permission already assigned"}