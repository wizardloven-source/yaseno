# core/application/handlers/users/change_password_handler.py

"""
Change Password Handler - معالج تغيير كلمة المرور
"""

import logging

from core.domain.auth.value_objects import UserId
from core.domain.auth.interfaces import IUserRepository
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.security.password_hasher import PasswordHasher
from core.application.users.commands import ChangePasswordCommand
from core.shared.exceptions import ConcurrentModificationError

logger = logging.getLogger(__name__)


class ChangePasswordHandler(BaseHandler[ChangePasswordCommand, dict]):
    """معالج تغيير كلمة المرور"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, command: ChangePasswordCommand, user_context: UserContext) -> dict:
        with self._uow:
            user_repo = self._uow.users
            
            # 1. جلب المستخدم
            user = user_repo.get_by_id(UserId.from_string(command.user_id))
            if not user:
                return {
                    "success": False,
                    "message": f"User {command.user_id} not found"
                }
            
            # 2. التحقق من كلمة المرور الحالية (للمستخدم نفسه فقط)
            if user_context.user_id == command.user_id:
                if not PasswordHasher.verify(command.old_password, user.password_hash):
                    return {
                        "success": False,
                        "message": "Current password is incorrect"
                    }
            
            # 3. التحقق من صحة كلمة المرور الجديدة
            if len(command.new_password) < 6:
                return {
                    "success": False,
                    "message": "New password must be at least 6 characters long"
                }
            
            # 4. التحقق من الإصدار
            if user.version != command.version:
                raise ConcurrentModificationError(
                    "User",
                    command.user_id,
                    command.version,
                    user.version
                )
            
            # 5. تحديث كلمة المرور
            user.password_hash = PasswordHasher.hash(command.new_password)
            user.updated_by = user_context.user_id
            user_repo.save(user)
            self._commit()
            
            logger.info(f"Password changed for user: {user.username} by {user_context.user_id}")
            
            return {
                "success": True,
                "message": "Password changed successfully"
            }