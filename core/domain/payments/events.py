# core/domain/payments/events.py
"""
Domain Events for Payments Context
أحداث مجال الدفعات
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import PaymentId, PaymentCode, PaymentType, Money


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class PaymentCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء عملية دفع جديدة"""
    payment_id: PaymentId
    payment_code: PaymentCode
    payment_type: PaymentType
    amount: Money
    customer_id: Optional[str]
    customer_name: Optional[str]
    created_by: str
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "payments.payment.created"


@dataclass(frozen=True)
class PaymentUpdatedEvent(BaseDomainEvent):
    """يُرفع عند تحديث عملية دفع"""
    payment_id: PaymentId
    payment_code: PaymentCode
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "payments.payment.updated"


@dataclass(frozen=True)
class PaymentApprovedEvent(BaseDomainEvent):
    """يُرفع عند اعتماد عملية دفع"""
    payment_id: PaymentId
    payment_code: PaymentCode
    approved_by: str
    amount: Money
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "payments.payment.approved"


@dataclass(frozen=True)
class PaymentRejectedEvent(BaseDomainEvent):
    """يُرفع عند رفض عملية دفع"""
    payment_id: PaymentId
    payment_code: PaymentCode
    rejected_by: str
    reason: str = ""
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "payments.payment.rejected"


@dataclass(frozen=True)
class PaymentCompletedEvent(BaseDomainEvent):
    """يُرفع عند إكمال عملية دفع"""
    payment_id: PaymentId
    payment_code: PaymentCode
    completed_by: str
    amount: Money
    fund_id: Optional[str]
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "payments.payment.completed"


@dataclass(frozen=True)
class PaymentCancelledEvent(BaseDomainEvent):
    """يُرفع عند إلغاء عملية دفع"""
    payment_id: PaymentId
    payment_code: PaymentCode
    cancelled_by: str
    reason: str = ""
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "payments.payment.cancelled"