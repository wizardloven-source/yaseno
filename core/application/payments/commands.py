"""
Commands and Queries for Payments Module
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

from core.domain.payments.value_objects import PaymentType, PaymentMethod, PaymentStatus


# ========== COMMANDS ==========

@dataclass(frozen=True)
class CreatePaymentCommand:
    """أمر إنشاء دفعة جديدة"""
    payment_type: str  # receive, pay
    amount: Decimal
    currency: str = "USD"
    payment_method: str = "cash"
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    fund_id: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: str = ""
    created_by: str = "system"


@dataclass(frozen=True)
class UpdatePaymentCommand:
    """أمر تحديث دفعة"""
    payment_id: str
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    fund_id: Optional[str] = None
    updated_by: str = "system"
    version: int = 1


@dataclass(frozen=True)
class AddPaymentLineCommand:
    """أمر إضافة سطر دفعة"""
    payment_id: str
    reference_type: str
    reference_id: str
    amount: Decimal
    currency: str = "USD"
    notes: str = ""


@dataclass(frozen=True)
class RemovePaymentLineCommand:
    """أمر حذف سطر دفعة"""
    payment_id: str
    line_id: str


@dataclass(frozen=True)
class ApprovePaymentCommand:
    """أمر اعتماد دفعة"""
    payment_id: str
    approved_by: str


@dataclass(frozen=True)
class RejectPaymentCommand:
    """أمر رفض دفعة"""
    payment_id: str
    rejected_by: str
    reason: str = ""


@dataclass(frozen=True)
class CompletePaymentCommand:
    """أمر إكمال دفعة"""
    payment_id: str
    completed_by: str


@dataclass(frozen=True)
class CancelPaymentCommand:
    """أمر إلغاء دفعة"""
    payment_id: str
    cancelled_by: str
    reason: str = ""


@dataclass(frozen=True)
class DeleteDraftPaymentCommand:
    """أمر حذف دفعة مسودة"""
    payment_id: str
    deleted_by: str = "system"


# ✅ إضافة أوامر التوزيع
@dataclass(frozen=True)
class AllocatePaymentCommand:
    """
    أمر توزيع دفعة على فاتورة
    
    يقوم بتوزيع مبلغ الدفعة على فاتورة محددة.
    """
    payment_id: str
    invoice_id: str
    amount: Decimal
    allocated_by: str = "system"


@dataclass(frozen=True)
class ReverseAllocationCommand:
    """
    أمر إلغاء توزيع دفعة
    
    يقوم بإلغاء توزيع الدفعة على الفاتورة مع إنشاء قيد عكسي.
    """
    allocation_id: str
    payment_id: str
    reason: Optional[str] = None
    reversed_by: str = "system"


# ========== QUERIES ==========

@dataclass(frozen=True)
class GetPaymentQuery:
    """استعلام لجلب دفعة بواسطة المعرف"""
    payment_id: str


@dataclass(frozen=True)
class ListPaymentsQuery:
    """استعلام لجلب قائمة الدفعات"""
    payment_type: Optional[str] = None
    status: Optional[str] = None
    customer_id: Optional[str] = None
    supplier_id: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetPaymentSummaryQuery:
    """استعلام لجلب ملخص الدفعات"""
    from_date: Optional[date] = None
    to_date: Optional[date] = None


@dataclass(frozen=True)
class GetCustomerPaymentsQuery:
    """استعلام لجلب دفعات العميل"""
    customer_id: str
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetSupplierPaymentsQuery:
    """استعلام لجلب دفعات المورد"""
    supplier_id: str
    limit: int = 100
    offset: int = 0


# ✅ إضافة استعلام جلب دفعات صندوق معين
@dataclass(frozen=True)
class GetFundPaymentsQuery:
    """استعلام لجلب دفعات صندوق معين"""
    fund_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    limit: int = 100
    offset: int = 0


# ✅ إضافة استعلام جلب دفعات حسب طريقة الدفع
@dataclass(frozen=True)
class GetPaymentsByMethodQuery:
    """استعلام لجلب دفعات حسب طريقة الدفع"""
    payment_method: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    limit: int = 100
    offset: int = 0


# ✅ إضافة استعلام جلب دفعات حسب النطاق الزمني مع التجميع
@dataclass(frozen=True)
class GetPaymentsByDateRangeQuery:
    """استعلام لجلب دفعات حسب النطاق الزمني مع التجميع"""
    from_date: date
    to_date: date
    payment_type: Optional[str] = None
    group_by: str = "day"  # day, week, month, year


# ✅ إضافة استعلام جلب إحصائيات الدفعات
@dataclass(frozen=True)
class GetPaymentStatisticsQuery:
    """استعلام لجلب إحصائيات الدفعات"""
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    currency: str = "USD"


# ✅ إضافة استعلام جلب توزيعات الدفعة
@dataclass(frozen=True)
class GetPaymentAllocationsQuery:
    """استعلام لجلب توزيعات دفعة معينة"""
    payment_id: str
    include_cancelled: bool = False


# ========== EXPORTS ==========

__all__ = [
    # Commands
    "CreatePaymentCommand",
    "UpdatePaymentCommand",
    "AddPaymentLineCommand",
    "RemovePaymentLineCommand",
    "ApprovePaymentCommand",
    "RejectPaymentCommand",
    "CompletePaymentCommand",
    "CancelPaymentCommand",
    "DeleteDraftPaymentCommand",
    "AllocatePaymentCommand",       # ✅ إضافة
    "ReverseAllocationCommand",     # ✅ إضافة
    
    # Queries
    "GetPaymentQuery",
    "ListPaymentsQuery",
    "GetPaymentSummaryQuery",
    "GetCustomerPaymentsQuery",
    "GetSupplierPaymentsQuery",
    "GetFundPaymentsQuery",           # ✅ إضافة
    "GetPaymentsByMethodQuery",       # ✅ إضافة
    "GetPaymentsByDateRangeQuery",    # ✅ إضافة
    "GetPaymentStatisticsQuery",      # ✅ إضافة
    "GetPaymentAllocationsQuery",     # ✅ إضافة
]