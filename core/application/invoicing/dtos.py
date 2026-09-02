"""
Data Transfer Objects for Invoicing
✅ محدث: دعم جميع حقول الضرائب
✅ محدث: دعم تفصيل الضرائب
✅ محدث: دمج الخصائص المساعدة
✅ محدث: دعم العملات المتعددة في الضرائب
✅ محدث: دعم فروع العملاء (Customer Branches)
✅ محدث: التحقق من صحة البيانات
✅ محدث: استخدام Money بدلاً من Decimal + currency
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
import logging

# استيراد Money من الـ Shared Kernel
try:
    from core.domain.shared.value_objects import Money, CurrencySettings
except ImportError:
    # Fallback للتوافق
    from dataclasses import dataclass
    from decimal import Decimal
    
    @dataclass(frozen=True)
    class Money:
        amount: Decimal
        currency: str = "USD"
        
        def format(self, include_currency: bool = True) -> str:
            return f"{self.amount:,.2f} {self.currency}" if include_currency else f"{self.amount:,.2f}"
    
    class CurrencySettings:
        @staticmethod
        def get_decimal_places(currency: str) -> int:
            return 0 if currency == "LBP" else 2

logger = logging.getLogger(__name__)


# =============================================================================
# دوال مساعدة للتحقق
# =============================================================================

def validate_amount(amount: Decimal, field_name: str = "Amount") -> None:
    """التحقق من صحة المبلغ"""
    if amount < 0:
        raise ValueError(f"{field_name} cannot be negative: {amount}")
    if amount > Decimal('999999999.99'):
        raise ValueError(f"{field_name} is too large: {amount}")


def validate_currency(currency: str) -> None:
    """التحقق من صحة العملة"""
    if not currency or len(currency.strip()) != 3:
        raise ValueError(f"Invalid currency code: '{currency}'. Must be 3 letters.")
    if not currency.isalpha():
        raise ValueError(f"Invalid currency code: '{currency}'. Must contain only letters.")


# =============================================================================
# DTO سطر الفاتورة
# =============================================================================

@dataclass
class InvoiceLineDTO:
    """
    سطر فاتورة - DTO
    ✅ محدث: دعم جميع حقول الضرائب
    ✅ محدث: التحقق من صحة البيانات
    """
    # ========== المعاملات الإجبارية ==========
    line_id: str
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    currency: str
    
    # ========== المعاملات الاختيارية ==========
    notes: str = ""
    tax_rate: Decimal = Decimal('0')
    tax_amount: Decimal = Decimal('0')
    tax_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    is_tax_inclusive: bool = False
    total_with_tax: Decimal = Decimal('0')
    
    def __post_init__(self):
        """التحقق من صحة البيانات بعد الإنشاء"""
        # التحقق من الكمية
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be greater than zero: {self.quantity}")
        
        # التحقق من السعر
        if self.unit_price <= 0:
            raise ValueError(f"Unit price must be greater than zero: {self.unit_price}")
        
        # التحقق من العملة
        validate_currency(self.currency)
        
        # التحقق من المبالغ
        validate_amount(self.total, "Total")
        validate_amount(self.tax_amount, "Tax amount")
        validate_amount(self.total_with_tax, "Total with tax")
        
        # التأكد من أن total_with_tax = total + tax_amount (إذا لم تكن الضريبة شاملة)
        if not self.is_tax_inclusive:
            expected_total_with_tax = self.total + self.tax_amount
            if abs(self.total_with_tax - expected_total_with_tax) > Decimal('0.01'):
                logger.warning(
                    f"Total with tax mismatch: expected {expected_total_with_tax}, got {self.total_with_tax}"
                )
    
    # ========== الخصائص المساعدة ==========
    
    @property
    def total_formatted(self) -> str:
        """الإجمالي منسقاً"""
        return f"{self.total:,.2f} {self.currency}"
    
    @property
    def unit_price_formatted(self) -> str:
        """سعر الوحدة منسقاً"""
        return f"{self.unit_price:,.2f} {self.currency}"
    
    @property
    def tax_amount_formatted(self) -> str:
        """مبلغ الضريبة منسقاً"""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.tax_amount:,.0f} {self.currency}"
        return f"{self.tax_amount:,.{decimal_places}f} {self.currency}"
    
    @property
    def total_with_tax_formatted(self) -> str:
        """الإجمالي شامل الضريبة منسقاً"""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.total_with_tax:,.0f} {self.currency}"
        return f"{self.total_with_tax:,.{decimal_places}f} {self.currency}"
    
    @property
    def has_tax(self) -> bool:
        """هل يحتوي السطر على ضريبة؟"""
        return self.tax_amount > 0
    
    @property
    def effective_tax_rate(self) -> float:
        """نسبة الضريبة الفعلية"""
        if self.total == 0:
            return 0.0
        return float((self.tax_amount / self.total) * 100)
    
    @property
    def tax_breakdown_formatted(self) -> str:
        """تفصيل الضرائب منسقاً"""
        if not self.tax_breakdown:
            return ""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return ", ".join([f"{k}: {v:,.0f} {self.currency}" for k, v in self.tax_breakdown.items()])
        return ", ".join([f"{k}: {v:,.{decimal_places}f} {self.currency}" for k, v in self.tax_breakdown.items()])
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض للسطر"""
        return f"{self.product_code} - {self.product_name}"
    
    @property
    def money_total(self) -> Money:
        """الإجمالي ككائن Money"""
        return Money(self.total, self.currency)
    
    @property
    def money_tax(self) -> Money:
        """مبلغ الضريبة ككائن Money"""
        return Money(self.tax_amount, self.currency)
    
    @property
    def money_total_with_tax(self) -> Money:
        """الإجمالي شامل الضريبة ككائن Money"""
        return Money(self.total_with_tax, self.currency)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتسلسل"""
        return {
            'line_id': self.line_id,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price),
            'total': float(self.total),
            'currency': self.currency,
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount),
            'tax_breakdown': {k: float(v) for k, v in self.tax_breakdown.items()},
            'is_tax_inclusive': self.is_tax_inclusive,
            'total_with_tax': float(self.total_with_tax),
            'notes': self.notes,
        }


# =============================================================================
# DTO الفاتورة الكاملة
# =============================================================================

@dataclass
class InvoiceDTO:
    """
    فاتورة - DTO كامل
    ✅ محدث: دعم جميع حقول الضرائب
    ✅ محدث: دعم فروع العملاء
    ✅ محدث: التحقق من صحة البيانات
    """
    # ========== المعاملات الإجبارية (بدون قيم افتراضية) ==========
    id: str
    customer_id: str
    customer_name: str
    currency: str
    payment_currency: str
    payment_type: str
    status: str
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    created_by: str
    
    # ========== المعاملات الاختيارية (بقيم افتراضية) ==========
    number: Optional[str] = None
    date: datetime = field(default_factory=datetime.now, compare=False)
    invoice_date: Optional[datetime] = field(default=None, compare=False)
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    customer_branch_code: Optional[str] = None
    fund_id: Optional[str] = None
    notes: str = ""
    lines: List[InvoiceLineDTO] = field(default_factory=list)
    journal_entry_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now, compare=False)
    posted_at: Optional[datetime] = field(default=None, compare=False)
    posted_by: Optional[str] = None
    tax_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    tax_rates_applied: List[str] = field(default_factory=list)
    is_tax_inclusive: bool = False
    total_with_tax: Decimal = Decimal('0')
    customer_tax_number: Optional[str] = None
    customer_tax_group: Optional[str] = None
    
    def __post_init__(self):
        """التحقق من صحة البيانات بعد الإنشاء"""
        # التحقق من العملة
        validate_currency(self.currency)
        validate_currency(self.payment_currency)
        
        # التحقق من المبالغ
        validate_amount(self.subtotal, "Subtotal")
        validate_amount(self.tax_amount, "Tax amount")
        validate_amount(self.total, "Total")
        validate_amount(self.total_with_tax, "Total with tax")
        
        # التأكد من أن total = subtotal (بدون ضريبة)
        if abs(self.total - self.subtotal) > Decimal('0.01'):
            logger.warning(f"Total ({self.total}) != Subtotal ({self.subtotal})")
        
        # التأكد من أن total_with_tax = total + tax_amount (إذا لم تكن الضريبة شاملة)
        if not self.is_tax_inclusive:
            expected_total_with_tax = self.total + self.tax_amount
            if abs(self.total_with_tax - expected_total_with_tax) > Decimal('0.01'):
                logger.warning(
                    f"Total with tax mismatch: expected {expected_total_with_tax}, got {self.total_with_tax}"
                )
    
    # ========== الخصائص المساعدة ==========
    
    @property
    def invoice_date_display(self) -> str:
        """عرض تاريخ الفاتورة"""
        dt = self.invoice_date or self.date
        return dt.strftime("%Y-%m-%d %H:%M") if dt else ""
    
    @property
    def subtotal_formatted(self) -> str:
        """المجموع الفرعي منسقاً"""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.subtotal:,.0f} {self.currency}"
        return f"{self.subtotal:,.{decimal_places}f} {self.currency}"
    
    @property
    def total_formatted(self) -> str:
        """الإجمالي منسقاً"""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.total:,.0f} {self.currency}"
        return f"{self.total:,.{decimal_places}f} {self.currency}"
    
    @property
    def tax_amount_formatted(self) -> str:
        """مبلغ الضريبة منسقاً"""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.tax_amount:,.0f} {self.currency}"
        return f"{self.tax_amount:,.{decimal_places}f} {self.currency}"
    
    @property
    def total_with_tax_formatted(self) -> str:
        """الإجمالي شامل الضريبة منسقاً"""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.total_with_tax:,.0f} {self.currency}"
        return f"{self.total_with_tax:,.{decimal_places}f} {self.currency}"
    
    @property
    def is_posted(self) -> bool:
        """هل الفاتورة مرحّلة؟"""
        return self.status == "posted"
    
    @property
    def is_draft(self) -> bool:
        """هل الفاتورة مسودة؟"""
        return self.status == "draft"
    
    @property
    def is_cancelled(self) -> bool:
        """هل الفاتورة ملغاة؟"""
        return self.status == "cancelled"
    
    @property
    def has_tax(self) -> bool:
        """هل تحتوي الفاتورة على ضريبة؟"""
        return self.tax_amount > 0
    
    @property
    def has_customer_branch(self) -> bool:
        """هل الفاتورة تحدد فرع عميل؟"""
        return bool(self.customer_branch_id)
    
    @property
    def customer_branch_display(self) -> str:
        """الاسم المعروض لفرع العميل"""
        if self.customer_branch_name:
            return self.customer_branch_name
        if self.customer_branch_code:
            return f"{self.customer_branch_code}"
        return "بدون فرع"
    
    @property
    def effective_tax_rate(self) -> float:
        """نسبة الضريبة الفعلية للفاتورة"""
        if self.subtotal == 0:
            return 0.0
        return float((self.tax_amount / self.subtotal) * 100)
    
    @property
    def tax_breakdown_formatted(self) -> str:
        """تفصيل الضرائب منسقاً"""
        if not self.tax_breakdown:
            return ""
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return ", ".join([f"{k}: {v:,.0f} {self.currency}" for k, v in self.tax_breakdown.items()])
        return ", ".join([f"{k}: {v:,.{decimal_places}f} {self.currency}" for k, v in self.tax_breakdown.items()])
    
    @property
    def tax_rates_display(self) -> str:
        """عرض نسب الضرائب المطبقة"""
        if not self.tax_rates_applied:
            return "بدون ضريبة"
        return ", ".join(self.tax_rates_applied)
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض للفاتورة"""
        branch_info = f" ({self.customer_branch_display})" if self.customer_branch_id else ""
        return f"{self.number} - {self.customer_name}{branch_info}" if self.number else f"فاتورة - {self.customer_name}"
    
    @property
    def summary(self) -> Dict[str, Any]:
        """ملخص سريع للفاتورة"""
        return {
            'id': self.id,
            'number': self.number,
            'date': self.invoice_date.isoformat() if self.invoice_date else (
                self.date.isoformat() if self.date else None
            ),
            'customer': self.customer_name,
            'customer_branch': self.customer_branch_display if self.customer_branch_id else None,
            'subtotal': float(self.subtotal),
            'tax': float(self.tax_amount),
            'total': float(self.total),
            'total_with_tax': float(self.total_with_tax),
            'currency': self.currency,
            'status': self.status,
            'has_tax': self.has_tax,
            'tax_rates': self.tax_rates_applied,
            'line_count': self.line_count,
            'total_quantity': float(self.total_quantity),
        }
    
    @property
    def line_count(self) -> int:
        """عدد البنود في الفاتورة"""
        return len(self.lines)
    
    @property
    def total_quantity(self) -> Decimal:
        """إجمالي الكميات في الفاتورة"""
        return sum(line.quantity for line in self.lines)
    
    @property
    def money_subtotal(self) -> Money:
        """المجموع الفرعي ككائن Money"""
        return Money(self.subtotal, self.currency)
    
    @property
    def money_tax(self) -> Money:
        """مبلغ الضريبة ككائن Money"""
        return Money(self.tax_amount, self.currency)
    
    @property
    def money_total(self) -> Money:
        """الإجمالي ككائن Money"""
        return Money(self.total, self.currency)
    
    @property
    def money_total_with_tax(self) -> Money:
        """الإجمالي شامل الضريبة ككائن Money"""
        return Money(self.total_with_tax, self.currency)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتسلسل"""
        return {
            'id': self.id,
            'number': self.number,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else (
                self.date.isoformat() if self.date else None
            ),
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'customer_branch_id': self.customer_branch_id,
            'customer_branch_name': self.customer_branch_name,
            'customer_branch_code': self.customer_branch_code,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'currency': self.currency,
            'payment_currency': self.payment_currency,
            'payment_type': self.payment_type,
            'fund_id': self.fund_id,
            'status': self.status,
            'subtotal': float(self.subtotal),
            'tax_amount': float(self.tax_amount),
            'total': float(self.total),
            'total_with_tax': float(self.total_with_tax),
            'tax_breakdown': {k: float(v) for k, v in self.tax_breakdown.items()},
            'tax_rates_applied': self.tax_rates_applied,
            'is_tax_inclusive': self.is_tax_inclusive,
            'lines': [line.to_dict() for line in self.lines],
            'journal_entry_id': self.journal_entry_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'posted_by': self.posted_by,
        }


# =============================================================================
# DTO لإنشاء فاتورة جديدة
# =============================================================================

@dataclass
class CreateInvoiceDTO:
    """
    بيانات إنشاء فاتورة جديدة
    ✅ محدث: دعم المعلومات الضريبية
    ✅ محدث: دعم فروع العملاء
    """
    # ========== المعاملات الإجبارية ==========
    customer_id: str
    customer_name: str
    
    # ========== المعاملات الاختيارية ==========
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    customer_branch_code: Optional[str] = None
    currency: str = "USD"
    payment_currency: str = "USD"
    payment_type: str = "cash"
    fund_id: Optional[str] = None
    customer_tax_number: Optional[str] = None
    customer_tax_group: Optional[str] = None
    is_tax_inclusive: bool = False
    notes: str = ""
    created_by: str = "system"
    
    def __post_init__(self):
        """التحقق من صحة البيانات بعد الإنشاء"""
        # التحقق من العملات
        validate_currency(self.currency)
        validate_currency(self.payment_currency)
        
        # التحقق من العميل
        if not self.customer_id:
            raise ValueError("Customer ID is required")
        if not self.customer_name:
            raise ValueError("Customer name is required")
        
        # التحقق من طريقة الدفع
        valid_payment_types = ['cash', 'credit', 'check', 'transfer']
        if self.payment_type not in valid_payment_types:
            raise ValueError(f"Invalid payment type: {self.payment_type}. Must be one of {valid_payment_types}")
    
    # ========== الخصائص المساعدة ==========
    
    @property
    def payment_type_enum(self):
        """تحويل payment_type إلى Enum"""
        from core.domain.invoicing.value_objects import PaymentType
        mapping = {
            'cash': PaymentType.CASH,
            'credit': PaymentType.CREDIT,
            'check': PaymentType.CHECK,
            'transfer': PaymentType.TRANSFER
        }
        return mapping.get(self.payment_type, PaymentType.CASH)
    
    @property
    def has_customer_branch(self) -> bool:
        """هل تم تحديد فرع عميل؟"""
        return bool(self.customer_branch_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        return {
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'customer_branch_id': self.customer_branch_id,
            'customer_branch_name': self.customer_branch_name,
            'customer_branch_code': self.customer_branch_code,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'currency': self.currency,
            'payment_currency': self.payment_currency,
            'payment_type': self.payment_type,
            'fund_id': self.fund_id,
            'customer_tax_number': self.customer_tax_number,
            'customer_tax_group': self.customer_tax_group,
            'is_tax_inclusive': self.is_tax_inclusive,
            'notes': self.notes,
            'created_by': self.created_by,
        }


# =============================================================================
# DTO لتحديث فاتورة
# =============================================================================

@dataclass
class UpdateInvoiceDTO:
    """
    بيانات تحديث فاتورة
    ✅ محدث: دعم تحديث المعلومات الضريبية
    ✅ محدث: دعم تحديث فرع العميل
    """
    # ========== المعاملات الإجبارية ==========
    invoice_id: str
    
    # ========== المعاملات الاختيارية ==========
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    customer_branch_code: Optional[str] = None
    currency: Optional[str] = None
    payment_currency: Optional[str] = None
    payment_type: Optional[str] = None
    fund_id: Optional[str] = None
    customer_tax_number: Optional[str] = None
    customer_tax_group: Optional[str] = None
    is_tax_inclusive: Optional[bool] = None
    notes: Optional[str] = None
    updated_by: str = "system"
    version: int = 1
    
    def __post_init__(self):
        """التحقق من صحة البيانات بعد الإنشاء"""
        if not self.invoice_id:
            raise ValueError("Invoice ID is required")
        
        # التحقق من العملات إذا تم تحديثها
        if self.currency:
            validate_currency(self.currency)
        if self.payment_currency:
            validate_currency(self.payment_currency)
        
        # التحقق من طريقة الدفع إذا تم تحديثها
        if self.payment_type:
            valid_payment_types = ['cash', 'credit', 'check', 'transfer']
            if self.payment_type not in valid_payment_types:
                raise ValueError(f"Invalid payment type: {self.payment_type}")
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        result = {
            'invoice_id': self.invoice_id,
            'updated_by': self.updated_by,
            'version': self.version,
        }
        
        # إضافة الحقول التي تم تحديثها فقط
        if self.customer_id is not None:
            result['customer_id'] = self.customer_id
        if self.customer_name is not None:
            result['customer_name'] = self.customer_name
        if self.customer_branch_id is not None:
            result['customer_branch_id'] = self.customer_branch_id
        if self.customer_branch_name is not None:
            result['customer_branch_name'] = self.customer_branch_name
        if self.customer_branch_code is not None:
            result['customer_branch_code'] = self.customer_branch_code
        if self.site_id is not None:
            result['site_id'] = self.site_id
        if self.site_name is not None:
            result['site_name'] = self.site_name
        if self.currency is not None:
            result['currency'] = self.currency
        if self.payment_currency is not None:
            result['payment_currency'] = self.payment_currency
        if self.payment_type is not None:
            result['payment_type'] = self.payment_type
        if self.fund_id is not None:
            result['fund_id'] = self.fund_id
        if self.customer_tax_number is not None:
            result['customer_tax_number'] = self.customer_tax_number
        if self.customer_tax_group is not None:
            result['customer_tax_group'] = self.customer_tax_group
        if self.is_tax_inclusive is not None:
            result['is_tax_inclusive'] = self.is_tax_inclusive
        if self.notes is not None:
            result['notes'] = self.notes
        
        return result


# =============================================================================
# DTO لملخص الفاتورة (للقراءة السريعة)
# =============================================================================

@dataclass
class InvoiceSummaryDTO:
    """
    ملخص الفاتورة - للقوائم والتقارير السريعة
    ✅ محدث: دعم المعلومات الضريبية
    ✅ محدث: دعم فروع العملاء
    """
    # ========== المعاملات الإجبارية ==========
    id: str
    number: str
    customer_name: str
    total: Decimal
    currency: str
    status: str
    
    # ========== المعاملات الاختيارية ==========
    date: datetime = field(default_factory=datetime.now, compare=False)
    tax_amount: Decimal = Decimal('0')
    total_with_tax: Decimal = Decimal('0')
    payment_type: str = "cash"
    customer_branch_name: Optional[str] = None
    
    @property
    def total_formatted(self) -> str:
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.total:,.0f} {self.currency}"
        return f"{self.total:,.{decimal_places}f} {self.currency}"
    
    @property
    def tax_amount_formatted(self) -> str:
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.tax_amount:,.0f} {self.currency}"
        return f"{self.tax_amount:,.{decimal_places}f} {self.currency}"
    
    @property
    def total_with_tax_formatted(self) -> str:
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.total_with_tax:,.0f} {self.currency}"
        return f"{self.total_with_tax:,.{decimal_places}f} {self.currency}"
    
    @property
    def has_tax(self) -> bool:
        return self.tax_amount > 0
    
    @property
    def is_posted(self) -> bool:
        return self.status == "posted"
    
    @property
    def display_name(self) -> str:
        branch_info = f" ({self.customer_branch_name})" if self.customer_branch_name else ""
        return f"{self.number} - {self.customer_name}{branch_info}"


# =============================================================================
# DTO لإحصائيات الفواتير
# =============================================================================

@dataclass
class InvoiceStatisticsDTO:
    """
    إحصائيات الفواتير - للتقارير ولوحة التحكم
    ✅ محدث: دعم التفصيل حسب فرع العميل
    """
    # ========== المعاملات الإجبارية ==========
    total_count: int
    total_amount: Decimal
    total_tax: Decimal
    total_with_tax: Decimal
    draft_count: int
    posted_count: int
    cancelled_count: int
    
    # ========== المعاملات الاختيارية ==========
    currency: str = "USD"
    by_currency: Dict[str, Decimal] = field(default_factory=dict)
    by_payment_type: Dict[str, Decimal] = field(default_factory=dict)
    by_customer_branch: Dict[str, Decimal] = field(default_factory=dict)
    average_amount: Decimal = Decimal('0')
    min_amount: Decimal = Decimal('0')
    max_amount: Decimal = Decimal('0')
    
    @property
    def total_amount_formatted(self) -> str:
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.total_amount:,.0f} {self.currency}"
        return f"{self.total_amount:,.{decimal_places}f} {self.currency}"
    
    @property
    def total_tax_formatted(self) -> str:
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.total_tax:,.0f} {self.currency}"
        return f"{self.total_tax:,.{decimal_places}f} {self.currency}"
    
    @property
    def total_with_tax_formatted(self) -> str:
        decimal_places = CurrencySettings.get_decimal_places(self.currency)
        if decimal_places == 0:
            return f"{self.total_with_tax:,.0f} {self.currency}"
        return f"{self.total_with_tax:,.{decimal_places}f} {self.currency}"
    
    @property
    def completion_rate(self) -> float:
        """نسبة الفواتير المرحلة"""
        if self.total_count == 0:
            return 0.0
        return (self.posted_count / self.total_count) * 100
    
    @property
    def tax_rate_over_total(self) -> float:
        """نسبة الضريبة من الإجمالي"""
        if self.total_amount == 0:
            return 0.0
        return float((self.total_tax / self.total_amount) * 100)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        return {
            'total_count': self.total_count,
            'total_amount': float(self.total_amount),
            'total_tax': float(self.total_tax),
            'total_with_tax': float(self.total_with_tax),
            'draft_count': self.draft_count,
            'posted_count': self.posted_count,
            'cancelled_count': self.cancelled_count,
            'currency': self.currency,
            'by_currency': {k: float(v) for k, v in self.by_currency.items()},
            'by_payment_type': {k: float(v) for k, v in self.by_payment_type.items()},
            'by_customer_branch': {k: float(v) for k, v in self.by_customer_branch.items()},
            'average_amount': float(self.average_amount),
            'min_amount': float(self.min_amount),
            'max_amount': float(self.max_amount),
            'completion_rate': self.completion_rate,
            'tax_rate_over_total': self.tax_rate_over_total,
        }


# =============================================================================
# DTO لفلترة الفواتير
# =============================================================================

@dataclass
class InvoiceFilterDTO:
    """
    فلتر البحث عن الفواتير
    ✅ محدث: دعم فلترة حسب فرع العميل
    """
    # ========== المعاملات الاختيارية ==========
    customer_id: Optional[str] = None
    site_id: Optional[str] = None
    customer_branch_id: Optional[str] = None
    status: Optional[str] = None
    payment_type: Optional[str] = None
    currency: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    has_tax: Optional[bool] = None
    search_text: Optional[str] = None
    limit: int = 100
    offset: int = 0
    order_by: str = "date"
    order_desc: bool = True
    
    def __post_init__(self):
        """التحقق من صحة الفلتر"""
        if self.limit <= 0 or self.limit > 1000:
            raise ValueError(f"Limit must be between 1 and 1000: {self.limit}")
        
        if self.offset < 0:
            raise ValueError(f"Offset cannot be negative: {self.offset}")
        
        # التحقق من صحة النطاق الزمني
        if self.from_date and self.to_date and self.from_date > self.to_date:
            raise ValueError("From date must be before to date")
        
        # التحقق من صحة المبالغ
        if self.min_amount is not None and self.min_amount < 0:
            raise ValueError(f"Min amount cannot be negative: {self.min_amount}")
        if self.max_amount is not None and self.max_amount < 0:
            raise ValueError(f"Max amount cannot be negative: {self.max_amount}")
        if self.min_amount is not None and self.max_amount is not None and self.min_amount > self.max_amount:
            raise ValueError("Min amount cannot be greater than max amount")
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        return {
            'customer_id': self.customer_id,
            'site_id': self.site_id,
            'customer_branch_id': self.customer_branch_id,
            'status': self.status,
            'payment_type': self.payment_type,
            'currency': self.currency,
            'from_date': self.from_date.isoformat() if self.from_date else None,
            'to_date': self.to_date.isoformat() if self.to_date else None,
            'min_amount': float(self.min_amount) if self.min_amount is not None else None,
            'max_amount': float(self.max_amount) if self.max_amount is not None else None,
            'has_tax': self.has_tax,
            'search_text': self.search_text,
            'limit': self.limit,
            'offset': self.offset,
            'order_by': self.order_by,
            'order_desc': self.order_desc,
        }


# =============================================================================
# تصدير جميع الكلاسات
# =============================================================================

__all__ = [
    # DTOs الأساسية
    "InvoiceLineDTO",
    "InvoiceDTO",
    "CreateInvoiceDTO",
    "UpdateInvoiceDTO",
    
    # DTOs المساعدة
    "InvoiceSummaryDTO",
    "InvoiceStatisticsDTO",
    "InvoiceFilterDTO",
]