# core/domain/shared/value_objects.py
"""
VALUE OBJECTS - مشترك بين جميع الـ Bounded Contexts
✅ مصحح: دعم أي عملة يضيفها المستخدم (بدون قائمة محددة مسبقاً)
✅ مصحح: دعم عدد المنازل العشرية حسب العملة
✅ مصحح: تقريب مصرفي صحيح (ROUND_HALF_UP)
✅ مصحح: دعم العملات التي لا تستخدم كسور عشرية (LBP, JPY, KRW)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import ClassVar, Set, Optional, Any, Dict, Callable
from uuid import UUID, uuid4
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# إعدادات العملات (قابلة للحقن من Service Layer)
# =============================================================================

class CurrencySettings:
    """
    إعدادات العملات - يتم حقنها من طبقة الـ Infrastructure
    """
    _decimal_places_func: Optional[Callable[[str], int]] = None
    _is_active_func: Optional[Callable[[str], bool]] = None
    
    @classmethod
    def set_decimal_places_func(cls, func: Callable[[str], int]) -> None:
        """تعيين دالة للحصول على عدد المنازل العشرية من قاعدة البيانات"""
        cls._decimal_places_func = func
    
    @classmethod
    def set_is_active_func(cls, func: Callable[[str], bool]) -> None:
        """تعيين دالة للتحقق من نشاط العملة"""
        cls._is_active_func = func
    
    @classmethod
    def get_decimal_places(cls, currency_code: str) -> int:
        """الحصول على عدد المنازل العشرية للعملة"""
        if cls._decimal_places_func:
            try:
                return cls._decimal_places_func(currency_code)
            except Exception as e:
                logger.warning(f"Error getting decimal places for {currency_code}: {e}")
        
        # Fallback: تحديد افتراضي حسب العملة
        return cls._get_default_decimal_places(currency_code)
    
    @classmethod
    def _get_default_decimal_places(cls, currency_code: str) -> int:
        """الحصول على عدد المنازل العشرية الافتراضي"""
        # العملات التي لا تستخدم كسور عشرية
        zero_decimal_currencies = {
            'LBP', 'JPY', 'KRW', 'VND', 'IDR', 'CLP', 'COP', 'ISK',
            'CVE', 'DJF', 'GNF', 'KMF', 'MGA', 'PYG', 'RWF', 'UGX',
            'VUV', 'XAF', 'XOF', 'XPF'
        }
        if currency_code.upper() in zero_decimal_currencies:
            return 0
        return 2


# ========== ACCOUNT CODE ==========

@dataclass(frozen=True)
class AccountCode:
    """كود الحساب الموحد المستخدم عبر جميع موديولات النظام."""
    code: str

    def __post_init__(self):
        if not self.code or len(str(self.code).strip()) < 3:
            raise ValueError(f"Accounting Violation: Invalid Account Code '{self.code}'. Must be at least 3 chars.")
        # تنظيف الكود - إزالة المسافات الزائدة
        cleaned = str(self.code).strip()
        # التأكد من أن الكود لا يحتوي على مسافات
        if ' ' in cleaned:
            raise ValueError(f"Account code cannot contain spaces: '{self.code}'")
        object.__setattr__(self, 'code', cleaned)

    def __str__(self) -> str:
        return self.code


# ========== MONEY ==========

@dataclass(frozen=True)
class Money:
    """
    القيمة النقدية مع العملة - النسخة الموحدة للنظام بأكمله.
    
    ✅ يدعم أي عملة يضيفها المستخدم
    ✅ يدعم عدد المنازل العشرية حسب العملة
    ✅ تقريب مصرفي صحيح (ROUND_HALF_UP)
    ✅ يدعم العملات التي لا تستخدم كسور عشرية (LBP, JPY)
    
    Attributes:
        amount: المبلغ كـ Decimal
        currency: كود العملة (3 أحرف)
    """
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        # 1. تحويل المبلغ إلى Decimal إذا لزم الأمر
        if not isinstance(self.amount, Decimal):
            if isinstance(self.amount, (int, float)):
                object.__setattr__(self, 'amount', Decimal(str(self.amount)))
            else:
                raise ValueError(f"Amount must be Decimal, got: {type(self.amount)}")
        
        # 2. التحقق من العملة
        if not self.currency or not isinstance(self.currency, str):
            raise ValueError(f"Currency must be a non-empty string, got: {self.currency}")
        
        # تنظيف العملة - تحويل إلى أحرف كبيرة وإزالة المسافات
        cleaned_currency = self.currency.strip().upper()
        if len(cleaned_currency) != 3:
            raise ValueError(f"Currency must be a 3-letter code, got: '{self.currency}'")
        object.__setattr__(self, 'currency', cleaned_currency)
        
        # 3. تقريب المبلغ حسب العملة
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            rounding = Decimal('1')
        else:
            rounding = Decimal('0.' + '0' * decimal_places)
        
        rounded = self.amount.quantize(rounding, rounding=ROUND_HALF_UP)
        object.__setattr__(self, 'amount', rounded)
    
    @classmethod
    def zero(cls, currency: str = "USD") -> 'Money':
        """إنشاء مبلغ صفر"""
        return cls(Decimal('0'), currency)
    
    @classmethod
    def from_float(cls, amount: float, currency: str = "USD") -> 'Money':
        """إنشاء Money من float"""
        return cls(Decimal(str(amount)), currency)
    
    def __add__(self, other: 'Money') -> 'Money':
        if other is None:
            return self
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __radd__(self, other) -> 'Money':
        """دعم عملية الجمع من اليمين (مثل sum([Money...]))"""
        if other is None or other == 0:
            return self
        if isinstance(other, Money):
            return self.__add__(other)
        raise TypeError(f"Cannot add Money and {type(other)}")
    
    def __sub__(self, other: 'Money') -> 'Money':
        if other is None:
            return self
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, multiplier: Decimal) -> 'Money':
        if not isinstance(multiplier, Decimal):
            multiplier = Decimal(str(multiplier))
        return Money(self.amount * multiplier, self.currency)
    
    def __rmul__(self, multiplier) -> 'Money':
        """دعم الضرب من اليمين (مثل 2 * Money(...))"""
        return self.__mul__(multiplier)
    
    def __truediv__(self, divisor: Decimal) -> 'Money':
        if not isinstance(divisor, Decimal):
            divisor = Decimal(str(divisor))
        if divisor == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return Money(self.amount / divisor, self.currency)
    
    def __neg__(self) -> 'Money':
        """النفي (مثل -Money(...))"""
        return Money(-self.amount, self.currency)
    
    def __abs__(self) -> 'Money':
        """القيمة المطلقة"""
        return Money(abs(self.amount), self.currency)
    
    def __lt__(self, other: 'Money') -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount < other.amount
    
    def __le__(self, other: 'Money') -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount <= other.amount
    
    def __gt__(self, other: 'Money') -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount > other.amount
    
    def __ge__(self, other: 'Money') -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount >= other.amount
    
    def __eq__(self, other) -> bool:
        if other is None:
            return False
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency
    
    def __hash__(self) -> int:
        return hash((self.amount, self.currency))
    
    def __str__(self) -> str:
        """تمثيل نصي للمبلغ"""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.currency} {self.amount:,.0f}"
        return f"{self.currency} {self.amount:,.{decimal_places}f}"
    
    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency='{self.currency}')"
    
    def is_zero(self) -> bool:
        """التحقق مما إذا كان المبلغ صفراً"""
        return self.amount == 0
    
    def is_positive(self) -> bool:
        """التحقق مما إذا كان المبلغ موجباً"""
        return self.amount > 0
    
    def is_negative(self) -> bool:
        """التحقق مما إذا كان المبلغ سالباً"""
        return self.amount < 0
    
    def to_decimal(self) -> Decimal:
        """استخراج المبلغ كـ Decimal"""
        return self.amount
    
    def format(self, include_currency: bool = True) -> str:
        """
        تنسيق المبلغ للعرض
        
        Args:
            include_currency: تضمين رمز العملة
        
        Returns:
            str: المبلغ المنسق
        """
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            formatted = f"{self.amount:,.0f}"
        else:
            formatted = f"{self.amount:,.{decimal_places}f}"
        
        if include_currency:
            return f"{formatted} {self.currency}"
        return formatted
    
    def get_symbol(self) -> str:
        """الحصول على رمز العملة"""
        symbols = {
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'JPY': '¥',
            'CAD': 'C$',
            'AUD': 'A$',
            'CHF': 'Fr',
            'CNY': '¥',
            'INR': '₹',
            'BRL': 'R$',
            'LBP': 'ل.ل',
            'LSP': 'ل.س',
            'SAR': 'ر.س',
            'AED': 'د.إ',
            'EGP': 'ج.م',
            'JOD': 'د.أ',
            'KWD': 'د.ك',
            'QAR': 'ر.ق',
            'BHD': 'د.ب',
            'OMR': 'ر.ع',
            'TRY': '₺',
            'RUB': '₽',
            'MXN': '$',
            'SGD': 'S$',
            'NZD': 'NZ$',
            'ZAR': 'R',
            'SEK': 'kr',
            'NOK': 'kr',
            'DKK': 'kr',
            'PLN': 'zł',
            'HUF': 'Ft',
            'CZK': 'Kč',
            'ILS': '₪',
            'AED': 'د.إ',
        }
        return symbols.get(self.currency, self.currency)
    
    def get_decimal_places(self) -> int:
        """الحصول على عدد المنازل العشرية لهذه العملة"""
        return CurrencySettings.get_decimal_places(self.currency)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتسلسل"""
        return {
            'amount': float(self.amount),
            'currency': self.currency,
            'formatted': self.format(),
            'symbol': self.get_symbol(),
        }


