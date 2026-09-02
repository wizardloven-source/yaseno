# core/application/handlers/notifications/test_email_handler.py
"""
Test Email Handler - معالج اختبار البريد الإلكتروني
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class TestEmailHandler(BaseHandler):
    """
    معالج اختبار البريد الإلكتروني
    """

    def __init__(self, uow: IUnitOfWork, email_service):
        super().__init__(uow)
        self._email_service = email_service

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ اختبار البريد الإلكتروني
        
        Args:
            command: أمر اختبار البريد الإلكتروني
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة الاختبار
        """
        logger.info(f"Sending test email to: {command.recipient}")

        try:
            result = self._email_service.send_test_email(
                recipient=command.recipient,
                sent_by=user_context.user_id if user_context else "system"
            )

            return {
                "success": True,
                "message": "Test email sent successfully",
                "recipient": command.recipient
            }
        except Exception as e:
            logger.error(f"Test email failed: {e}")
            return {
                "success": False,
                "message": f"Test email failed: {str(e)}",
                "recipient": command.recipient
            }