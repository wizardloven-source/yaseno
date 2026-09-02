# core/application/handlers/notifications/delete_notification_handler.py
"""
Delete Notification Handler - معالج حذف إشعار
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class DeleteNotificationHandler(BaseHandler):
    """
    معالج حذف إشعار
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ حذف الإشعار
        
        Args:
            command: أمر حذف الإشعار
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Deleting notification: {command.notification_id}")

        with self._uow:
            notification_repo = self._uow.notifications

            notification = notification_repo.get_by_id(command.notification_id)
            if not notification:
                return {
                    "success": False,
                    "message": f"Notification {command.notification_id} not found"
                }

            notification_repo.delete(command.notification_id)
            self._commit()

        return {
            "success": True,
            "message": "Notification deleted successfully",
            "notification_id": command.notification_id
        }