# ========== TIMESTAMP ==========

@dataclass(frozen=True)
class Timestamp:
    """طابع زمني مع دعم UTC"""
    value: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        # التأكد من أن الوقت واعي بالمنطقة الزمنية
        if self.value.tzinfo is None:
            object.__setattr__(self, 'value', self.value.replace(tzinfo=timezone.utc))
    
    def __str__(self) -> str:
        return self.value.isoformat()
    
    @classmethod
    def now(cls) -> 'Timestamp':
        return cls(datetime.now(timezone.utc))
    
    def to_datetime(self) -> datetime:
        """استخراج كائن datetime"""
        return self.value


# ========== QUANTITY ==========

@dataclass(frozen=True)
class Quantity:
    """الكمية - عدد صحيح غير سالب"""
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Quantity cannot be negative")
        if not isinstance(self.value, int):
            raise ValueError("Quantity must be an integer")
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __add__(self, other: 'Quantity') -> 'Quantity':
        return Quantity(self.value + other.value)
    
    def __sub__(self, other: 'Quantity') -> 'Quantity':
        if self.value < other.value:
            raise ValueError("Cannot subtract larger quantity from smaller")
        return Quantity(self.value - other.value)


# ========== ID VALUE OBJECTS ==========

@dataclass(frozen=True)
class EntityId:
    """معرف الكيان - UUID مع نوع الكيان اختياري

    يدعم صيغتين:
        EntityId("product", "uuid")  # entity_type + value
        EntityId("uuid")             # entity_type = "product" افتراضياً
    """
    entity_type: str = "product"
    value: UUID = None

    def __init__(self, *args):
        if len(args) == 1:
            entity_type, value = "product", args[0]
        elif len(args) == 2:
            entity_type, value = args
        else:
            raise TypeError(
                f"EntityId expects 1 or 2 positional arguments, got {len(args)}"
            )
        object.__setattr__(self, 'entity_type', entity_type or "product")
        if not isinstance(value, UUID):
            if isinstance(value, str):
                try:
                    value = UUID(value)
                except ValueError:
                    raise ValueError(f"Invalid UUID string: {value}")
            else:
                raise ValueError("ID must be UUID or UUID string")
        object.__setattr__(self, 'value', value)

    @property
    def entity_id(self) -> str:
        """معرف الكيان كنص (للتوافق مع أعمدة VARCHAR في قاعدة البيانات)"""
        return str(self.value)

    @classmethod
    def generate(cls) -> 'EntityId':
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> 'EntityId':
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __eq__(self, other) -> bool:
        if other is None:
            return False
        if not isinstance(other, EntityId):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)


