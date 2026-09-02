# core/application/suppliers/commands.py
"""Commands and Queries for Suppliers Module"""

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
from datetime import date, datetime  # ✅ إضافة date, datetime


# ========== COMMANDS ==========

@dataclass(frozen=True)
class CreateSupplierCommand:
    """أمر إنشاء مورد جديد"""
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
class UpdateSupplierCommand:
    """
    أمر تحديث مورد
    
    ملاحظة: version إجباري ولا توجد قيمة افتراضية
    """
    supplier_id: str
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
class ChangeSupplierStatusCommand:
    """أمر تغيير حالة المورد"""
    supplier_id: str
    new_status: str  # active, inactive, suspended, blocked
    reason: Optional[str] = None
    changed_by: str = "system"


@dataclass(frozen=True)
class DeleteSupplierCommand:
    """أمر حذف مورد"""
    supplier_id: str
    deleted_by: str = "system"
    permanent: bool = False  # True: حذف دائم, False: حذف ناعم


# ========== QUERIES ==========

@dataclass(frozen=True)
class GetSupplierQuery:
    """استعلام لجلب مورد بواسطة المعرف"""
    supplier_id: str


@dataclass(frozen=True)
class GetSupplierByCodeQuery:
    """استعلام لجلب مورد بواسطة الكود"""
    code: str


@dataclass(frozen=True)
class ListSuppliersQuery:
    """استعلام لجلب قائمة الموردين"""
    status: Optional[str] = None
    include_deleted: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class SearchSuppliersQuery:
    """استعلام للبحث عن الموردين"""
    search_text: str
    limit: int = 50
    offset: int = 0


# ✅ إضافة استعلام كشف حساب المورد
@dataclass(frozen=True)
class GetSupplierStatementQuery:
    """
    استعلام لكشف حساب المورد
    
    يقوم بإنشاء كشف حساب شامل لمورد معين يشمل جميع أوامر الشراء والمدفوعات.
    """
    supplier_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    currency: str = "USD"
    include_details: bool = True
    generated_at: datetime = None  # سيتم تعيينه تلقائياً


# ✅ إضافة استعلام إحصائيات المورد
@dataclass(frozen=True)
class GetSupplierStatisticsQuery:
    """
    استعلام لجلب إحصائيات المورد
    
    يقوم بجلب إحصائيات مالية للمورد مثل إجمالي المشتريات وعدد الطلبيات.
    """
    supplier_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None


# ========== EXPORTS ==========

__all__ = [
    # Commands
    "CreateSupplierCommand",
    "UpdateSupplierCommand",
    "ChangeSupplierStatusCommand",
    "DeleteSupplierCommand",
    
    # Queries
    "GetSupplierQuery",
    "GetSupplierByCodeQuery",
    "ListSuppliersQuery",
    "SearchSuppliersQuery",
    "GetSupplierStatementQuery",      # ✅ إضافة
    "GetSupplierStatisticsQuery",     # ✅ إضافة
]