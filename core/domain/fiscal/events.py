# core/domain/fiscal/events.py
"""
Fiscal Year Events - أحداث السنة المالية
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import FiscalYearId, FiscalYearCode, FiscalPeriodReference


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class FiscalYearCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء سنة مالية جديدة"""
    fiscal_year_id: FiscalYearId
    code: FiscalYearCode
    name: str
    start_date: datetime
    end_date: datetime
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fiscal.year.created"


@dataclass(frozen=True)
class FiscalYearOpenedEvent(BaseDomainEvent):
    """يُرفع عند فتح سنة مالية"""
    fiscal_year_id: FiscalYearId
    code: FiscalYearCode
    opened_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fiscal.year.opened"


@dataclass(frozen=True)
class FiscalYearClosedEvent(BaseDomainEvent):
    """يُرفع عند إغلاق سنة مالية"""
    fiscal_year_id: FiscalYearId
    code: FiscalYearCode
    closed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fiscal.year.closed"


@dataclass(frozen=True)
class PeriodClosedEvent(BaseDomainEvent):
    """يُرفع عند إغلاق فترة مالية"""
    fiscal_year_id: FiscalYearId
    period_reference: FiscalPeriodReference
    closed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fiscal.period.closed"


@dataclass(frozen=True)
class PeriodOpenedEvent(BaseDomainEvent):
    """يُرفع عند فتح فترة مالية"""
    fiscal_year_id: FiscalYearId
    period_reference: FiscalPeriodReference
    opened_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fiscal.period.opened"