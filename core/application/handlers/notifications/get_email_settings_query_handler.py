# core/application/handlers/notifications/get_email_settings_query_handler.py
"""
Get Email Settings Query Handler - استعلام لجلب إعدادات البريد الإلكتروني
"""

import logging

from core.domain.settings.interfaces import ISettingsRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetEmailSettingsQueryHandler(BaseQueryHandler):
    """
    معالج استعلام لجلب إعدادات البريد الإلكتروني
    """

    def __init__(self, settings_repo: ISettingsRepository):
        self._settings_repo = settings_repo

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, query) -> dict:
        """
        تنفيذ جلب إعدادات البريد الإلكتروني
        
        Args:
            query: استعلام جلب إعدادات البريد الإلكتروني
        
        Returns:
            dict: إعدادات البريد الإلكتروني
        """
        logger.debug("Fetching email settings")

        settings = self._settings_repo.get()
        if not settings:
            return {}

        email_settings = settings.notifications if hasattr(settings, 'notifications') else {}

        return {
            "smtp_server": email_settings.get("email_smtp_server", ""),
            "smtp_port": email_settings.get("email_smtp_port", 587),
            "username": email_settings.get("email_username", ""),
            "from_email": email_settings.get("email_from", ""),
            "is_configured": bool(
                email_settings.get("email_smtp_server") and
                email_settings.get("email_username") and
                email_settings.get("email_from")
            )
        }