# core/domain/funds/events.py
"""
Domain Events for Funds Context
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import FundId, FundCode, FundType


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class FundCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء صندوق جديد"""
    fund_id: FundId
    fund_code: FundCode
    fund_name: str
    fund_type: FundType
    account_code: str
    currency: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.fund.created"


@dataclass(frozen=True)
class FundUpdatedEvent(BaseDomainEvent):
    """يُرفع عند تحديث بيانات الصندوق"""
    fund_id: FundId
    fund_code: FundCode
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.fund.updated"


@dataclass(frozen=True)
class FundDeletedEvent(BaseDomainEvent):
    """يُرفع عند حذف/تعطيل صندوق"""
    fund_id: FundId
    fund_code: FundCode
    fund_name: str
    deleted_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.fund.deleted"


@dataclass(frozen=True)
class FundBalanceChangedEvent(BaseDomainEvent):
    """يُرفع عند تغيير رصيد الصندوق"""
    fund_code: str
    old_balance: float
    new_balance: float
    currency: str
    changed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.balance.changed"


@dataclass(frozen=True)
class FundTransferCompletedEvent(BaseDomainEvent):
    """يُرفع عند اكتمال تحويل بين الصناديق"""
    transfer_id: str
    from_fund: str
    to_fund: str
    amount: float
    from_currency: str
    to_currency: str
    exchange_rate: float
    converted_amount: float
    journal_entry_id: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.transfer.completed"


@dataclass(frozen=True)
class FundTransactionCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء حركة صندوق جديدة"""
    fund_code: str
    transaction_id: str
    transaction_type: str
    amount: float
    currency: str
    balance_before: float
    balance_after: float
    reference_id: Optional[str]
    description: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.transaction.created"


@dataclass(frozen=True)
class FundStatusChangedEvent(BaseDomainEvent):
    """يُرفع عند تغيير حالة الصندوق"""
    fund_id: FundId
    fund_code: FundCode
    old_status: str
    new_status: str
    changed_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.status.changed"


@dataclass(frozen=True)
class FundMovementCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء حركة صندوق جديدة (للتوافق مع الكود القديم)"""
    movement_data: Dict[str, Any]
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.movement.created"


@dataclass(frozen=True)
class FundMovementDeletedEvent(BaseDomainEvent):
    """يُرفع عند حذف حركة صندوق"""
    movement_id: str
    fund_code: str
    deleted_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "funds.movement.deleted"