# core/application/handlers/notifications/send_notification_handler.py
"""
Send Notification Handler - معالج إرسال إشعار
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class SendNotificationHandler(BaseHandler):
    """
    معالج إرسال إشعار
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        super().__init__(uow)
        self._notification_service = notification_service

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ إرسال إشعار
        
        Args:
            command: أمر إرسال الإشعار
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة الإرسال
        """
        logger.info(f"Sending notification: {command.title}")

        result = self._notification_service.send(
            recipient=command.recipient,
            title=command.title,
            message=command.message,
            notification_type=command.notification_type,
            data=command.data,
            sent_by=user_context.user_id if user_context else "system"
        )

        return {
            "success": result.success,
            "notification_id": result.notification_id,
            "message": result.message
        }