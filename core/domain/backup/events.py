# core/domain/backup/events.py
"""
Backup Events - أحداث النسخ الاحتياطي
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.domain.shared.value_objects import BaseDomainEvent


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class BackupCompletedEvent(BaseDomainEvent):
    """
    حدث اكتمال النسخ الاحتياطي
    """
    backup_path: str
    backup_size: Optional[int] = None
    backup_date: datetime = field(default_factory=_aware_utc_now)
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "backup.completed"