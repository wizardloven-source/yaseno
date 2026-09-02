# core/domain/invoicing/events.py
"""
Domain Events for Invoicing Context
✅ محدث: دعم أحداث الضرائب
✅ محدث: دعم تفصيل الضرائب في أحداث الترحيل
✅ محدث: إضافة حدث حساب الضريبة
✅ محدث: إضافة حدث تحديث الضريبة
✅ محدث: إضافة حدث الفاتورة المتأخرة
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from ..shared.value_objects import BaseDomainEvent, Money
from .value_objects import InvoiceId


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# الأحداث الأساسية (موجودة - محسنة)
# =============================================================================

@dataclass(frozen=True)
class InvoiceCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء فاتورة جديدة"""
    invoice_id: InvoiceId
    customer_id: str
    total_amount: Money
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.created"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "customer_id": self.customer_id,
            "total_amount": str(self.total_amount.amount),
            "currency": self.total_amount.currency,
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class InvoicePostedEvent(BaseDomainEvent):
    """
    يُرفع عند ترحيل الفاتورة وإنشاء القيد المحاسبي
    ✅ محدث: إضافة tax_amount و tax_breakdown
    """
    invoice_id: InvoiceId
    invoice_number: Optional[str]
    journal_entry_id: str
    total_amount: Money
    customer_id: str
    posted_by: str
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    
    # ✅ حقول الضرائب الجديدة
    tax_amount: Money = field(default_factory=lambda: Money.zero())
    tax_breakdown: Dict[str, Money] = field(default_factory=dict)
    total_with_tax: Money = field(default_factory=lambda: Money.zero())
    is_tax_inclusive: bool = False
    
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.posted"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "invoice_number": self.invoice_number,
            "journal_entry_id": self.journal_entry_id,
            "total_amount": str(self.total_amount.amount),
            "currency": self.total_amount.currency,
            "customer_id": self.customer_id,
            "posted_by": self.posted_by,
            "customer_branch_id": self.customer_branch_id,
            "customer_branch_name": self.customer_branch_name,
            # ✅ حقول الضرائب
            "tax_amount": str(self.tax_amount.amount),
            "tax_breakdown": {k: str(v.amount) for k, v in self.tax_breakdown.items()},
            "total_with_tax": str(self.total_with_tax.amount),
            "is_tax_inclusive": self.is_tax_inclusive,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class InvoiceLineAddedEvent(BaseDomainEvent):
    """يُرفع عند إضافة سطر إلى الفاتورة"""
    invoice_id: InvoiceId
    product_code: str
    product_name: str
    quantity: int
    unit_price: Money
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.line_added"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "product_code": self.product_code,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": str(self.unit_price.amount),
            "currency": self.unit_price.currency,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث الضرائب الجديدة
# =============================================================================

@dataclass(frozen=True)
class InvoiceTaxCalculatedEvent(BaseDomainEvent):
    """
    يُرفع عند حساب ضريبة الفاتورة
    هذا الحدث مفيد لتحديث واجهة المستخدم أو تسجيل سجل التدقيق
    """
    # ✅ جميع الحقول التي ليس لها قيمة افتراضية أولاً
    invoice_id: InvoiceId
    customer_id: str
    taxable_amount: Money
    tax_amount: Money
    total_with_tax: Money
    tax_breakdown: Dict[str, Money]  # {tax_code: amount}
    tax_rates_applied: List[str]     # قائمة أكواد الضرائب المطبقة
    calculated_by: str
    is_tax_inclusive: bool
    
    # ✅ الحقول ذات القيم الافتراضية أخيراً
    invoice_number: Optional[str] = None
    calculated_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.tax_calculated"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "taxable_amount": str(self.taxable_amount.amount),
            "tax_amount": str(self.tax_amount.amount),
            "total_with_tax": str(self.total_with_tax.amount),
            "currency": self.taxable_amount.currency,
            "tax_breakdown": {k: str(v.amount) for k, v in self.tax_breakdown.items()},
            "tax_rates_applied": self.tax_rates_applied,
            "is_tax_inclusive": self.is_tax_inclusive,
            "calculated_by": self.calculated_by,
            "calculated_at": self.calculated_at.isoformat()
        }


@dataclass(frozen=True)
class InvoiceLineTaxCalculatedEvent(BaseDomainEvent):
    """
    يُرفع عند حساب ضريبة سطر فردي في الفاتورة
    مفيد لتتبع الضرائب لكل منتج على حدة
    """
    invoice_id: InvoiceId
    line_id: str
    product_code: str
    product_name: str
    
    # تفاصيل الضريبة للسطر
    taxable_amount: Money
    tax_amount: Money
    tax_rate: float
    total_with_tax: Money
    tax_breakdown: Dict[str, Money]
    is_tax_inclusive: bool
    
    calculated_by: str
    calculated_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.line_tax_calculated"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "line_id": self.line_id,
            "product_code": self.product_code,
            "product_name": self.product_name,
            "taxable_amount": str(self.taxable_amount.amount),
            "tax_amount": str(self.tax_amount.amount),
            "tax_rate": self.tax_rate,
            "total_with_tax": str(self.total_with_tax.amount),
            "currency": self.taxable_amount.currency,
            "tax_breakdown": {k: str(v.amount) for k, v in self.tax_breakdown.items()},
            "is_tax_inclusive": self.is_tax_inclusive,
            "calculated_by": self.calculated_by,
            "calculated_at": self.calculated_at.isoformat()
        }


