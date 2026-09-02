# core/application/reports/commands.py
"""
Reports Commands and Queries - الأوامر والاستعلامات للتقارير
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


# =============================================================================
# COMMANDS - أوامر توليد التقارير
# =============================================================================

@dataclass(frozen=True)
class GenerateReportCommand:
    """
    أمر توليد تقرير
    
    Attributes:
        report_type: نوع التقرير
        parameters: معلمات التقرير
        format: صيغة التقرير (pdf, excel, csv, json)
        save_report: هل يتم حفظ التقرير؟
        generated_by: من قام بالتوليد
    """
    report_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    format: str = "pdf"
    save_report: bool = True
    generated_by: str = "system"


@dataclass(frozen=True)
class ExportReportCommand:
    """
    أمر تصدير تقرير
    
    Attributes:
        report_id: معرف التقرير
        format: صيغة التصدير (pdf, excel, csv, json)
        export_path: مسار حفظ الملف (اختياري)
        include_details: تضمين التفاصيل
        generated_by: من قام بالتصدير
    """
    report_id: str
    format: str = "pdf"
    export_path: Optional[str] = None
    include_details: bool = True
    generated_by: str = "system"


@dataclass(frozen=True)
class ScheduleReportCommand:
    """
    أمر جدولة تقرير
    
    Attributes:
        report_type: نوع التقرير
        parameters: معلمات التقرير
        frequency: التكرار (daily, weekly, monthly, quarterly, yearly)
        start_date: تاريخ البدء
        end_date: تاريخ الانتهاء (اختياري)
        recipients: قائمة المستلمين
        format: صيغة التقرير
        generated_by: من قام بالجدولة
    """
    report_type: str
    frequency: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    recipients: List[str] = field(default_factory=list)
    format: str = "pdf"
    generated_by: str = "system"


@dataclass(frozen=True)
class DeleteScheduledReportCommand:
    """
    أمر حذف جدولة تقرير
    
    Attributes:
        schedule_id: معرف الجدولة
        deleted_by: من قام بالحذف
    """
    schedule_id: str
    deleted_by: str = "system"


@dataclass(frozen=True)
class RunScheduledReportCommand:
    """
    أمر تشغيل تقرير مجدول (يدوياً)
    
    Attributes:
        schedule_id: معرف الجدولة
        executed_by: من قام بالتنفيذ
    """
    schedule_id: str
    executed_by: str = "system"


# =============================================================================
# QUERIES - استعلامات التقارير
# =============================================================================

@dataclass(frozen=True)
class GetReportQuery:
    """
    استعلام لجلب تقرير بواسطة المعرف
    
    Attributes:
        report_id: معرف التقرير
    """
    report_id: str


@dataclass(frozen=True)
class ListReportsQuery:
    """
    استعلام لقائمة التقارير
    
    Attributes:
        category: تصنيف التقرير (financial, sales, purchasing, inventory, tax, performance)
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات
    """
    category: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetScheduledReportsQuery:
    """
    استعلام لجلب التقارير المجدولة
    
    Attributes:
        user_id: معرف المستخدم (لجلب جداول المستخدم فقط)
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات
    """
    user_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetReportFormatsQuery:
    """
    استعلام لجلب صيغ التقارير المدعومة
    """
    pass


# =============================================================================
# QUERIES - تقارير مالية
# =============================================================================

@dataclass(frozen=True)
class GetTrialBalanceReportQuery:
    """
    استعلام لتوليد ميزان المراجعة
    
    Attributes:
        as_of_date: التاريخ
        currency: العملة
    """
    as_of_date: date
    currency: str = "USD"


@dataclass(frozen=True)
class GetBalanceSheetReportQuery:
    """
    استعلام لتوليد الميزانية العمومية
    
    Attributes:
        as_of_date: التاريخ
        currency: العملة
    """
    as_of_date: date
    currency: str = "USD"


@dataclass(frozen=True)
class GetIncomeStatementReportQuery:
    """
    استعلام لتوليد قائمة الدخل
    
    Attributes:
        period_start: بداية الفترة
        period_end: نهاية الفترة
        currency: العملة
        include_comparative: مقارنة مع الفترة السابقة
    """
    period_start: date
    period_end: date
    currency: str = "USD"
    include_comparative: bool = False


@dataclass(frozen=True)
class GetCashFlowReportQuery:
    """
    استعلام لتوليد قائمة التدفقات النقدية
    
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


@dataclass(frozen=True)
class GetGeneralLedgerReportQuery:
    """
    استعلام لتوليد دفتر الأستاذ العام
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        account_code: كود الحساب (اختياري)
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    account_code: Optional[str] = None


@dataclass(frozen=True)
class GetSubsidiaryLedgerReportQuery:
    """
    استعلام لتوليد دفتر الأستاذ المساعد
    
    Attributes:
        account_code: كود الحساب
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
    """
    account_code: str
    from_date: date
    to_date: date
    currency: str = "USD"


# =============================================================================
# QUERIES - تقارير المبيعات والمشتريات
# =============================================================================

@dataclass(frozen=True)
class GetSalesReportQuery:
    """
    استعلام لتوليد تقرير المبيعات
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        customer_id: معرف العميل (اختياري)
        product_code: كود المنتج (اختياري)
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    customer_id: Optional[str] = None
    product_code: Optional[str] = None


