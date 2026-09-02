# core/domain/sites/events.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from core.domain.shared.value_objects import BaseDomainEvent


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SiteCreatedEvent(BaseDomainEvent):
    site_id: UUID
    site_code: str
    site_name: str
    site_type: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "sites.site.created"


@dataclass(frozen=True)
class SiteUpdatedEvent(BaseDomainEvent):
    site_id: UUID
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "sites.site.updated"


@dataclass(frozen=True)
class SiteDeletedEvent(BaseDomainEvent):
    site_id: UUID
    site_code: str
    site_name: str
    deleted_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "sites.site.deleted"


# core/domain/sites/exceptions.py
class SiteError(Exception):
    pass


class SiteNotFoundError(SiteError):
    def __init__(self, site_id: str):
        self.site_id = site_id
        super().__init__(f"Site not found: {site_id}")


class DuplicateSiteCodeError(SiteError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Site code already exists: {code}")
