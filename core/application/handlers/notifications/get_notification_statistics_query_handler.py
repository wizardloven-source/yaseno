# core/application/handlers/notifications/get_notification_statistics_query_handler.py
"""
Get Notification Statistics Query Handler - استعلام لإحصائيات الإشعارات
"""

import logging
from typing import Dict, Any

from core.domain.notifications.interfaces import INotificationRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetNotificationStatisticsQueryHandler(BaseQueryHandler):
    """
    معالج استعلام لإحصائيات الإشعارات
    """

    def __init__(self, notification_repo: INotificationRepository):
        self._notification_repo = notification_repo

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query) -> Dict[str, Any]:
        """
        تنفيذ جلب إحصائيات الإشعارات
        
        Args:
            query: استعلام إحصائيات الإشعارات
        
        Returns:
            Dict[str, Any]: إحصائيات الإشعارات
        """
        logger.debug("Fetching notification statistics")

        stats = self._notification_repo.get_statistics(
            user_id=query.user_id,
            from_date=query.from_date,
            to_date=query.to_date
        )

        return {
            "success": True,
            "statistics": stats
        }