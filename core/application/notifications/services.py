# core/application/notifications/services.py

"""
Notification Services - خدمات الإشعارات
الإصدار المُصحَّح
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, field

from core.domain.notifications.entities import Notification, NotificationPreference
from core.domain.notifications.interfaces import INotificationRepository, INotificationPreferenceRepository
from core.domain.accounting.interfaces import IUnitOfWork


@dataclass
class NotificationResult:
    """نتيجة إرسال إشعار"""
    success: bool
    notification_id: Optional[str] = None
    message: str = ""


class NotificationService:
    """
    خدمة الإشعارات - إدارة إرسال الإشعارات
    ✅ مصحح: قبول معاملين فقط (notification_repo, uow)
    """
    
    def __init__(self, notification_repo: INotificationRepository, uow: IUnitOfWork):
        """
        Args:
            notification_repo: مستودع الإشعارات
            uow: Unit of Work
        """
        self._notification_repo = notification_repo
        self._uow = uow

    def send(
        self,
        recipient: str,
        title: str,
        message: str,
        notification_type: str = "system",
        data: Optional[Dict[str, Any]] = None,
        sent_by: str = "system"
    ) -> NotificationResult:
        """
        إرسال إشعار
        
        Args:
            recipient: معرف المستلم
            title: عنوان الإشعار
            message: نص الإشعار
            notification_type: نوع الإشعار
            data: بيانات إضافية
            sent_by: من قام بالإرسال
        
        Returns:
            NotificationResult: نتيجة الإرسال
        """
        try:
            notification = Notification.create(
                user_id=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                data=data or {}
            )

            self._notification_repo.save(notification)
            self._uow.commit()

            return NotificationResult(
                success=True,
                notification_id=str(notification.id),
                message="Notification sent successfully"
            )

        except Exception as e:
            return NotificationResult(
                success=False,
                message=f"Failed to send notification: {str(e)}"
            )

    def send_bulk(
        self,
        recipients: List[str],
        title: str,
        message: str,
        notification_type: str = "system",
        data: Optional[Dict[str, Any]] = None,
        sent_by: str = "system"
    ) -> List[NotificationResult]:
        """
        إرسال إشعارات جماعية
        
        Args:
            recipients: قائمة المستلمين
            title: عنوان الإشعار
            message: نص الإشعار
            notification_type: نوع الإشعار
            data: بيانات إضافية
            sent_by: من قام بالإرسال
        
        Returns:
            List[NotificationResult]: قائمة نتائج الإرسال
        """
        results = []
        for recipient in recipients:
            result = self.send(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                data=data,
                sent_by=sent_by
            )
            results.append(result)
        return results


class EmailService:
    """
    خدمة البريد الإلكتروني
    """
    
    def __init__(self, settings_repo):
        self._settings_repo = settings_repo

    def send_test_email(self, recipient: str, sent_by: str = "system") -> bool:
        """إرسال بريد اختبار"""
        return True


class SoundService:
    """
    خدمة الصوت للإشعارات
    """

    def play_test_sound(self, sound_type: str = "default") -> bool:
        """تشغيل صوت اختبار"""
        return True


class NotificationPreferenceService:
    """
    خدمة تفضيلات الإشعارات
    """
    
    def __init__(self, preference_repo, uow):
        self._preference_repo = preference_repo
        self._uow = uow

    def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        updated_by: str = "system"
    ) -> NotificationPreference:
        """تحديث تفضيلات الإشعارات"""
        existing = self._preference_repo.get_by_user(user_id)

        if existing:
            for key, value in preferences.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            existing = NotificationPreference(
                user_id=user_id,
                **preferences
            )

        self._preference_repo.save(existing)
        self._uow.commit()

        return existing