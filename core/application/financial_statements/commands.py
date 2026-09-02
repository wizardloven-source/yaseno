# core/application/financial_statements/commands.py
"""
Financial Statements Commands and Queries - الأوامر والاستعلامات للقوائم المالية
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


# =============================================================================
# COMMANDS - أوامر توليد القوائم المالية
# =============================================================================

@dataclass(frozen=True)
class GenerateIncomeStatementCommand:
    """
    أمر توليد قائمة الدخل
    
    Attributes:
        period_start: تاريخ بداية الفترة
        period_end: تاريخ نهاية الفترة
        currency: العملة المطلوبة للقائمة
        include_comparative: هل تشمل مقارنة مع الفترة السابقة؟
        generated_by: من قام بتوليد القائمة
    """
    period_start: date
    period_end: date
    currency: str = "USD"
    include_comparative: bool = False
    generated_by: str = "system"


@dataclass(frozen=True)
class GenerateBalanceSheetCommand:
    """
    أمر توليد الميزانية العمومية
    
    Attributes:
        as_of_date: التاريخ الذي تتم عنده الميزانية
        currency: العملة المطلوبة للقائمة
        generated_by: من قام بتوليد القائمة
    """
    as_of_date: date
    currency: str = "USD"
    generated_by: str = "system"


@dataclass(frozen=True)
class GenerateCashFlowCommand:
    """
    أمر توليد قائمة التدفقات النقدية
    
    Attributes:
        period_start: تاريخ بداية الفترة
        period_end: تاريخ نهاية الفترة
        currency: العملة المطلوبة للقائمة
        method: طريقة الحساب (direct, indirect)
        generated_by: من قام بتوليد القائمة
    """
    period_start: date
    period_end: date
    currency: str = "USD"
    method: str = "indirect"  # direct, indirect
    generated_by: str = "system"


@dataclass(frozen=True)
class GenerateEquityStatementCommand:
    """
    أمر توليد قائمة التغيرات في حقوق الملكية
    
    Attributes:
        period_start: تاريخ بداية الفترة
        period_end: تاريخ نهاية الفترة
        currency: العملة المطلوبة للقائمة
        generated_by: من قام بتوليد القائمة
    """
    period_start: date
    period_end: date
    currency: str = "USD"
    generated_by: str = "system"


@dataclass(frozen=True)
class GenerateTrialBalanceCommand:
    """
    أمر توليد ميزان المراجعة
    
    Attributes:
        as_of_date: التاريخ الذي تتم عنده الميزان
        currency: العملة المطلوبة
        include_zero_balance: تضمين الحسابات ذات الرصيد الصفري
        generated_by: من قام بتوليد الميزان
    """
    as_of_date: date
    currency: str = "USD"
    include_zero_balance: bool = False
    generated_by: str = "system"


# =============================================================================
# ✅ الأوامر المفقودة - تم إضافتها
# =============================================================================

@dataclass(frozen=True)
class ExportFinancialStatementCommand:
    """
    أمر تصدير قائمة مالية
    
    Attributes:
        statement_id: معرف القائمة المالية
        format: صيغة التصدير (pdf, excel, csv, json)
        export_path: مسار حفظ الملف (اختياري)
        include_details: تضمين التفاصيل
        generated_by: من قام بالتصدير
    """
    statement_id: str
    format: str = "pdf"
    export_path: Optional[str] = None
    include_details: bool = True
    generated_by: str = "system"


@dataclass(frozen=True)
class PrintFinancialStatementCommand:
    """
    أمر طباعة قائمة مالية
    
    Attributes:
        statement_id: معرف القائمة المالية
        printer_name: اسم الطابعة (اختياري)
        copies: عدد النسخ
        paper_size: حجم الورق (A4, A5, Letter)
        orientation: اتجاه الطباعة (portrait, landscape)
        generated_by: من قام بالطباعة
    """
    statement_id: str
    printer_name: Optional[str] = None
    copies: int = 1
    paper_size: str = "A4"
    orientation: str = "portrait"
    generated_by: str = "system"


# =============================================================================
# QUERIES - استعلامات جلب القوائم المالية
# =============================================================================

@dataclass(frozen=True)
class GetFinancialStatementQuery:
    """
    استعلام لجلب قائمة مالية بواسطة المعرف
    
    Attributes:
        statement_id: معرف القائمة المالية
    """
    statement_id: str


@dataclass(frozen=True)
class ListFinancialStatementsQuery:
    """
    استعلام لقائمة القوائم المالية مع خيارات التصفية
    
    Attributes:
        statement_type: نوع القائمة (income_statement, balance_sheet, cash_flow, equity_statement)
        from_date: تاريخ البداية
        to_date: تاريخ النهاية
        fiscal_year: السنة المالية
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات
        order_by: ترتيب النتائج
        order_desc: ترتيب تنازلي
    """
    statement_type: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    fiscal_year: Optional[int] = None
    limit: int = 100
    offset: int = 0
    order_by: str = "generated_at"
    order_desc: bool = True


@dataclass(frozen=True)
class GetLatestIncomeStatementQuery:
    """
    استعلام لجلب أحدث قائمة دخل
    
    Attributes:
        currency: العملة المطلوبة
    """
    currency: str = "USD"


@dataclass(frozen=True)
class GetLatestBalanceSheetQuery:
    """
    استعلام لجلب أحدث ميزانية عمومية
    
    Attributes:
        currency: العملة المطلوبة
    """
    currency: str = "USD"


# =============================================================================
# ✅ QUERIES - النسب المالية (تم إضافتها)
# =============================================================================

@dataclass(frozen=True)
class GetFinancialRatiosQuery:
    """
    استعلام لجلب النسب المالية
    
    Attributes:
        as_of_date: التاريخ الذي تتم عنده النسب
        currency: العملة المطلوبة
    """
    as_of_date: date
    currency: str = "USD"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Commands
    "GenerateIncomeStatementCommand",
    "GenerateBalanceSheetCommand",
    "GenerateCashFlowCommand",
    "GenerateEquityStatementCommand",
    "GenerateTrialBalanceCommand",
    "ExportFinancialStatementCommand",
    "PrintFinancialStatementCommand",
    
    # Queries
    "GetFinancialStatementQuery",
    "ListFinancialStatementsQuery",
    "GetLatestIncomeStatementQuery",
    "GetLatestBalanceSheetQuery",
    "GetFinancialRatiosQuery",  # ✅ تمت الإضافة
]