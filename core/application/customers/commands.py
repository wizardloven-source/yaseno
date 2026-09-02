"""Commands and Queries for Customers Module"""

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from datetime import date, datetime  # ✅ إضافة date, datetime


# ========== COMMANDS ==========

@dataclass(frozen=True)
class CreateCustomerCommand:
    """أمر إنشاء عميل جديد"""
    code: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    tax_number: Optional[str] = None
    credit_limit: Decimal = Decimal('0')
    currency: str = "USD"
    notes: Optional[str] = None
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateCustomerCommand:
    """
    أمر تحديث عميل
    
    ملاحظة: version إجباري ولا توجد قيمة افتراضية
    """
    customer_id: str
    version: int  # ✅ إجباري، بدون قيمة افتراضية
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_number: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class ChangeCustomerStatusCommand:
    """أمر تغيير حالة العميل"""
    customer_id: str
    new_status: str
    reason: Optional[str] = None
    changed_by: str = "system"


@dataclass(frozen=True)
class DeleteCustomerCommand:
    """أمر حذف عميل"""
    customer_id: str
    deleted_by: str = "system"
    permanent: bool = False


# ========== QUERIES ==========

@dataclass(frozen=True)
class GetCustomerQuery:
    """استعلام لجلب عميل بواسطة المعرف"""
    customer_id: str


@dataclass(frozen=True)
class GetCustomerByCodeQuery:
    """استعلام لجلب عميل بواسطة الكود"""
    code: str


@dataclass(frozen=True)
class ListCustomersQuery:
    """استعلام لجلب قائمة العملاء"""
    status: Optional[str] = None
    include_deleted: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class SearchCustomersQuery:
    """استعلام للبحث عن العملاء"""
    search_text: str
    limit: int = 50
    offset: int = 0


# ✅ إضافة استعلام كشف حساب العميل
@dataclass(frozen=True)
class GetCustomerStatementQuery:
    """
    استعلام لكشف حساب العميل
    
    يقوم بإنشاء كشف حساب شامل لعميل معين يشمل جميع الفواتير والمدفوعات.
    """
    customer_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    currency: str = "USD"
    include_details: bool = True
    generated_at: datetime = None  # سيتم تعيينه تلقائياً


# ✅ إضافة استعلام إحصائيات العميل
@dataclass(frozen=True)
class GetCustomerStatisticsQuery:
    """
    استعلام لجلب إحصائيات العميل
    
    يقوم بجلب إحصائيات مالية للعميل مثل إجمالي المشتريات وعدد الفواتير.
    """
    customer_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None


__all__ = [
    # Commands
    "CreateCustomerCommand",
    "UpdateCustomerCommand",
    "ChangeCustomerStatusCommand",
    "DeleteCustomerCommand",
    
    # Queries
    "GetCustomerQuery",
    "GetCustomerByCodeQuery",
    "ListCustomersQuery",
    "SearchCustomersQuery",
    "GetCustomerStatementQuery",      # ✅ إضافة
    "GetCustomerStatisticsQuery",     # ✅ إضافة
]