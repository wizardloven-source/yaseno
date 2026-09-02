# core/application/invoicing/commands.py (تحديث - إضافة دعم فروع العملاء)

"""
Commands and Queries for Invoicing Module
✅ محدث: إضافة دعم فروع العملاء (Customer Branches)
✅ محدث: إضافة الأوامر المفقودة وعملة الدفع
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from decimal import Decimal


# ========== COMMANDS ==========

@dataclass(frozen=True)
class CreateInvoiceCommand:
    """
    أمر إنشاء فاتورة جديدة
    ✅ محدث: إضافة دعم فروع العملاء
    """
    customer_id: str
    customer_name: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    currency: str = "USD"
    payment_type: str = "cash"          # cash / credit / check / transfer
    payment_currency: str = "USD"       # ✅ عملة الدفع (USD/LBP)
    fund_id: Optional[str] = None       # للدفع النقدي
    
    # ✅ فروع العملاء (جديد)
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    customer_branch_code: Optional[str] = None
    
    notes: str = ""
    created_by: str = "system"


@dataclass(frozen=True)
class AddInvoiceLineCommand:
    """أمر إضافة سطر إلى فاتورة"""
    invoice_id: str
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    currency: str
    notes: str = ""


@dataclass(frozen=True)
class PostInvoiceCommand:
    """
    أمر ترحيل الفاتورة وإنشاء قيد محاسبي
    ✅ محدث: إضافة دعم فروع العملاء
    """
    invoice_id: str
    posted_by: str


@dataclass(frozen=True)
class UpdateInvoiceLineCommand:
    """أمر تحديث سطر في الفاتورة"""
    invoice_id: str
    line_id: str
    quantity: Decimal
    unit_price: Decimal
    notes: str = ""


@dataclass(frozen=True)
class RemoveInvoiceLineCommand:
    """أمر حذف سطر من الفاتورة"""
    invoice_id: str
    line_id: str


@dataclass(frozen=True)
class ClearInvoiceLinesCommand:
    """أمر مسح جميع بنود الفاتورة"""
    invoice_id: str


# ✅ إضافة أمر حذف الفاتورة المسودة
@dataclass(frozen=True)
class DeleteDraftInvoiceCommand:
    """أمر حذف فاتورة مسودة (غير مرحّلة)"""
    invoice_id: str
    deleted_by: str = "system"  # من قام بالحذف


# ✅ إضافة أمر إلغاء الفاتورة (جديد)
@dataclass(frozen=True)
class CancelInvoiceCommand:
    """أمر إلغاء فاتورة (مرحلة أو مسودة)"""
    invoice_id: str
    reason: Optional[str] = None
    cancelled_by: str = "system"


# ✅ إضافة أمر إنشاء فاتورة مرتجع (جديد)
@dataclass(frozen=True)
class ReturnInvoiceCommand:
    """أمر إنشاء فاتورة مرتجع من فاتورة موجودة"""
    invoice_id: str
    reason: str
    created_by: str = "system"


# ✅ إضافة أمر تنشيط فاتورة (لإلغاء الحذف)
@dataclass(frozen=True)
class RestoreDraftInvoiceCommand:
    """أمر استعادة فاتورة محذوفة (إلغاء الحذف الناعم)"""
    invoice_id: str
    restored_by: str = "system"


# ✅ إضافة أمر تحديث فرع العميل في الفاتورة (جديد)
@dataclass(frozen=True)
class UpdateInvoiceBranchCommand:
    """
    أمر تحديث فرع العميل في فاتورة موجودة
    ✅ جديد: يسمح بتغيير فرع العميل بعد إنشاء الفاتورة
    """
    invoice_id: str
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    customer_branch_code: Optional[str] = None
    updated_by: str = "system"
    version: int = 1


# ✅ إضافة أمر إزالة فرع العميل من الفاتورة (جديد)
@dataclass(frozen=True)
class ClearInvoiceBranchCommand:
    """
    أمر إزالة فرع العميل من الفاتورة
    ✅ جديد: يسمح بإزالة ربط فرع العميل بالفاتورة
    """
    invoice_id: str
    updated_by: str = "system"
    version: int = 1


# ========== QUERIES ==========

@dataclass(frozen=True)
class GetInvoiceQuery:
    """استعلام لجلب فاتورة بواسطة المعرف"""
    invoice_id: str


@dataclass(frozen=True)
class ListInvoicesQuery:
    """
    استعلام لجلب قائمة الفواتير
    ✅ محدث: إضافة فلترة حسب فرع العميل
    """
    status: Optional[str] = None
    customer_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    site_id: Optional[str] = None
    
    # ✅ فلترة حسب فرع العميل (جديد)
    customer_branch_id: Optional[str] = None
    
    limit: int = 100
    offset: int = 0


# ✅ إضافة استعلام لجلب فواتير العميل
@dataclass(frozen=True)
class GetCustomerInvoicesQuery:
    """
    استعلام لجلب فواتير عميل معين
    ✅ محدث: إضافة فلترة حسب فرع العميل
    """
    customer_id: str
    
    # ✅ فلترة حسب فرع العميل (جديد)
    customer_branch_id: Optional[str] = None
    
    limit: int = 100
    offset: int = 0


# ✅ إضافة استعلام لإحصائيات الفواتير
@dataclass(frozen=True)
class GetInvoiceStatsQuery:
    """
    استعلام لجلب إحصائيات الفواتير
    ✅ محدث: إضافة تجميع حسب فرع العميل
    """
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    
    # ✅ تجميع حسب فرع العميل (جديد)
    group_by_branch: bool = False


# ✅ إضافة استعلام للبحث في الفواتير
@dataclass(frozen=True)
class SearchInvoicesQuery:
    """
    استعلام للبحث في الفواتير
    ✅ محدث: إضافة فلترة حسب فرع العميل
    """
    search_text: str
    
    # ✅ فلترة حسب فرع العميل (جديد)
    customer_branch_id: Optional[str] = None
    
    limit: int = 50
    offset: int = 0


# ✅ إضافة استعلام لجلب فواتير فرع عميل معين (جديد)
@dataclass(frozen=True)
class GetBranchInvoicesQuery:
    """
    استعلام لجلب فواتير فرع عميل معين
    ✅ جديد: يستخدم لعرض جميع الفواتير المرتبطة بفرع عميل
    """
    customer_branch_id: str
    status: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


# ✅ إضافة استعلام لإحصائيات فرع عميل (جديد)
@dataclass(frozen=True)
class GetBranchStatisticsQuery:
    """
    استعلام لإحصائيات فواتير فرع عميل
    ✅ جديد: يحسب إجمالي الفواتير والمبالغ لفرع معين
    """
    customer_branch_id: str
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None


# ========== EXPORTS ==========

__all__ = [
    # Commands
    "CreateInvoiceCommand",
    "AddInvoiceLineCommand",
    "PostInvoiceCommand",
    "UpdateInvoiceLineCommand",
    "RemoveInvoiceLineCommand",
    "ClearInvoiceLinesCommand",
    "DeleteDraftInvoiceCommand",
    "CancelInvoiceCommand",
    "ReturnInvoiceCommand",
    "RestoreDraftInvoiceCommand",
    "UpdateInvoiceBranchCommand",      # ✅ جديد
    "ClearInvoiceBranchCommand",        # ✅ جديد
    
    # Queries
    "GetInvoiceQuery",
    "ListInvoicesQuery",
    "GetCustomerInvoicesQuery",
    "GetInvoiceStatsQuery",
    "SearchInvoicesQuery",
    "GetBranchInvoicesQuery",           # ✅ جديد
    "GetBranchStatisticsQuery",         # ✅ جديد
]