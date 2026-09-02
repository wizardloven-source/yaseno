# core/application/handlers/notifications/new_user_notification_handler.py
"""
New User Notification Handler - معالج إشعار مستخدم جديد
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.auth.events import UserCreatedEvent

logger = logging.getLogger(__name__)


class NewUserNotificationHandler:
    """
    معالج إشعار مستخدم جديد
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: UserCreatedEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث إنشاء مستخدم جديد
        """
        try:
            logger.info(f"Processing new user notification: {event.username}")

            with self._uow:
                # جلب مديري النظام
                users = self._uow.users.list_by_role("admin")

                # إرسال إشعار للمستخدم الجديد
                self._notification_service.send(
                    recipient=event.user_id,
                    title=f"مرحباً بك في النظام",
                    message=f"تم إنشاء حسابك بنجاح. اسم المستخدم: {event.username}",
                    notification_type="new_user",
                    data={
                        "username": event.username,
                        "email": event.email
                    }
                )

                # إشعار المديرين
                for user in users:
                    self._notification_service.send(
                        recipient=user.id,
                        title=f"مستخدم جديد - {event.username}",
                        message=f"تم إنشاء مستخدم جديد في النظام: {event.username} ({event.email})",
                        notification_type="new_user_admin",
                        data={
                            "user_id": str(event.user_id),
                            "username": event.username,
                            "email": event.email
                        }
                    )

            logger.info(f"New user notification sent for {event.username}")

        except Exception as e:
            logger.error(f"Error processing new user notification: {e}")