# core/application/handlers/roles/create_role_handler.py
"""Create Role Handler - معالج إنشاء دور جديد"""

import logging

from core.domain.auth.entities import Role
from core.domain.auth.value_objects import RoleId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class CreateRoleHandler(BaseHandler):
    """معالج إنشاء دور جديد"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MANAGE_USERS)
    def handle(self, command, user_context: UserContext):
        """تنفيذ إنشاء دور جديد"""
        with self._uow:
            role_repo = self._uow.roles
            
            # التحقق من عدم وجود دور بنفس الاسم
            existing = role_repo.get_by_name(command.name)
            if existing:
                raise ValueError(f"Role '{command.name}' already exists")
            
            # إنشاء الدور
            role = Role(
                id=RoleId.generate(),
                name=command.name,
                display_name=command.display_name,
                description=command.description,
                is_admin=command.is_admin or False,
                is_active=True,
                created_by=user_context.user_id,
                updated_by=user_context.user_id
            )
            
            # إضافة الصلاحيات إذا تم تحديدها
            if command.permission_ids:
                permission_repo = self._uow.permissions
                for perm_id in command.permission_ids:
                    permission = permission_repo.get_by_id(perm_id)
                    if permission:
                        role.permissions.append(permission)
            
            role_repo.save(role)
            self._commit()
            
            logger.info(f"Role created: {role.name} by {user_context.user_id}")
            return role