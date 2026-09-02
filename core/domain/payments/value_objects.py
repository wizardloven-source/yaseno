# core/domain/payments/value_objects.py
"""
Value Objects for Payments Domain
كائنات القيمة لنظام الدفع والقبض
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from decimal import Decimal


class PaymentType(str, Enum):
    """نوع العملية المالية"""
    RECEIVE = "receive"  # قبض - استلام مبلغ
    PAY = "pay"          # دفع - صرف مبلغ
    TRANSFER = "transfer"  # تحويل بين الحسابات


class PaymentMethod(str, Enum):
    """طريقة الدفع"""
    CASH = "cash"
    CHECK = "check"
    TRANSFER = "transfer"
    CREDIT = "credit"
    CARD = "card"


class PaymentStatus(str, Enum):
    """حالة الدفع"""
    DRAFT = "draft"          # مسودة
    PENDING = "pending"      # قيد الانتظار
    APPROVED = "approved"    # معتمد
    COMPLETED = "completed"  # مكتمل
    REJECTED = "rejected"    # مرفوض
    CANCELLED = "cancelled"  # ملغي

    @classmethod
    def get_display_name(cls, status: str) -> str:
        """الحصول على الاسم المعروض للحالة"""
        from core.i18n.translator import tr
        mapping = {
            cls.DRAFT.value: "status.draft",
            cls.PENDING.value: "status.pending",
            cls.APPROVED.value: "status.approved",
            cls.COMPLETED.value: "status.completed",
            cls.REJECTED.value: "status.rejected",
            cls.CANCELLED.value: "status.cancelled",
        }
        return tr(mapping.get(status, status))

    @classmethod
    def get_color(cls, status: str) -> str:
        """الحصول على لون الحالة"""
        colors = {
            cls.DRAFT.value: "#FF9800",
            cls.PENDING.value: "#2196F3",
            cls.APPROVED.value: "#4CAF50",
            cls.COMPLETED.value: "#2E7D32",
            cls.REJECTED.value: "#F44336",
            cls.CANCELLED.value: "#9E9E9E",
        }
        return colors.get(status, "#666666")

    @classmethod
    def get_icon(cls, status: str) -> str:
        """الحصول على أيقونة الحالة"""
        icons = {
            cls.DRAFT.value: "📝",
            cls.PENDING.value: "⏳",
            cls.APPROVED.value: "✅",
            cls.COMPLETED.value: "✓",
            cls.REJECTED.value: "❌",
            cls.CANCELLED.value: "⛔",
        }
        return icons.get(status, "📋")

    def can_transition_to(self, new_status: 'PaymentStatus') -> bool:
        """التحقق من إمكانية الانتقال إلى حالة جديدة"""
        transitions = {
            PaymentStatus.DRAFT: {
                PaymentStatus.PENDING,
                PaymentStatus.CANCELLED,
            },
            PaymentStatus.PENDING: {
                PaymentStatus.APPROVED,
                PaymentStatus.REJECTED,
                PaymentStatus.CANCELLED,
            },
            PaymentStatus.APPROVED: {
                PaymentStatus.COMPLETED,
                PaymentStatus.CANCELLED,
            },
            PaymentStatus.COMPLETED: set(),
            PaymentStatus.REJECTED: {
                PaymentStatus.DRAFT,
            },
            PaymentStatus.CANCELLED: {
                PaymentStatus.DRAFT,
            },
        }
        return new_status in transitions.get(self, set())


@dataclass(frozen=True)
class PaymentId:
    """معرف الدفع الفريد"""
    value: UUID

    def __post_init__(self):
        if isinstance(self.value, str):
            object.__setattr__(self, 'value', UUID(self.value))
        elif not isinstance(self.value, UUID):
            raise ValueError("PaymentId must be UUID or UUID string")

    @classmethod
    def generate(cls) -> 'PaymentId':
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> 'PaymentId':
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PaymentCode:
    """كود الدفع"""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Payment code cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PaymentReference:
    """مرجع الدفع (فاتورة، أمر شراء، إلخ)"""
    reference_type: str  # invoice, purchase_order, journal_entry, etc.
    reference_id: str

    def __str__(self) -> str:
        return f"{self.reference_type}:{self.reference_id}"


@dataclass(frozen=True)
class Money:
    """قيمة نقدية مع العملة"""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if not self.currency or not isinstance(self.currency, str):
            raise ValueError("Currency must be a non-empty string")

    @classmethod
    def zero(cls, currency: str = "USD") -> 'Money':
        return cls(Decimal('0'), currency)

    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        if self.amount < other.amount:
            raise ValueError(f"Insufficient amount: {self.amount} < {other.amount}")
        return Money(self.amount - other.amount, self.currency)

    def is_zero(self) -> bool:
        return self.amount == 0

    def format(self) -> str:
        """تنسيق المبلغ للعرض"""
        if self.currency == "LBP":
            return f"{self.amount:,.0f} {self.currency}"
        return f"{self.amount:,.2f} {self.currency}"