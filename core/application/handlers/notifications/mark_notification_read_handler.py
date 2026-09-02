# core/application/handlers/notifications/mark_notification_read_handler.py
"""
Mark Notification Read Handler - معالج تعيين إشعار كمقروء
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class MarkNotificationReadHandler(BaseHandler):
    """
    معالج تعيين إشعار كمقروء
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ تعيين الإشعار كمقروء
        
        Args:
            command: أمر تعيين الإشعار كمقروء
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Marking notification as read: {command.notification_id}")

        with self._uow:
            notification_repo = self._uow.notifications

            notification = notification_repo.get_by_id(command.notification_id)
            if not notification:
                return {
                    "success": False,
                    "message": f"Notification {command.notification_id} not found"
                }

            notification.mark_as_read(user_context.user_id)
            notification_repo.save(notification)
            self._commit()

        return {
            "success": True,
            "message": "Notification marked as read",
            "notification_id": command.notification_id
        }