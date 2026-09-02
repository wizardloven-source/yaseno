# core/application/handlers/notifications/get_unread_notifications_query_handler.py
"""
Get Unread Notifications Query Handler - استعلام لجلب الإشعارات غير المقروءة
"""

import logging
from typing import List

from core.domain.notifications.interfaces import INotificationRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetUnreadNotificationsQueryHandler(BaseQueryHandler):
    """
    معالج استعلام لجلب الإشعارات غير المقروءة
    """

    def __init__(self, notification_repo: INotificationRepository):
        self._notification_repo = notification_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query) -> List[dict]:
        """
        تنفيذ جلب الإشعارات غير المقروءة
        
        Args:
            query: استعلام جلب الإشعارات غير المقروءة
        
        Returns:
            List[dict]: قائمة الإشعارات غير المقروءة
        """
        logger.debug(f"Fetching unread notifications for user: {query.user_id}")

        notifications = self._notification_repo.list_unread(
            user_id=query.user_id,
            limit=query.limit
        )

        return [
            {
                "id": str(n.id),
                "title": n.title,
                "message": n.message,
                "type": n.notification_type,
                "created_at": n.created_at.isoformat()
            }
            for n in notifications
        ]