# core/application/accounting/commands.py

"""
Commands and Queries for the Accounting Application Layer
"""

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any


# ============================================================
# Journal Entry Commands
# ============================================================

@dataclass(frozen=True)
class CreateJournalEntryCommand:
    """
    أمر إنشاء قيد محاسبي جديد
    
    Attributes:
        date: تاريخ القيد
        description: وصف القيد
        lines: قائمة الأسطر المحاسبية (كل سطر يحتوي على account_code, debit, credit)
        transaction_type: نوع المعاملة (اختياري)
        reference_id: معرف المرجع (اختياري)
        notes: ملاحظات إضافية (اختياري)
        created_by: من قام بالإنشاء
    """
    date: date
    description: str
    lines: List[Dict[str, Any]]  # [{"account_code": str, "debit": Decimal, "credit": Decimal}]
    transaction_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    created_by: str = "system"


@dataclass(frozen=True)
class PostJournalEntryCommand:
    """
    أمر ترحيل قيد محاسبي
    
    Attributes:
        entry_id: معرف القيد
        posted_by: من قام بالترحيل
        force: تجاوز التحقق من الفترة المقفلة (للمسؤول فقط)
    """
    entry_id: str
    posted_by: str = "system"
    force: bool = False


@dataclass(frozen=True)
class ReverseJournalEntryCommand:
    """
    أمر عكس قيد محاسبي
    
    Attributes:
        entry_id: معرف القيد المراد عكسه
        reason: سبب العكس
        reversed_by: من قام بالعكس
    """
    entry_id: str
    reason: str
    reversed_by: str = "system"


@dataclass(frozen=True)
class ClosePeriodCommand:
    """
    أمر إغلاق فترة مالية
    
    Attributes:
        period_name: اسم الفترة (مثل "2024-01")
        closed_by: من قام بالإغلاق
        force: تجاوز التحقق من القيود غير المرحلة
    """
    period_name: str
    closed_by: str = "system"
    force: bool = False


@dataclass(frozen=True)
class OpenPeriodCommand:
    """
    أمر فتح فترة مالية
    
    Attributes:
        period_name: اسم الفترة (مثل "2024-01")
        opened_by: من قام بالفتح
    """
    period_name: str
    opened_by: str = "system"


# ============================================================
# Journal Entry Queries
# ============================================================

@dataclass(frozen=True)
class GetJournalEntryQuery:
    """
    استعلام لجلب قيد محاسبي بواسطة المعرف
    
    Attributes:
        entry_id: معرف القيد
    """
    entry_id: str


@dataclass(frozen=True)
class GetTrialBalanceQuery:
    """
    استعلام لجلب ميزان المراجعة
    
    Attributes:
        as_of_date: تاريخ الميزان
        currency: العملة
        include_zero_balance: تضمين الحسابات ذات الرصيد الصفري
    """
    as_of_date: date
    currency: str = "USD"
    include_zero_balance: bool = False


@dataclass(frozen=True)
class GetAccountBalanceQuery:
    """
    استعلام لجلب رصيد حساب
    
    Attributes:
        account_code: كود الحساب
        as_of_date: تاريخ الرصيد
        currency: العملة
    """
    account_code: str
    as_of_date: date
    currency: str = "USD"


@dataclass(frozen=True)
class ListJournalEntriesQuery:
    """
    استعلام لقائمة القيود المحاسبية
    
    Attributes:
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات
        is_posted: تصفية حسب حالة الترحيل
        from_date: تاريخ البداية
        to_date: تاريخ النهاية
    """
    limit: int = 100
    offset: int = 0
    is_posted: Optional[bool] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None


@dataclass(frozen=True)
class GetPeriodStatusQuery:
    """
    استعلام لحالة الفترة المالية
    
    Attributes:
        period_name: اسم الفترة
    """
    period_name: str


@dataclass(frozen=True)
class GetAuditLogQuery:
    """
    استعلام لسجل التدقيق
    
    Attributes:
        entity_type: نوع الكيان (اختياري)
        entity_id: معرف الكيان (اختياري)
        from_date: تاريخ البداية (اختياري)
        to_date: تاريخ النهاية (اختياري)
        limit: الحد الأقصى للنتائج
    """
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 100


# ============================================================
# Account Commands and Queries
# ============================================================

@dataclass(frozen=True)
class ListAccountsQuery:
    """
    استعلام لجلب قائمة الحسابات
    
    Attributes:
        account_type: نوع الحساب (asset, liability, equity, revenue, expense)
        include_inactive: تضمين الحسابات غير النشطة
    """
    account_type: Optional[str] = None
    include_inactive: bool = False


@dataclass(frozen=True)
class GetAccountByCodeQuery:
    """
    استعلام لجلب حساب بواسطة الكود
    
    Attributes:
        code: كود الحساب
    """
    code: str


