# core/domain/notifications/interfaces.py
"""
Notifications Repository Interfaces - واجهات مستودع الإشعارات
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime


class INotificationRepository(ABC):
    """واجهة مستودع الإشعارات"""

    @abstractmethod
    def save(self, notification) -> None:
        """حفظ إشعار"""
        pass

    @abstractmethod
    def get_by_id(self, notification_id: str) -> Optional[Any]:
        """الحصول على إشعار بواسطة المعرف"""
        pass

    @abstractmethod
    def list_by_user(
        self,
        user_id: str,
        include_read: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Any]:
        """قائمة إشعارات المستخدم"""
        pass

    @abstractmethod
    def list_unread(self, user_id: str, limit: int = 100) -> List[Any]:
        """قائمة الإشعارات غير المقروءة"""
        pass

    @abstractmethod
    def mark_as_read(self, notification_id: str, user_id: str) -> None:
        """تعيين إشعار كمقروء"""
        pass

    @abstractmethod
    def mark_all_as_read(self, user_id: str) -> int:
        """تعيين جميع إشعارات المستخدم كمقروءة"""
        pass

    @abstractmethod
    def delete(self, notification_id: str) -> bool:
        """حذف إشعار"""
        pass

    @abstractmethod
    def get_statistics(
        self,
        user_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """الحصول على إحصائيات الإشعارات"""
        pass


class INotificationPreferenceRepository(ABC):
    """واجهة مستودع تفضيلات الإشعارات"""

    @abstractmethod
    def save(self, preferences) -> None:
        """حفظ تفضيلات الإشعارات"""
        pass

    @abstractmethod
    def get_by_user(self, user_id: str) -> Optional[Any]:
        """الحصول على تفضيلات مستخدم"""
        pass

    @abstractmethod
    def update(self, user_id: str, preferences: Dict[str, Any]) -> Optional[Any]:
        """تحديث تفضيلات مستخدم"""
        pass

    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """حذف تفضيلات مستخدم"""
        pass