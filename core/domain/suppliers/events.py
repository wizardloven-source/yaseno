# core/domain/suppliers/events.py
"""Domain Events for Suppliers Context"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import SupplierId, SupplierCode, SupplierStatus


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SupplierCreatedEvent(BaseDomainEvent):
    supplier_id: SupplierId
    supplier_code: SupplierCode
    supplier_name: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "suppliers.supplier.created"


@dataclass(frozen=True)
class SupplierUpdatedEvent(BaseDomainEvent):
    supplier_id: SupplierId
    supplier_code: SupplierCode
    supplier_name: str
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "suppliers.supplier.updated"


@dataclass(frozen=True)
class SupplierDeletedEvent(BaseDomainEvent):
    supplier_id: SupplierId
    supplier_code: SupplierCode
    supplier_name: str
    deleted_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "suppliers.supplier.deleted"