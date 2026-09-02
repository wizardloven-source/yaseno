# core/application/handlers/notifications/get_notifications_query_handler.py
"""
Get Notifications Query Handler - استعلام لجلب الإشعارات
"""

import logging
from typing import List

from core.domain.notifications.interfaces import INotificationRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetNotificationsQueryHandler(BaseQueryHandler):
    """
    معالج استعلام لجلب الإشعارات
    """

    def __init__(self, notification_repo: INotificationRepository):
        self._notification_repo = notification_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query) -> List[dict]:
        """
        تنفيذ جلب الإشعارات
        
        Args:
            query: استعلام جلب الإشعارات
        
        Returns:
            List[dict]: قائمة الإشعارات
        """
        logger.debug(f"Fetching notifications for user: {query.user_id}")

        notifications = self._notification_repo.list_by_user(
            user_id=query.user_id,
            limit=query.limit,
            offset=query.offset,
            include_read=query.include_read or False
        )

        return [
            {
                "id": str(n.id),
                "title": n.title,
                "message": n.message,
                "type": n.notification_type,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            }
            for n in notifications
        ]