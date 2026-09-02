# core/domain/funds/value_objects.py
"""
Value Objects for Funds Domain - Professional Edition
العملات ديناميكية من نظام العملات
"""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4
from decimal import Decimal
from typing import Optional, Set, Callable
from datetime import datetime, timezone, timedelta


# =============================================================================
# Enums
# =============================================================================

class FundType(str, Enum):
    """نوع الصندوق"""
    MAIN = "main"
    PROJECT = "project"
    RESERVE = "reserve"
    CLEARING = "clearing"


class TransactionType(str, Enum):
    """نوع حركة الصندوق - Source of Truth"""
    # Inflows (تزيد الرصيد)
    OPENING_BALANCE = "opening_balance"
    DEPOSIT = "deposit"
    TRANSFER_IN = "transfer_in"
    COLLECTION = "collection"
    
    # Outflows (تنقص الرصيد)
    WITHDRAWAL = "withdrawal"
    TRANSFER_OUT = "transfer_out"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    
    @property
    def is_inflow(self) -> bool:
        return self in [
            TransactionType.OPENING_BALANCE,
            TransactionType.DEPOSIT,
            TransactionType.TRANSFER_IN,
            TransactionType.COLLECTION
        ]
    
    @property
    def is_outflow(self) -> bool:
        return not self.is_inflow


