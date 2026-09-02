# core/domain/inventory/events.py
"""
Inventory Events - أحداث المخزون
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from decimal import Decimal

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import (
    StockMovementId,
    StockBatchId,
    StockTransferId,
    EntityId,
    StockMovementType,
    BatchNumber,
    SerialNumber,
    ExpiryDate,
    StockLocation,
    Money,
)


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# أحداث حركات المخزون
# =============================================================================

@dataclass(frozen=True)
class StockMovementCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء حركة مخزون جديدة"""
    movement_id: StockMovementId
    entity: EntityId
    movement_type: StockMovementType
    quantity: Decimal
    unit_cost: Money
    total_cost: Money
    reference_type: str
    reference_id: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.movement.created"


@dataclass(frozen=True)
class StockMovementDeletedEvent(BaseDomainEvent):
    """يُرفع عند حذف حركة مخزون"""
    movement_id: StockMovementId
    entity: EntityId
    deleted_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.movement.deleted"


# =============================================================================
# أحداث دفعات المخزون
# =============================================================================

@dataclass(frozen=True)
class StockBatchCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء دفعة مخزون جديدة"""
    batch_id: StockBatchId
    entity: EntityId
    batch_number: BatchNumber
    initial_quantity: Decimal
    unit_cost: Money
    total_cost: Money
    expiry_date: Optional[ExpiryDate] = None
    created_by: str = ""
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.batch.created"


@dataclass(frozen=True)
class StockBatchConsumedEvent(BaseDomainEvent):
    """يُرفع عند استهلاك جزء من دفعة مخزون"""
    batch_id: StockBatchId
    entity: EntityId
    batch_number: BatchNumber
    consumed_quantity: Decimal
    remaining_quantity: Decimal
    reference_type: str
    reference_id: str
    consumed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.batch.consumed"


@dataclass(frozen=True)
class StockBatchExpiredEvent(BaseDomainEvent):
    """يُرفع عند انتهاء صلاحية دفعة مخزون"""
    batch_id: StockBatchId
    entity: EntityId
    batch_number: BatchNumber
    expired_quantity: Decimal
    expiry_date: ExpiryDate
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.batch.expired"


# =============================================================================
# أحداث تحويلات المخزون
# =============================================================================

@dataclass(frozen=True)
class StockTransferCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء عملية تحويل مخزون"""
    transfer_id: StockTransferId
    entity: EntityId
    quantity: Decimal
    from_location: StockLocation
    to_location: StockLocation
    reference_id: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.transfer.created"


@dataclass(frozen=True)
class StockTransferCompletedEvent(BaseDomainEvent):
    """يُرفع عند إكمال عملية تحويل المخزون"""
    transfer_id: StockTransferId
    entity: EntityId
    quantity: Decimal
    from_location: StockLocation
    to_location: StockLocation
    completed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.transfer.completed"


# =============================================================================
# أحداث التنبيهات
# =============================================================================

@dataclass(frozen=True)
class LowStockAlertEvent(BaseDomainEvent):
    """يُرفع عند انخفاض المخزون عن الحد المحدد"""
    entity: EntityId
    current_quantity: Decimal
    threshold: Decimal
    location: Optional[StockLocation] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.alert.low_stock"


@dataclass(frozen=True)
class ExpiryAlertEvent(BaseDomainEvent):
    """يُرفع عند اقتراب انتهاء صلاحية المخزون"""
    entity: EntityId
    batch_number: BatchNumber
    expiry_date: ExpiryDate
    quantity: Decimal
    days_remaining: int
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.alert.expiry"


@dataclass(frozen=True)
class StockOutEvent(BaseDomainEvent):
    """يُرفع عند نفاد المخزون"""
    entity: EntityId
    location: Optional[StockLocation] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "inventory.alert.stock_out"


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "StockMovementCreatedEvent",
    "StockMovementDeletedEvent",
    "StockBatchCreatedEvent",
    "StockBatchConsumedEvent",
    "StockBatchExpiredEvent",
    "StockTransferCreatedEvent",
    "StockTransferCompletedEvent",
    "LowStockAlertEvent",
    "ExpiryAlertEvent",
    "StockOutEvent",
]