# ========== DEBIT AND CREDIT ==========

@dataclass(frozen=True)
class Debit:
    """قيد مدين"""
    amount: Money
    
    def __str__(self) -> str:
        return f"Debit({self.amount})"
    
    @property
    def value(self) -> Money:
        return self.amount


@dataclass(frozen=True)
class Credit:
    """قيد دائن"""
    amount: Money
    
    def __str__(self) -> str:
        return f"Credit({self.amount})"
    
    @property
    def value(self) -> Money:
        return self.amount


# ========== TRANSACTION DATE ==========

@dataclass(frozen=True)
class TransactionDate:
    """تاريخ المعاملة مع دعم UTC"""
    value: datetime
    
    def __post_init__(self):
        if self.value.tzinfo is None:
            object.__setattr__(self, 'value', self.value.replace(tzinfo=timezone.utc))
    
    @classmethod
    def now(cls) -> 'TransactionDate':
        return cls(datetime.now(timezone.utc))
    
    def __str__(self) -> str:
        return self.value.isoformat()
    
    def to_datetime(self) -> datetime:
        return self.value
    
    def to_date(self) -> date:
        return self.value.date()


# ========== USER ID ==========

@dataclass(frozen=True)
class UserId:
    """معرف المستخدم"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("User ID cannot be empty")
        object.__setattr__(self, 'value', self.value.strip())
    
    def __str__(self) -> str:
        return self.value


# ========== DOMAIN EVENT BASE ==========

class BaseDomainEvent:
    """
    الفئة الأساسية لجميع أحداث المجال
    
    ملاحظة: هذه الفئة ليست dataclass للسماح بالمرونة في تعريف الأحداث
    """
    
    def __init__(self, **kwargs):
        """تهيئة الحدث مع السماح بتعيين الخصائص"""
        for key, value in kwargs.items():
            super().__setattr__(key, value)
        if not hasattr(self, '_occurred_at'):
            super().__setattr__('_occurred_at', datetime.now(timezone.utc))
        if not hasattr(self, '_event_id'):
            super().__setattr__('_event_id', str(uuid4()))
    
    @property
    def event_id(self) -> str:
        """معرف فريد للحدث"""
        return getattr(self, '_event_id', str(uuid4()))
    
    @property
    def occurred_at(self) -> datetime:
        """وقت وقوع الحدث"""
        return getattr(self, '_occurred_at', datetime.now(timezone.utc))
    
    @occurred_at.setter
    def occurred_at(self, value: datetime):
        super().__setattr__('_occurred_at', value)
    
    def __setattr__(self, key, value):
        """السماح بتعيين أي خاصية"""
        super().__setattr__(key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الحدث إلى قاموس للتسلسل"""
        result = {
            "event_type": self.get_event_name(),
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
        }
        # إضافة الخصائص المخصصة
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, (Money, AccountCode)):
                    result[key] = str(value)
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    result[key] = str(value)
                else:
                    result[key] = value
        return result
    
    def get_event_name(self) -> str:
        """الحصول على اسم الحدث (يُورث في الفئات الفرعية)"""
        return self.__class__.__name__


