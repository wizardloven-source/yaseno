# core/application/handlers/notifications/update_notification_preferences_handler.py
"""
Update Notification Preferences Handler - معالج تحديث تفضيلات الإشعارات
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class UpdateNotificationPreferencesHandler(BaseHandler):
    """
    معالج تحديث تفضيلات الإشعارات
    """

    def __init__(self, uow: IUnitOfWork, notification_preference_service):
        super().__init__(uow)
        self._preference_service = notification_preference_service

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext = None):
        """
        تنفيذ تحديث تفضيلات الإشعارات
        
        Args:
            command: أمر تحديث تفضيلات الإشعارات
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة العملية
        """
        logger.info(f"Updating notification preferences for user: {user_context.user_id}")

        with self._uow:
            preferences = self._preference_service.update_preferences(
                user_id=user_context.user_id,
                preferences=command.preferences,
                updated_by=user_context.user_id
            )
            self._commit()

        return {
            "success": True,
            "message": "Notification preferences updated successfully",
            "preferences": preferences
        }# core/application/handlers/notifications/backup_completed_notification_handler.py
"""
Backup Completed Notification Handler - معالج إشعار اكتمال النسخ الاحتياطي
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.backup.events import BackupCompletedEvent

logger = logging.getLogger(__name__)


class BackupCompletedNotificationHandler:
    """
    معالج إشعار اكتمال النسخ الاحتياطي
    """

    def __init__(self, uow: IUnitOfWork, notification_service):
        self._uow = uow
        self._notification_service = notification_service

    def __call__(self, event: BackupCompletedEvent) -> None:
        """
        معالجة الحدث
        
        Args:
            event: حدث اكتمال النسخ الاحتياطي
        """
        try:
            logger.info(f"Processing backup completed notification")

            # جلب مديري النظام
            with self._uow:
                users = self._uow.users.list_by_role("admin")

                if not users:
                    logger.warning("No admins found for backup notification")
                    return

                # إرسال إشعار لكل مستخدم
                for user in users:
                    self._notification_service.send(
                        recipient=user.id,
                        title=f"تم إكمال النسخ الاحتياطي",
                        message=f"تم إنشاء نسخة احتياطية جديدة في {event.backup_path}",
                        notification_type="backup_completed",
                        data={
                            "backup_path": event.backup_path,
                            "backup_size": event.backup_size,
                            "backup_date": event.backup_date.isoformat()
                        }
                    )

            logger.info(f"Backup completed notification sent")

        except Exception as e:
            logger.error(f"Error processing backup completed notification: {e}")