# core/application/handlers/notifications/mark_all_notifications_read_handler.py
"""
Mark All Notifications Read Handler - معالج تعيين جميع الإشعارات كمقروءة
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class MarkAllNotificationsReadHandler(BaseHandler):
    """
    معالج تعيين جميع الإشعارات كمقروءة
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ تعيين جميع الإشعارات كمقروءة
        
        Args:
            command: أمر تعيين جميع الإشعارات كمقروءة
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Marking all notifications as read for user: {user_context.user_id}")

        with self._uow:
            notification_repo = self._uow.notifications

            count = notification_repo.mark_all_as_read(user_context.user_id)
            self._commit()

        return {
            "success": True,
            "message": f"Marked {count} notifications as read",
            "count": count
        }