# =============================================================================
# دوال مساعدة للاستخدام السريع
# =============================================================================

def zero_money(currency: str = "USD") -> Money:
    """دالة مساعدة لإنشاء مبلغ صفر"""
    return Money.zero(currency)


def sum_money(items, currency: str = "USD") -> Money:
    """
    جمع قائمة من Money
    
    Args:
        items: قائمة من Money أو أرقام
        currency: العملة الناتجة
    
    Returns:
        Money: المجموع
    """
    total = Decimal('0')
    for item in items:
        if isinstance(item, Money):
            if item.currency != currency:
                raise ValueError(f"Currency mismatch: {item.currency} != {currency}")
            total += item.amount
        elif isinstance(item, (int, float, Decimal)):
            total += Decimal(str(item))
        else:
            raise TypeError(f"Cannot sum {type(item)}")
    return Money(total, currency)


# =============================================================================
# تصدير جميع الكائنات
# =============================================================================

__all__ = [
    # Settings
    "CurrencySettings",
    
    # Core Value Objects
    "AccountCode",
    "Money",
    "Timestamp",
    "Quantity",
    "EntityId",
    "Debit",
    "Credit",
    "TransactionDate",
    "UserId",
    "BaseDomainEvent",
    
    # Helper Functions
    "zero_money",
    "sum_money",
]