# core/application/handlers/users/delete_user_handler.py

"""
Delete User Handler - معالج حذف مستخدم
"""

import logging

from core.domain.auth.value_objects import UserId
from core.domain.auth.interfaces import IUserRepository
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.users.commands import DeleteUserCommand

logger = logging.getLogger(__name__)


class DeleteUserHandler(BaseHandler[DeleteUserCommand, dict]):
    """معالج حذف مستخدم"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MANAGE_USERS)
    def handle(self, command: DeleteUserCommand, user_context: UserContext) -> dict:
        with self._uow:
            user_repo = self._uow.users
            
            # 1. جلب المستخدم
            user = user_repo.get_by_id(UserId.from_string(command.user_id))
            if not user:
                return {
                    "success": False,
                    "message": f"User {command.user_id} not found"
                }
            
            # 2. منع حذف المستخدم الحالي
            if user.id.value == user_context.user_id:
                return {
                    "success": False,
                    "message": "Cannot delete your own account"
                }
            
            # 3. حذف المستخدم
            if command.permanent:
                result = user_repo.delete(user.id)
                message = "User permanently deleted"
            else:
                result = user_repo.soft_delete(user.id, user_context.user_id)
                message = "User deactivated"
            
            self._commit()
            
            logger.info(f"User deleted: {user.username} by {user_context.user_id}")
            
            return {
                "success": result,
                "message": message,
                "user_id": command.user_id
            }