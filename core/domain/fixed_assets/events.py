# core/domain/fixed_assets/events.py
"""
Fixed Assets Events - أحداث مجال الأصول الثابتة
الإصدار: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import AssetId, AssetCode, DepreciationMethod


def _aware_utc_now() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class AssetCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء أصل ثابت جديد"""
    asset_id: AssetId
    asset_code: AssetCode
    asset_name: str
    acquisition_cost: Decimal
    acquisition_date: date
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fixed_assets.asset.created"


@dataclass(frozen=True)
class AssetUpdatedEvent(BaseDomainEvent):
    """يُرفع عند تحديث بيانات الأصل"""
    asset_id: AssetId
    asset_code: AssetCode
    asset_name: str
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fixed_assets.asset.updated"


@dataclass(frozen=True)
class DepreciationPostedEvent(BaseDomainEvent):
    """يُرفع عند ترحيل إهلاك فترة"""
    asset_id: AssetId
    asset_code: AssetCode
    asset_name: str
    period: int
    depreciation_amount: Decimal
    accumulated_depreciation: Decimal
    net_book_value: Decimal
    journal_entry_id: str
    posted_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fixed_assets.depreciation.posted"


@dataclass(frozen=True)
class AssetDisposedEvent(BaseDomainEvent):
    """يُرفع عند التصرف في الأصل"""
    asset_id: AssetId
    asset_code: AssetCode
    asset_name: str
    disposal_method: str
    disposal_date: date
    sale_amount: Optional[Decimal]
    gain_loss_amount: Optional[Decimal]
    disposed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fixed_assets.asset.disposed"


@dataclass(frozen=True)
class AssetFullyDepreciatedEvent(BaseDomainEvent):
    """يُرفع عند اكتمال إهلاك الأصل"""
    asset_id: AssetId
    asset_code: AssetCode
    asset_name: str
    net_book_value: Decimal
    total_depreciation: Decimal
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "fixed_assets.asset.fully_depreciated"


__all__ = [
    'AssetCreatedEvent',
    'AssetUpdatedEvent',
    'DepreciationPostedEvent',
    'AssetDisposedEvent',
    'AssetFullyDepreciatedEvent',
]