@dataclass(frozen=True)
class CreateAccountCommand:
    """
    أمر إنشاء حساب جديد
    
    Attributes:
        code: كود الحساب
        name: اسم الحساب
        account_type: نوع الحساب
        currency: العملة
        parent_code: كود الحساب الأب (اختياري)
        description: وصف الحساب (اختياري)
        is_active: هل الحساب نشط؟
        created_by: من قام بالإنشاء
    """
    code: str
    name: str
    account_type: str
    currency: str = "USD"
    parent_code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateAccountCommand:
    """
    أمر تحديث حساب
    
    Attributes:
        code: كود الحساب
        name: اسم الحساب
        account_type: نوع الحساب
        is_active: هل الحساب نشط؟
        currency: العملة
        parent_code: كود الحساب الأب (اختياري)
        description: وصف الحساب (اختياري)
        updated_by: من قام بالتحديث
        version: رقم الإصدار (للتحكم في التزامن)
    """
    code: str
    name: str
    account_type: str
    is_active: bool = True
    currency: str = "USD"
    parent_code: Optional[str] = None
    description: Optional[str] = None
    updated_by: str = "system"
    version: int = 1


# ============================================================
# Fiscal Period Commands and Queries
# ============================================================

@dataclass(frozen=True)
class CreateFiscalYearCommand:
    """
    أمر إنشاء سنة مالية جديدة
    
    Attributes:
        code: كود السنة المالية
        name: اسم السنة المالية
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
        periods_per_year: عدد الفترات في السنة (12 شهراً أو 4 أرباع)
        period_type: نوع الفترة (month, quarter)
        created_by: من قام بالإنشاء
    """
    code: str
    name: str
    start_date: date
    end_date: date
    periods_per_year: int = 12
    period_type: str = "month"
    created_by: str = "system"


@dataclass(frozen=True)
class GetFiscalYearQuery:
    """
    استعلام لجلب سنة مالية
    
    Attributes:
        fiscal_year_id: معرف السنة المالية
    """
    fiscal_year_id: str


@dataclass(frozen=True)
class GetCurrentFiscalYearQuery:
    """
    استعلام لجلب السنة المالية الحالية
    """
    pass


@dataclass(frozen=True)
class ListFiscalYearsQuery:
    """
    استعلام لقائمة السنوات المالية
    
    Attributes:
        include_closed: تضمين السنوات المغلقة
        include_archived: تضمين السنوات المؤرشفة
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات
    """
    include_closed: bool = False
    include_archived: bool = False
    limit: int = 100
    offset: int = 0


# ============================================================
# Tax Commands and Queries
# ============================================================

@dataclass(frozen=True)
class CalculateTaxQuery:
    """
    استعلام لحساب الضريبة
    
    Attributes:
        amount: المبلغ الخاضع للضريبة
        currency: العملة
        product_code: كود المنتج (اختياري)
        customer_id: معرف العميل (اختياري)
        site_id: معرف الموقع (اختياري)
        is_tax_inclusive: هل المبلغ شامل الضريبة؟
    """
    amount: Decimal
    currency: str = "USD"
    product_code: Optional[str] = None
    customer_id: Optional[str] = None
    site_id: Optional[str] = None
    is_tax_inclusive: bool = False


# ============================================================
# Reports Queries
# ============================================================

@dataclass(frozen=True)
class GetIncomeStatementQuery:
    """
    استعلام لقائمة الدخل
    
    Attributes:
        period_start: بداية الفترة
        period_end: نهاية الفترة
        currency: العملة
        include_comparative: تضمين مقارنة مع الفترة السابقة
    """
    period_start: date
    period_end: date
    currency: str = "USD"
    include_comparative: bool = False


@dataclass(frozen=True)
class GetBalanceSheetQuery:
    """
    استعلام للميزانية العمومية
    
    Attributes:
        as_of_date: تاريخ الميزانية
        currency: العملة
    """
    as_of_date: date
    currency: str = "USD"


@dataclass(frozen=True)
class GetCashFlowQuery:
    """
    استعلام لقائمة التدفقات النقدية
    
    Attributes:
        period_start: بداية الفترة
        period_end: نهاية الفترة
        currency: العملة
        method: طريقة الحساب (direct, indirect)
    """
    period_start: date
    period_end: date
    currency: str = "USD"
    method: str = "indirect"


# ============================================================
# Export
# ============================================================

__all__ = [
    # Journal Entry Commands
    "CreateJournalEntryCommand",
    "PostJournalEntryCommand",
    "ReverseJournalEntryCommand",
    "ClosePeriodCommand",
    "OpenPeriodCommand",
    
    # Journal Entry Queries
    "GetJournalEntryQuery",
    "GetTrialBalanceQuery",
    "GetAccountBalanceQuery",
    "ListJournalEntriesQuery",
    "GetPeriodStatusQuery",
    "GetAuditLogQuery",
    
    # Account Commands & Queries
    "ListAccountsQuery",
    "GetAccountByCodeQuery",
    "CreateAccountCommand",
    "UpdateAccountCommand",
    
    # Fiscal Period
    "CreateFiscalYearCommand",
    "GetFiscalYearQuery",
    "GetCurrentFiscalYearQuery",
    "ListFiscalYearsQuery",
    
    # Tax
    "CalculateTaxQuery",
    
    # Reports
    "GetIncomeStatementQuery",
    "GetBalanceSheetQuery",
    "GetCashFlowQuery",
]