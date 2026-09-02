# core/domain/tax/value_objects.py
"""
Tax Value Objects - كائنات القيمة للضرائب
✅ يدعم: VAT, GST, Sales Tax, Excise, Customs, Withholding
✅ يدعم: Inclusive, Exclusive, Compound, Zero Rated, Exempt
✅ يدعم: الضرائب المتعددة والمركبة
✅ يدعم: العملات المتعددة
"""

from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
from datetime import date
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4


# =============================================================================
# Enums الرئيسية
# =============================================================================

class TaxType(str, Enum):
    """نوع الضريبة"""
    VAT = "vat"                  # ضريبة القيمة المضافة
    GST = "gst"                  # ضريبة السلع والخدمات
    SALES_TAX = "sales_tax"      # ضريبة المبيعات
    EXCISE = "excise"            # ضريبة المكوس
    CUSTOMS = "customs"          # ضريبة جمركية
    WITHHOLDING = "withholding"  # ضريبة الاستقطاع


class TaxCalculationType(str, Enum):
    """نوع حساب الضريبة"""
    INCLUSIVE = "inclusive"      # الضريبة شاملة في السعر
    EXCLUSIVE = "exclusive"      # الضريبة مضافة على السعر
    COMPOUND = "compound"        # ضريبة مركبة (تحسب على المبلغ + الضرائب الأخرى)
    ZERO_RATED = "zero_rated"    # نسبة صفر
    EXEMPT = "exempt"            # معفى


class TaxJurisdiction(str, Enum):
    """الجهة المختصة بالضريبة"""
    FEDERAL = "federal"          # اتحادية
    STATE = "state"              # ولاية/محافظة
    LOCAL = "local"              # محلية
    INTERNATIONAL = "international"  # دولية


class TaxApplicationScope(str, Enum):
    """نطاق تطبيق الضريبة"""
    ALL_PRODUCTS = "all_products"
    PRODUCT_CATEGORY = "product_category"
    SPECIFIC_PRODUCT = "specific_product"
    ALL_CUSTOMERS = "all_customers"
    CUSTOMER_GROUP = "customer_group"
    SPECIFIC_CUSTOMER = "specific_customer"
    REGION = "region"
    CUSTOM = "custom"


# =============================================================================
# Value Objects الأساسية
# =============================================================================

