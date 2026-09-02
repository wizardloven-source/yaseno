# core/application/handlers/users/reset_password_handler.py

"""
Reset Password Handler - معالج إعادة تعيين كلمة المرور
"""

import logging

from core.domain.auth.value_objects import UserId
from core.domain.auth.interfaces import IUserRepository
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.security.password_hasher import PasswordHasher
from core.application.users.commands import ResetPasswordCommand

logger = logging.getLogger(__name__)


class ResetPasswordHandler(BaseHandler[ResetPasswordCommand, dict]):
    """معالج إعادة تعيين كلمة المرور"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MANAGE_USERS)
    def handle(self, command: ResetPasswordCommand, user_context: UserContext) -> dict:
        with self._uow:
            user_repo = self._uow.users
            
            # 1. جلب المستخدم
            user = user_repo.get_by_id(UserId.from_string(command.user_id))
            if not user:
                return {
                    "success": False,
                    "message": f"User {command.user_id} not found"
                }
            
            # 2. التحقق من صحة كلمة المرور الجديدة
            if len(command.new_password) < 6:
                return {
                    "success": False,
                    "message": "New password must be at least 6 characters long"
                }
            
            # 3. تحديث كلمة المرور
            user.password_hash = PasswordHasher.hash(command.new_password)
            user.updated_by = user_context.user_id
            user_repo.save(user)
            self._commit()
            
            logger.info(f"Password reset for user: {user.username} by {user_context.user_id}")
            
            return {
                "success": True,
                "message": "Password reset successfully"
            }