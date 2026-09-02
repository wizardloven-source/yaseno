# core/application/handlers/users/create_user_handler.py

"""
Create User Handler - معالج إنشاء مستخدم جديد
"""

import logging
from decimal import Decimal  # ✅ هذا هو الاستيراد المطلوب
from typing import Optional

from core.domain.auth.entities import User
from core.domain.auth.value_objects import UserId, RoleId
from core.domain.auth.interfaces import IUserRepository, IRoleRepository
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.security.password_hasher import PasswordHasher
from core.application.users.commands import CreateUserCommand
from core.application.users.dtos import UserDTO
from core.application.users.converters import user_to_dto

logger = logging.getLogger(__name__)


class CreateUserHandler(BaseHandler[CreateUserCommand, UserDTO]):
    """
    معالج إنشاء مستخدم جديد
    
    مسؤولياته:
        1. التحقق من عدم وجود اسم مستخدم مكرر
        2. التحقق من صحة كلمة المرور
        3. إنشاء كيان المستخدم
        4. تعيين الأدوار
        5. الحفظ في قاعدة البيانات
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MANAGE_USERS)
    def handle(self, command: CreateUserCommand, user_context: UserContext) -> UserDTO:
        with self._uow:
            user_repo = self._uow.users
            role_repo = self._uow.roles
            
            # 1. التحقق من عدم وجود اسم مستخدم مكرر
            existing = user_repo.get_by_username(command.username)
            if existing:
                raise ValueError(f"Username '{command.username}' already exists")
            
            # 2. التحقق من صحة كلمة المرور
            if len(command.password) < 6:
                raise ValueError("Password must be at least 6 characters long")
            
            # 3. تشفير كلمة المرور
            hashed_password = PasswordHasher.hash(command.password)
            
            # 4. إنشاء المستخدم
            user = User(
                id=UserId.generate(),
                username=command.username,
                email=command.email,
                full_name=command.full_name,
                password_hash=hashed_password,
                is_active=command.is_active,
                is_super_admin=command.is_super_admin,
                created_by=user_context.user_id,
                updated_by=user_context.user_id
            )
            
            # 5. تعيين الأدوار
            if command.role_ids:
                for role_id in command.role_ids:
                    role = role_repo.get_by_id(RoleId.from_string(role_id))
                    if role:
                        user.roles.append(role)
            
            # 6. حفظ المستخدم
            user_repo.save(user)
            self._commit()
            
            logger.info(f"User created: {user.username} by {user_context.user_id}")
            
            return user_to_dto(user)