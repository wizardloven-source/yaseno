# core/infrastructure/db/postgres/notification_repository.py
"""
Notification Repository - مستودع الإشعارات
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.orm import Session

from core.domain.notifications.entities import Notification, NotificationPreference
from core.domain.notifications.interfaces import (
    INotificationRepository,
    INotificationPreferenceRepository
)

from ..models.notification_model import (
    NotificationModel,
    NotificationPreferenceModel,
    NotificationTemplateModel
)

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _model_to_domain_notification(model: NotificationModel) -> Notification:
    """تحويل ORM Model إلى Domain Entity - إشعار"""
    return Notification(
        id=model.id,
        user_id=model.user_id,
        title=model.title,
        message=model.message,
        notification_type=model.notification_type,
        is_read=model.is_read,
        data=model.data or {},
        created_at=model.created_at,
        read_at=model.read_at
    )


def _domain_to_model_notification(notification: Notification) -> NotificationModel:
    """تحويل Domain Entity إلى ORM Model - إشعار"""
    return NotificationModel(
        id=notification.id if hasattr(notification, 'id') and notification.id else uuid4(),
        user_id=notification.user_id,
        title=notification.title,
        message=notification.message,
        notification_type=notification.notification_type,
        is_read=notification.is_read,
        data=notification.data,
        created_at=notification.created_at,
        read_at=notification.read_at
    )


def _model_to_domain_preference(model: NotificationPreferenceModel) -> NotificationPreference:
    """تحويل ORM Model إلى Domain Entity - تفضيلات"""
    return NotificationPreference(
        user_id=model.user_id,
        email_notifications=model.email_notifications,
        system_notifications=model.system_notifications,
        sound_notifications=model.sound_notifications,
        preferences=model.preferences or {}
    )


# =============================================================================
# INotificationRepository Implementation
# =============================================================================

class PostgresNotificationRepository(INotificationRepository):
    """تطبيق PostgreSQL لمستودع الإشعارات"""

    def __init__(self, session: Session):
        self._session = session

    def save(self, notification: Notification) -> None:
        """حفظ إشعار"""
        if hasattr(notification, 'id') and notification.id:
            existing = self._session.execute(
                select(NotificationModel).where(NotificationModel.id == notification.id)
            ).scalar_one_or_none()

            if existing:
                # تحديث
                existing.user_id = notification.user_id
                existing.title = notification.title
                existing.message = notification.message
                existing.notification_type = notification.notification_type
                existing.is_read = notification.is_read
                existing.data = notification.data
                existing.read_at = notification.read_at
            else:
                # إضافة جديدة
                model = _domain_to_model_notification(notification)
                self._session.add(model)
        else:
            # إضافة جديدة بدون ID
            model = NotificationModel(
                id=uuid4(),
                user_id=notification.user_id,
                title=notification.title,
                message=notification.message,
                notification_type=notification.notification_type,
                is_read=notification.is_read,
                data=notification.data,
                created_at=notification.created_at or utc_now(),
                read_at=notification.read_at
            )
            self._session.add(model)
            self._session.flush()
            notification.id = model.id

    def get_by_id(self, notification_id: str) -> Optional[Notification]:
        """الحصول على إشعار بواسطة المعرف"""
        model = self._session.execute(
            select(NotificationModel).where(NotificationModel.id == UUID(notification_id))
        ).scalar_one_or_none()

        return _model_to_domain_notification(model) if model else None

    def list_by_user(
        self,
        user_id: str,
        include_read: bool = True,
        limit: int = 100,
        offset: int = 0
    ) -> List[Notification]:
        """قائمة إشعارات المستخدم"""
        query = select(NotificationModel).where(NotificationModel.user_id == user_id)

        if not include_read:
            query = query.where(NotificationModel.is_read == False)

        query = query.order_by(NotificationModel.created_at.desc()).limit(limit).offset(offset)

        models = self._session.execute(query).scalars().all()
        return [_model_to_domain_notification(m) for m in models]

    def list_unread(self, user_id: str, limit: int = 100) -> List[Notification]:
        """قائمة الإشعارات غير المقروءة"""
        return self.list_by_user(user_id, include_read=False, limit=limit)

    def mark_as_read(self, notification_id: str, user_id: str) -> None:
        """تعيين إشعار كمقروء"""
        now = utc_now()
        self._session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.id == UUID(notification_id),
                NotificationModel.user_id == user_id
            )
            .values(is_read=True, read_at=now)
        )

    def mark_all_as_read(self, user_id: str) -> int:
        """تعيين جميع إشعارات المستخدم كمقروءة"""
        now = utc_now()
        result = self._session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.user_id == user_id,
                NotificationModel.is_read == False
            )
            .values(is_read=True, read_at=now)
        )
        return result.rowcount

    def delete(self, notification_id: str) -> bool:
        """حذف إشعار"""
        result = self._session.execute(
            select(NotificationModel).where(NotificationModel.id == UUID(notification_id))
        ).scalar_one_or_none()

        if result:
            self._session.delete(result)
            return True
        return False

    def get_statistics(
        self,
        user_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """الحصول على إحصائيات الإشعارات"""
        query = select(
            func.count().label('total'),
            func.sum(func.cast(NotificationModel.is_read, func.Integer)).label('read_count')
        )

        if user_id:
            query = query.where(NotificationModel.user_id == user_id)
        if from_date:
            query = query.where(NotificationModel.created_at >= from_date)
        if to_date:
            query = query.where(NotificationModel.created_at <= to_date)

        result = self._session.execute(query).first()

        total = result.total or 0
        read_count = result.read_count or 0

        return {
            'total': total,
            'unread': total - read_count,
            'read': read_count,
            'user_id': user_id,
            'from_date': from_date.isoformat() if from_date else None,
            'to_date': to_date.isoformat() if to_date else None
        }


# =============================================================================
# INotificationPreferenceRepository Implementation
# =============================================================================

class PostgresNotificationPreferenceRepository(INotificationPreferenceRepository):
    """تطبيق PostgreSQL لمستودع تفضيلات الإشعارات"""

    def __init__(self, session: Session):
        self._session = session

    def save(self, preferences: NotificationPreference) -> None:
        """حفظ تفضيلات الإشعارات"""
        existing = self._session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.user_id == preferences.user_id
            )
        ).scalar_one_or_none()

        if existing:
            # تحديث
            existing.email_notifications = preferences.email_notifications
            existing.system_notifications = preferences.system_notifications
            existing.sound_notifications = preferences.sound_notifications
            existing.preferences = preferences.preferences
            existing.updated_at = utc_now()
        else:
            # إضافة جديدة
            model = NotificationPreferenceModel(
                user_id=preferences.user_id,
                email_notifications=preferences.email_notifications,
                system_notifications=preferences.system_notifications,
                sound_notifications=preferences.sound_notifications,
                preferences=preferences.preferences
            )
            self._session.add(model)

    def get_by_user(self, user_id: str) -> Optional[NotificationPreference]:
        """الحصول على تفضيلات مستخدم"""
        model = self._session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.user_id == user_id
            )
        ).scalar_one_or_none()

        return _model_to_domain_preference(model) if model else None

    def update(self, user_id: str, preferences: Dict[str, Any]) -> Optional[NotificationPreference]:
        """تحديث تفضيلات مستخدم"""
        model = self._session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.user_id == user_id
            )
        ).scalar_one_or_none()

        if model:
            for key, value in preferences.items():
                if hasattr(model, key):
                    setattr(model, key, value)
            model.updated_at = utc_now()
            self._session.flush()
            return _model_to_domain_preference(model)

        return None

    def delete(self, user_id: str) -> bool:
        """حذف تفضيلات مستخدم"""
        model = self._session.execute(
            select(NotificationPreferenceModel).where(
                NotificationPreferenceModel.user_id == user_id
            )
        ).scalar_one_or_none()

        if model:
            self._session.delete(model)
            return True
        return False


# =============================================================================
# Notification Template Repository - اختياري
# =============================================================================

class PostgresNotificationTemplateRepository:
    """تطبيق PostgreSQL لمستودع قوالب الإشعارات"""

    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, template_id: str) -> Optional[NotificationTemplateModel]:
        """الحصول على قالب بواسطة المعرف"""
        return self._session.execute(
            select(NotificationTemplateModel).where(
                NotificationTemplateModel.id == UUID(template_id)
            )
        ).scalar_one_or_none()

    def get_by_code(self, code: str) -> Optional[NotificationTemplateModel]:
        """الحصول على قالب بواسطة الكود"""
        return self._session.execute(
            select(NotificationTemplateModel).where(
                NotificationTemplateModel.code == code
            )
        ).scalar_one_or_none()

    def list_all(self, limit: int = 100, offset: int = 0) -> List[NotificationTemplateModel]:
        """قائمة جميع القوالب"""
        return self._session.execute(
            select(NotificationTemplateModel)
            .limit(limit)
            .offset(offset)
        ).scalars().all()


__all__ = [
    "PostgresNotificationRepository",
    "PostgresNotificationPreferenceRepository",
    "PostgresNotificationTemplateRepository",
]