class TransferStatus(str, Enum):
    """حالة التحويل"""
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FundStatus(str, Enum):
    """حالة الصندوق"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    
    @property
    def can_transact(self) -> bool:
        return self == FundStatus.ACTIVE


# =============================================================================
# Identifiers
# =============================================================================

@dataclass(frozen=True)
class FundId:
    value: UUID
    
    def __post_init__(self):
        if isinstance(self.value, str):
            object.__setattr__(self, 'value', UUID(self.value))
        elif not isinstance(self.value, UUID):
            raise ValueError(f"FundId must be UUID, got {type(self.value)}")
    
    @classmethod
    def generate(cls) -> 'FundId':
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> 'FundId':
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class FundCode:
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Fund code cannot be empty")
        
        cleaned = self.value.strip().upper()
        
        import re
        if not re.match(r'^[A-Z0-9\-_]+$', cleaned):
            raise ValueError(f"Invalid fund code format: {self.value}")
        
        object.__setattr__(self, 'value', cleaned)
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TransactionId:
    value: str
    
    @classmethod
    def generate(cls) -> 'TransactionId':
        return cls(str(uuid4()))
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TransferId:
    value: str
    
    @classmethod
    def generate(cls) -> 'TransferId':
        return cls(str(uuid4()))
    
    def __str__(self) -> str:
        return self.value


# =============================================================================
# Money - بدون قائمة عملات ثابتة
# =============================================================================

@dataclass(frozen=True)
class Money:
    """
    كائن القيمة النقدية - العملات تُتحقق من نظام العملات الخارجي
    """
    amount: Decimal
    currency: str  # كود العملة (مثل USD, EUR, LBP, GBP, ...)
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError(f"Money amount cannot be negative: {self.amount}")
        
        # لا نتحقق من العملة هنا - سيتم التحقق في طبقة الـ Application
        # أو عبر خدمة العملات قبل إنشاء الكائن
        
        # تقريب حسب نوع العملة (يتم تحديده من إعدادات العملة)
        # هذا التقريب مؤقت، سيتم استبداله بقيم من قاعدة البيانات
        if self.currency == "LBP":
            rounded = self.amount.quantize(Decimal('1'))
        else:
            rounded = self.amount.quantize(Decimal('0.01'))
        
        object.__setattr__(self, 'amount', rounded)
    
    @classmethod
    def zero(cls, currency: str = "USD") -> 'Money':
        """إنشاء مبلغ صفر"""
        return cls(Decimal('0'), currency)
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        if self.amount < other.amount:
            raise ValueError(f"Insufficient funds: {self.amount} < {other.amount}")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, multiplier: Decimal) -> 'Money':
        return Money(self.amount * multiplier, self.currency)
    
    def __truediv__(self, divisor: Decimal) -> 'Money':
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Money(self.amount / divisor, self.currency)
    
    def is_zero(self) -> bool:
        return self.amount == 0
    
    def to_decimal(self) -> Decimal:
        return self.amount


# =============================================================================
# Currency Validator - يتم حقنه من Service Layer
# =============================================================================

class CurrencyValidator:
    """
    مدقق العملات - يتم حقنه من طبقة الـ Infrastructure
    يتحقق من صحة العملات مقابل قاعدة البيانات
    """
    
    _validate_func: Optional[Callable[[str], bool]] = None
    _get_decimal_places_func: Optional[Callable[[str], int]] = None
    
    @classmethod
    def set_validator(cls, validate_func: Callable[[str], bool]) -> None:
        """تعيين دالة التحقق من صحة العملة (من CurrencyService)"""
        cls._validate_func = validate_func
    
    @classmethod
    def set_decimal_places_func(cls, func: Callable[[str], int]) -> None:
        """تعيين دالة الحصول على عدد الخانات العشرية (من CurrencyService)"""
        cls._decimal_places_func = func
    
    @classmethod
    def is_valid(cls, currency_code: str) -> bool:
        """التحقق من صحة العملة"""
        if cls._validate_func:
            return cls._validate_func(currency_code)
        # Fallback آمن - إذا لم يتم تعيين المدقق، نسمح بكل العملات
        # ولكن هذا لن يحدث في الإنتاج لأننا سنعينه عند بدء التشغيل
        return True
    
    @classmethod
    def get_decimal_places(cls, currency_code: str) -> int:
        """الحصول على عدد الخانات العشرية للعملة"""
        if cls._decimal_places_func:
            return cls._decimal_places_func(currency_code)
        # Fallback: USD و EUR منزلتين، LBP بدون منازل
        if currency_code == "LBP":
            return 0
        return 2


# =============================================================================
# Exchange Rate - مع التحقق الديناميكي
# =============================================================================

@dataclass(frozen=True)
class ExchangeRate:
    """سعر الصرف بين عملتين"""
    from_currency: str
    to_currency: str
    rate: Decimal
    
    def __post_init__(self):
        if self.from_currency == self.to_currency:
            raise ValueError("Cannot set exchange rate for same currency")
        if self.rate <= 0:
            raise ValueError(f"Exchange rate must be positive, got {self.rate}")
    
    def convert(self, amount: Money) -> Money:
        """تحويل مبلغ من from_currency إلى to_currency"""
        if amount.currency != self.from_currency:
            raise ValueError(f"Cannot convert {amount.currency} using rate from {self.from_currency}")
        converted_amount = amount.amount * self.rate
        return Money(converted_amount, self.to_currency)
    
    def inverse(self) -> 'ExchangeRate':
        """الحصول على السعر العكسي"""
        return ExchangeRate(
            from_currency=self.to_currency,
            to_currency=self.from_currency,
            rate=Decimal('1') / self.rate
        )


# =============================================================================
# Fund Limits
# =============================================================================

@dataclass(frozen=True)
class FundLimits:
    """حدود الصندوق"""
    daily_limit: Money
    monthly_limit: Money
    min_balance_alert: Money
    max_balance_alert: Money
    
    @classmethod
    def default(cls, currency: str = "USD") -> 'FundLimits':
        """الحدود الافتراضية (صفر = غير محدود)"""
        return cls(
            daily_limit=Money.zero(currency),
            monthly_limit=Money.zero(currency),
            min_balance_alert=Money.zero(currency),
            max_balance_alert=Money.zero(currency)
        )
    
    def is_withdrawal_within_daily_limit(self, amount: Money, today_withdrawn: Money) -> bool:
        if self.daily_limit.is_zero():
            return True
        return (today_withdrawn + amount).amount <= self.daily_limit.amount
    
    def is_withdrawal_within_monthly_limit(self, amount: Money, month_withdrawn: Money) -> bool:
        if self.monthly_limit.is_zero():
            return True
        return (month_withdrawn + amount).amount <= self.monthly_limit.amount


# =============================================================================
# Date Range
# =============================================================================

@dataclass(frozen=True)
class DateRange:
    """نطاق زمني"""
    start_date: datetime
    end_date: datetime
    
    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")
    
    def contains(self, dt: datetime) -> bool:
        return self.start_date <= dt <= self.end_date


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "FundType",
    "TransactionType",
    "TransferStatus",
    "FundStatus",
    # Identifiers
    "FundId",
    "FundCode",
    "TransactionId",
    "TransferId",
    # Money
    "Money",
    "CurrencyValidator",
    # Exchange Rate
    "ExchangeRate",
    # Limits
    "FundLimits",
    # Date Range
    "DateRange",
]