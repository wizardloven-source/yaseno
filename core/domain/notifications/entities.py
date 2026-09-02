# core/domain/notifications/entities.py
"""
Notification Entities - كيانات الإشعارات
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Notification:
    """إشعار"""
    id: UUID = field(default_factory=uuid4)
    user_id: str = ""
    title: str = ""
    message: str = ""
    notification_type: str = "system"
    is_read: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    read_at: Optional[datetime] = None

    def mark_as_read(self, user_id: str) -> None:
        """تعيين الإشعار كمقروء"""
        if not self.is_read:
            self.is_read = True
            self.read_at = utc_now()

    @classmethod
    def create(
        cls,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "system",
        data: Optional[Dict[str, Any]] = None
    ) -> 'Notification':
        """إنشاء إشعار جديد"""
        return cls(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            data=data or {}
        )


@dataclass
class NotificationPreference:
    """تفضيلات الإشعارات"""
    user_id: str = ""
    email_notifications: bool = True
    system_notifications: bool = True
    sound_notifications: bool = True
    preferences: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email_notifications": self.email_notifications,
            "system_notifications": self.system_notifications,
            "sound_notifications": self.sound_notifications,
            "preferences": self.preferences
        }