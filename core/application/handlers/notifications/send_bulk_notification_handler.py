# core/application/handlers/notifications/send_bulk_notification_handler.py
"""
Send Bulk Notification Handler - معالج إرسال إشعارات جماعية
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class SendBulkNotificationHandler(BaseHandler):
    """
    معالج إرسال إشعارات جماعية
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        super().__init__(uow)
        self._notification_service = notification_service

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ إرسال إشعارات جماعية
        
        Args:
            command: أمر إرسال الإشعارات الجماعية
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة الإرسال
        """
        logger.info(f"Sending bulk notification to {len(command.recipients)} recipients")

        results = []
        for recipient in command.recipients:
            result = self._notification_service.send(
                recipient=recipient,
                title=command.title,
                message=command.message,
                notification_type=command.notification_type,
                data=command.data,
                sent_by=user_context.user_id if user_context else "system"
            )
            results.append({
                "recipient": recipient,
                "success": result.success,
                "notification_id": result.notification_id
            })

        success_count = sum(1 for r in results if r["success"])

        return {
            "success": success_count > 0,
            "total": len(results),
            "success_count": success_count,
            "failed_count": len(results) - success_count,
            "results": results
        }