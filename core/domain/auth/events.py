# core/domain/auth/events.py
"""
Authentication Events - أحداث المصادقة
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.domain.shared.value_objects import BaseDomainEvent


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class UserCreatedEvent(BaseDomainEvent):
    """
    حدث إنشاء مستخدم جديد
    """
    user_id: str
    username: str
    email: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "auth.user.created"


@dataclass(frozen=True)
class UserDeletedEvent(BaseDomainEvent):
    """
    حدث حذف مستخدم
    """
    user_id: str
    username: str
    deleted_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "auth.user.deleted"


@dataclass(frozen=True)
class UserLoggedInEvent(BaseDomainEvent):
    """
    حدث تسجيل دخول مستخدم
    """
    user_id: str
    username: str
    ip_address: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "auth.user.logged_in"