# =============================================================================
# أحداث إضافية
# =============================================================================

@dataclass(frozen=True)
class InvoiceTaxUpdatedEvent(BaseDomainEvent):
    """
    يُرفع عند تحديث الضريبة في الفاتورة (يدوياً أو تلقائياً)
    """
    invoice_id: InvoiceId
    invoice_number: Optional[str]
    
    # القيم القديمة والجديدة
    old_tax_amount: Money
    new_tax_amount: Money
    old_total_with_tax: Money
    new_total_with_tax: Money
    changes: Dict[str, Any]  # تفاصيل التغييرات
    
    updated_by: str
    updated_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.tax_updated"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "invoice_number": self.invoice_number,
            "old_tax_amount": str(self.old_tax_amount.amount),
            "new_tax_amount": str(self.new_tax_amount.amount),
            "old_total_with_tax": str(self.old_total_with_tax.amount),
            "new_total_with_tax": str(self.new_total_with_tax.amount),
            "currency": self.new_tax_amount.currency,
            "changes": self.changes,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat()
        }


@dataclass(frozen=True)
class InvoiceTaxExemptionAppliedEvent(BaseDomainEvent):
    """
    يُرفع عند تطبيق إعفاء ضريبي على الفاتورة
    """
    # ✅ جميع الحقول التي ليس لها قيمة افتراضية أولاً
    invoice_id: InvoiceId
    customer_id: str
    exemption_reason: str
    exempted_tax_amount: Money
    applied_by: str
    
    # ✅ الحقول ذات القيم الافتراضية أخيراً
    invoice_number: Optional[str] = None
    exemption_certificate: Optional[str] = None
    applied_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.tax_exemption_applied"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "exemption_reason": self.exemption_reason,
            "exemption_certificate": self.exemption_certificate,
            "exempted_tax_amount": str(self.exempted_tax_amount.amount),
            "currency": self.exempted_tax_amount.currency,
            "applied_by": self.applied_by,
            "applied_at": self.applied_at.isoformat()
        }


# =============================================================================
# أحداث الفواتير المتأخرة ✅ تم الإضافة
# =============================================================================

@dataclass(frozen=True)
class InvoiceOverdueEvent(BaseDomainEvent):
    """
    يُرفع عندما تصبح الفاتورة متأخرة
    
    هذا الحدث يُستخدم لتشغيل تنبيهات وإشعارات الفواتير المتأخرة.
    """
    invoice_id: InvoiceId
    invoice_number: str
    customer_id: str
    customer_name: str
    amount: Money
    currency: str
    days_overdue: int
    due_date: datetime
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.overdue"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "invoice_number": self.invoice_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "amount": str(self.amount.amount),
            "currency": self.currency,
            "days_overdue": self.days_overdue,
            "due_date": self.due_date.isoformat(),
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث أخرى
# =============================================================================

@dataclass(frozen=True)
class InvoiceCancelledEvent(BaseDomainEvent):
    """يُرفع عند إلغاء فاتورة"""
    invoice_id: InvoiceId
    invoice_number: Optional[str]
    cancelled_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.cancelled"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "invoice_number": self.invoice_number,
            "cancelled_by": self.cancelled_by,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class InvoiceLineRemovedEvent(BaseDomainEvent):
    """يُرفع عند حذف سطر من الفاتورة"""
    invoice_id: InvoiceId
    line_id: str
    product_code: str
    quantity: int
    unit_price: Money
    removed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.line_removed"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "line_id": self.line_id,
            "product_code": self.product_code,
            "quantity": self.quantity,
            "unit_price": str(self.unit_price.amount),
            "currency": self.unit_price.currency,
            "removed_by": self.removed_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class InvoiceLineUpdatedEvent(BaseDomainEvent):
    """يُرفع عند تحديث سطر في الفاتورة"""
    invoice_id: InvoiceId
    line_id: str
    product_code: str
    old_quantity: int
    new_quantity: int
    old_unit_price: Money
    new_unit_price: Money
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "invoicing.invoice.line_updated"
    
    def to_dict(self) -> dict:
        return {
            "event_type": self.get_event_name(),
            "invoice_id": str(self.invoice_id),
            "line_id": self.line_id,
            "product_code": self.product_code,
            "old_quantity": self.old_quantity,
            "new_quantity": self.new_quantity,
            "old_unit_price": str(self.old_unit_price.amount),
            "new_unit_price": str(self.new_unit_price.amount),
            "currency": self.new_unit_price.currency,
            "updated_by": self.updated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# تصدير جميع الأحداث
# =============================================================================

__all__ = [
    # الأحداث الأساسية
    "InvoiceCreatedEvent",
    "InvoicePostedEvent",
    "InvoiceLineAddedEvent",
    "InvoiceCancelledEvent",
    "InvoiceLineRemovedEvent",
    "InvoiceLineUpdatedEvent",
    
    # أحداث الضرائب
    "InvoiceTaxCalculatedEvent",
    "InvoiceLineTaxCalculatedEvent",
    "InvoiceTaxUpdatedEvent",
    "InvoiceTaxExemptionAppliedEvent",
    
    # أحداث الفواتير المتأخرة ✅ تم الإضافة
    "InvoiceOverdueEvent",
]