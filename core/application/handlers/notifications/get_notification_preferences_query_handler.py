# core/application/handlers/notifications/get_notification_preferences_query_handler.py
"""
Get Notification Preferences Query Handler - استعلام لجلب تفضيلات الإشعارات
"""

import logging

from core.domain.notifications.interfaces import INotificationPreferenceRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetNotificationPreferencesQueryHandler(BaseQueryHandler):
    """
    معالج استعلام لجلب تفضيلات الإشعارات
    """

    def __init__(self, preference_repo: INotificationPreferenceRepository):
        self._preference_repo = preference_repo

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query) -> dict:
        """
        تنفيذ جلب تفضيلات الإشعارات
        
        Args:
            query: استعلام جلب تفضيلات الإشعارات
        
        Returns:
            dict: تفضيلات الإشعارات
        """
        logger.debug(f"Fetching notification preferences for user: {query.user_id}")

        preferences = self._preference_repo.get_by_user(query.user_id)

        if not preferences:
            return {
                "user_id": query.user_id,
                "preferences": {}
            }

        return preferences.to_dict()