@dataclass(frozen=True)
class TaxId:
    """معرف الضريبة"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("TaxId cannot be empty")
        # إذا كان UUID، نحتفظ به كـ string
        try:
            UUID(self.value)
        except ValueError:
            pass  # قد يكون معرفاً مخصصاً

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> 'TaxId':
        return cls(str(uuid4()))

    @classmethod
    def from_string(cls, value: str) -> 'TaxId':
        return cls(value)


@dataclass(frozen=True)
class TaxCode:
    """كود الضريبة (فريد)"""
    value: str

    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("TaxCode cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TaxRate:
    """نسبة الضريبة"""
    rate: Decimal

    def __post_init__(self):
        if self.rate < 0:
            raise ValueError(f"Tax rate cannot be negative: {self.rate}")
        if self.rate > 100:
            raise ValueError(f"Tax rate cannot exceed 100: {self.rate}")

    def as_decimal(self) -> Decimal:
        """تحويل النسبة إلى رقم عشري (مثال: 15% → 0.15)"""
        return self.rate / Decimal('100')

    def apply_to(self, amount: Decimal) -> Decimal:
        """تطبيق الضريبة على مبلغ"""
        return amount * self.as_decimal()

    def apply_with_rounding(self, amount: Decimal, decimal_places: int = 2) -> Decimal:
        """تطبيق الضريبة مع تقريب"""
        result = self.apply_to(amount)
        return result.quantize(Decimal('0.01'))

    def __str__(self) -> str:
        return f"{self.rate}%"


@dataclass(frozen=True)
class TaxAmount:
    """مبلغ الضريبة مع العملة"""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError(f"Tax amount cannot be negative: {self.amount}")
        if not self.currency or len(self.currency) != 3:
            raise ValueError(f"Invalid currency: {self.currency}")

    def __add__(self, other: 'TaxAmount') -> 'TaxAmount':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return TaxAmount(self.amount + other.amount, self.currency)

    def __str__(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"


# =============================================================================
# TaxCalculationResult - نتيجة حساب الضريبة
# =============================================================================

@dataclass(frozen=True)
class TaxCalculationResult:
    """
    نتيجة حساب الضريبة - كائن غير قابل للتعديل
    
    يحتوي على:
        - المبلغ الخاضع للضريبة
        - إجمالي مبلغ الضريبة
        - تفصيل الضرائب (لكل قاعدة)
        - القواعد المطبقة
        - نوع الحساب
        - النسبة الفعلية
    """
    taxable_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    breakdown: Dict[str, Decimal] = field(default_factory=dict)
    applied_rules: List['TaxRule'] = field(default_factory=list)
    calculation_type: TaxCalculationType = TaxCalculationType.EXCLUSIVE
    effective_rate: Decimal = field(default_factory=lambda: Decimal('0'))

    def __post_init__(self):
        # حساب النسبة الفعلية
        if self.taxable_amount > 0:
            effective = (self.tax_amount / self.taxable_amount) * Decimal('100')
            object.__setattr__(self, 'effective_rate', effective)

    @property
    def tax_amount_formatted(self) -> str:
        return f"{self.tax_amount:,.2f}"

    @property
    def total_amount_formatted(self) -> str:
        return f"{self.total_amount:,.2f}"

    @property
    def is_zero(self) -> bool:
        return self.tax_amount == 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'taxable_amount': str(self.taxable_amount),
            'tax_amount': str(self.tax_amount),
            'total_amount': str(self.total_amount),
            'breakdown': {k: str(v) for k, v in self.breakdown.items()},
            'applied_rules': [str(r.id) for r in self.applied_rules],
            'calculation_type': self.calculation_type.value,
            'effective_rate': str(self.effective_rate)
        }

    def merge(self, other: 'TaxCalculationResult') -> 'TaxCalculationResult':
        """دمج نتيجتين حساب"""
        merged_breakdown = self.breakdown.copy()
        for key, value in other.breakdown.items():
            merged_breakdown[key] = merged_breakdown.get(key, Decimal('0')) + value

        return TaxCalculationResult(
            taxable_amount=self.taxable_amount + other.taxable_amount,
            tax_amount=self.tax_amount + other.tax_amount,
            total_amount=self.total_amount + other.total_amount,
            breakdown=merged_breakdown,
            applied_rules=self.applied_rules + other.applied_rules,
            calculation_type=self.calculation_type
        )


# =============================================================================
# TaxRuleSummary - ملخص القاعدة الضريبية
# =============================================================================

@dataclass(frozen=True)
class TaxRuleSummary:
    """ملخص قاعدة ضريبية - للقراءة السريعة"""
    id: str
    code: str
    name: str
    rate: Decimal
    tax_type: str
    is_active: bool
    is_default: bool
    valid_from: date
    valid_to: Optional[date]

    @property
    def rate_display(self) -> str:
        return f"{self.rate}%"

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        today = date.today()
        if self.valid_to and today > self.valid_to:
            return False
        return today >= self.valid_from

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'rate': str(self.rate),
            'tax_type': self.tax_type,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'valid_from': self.valid_from.isoformat(),
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'is_valid': self.is_valid
        }


# =============================================================================
# TaxContext - سياق حساب الضريبة
# =============================================================================

@dataclass
class TaxContext:
    """
    سياق حساب الضريبة - يحتوي على جميع المعلومات اللازمة لحساب الضريبة
    
    يستخدم هذا الكائن في TaxEngine.calculate_tax()
    """
    # معلومات المنتج
    product_code: Optional[str] = None
    product_category: Optional[str] = None
    product_tags: Optional[List[str]] = None

    # معلومات العميل
    customer_id: Optional[str] = None
    customer_group: Optional[str] = None
    customer_tax_number: Optional[str] = None
    customer_country: Optional[str] = None

    # معلومات الفاتورة
    invoice_id: Optional[str] = None
    invoice_date: Optional[date] = None
    currency: str = "USD"

    # معلومات الموقع
    site_id: Optional[str] = None
    site_country: Optional[str] = None
    site_region: Optional[str] = None

    # معلومات إضافية
    amount: Decimal = Decimal('0')
    is_tax_inclusive: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_b2b(self) -> bool:
        """هل المعاملة بين شركتين (B2B)؟"""
        return bool(self.customer_tax_number)

    def is_b2c(self) -> bool:
        """هل المعاملة مع مستهلك نهائي (B2C)؟"""
        return not self.is_b2b()

    def is_domestic(self) -> bool:
        """هل المعاملة محلية؟"""
        return self.customer_country == self.site_country

    def is_international(self) -> bool:
        """هل المعاملة دولية؟"""
        return not self.is_domestic()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    'TaxType',
    'TaxCalculationType',
    'TaxJurisdiction',
    'TaxApplicationScope',

    # Value Objects
    'TaxId',
    'TaxCode',
    'TaxRate',
    'TaxAmount',

    # Results
    'TaxCalculationResult',
    'TaxRuleSummary',

    # Context
    'TaxContext',
]