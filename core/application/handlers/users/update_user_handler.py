# core/application/handlers/users/update_user_handler.py

"""
Update User Handler - معالج تحديث مستخدم
"""

import logging

from core.domain.auth.value_objects import UserId, RoleId
from core.domain.auth.interfaces import IUserRepository, IRoleRepository
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.users.commands import UpdateUserCommand
from core.application.users.dtos import UserDTO
from core.application.users.converters import user_to_dto
from core.shared.exceptions import ConcurrentModificationError

logger = logging.getLogger(__name__)


class UpdateUserHandler(BaseHandler[UpdateUserCommand, UserDTO]):
    """معالج تحديث مستخدم موجود"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MANAGE_USERS)
    def handle(self, command: UpdateUserCommand, user_context: UserContext) -> UserDTO:
        with self._uow:
            user_repo = self._uow.users
            role_repo = self._uow.roles
            
            # 1. جلب المستخدم
            user = user_repo.get_by_id(UserId.from_string(command.user_id))
            if not user:
                raise ValueError(f"User {command.user_id} not found")
            
            # 2. التحقق من الإصدار (Optimistic Locking)
            if user.version != command.version:
                raise ConcurrentModificationError(
                    "User",
                    command.user_id,
                    command.version,
                    user.version
                )
            
            # 3. تحديث البيانات
            user.full_name = command.full_name or user.full_name
            user.email = command.email or user.email
            user.is_active = command.is_active if command.is_active is not None else user.is_active
            user.is_super_admin = command.is_super_admin if command.is_super_admin is not None else user.is_super_admin
            user.updated_by = user_context.user_id
            
            # 4. تحديث الأدوار
            if command.role_ids is not None:
                user.roles.clear()
                for role_id in command.role_ids:
                    role = role_repo.get_by_id(RoleId.from_string(role_id))
                    if role:
                        user.roles.append(role)
            
            # 5. حفظ التغييرات
            user_repo.save(user)
            self._commit()
            
            logger.info(f"User updated: {user.username} by {user_context.user_id}")
            
            return user_to_dto(user)