@dataclass(frozen=True)
class GetPurchasesReportQuery:
    """
    استعلام لتوليد تقرير المشتريات
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        supplier_id: معرف المورد (اختياري)
        product_code: كود المنتج (اختياري)
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    supplier_id: Optional[str] = None
    product_code: Optional[str] = None


@dataclass(frozen=True)
class GetCustomerReportQuery:
    """
    استعلام لتوليد تقرير العملاء
    
    Attributes:
        customer_id: معرف العميل (اختياري - الكل إذا لم يحدد)
        status: حالة العميل (اختياري)
    """
    customer_id: Optional[str] = None
    status: Optional[str] = None


@dataclass(frozen=True)
class GetSupplierReportQuery:
    """
    استعلام لتوليد تقرير الموردين
    
    Attributes:
        supplier_id: معرف المورد (اختياري - الكل إذا لم يحدد)
        status: حالة المورد (اختياري)
    """
    supplier_id: Optional[str] = None
    status: Optional[str] = None


# =============================================================================
# QUERIES - تقارير المخزون
# =============================================================================

@dataclass(frozen=True)
class GetInventoryReportQuery:
    """
    استعلام لتوليد تقرير المخزون
    
    Attributes:
        as_of_date: التاريخ
        include_inactive: تضمين المنتجات غير النشطة
        category: تصنيف المنتج (اختياري)
    """
    as_of_date: date
    include_inactive: bool = False
    category: Optional[str] = None


@dataclass(frozen=True)
class GetInventoryValuationReportQuery:
    """
    استعلام لتوليد تقرير تقييم المخزون
    
    Attributes:
        as_of_date: التاريخ
        method: طريقة التقييم (fifo, lifo, weighted_average)
        currency: العملة
    """
    as_of_date: date
    method: str = "fifo"
    currency: str = "USD"


@dataclass(frozen=True)
class GetLowStockReportQuery:
    """
    استعلام لتوليد تقرير المخزون المنخفض
    
    Attributes:
        threshold: الحد الأدنى للمخزون
        limit: الحد الأقصى للنتائج
    """
    threshold: int = 10
    limit: int = 100


# =============================================================================
# QUERIES - تقارير الضرائب
# =============================================================================

@dataclass(frozen=True)
class GetTaxReportQuery:
    """
    استعلام لتوليد تقرير الضرائب
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        tax_type: نوع الضريبة (اختياري)
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    tax_type: Optional[str] = None


# =============================================================================
# QUERIES - تقارير الأداء
# =============================================================================

@dataclass(frozen=True)
class GetProfitabilityReportQuery:
    """
    استعلام لتوليد تقرير الربحية
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        group_by: التجميع حسب (product, customer, category, site)
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    group_by: str = "product"


@dataclass(frozen=True)
class GetKPIReportQuery:
    """
    استعلام لتوليد تقرير مؤشرات الأداء
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
    """
    from_date: date
    to_date: date
    currency: str = "USD"


# =============================================================================
# QUERIES - تقارير العملاء والموردين
# =============================================================================

@dataclass(frozen=True)
class GetCustomerStatementReportQuery:
    """
    استعلام لتوليد كشف حساب عميل
    
    Attributes:
        customer_id: معرف العميل
        from_date: بداية الفترة (اختياري)
        to_date: نهاية الفترة (اختياري)
        currency: العملة
    """
    customer_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    currency: str = "USD"


@dataclass(frozen=True)
class GetSupplierStatementReportQuery:
    """
    استعلام لتوليد كشف حساب مورد
    
    Attributes:
        supplier_id: معرف المورد
        from_date: بداية الفترة (اختياري)
        to_date: نهاية الفترة (اختياري)
        currency: العملة
    """
    supplier_id: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    currency: str = "USD"


@dataclass(frozen=True)
class GetAgingReportQuery:
    """
    استعلام لتوليد تقرير الأعمار
    
    Attributes:
        as_of_date: التاريخ
        currency: العملة
        customer_id: معرف العميل (اختياري)
    """
    as_of_date: date
    currency: str = "USD"
    customer_id: Optional[str] = None


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Commands
    "GenerateReportCommand",
    "ExportReportCommand",
    "ScheduleReportCommand",
    "DeleteScheduledReportCommand",
    "RunScheduledReportCommand",
    
    # Queries - General
    "GetReportQuery",
    "ListReportsQuery",
    "GetScheduledReportsQuery",
    "GetReportFormatsQuery",
    
    # Queries - Financial
    "GetTrialBalanceReportQuery",
    "GetBalanceSheetReportQuery",
    "GetIncomeStatementReportQuery",
    "GetCashFlowReportQuery",
    "GetGeneralLedgerReportQuery",
    "GetSubsidiaryLedgerReportQuery",
    
    # Queries - Sales & Purchases
    "GetSalesReportQuery",
    "GetPurchasesReportQuery",
    "GetCustomerReportQuery",
    "GetSupplierReportQuery",
    
    # Queries - Inventory
    "GetInventoryReportQuery",
    "GetInventoryValuationReportQuery",
    "GetLowStockReportQuery",
    
    # Queries - Tax
    "GetTaxReportQuery",
    
    # Queries - Performance
    "GetProfitabilityReportQuery",
    "GetKPIReportQuery",
    
    # Queries - Customer & Supplier
    "GetCustomerStatementReportQuery",
    "GetSupplierStatementReportQuery",
    "GetAgingReportQuery",
]