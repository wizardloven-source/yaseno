# core/application/financial_statements/dtos.py
"""
Financial Statements DTOs - كائنات نقل البيانات للقوائم المالية
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


# =============================================================================
# DTOs لأسطر وأقسام القوائم
# =============================================================================

@dataclass
class StatementLineDTO:
    """
    سطر في القائمة المالية - DTO
    
    Attributes:
        code: كود الحساب/البند
        name: اسم الحساب/البند
        amount: المبلغ
        currency: العملة
        level: مستوى التبويب (للهيكل الهرمي)
        is_total: هل هو سطر إجمالي؟
        is_subtotal: هل هو سطر مجموع فرعي؟
        is_section_header: هل هو عنوان قسم؟
        parent_id: معرف السطر الأب (للهيكل الهرمي)
    """
    code: str
    name: str
    amount: Decimal
    currency: str
    level: int = 0
    is_total: bool = False
    is_subtotal: bool = False
    is_section_header: bool = False
    parent_id: Optional[str] = None
    
    @property
    def amount_formatted(self) -> str:
        """المبلغ منسقاً للعرض"""
        return f"{self.amount:,.2f} {self.currency}"
    
    @property
    def indent(self) -> str:
        """المسافة البادئة حسب المستوى"""
        return "  " * self.level
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض مع المسافة البادئة"""
        return f"{self.indent}{self.name}"


@dataclass
class StatementSectionDTO:
    """
    قسم في القائمة المالية - DTO
    
    Attributes:
        id: معرف القسم
        name: اسم القسم
        category: تصنيف القسم
        lines: قائمة الأسطر في القسم
        total: إجمالي القسم
        currency: العملة
    """
    id: str
    name: str
    category: str
    lines: List[StatementLineDTO]
    total: Decimal
    currency: str
    
    @property
    def total_formatted(self) -> str:
        """الإجمالي منسقاً"""
        return f"{self.total:,.2f} {self.currency}"
    
    @property
    def line_count(self) -> int:
        """عدد الأسطر في القسم"""
        return len(self.lines)


# =============================================================================
# DTOs للقوائم المالية الرئيسية
# =============================================================================

@dataclass
class IncomeStatementDTO:
    """
    قائمة الدخل - DTO
    
    تحتوي على جميع بنود قائمة الدخل مع النسب المئوية
    """
    # المعلومات الأساسية
    id: str
    period_start: date
    period_end: date
    currency: str
    generated_at: datetime
    generated_by: str = "system"
    
    # الإيرادات
    revenue: Decimal = Decimal('0')
    revenue_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    # تكلفة البضاعة المباعة
    cogs: Decimal = Decimal('0')
    cogs_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    # الربح الإجمالي
    gross_profit: Decimal = Decimal('0')
    
    # مصروفات التشغيل
    operating_expenses: Decimal = Decimal('0')
    operating_expenses_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    # الربح التشغيلي
    operating_profit: Decimal = Decimal('0')
    
    # إيرادات ومصروفات أخرى
    other_income: Decimal = Decimal('0')
    other_income_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    other_expenses: Decimal = Decimal('0')
    other_expenses_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    # صافي الدخل قبل الضريبة
    net_income_before_tax: Decimal = Decimal('0')
    
    # ضريبة الدخل
    income_tax: Decimal = Decimal('0')
    income_tax_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    # صافي الدخل
    net_income: Decimal = Decimal('0')
    
    # النسب المئوية (مقارنة بالإيرادات)
    gross_margin: Optional[Decimal] = None
    operating_margin: Optional[Decimal] = None
    net_margin: Optional[Decimal] = None
    
    # للمقارنة مع الفترة السابقة
    previous_period_net_income: Optional[Decimal] = None
    previous_period_revenue: Optional[Decimal] = None
    growth_percent: Optional[Decimal] = None
    
    # الأقسام (للتفصيل)
    sections: List[StatementSectionDTO] = field(default_factory=list)
    
    # ========== الخصائص المساعدة ==========
    
    @property
    def period_display(self) -> str:
        """عرض الفترة"""
        return f"{self.period_start} إلى {self.period_end}"
    
    @property
    def revenue_formatted(self) -> str:
        return f"{self.revenue:,.2f} {self.currency}"
    
    @property
    def gross_profit_formatted(self) -> str:
        return f"{self.gross_profit:,.2f} {self.currency}"
    
    @property
    def operating_profit_formatted(self) -> str:
        return f"{self.operating_profit:,.2f} {self.currency}"
    
    @property
    def net_income_formatted(self) -> str:
        return f"{self.net_income:,.2f} {self.currency}"
    
    @property
    def net_income_formatted_arabic(self) -> str:
        """صافي الدخل منسقاً بالأرقام العربية"""
        from core.i18n.utils import convert_to_arabic_numbers
        return convert_to_arabic_numbers(self.net_income_formatted)
    
    @property
    def is_profit(self) -> bool:
        """هل هناك ربح؟"""
        return self.net_income > 0
    
    @property
    def is_loss(self) -> bool:
        """هل هناك خسارة؟"""
        return self.net_income < 0
    
    @property
    def growth_display(self) -> str:
        """عرض النمو مع إشارة"""
        if self.growth_percent is None:
            return "-"
        sign = "+" if self.growth_percent > 0 else ""
        return f"{sign}{self.growth_percent:.1f}%"
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتسلسل"""
        return {
            'id': self.id,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'currency': self.currency,
            'generated_at': self.generated_at.isoformat(),
            'generated_by': self.generated_by,
            'revenue': float(self.revenue),
            'cogs': float(self.cogs),
            'gross_profit': float(self.gross_profit),
            'operating_expenses': float(self.operating_expenses),
            'operating_profit': float(self.operating_profit),
            'other_income': float(self.other_income),
            'other_expenses': float(self.other_expenses),
            'net_income_before_tax': float(self.net_income_before_tax),
            'income_tax': float(self.income_tax),
            'net_income': float(self.net_income),
            'gross_margin': float(self.gross_margin) if self.gross_margin else None,
            'operating_margin': float(self.operating_margin) if self.operating_margin else None,
            'net_margin': float(self.net_margin) if self.net_margin else None,
        }


@dataclass
class BalanceSheetDTO:
    """
    الميزانية العمومية - DTO
    
    تحتوي على الأصول والخصوم وحقوق الملكية مع المؤشرات المالية
    """
    # المعلومات الأساسية
    id: str
    as_of_date: date
    currency: str
    generated_at: datetime
    generated_by: str = "system"
    
    # الأصول
    current_assets: Decimal = Decimal('0')
    current_assets_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    fixed_assets: Decimal = Decimal('0')
    fixed_assets_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    intangible_assets: Decimal = Decimal('0')
    intangible_assets_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    other_assets: Decimal = Decimal('0')
    other_assets_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    total_assets: Decimal = Decimal('0')
    
    # الخصوم
    current_liabilities: Decimal = Decimal('0')
    current_liabilities_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    long_term_liabilities: Decimal = Decimal('0')
    long_term_liabilities_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    total_liabilities: Decimal = Decimal('0')
    
    # حقوق الملكية
    paid_in_capital: Decimal = Decimal('0')
    retained_earnings: Decimal = Decimal('0')
    other_equity: Decimal = Decimal('0')
    total_equity: Decimal = Decimal('0')
    
    # المؤشرات المالية
    working_capital: Optional[Decimal] = None
    current_ratio: Optional[Decimal] = None
    quick_ratio: Optional[Decimal] = None
    debt_to_equity: Optional[Decimal] = None
    debt_to_assets: Optional[Decimal] = None
    
    is_balanced: bool = True
    difference: Optional[Decimal] = None
    
    # الأقسام
    sections: List[StatementSectionDTO] = field(default_factory=list)
    
    # للمقارنة مع الفترة السابقة
    previous_period_total_assets: Optional[Decimal] = None
    previous_period_total_equity: Optional[Decimal] = None
    
    # ========== الخصائص المساعدة ==========
    
    @property
    def as_of_display(self) -> str:
        """عرض التاريخ"""
        return self.as_of_date.strftime("%Y-%m-%d")
    
    @property
    def total_assets_formatted(self) -> str:
        return f"{self.total_assets:,.2f} {self.currency}"
    
    @property
    def total_liabilities_formatted(self) -> str:
        return f"{self.total_liabilities:,.2f} {self.currency}"
    
    @property
    def total_equity_formatted(self) -> str:
        return f"{self.total_equity:,.2f} {self.currency}"
    
    @property
    def working_capital_formatted(self) -> str:
        if self.working_capital is None:
            return "-"
        return f"{self.working_capital:,.2f} {self.currency}"
    
    @property
    def current_ratio_display(self) -> str:
        if self.current_ratio is None:
            return "-"
        return f"{self.current_ratio:.2f}"
    
    @property
    def debt_to_equity_display(self) -> str:
        if self.debt_to_equity is None:
            return "-"
        return f"{self.debt_to_equity:.2f}"
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتسلسل"""
        return {
            'id': self.id,
            'as_of_date': self.as_of_date.isoformat(),
            'currency': self.currency,
            'generated_at': self.generated_at.isoformat(),
            'generated_by': self.generated_by,
            'total_assets': float(self.total_assets),
            'total_liabilities': float(self.total_liabilities),
            'total_equity': float(self.total_equity),
            'is_balanced': self.is_balanced,
            'working_capital': float(self.working_capital) if self.working_capital else None,
            'current_ratio': float(self.current_ratio) if self.current_ratio else None,
            'debt_to_equity': float(self.debt_to_equity) if self.debt_to_equity else None,
        }


@dataclass
class CashFlowItemDTO:
    """
    بند في قائمة التدفقات النقدية - DTO
    
    Attributes:
        code: كود البند
        name: اسم البند
        amount: المبلغ
        currency: العملة
        flow_type: نوع التدفق (operating, investing, financing)
    """
    code: str
    name: str
    amount: Decimal
    currency: str
    flow_type: str
    
    @property
    def amount_formatted(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"
    
    @property
    def is_positive(self) -> bool:
        return self.amount > 0
    
    @property
    def is_negative(self) -> bool:
        return self.amount < 0


@dataclass
class CashFlowStatementDTO:
    """
    قائمة التدفقات النقدية - DTO
    
    تحتوي على التدفقات التشغيلية والاستثمارية والتمويلية
    """
    # المعلومات الأساسية
    id: str
    period_start: date
    period_end: date
    currency: str
    generated_at: datetime
    generated_by: str = "system"
    method: str = "indirect"
    
    # التدفقات التشغيلية
    operating_cash_flow: Decimal = Decimal('0')
    operating_activities: List[CashFlowItemDTO] = field(default_factory=list)
    operating_activities_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    # التدفقات الاستثمارية
    investing_cash_flow: Decimal = Decimal('0')
    investing_activities: List[CashFlowItemDTO] = field(default_factory=list)
    investing_activities_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    # التدفقات التمويلية
    financing_cash_flow: Decimal = Decimal('0')
    financing_activities: List[CashFlowItemDTO] = field(default_factory=list)
    financing_activities_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    # الإجماليات
    net_cash_flow: Decimal = Decimal('0')
    beginning_cash: Decimal = Decimal('0')
    ending_cash: Decimal = Decimal('0')
    
    # المؤشرات الإضافية
    free_cash_flow: Optional[Decimal] = None
    cash_flow_to_debt: Optional[Decimal] = None
    
    # الأقسام
    sections: List[StatementSectionDTO] = field(default_factory=list)
    
    # ========== الخصائص المساعدة ==========
    
    @property
    def period_display(self) -> str:
        return f"{self.period_start} إلى {self.period_end}"
    
    @property
    def operating_cash_flow_formatted(self) -> str:
        return f"{self.operating_cash_flow:,.2f} {self.currency}"
    
    @property
    def investing_cash_flow_formatted(self) -> str:
        return f"{self.investing_cash_flow:,.2f} {self.currency}"
    
    @property
    def financing_cash_flow_formatted(self) -> str:
        return f"{self.financing_cash_flow:,.2f} {self.currency}"
    
    @property
    def net_cash_flow_formatted(self) -> str:
        return f"{self.net_cash_flow:,.2f} {self.currency}"
    
    @property
    def ending_cash_formatted(self) -> str:
        return f"{self.ending_cash:,.2f} {self.currency}"
    
    @property
    def is_positive_operating(self) -> bool:
        return self.operating_cash_flow > 0
    
    @property
    def is_positive_net(self) -> bool:
        return self.net_cash_flow > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتسلسل"""
        return {
            'id': self.id,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'currency': self.currency,
            'generated_at': self.generated_at.isoformat(),
            'generated_by': self.generated_by,
            'operating_cash_flow': float(self.operating_cash_flow),
            'investing_cash_flow': float(self.investing_cash_flow),
            'financing_cash_flow': float(self.financing_cash_flow),
            'net_cash_flow': float(self.net_cash_flow),
            'beginning_cash': float(self.beginning_cash),
            'ending_cash': float(self.ending_cash),
        }


@dataclass
class EquityStatementDTO:
    """
    قائمة التغيرات في حقوق الملكية - DTO
    """
    id: str
    period_start: date
    period_end: date
    currency: str
    generated_at: datetime
    generated_by: str = "system"
    
    # رأس المال
    beginning_capital: Decimal = Decimal('0')
    additional_capital: Decimal = Decimal('0')
    ending_capital: Decimal = Decimal('0')
    
    # الأرباح المحتجزة
    beginning_retained_earnings: Decimal = Decimal('0')
    net_income: Decimal = Decimal('0')
    dividends_paid: Decimal = Decimal('0')
    ending_retained_earnings: Decimal = Decimal('0')
    
    # حقوق ملكية أخرى
    other_equity_beginning: Decimal = Decimal('0')
    other_equity_changes: Decimal = Decimal('0')
    other_equity_ending: Decimal = Decimal('0')
    
    # الإجمالي
    total_beginning_equity: Decimal = Decimal('0')
    total_ending_equity: Decimal = Decimal('0')
    
    sections: List[StatementSectionDTO] = field(default_factory=list)
    
    @property
    def total_beginning_equity_formatted(self) -> str:
        return f"{self.total_beginning_equity:,.2f} {self.currency}"
    
    @property
    def total_ending_equity_formatted(self) -> str:
        return f"{self.total_ending_equity:,.2f} {self.currency}"


@dataclass
class TrialBalanceDTO:
    """
    ميزان المراجعة - DTO
    """
    id: str
    as_of_date: date
    currency: str
    generated_at: datetime
    generated_by: str = "system"
    
    # الحسابات
    accounts: List[StatementLineDTO] = field(default_factory=list)
    
    # الإجماليات
    total_debits: Decimal = Decimal('0')
    total_credits: Decimal = Decimal('0')
    is_balanced: bool = True
    difference: Decimal = Decimal('0')
    
    # التصنيفات
    by_account_type: Dict[str, Decimal] = field(default_factory=dict)
    
    @property
    def total_debits_formatted(self) -> str:
        return f"{self.total_debits:,.2f} {self.currency}"
    
    @property
    def total_credits_formatted(self) -> str:
        return f"{self.total_credits:,.2f} {self.currency}"
    
    @property
    def account_count(self) -> int:
        return len(self.accounts)


# =============================================================================
# ✅ DTOs الجديدة المطلوبة
# =============================================================================

@dataclass
class FinancialStatementDTO:
    """
    قائمة مالية عامة - DTO أساسي
    
    يستخدم كفئة أساسية للقوائم المالية أو للقوائم العامة
    """
    id: str
    statement_type: str  # income_statement, balance_sheet, cash_flow, equity_statement
    period_start: date
    period_end: date
    currency: str
    total: Decimal
    generated_at: datetime
    generated_by: str = "system"
    
    # أقسام القائمة
    sections: List[StatementSectionDTO] = field(default_factory=list)
    
    # بيانات إضافية (مرنة)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def period_display(self) -> str:
        """عرض الفترة"""
        return f"{self.period_start} إلى {self.period_end}"
    
    @property
    def total_formatted(self) -> str:
        """الإجمالي منسقاً"""
        return f"{self.total:,.2f} {self.currency}"
    
    @property
    def type_display(self) -> str:
        """نوع القائمة بالعربية"""
        types = {
            "income_statement": "قائمة الدخل",
            "balance_sheet": "الميزانية العمومية",
            "cash_flow": "قائمة التدفقات النقدية",
            "equity_statement": "قائمة التغيرات في حقوق الملكية",
            "trial_balance": "ميزان المراجعة",
        }
        return types.get(self.statement_type, self.statement_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتسلسل"""
        return {
            'id': self.id,
            'statement_type': self.statement_type,
            'period_start': self.period_start.isoformat(),
            'period_end': self.period_end.isoformat(),
            'currency': self.currency,
            'total': float(self.total),
            'generated_at': self.generated_at.isoformat(),
            'generated_by': self.generated_by,
            'sections': [
                {
                    'id': s.id,
                    'name': s.name,
                    'category': s.category,
                    'total': float(s.total),
                    'currency': s.currency,
                    'lines': [
                        {
                            'code': l.code,
                            'name': l.name,
                            'amount': float(l.amount),
                            'currency': l.currency,
                            'level': l.level,
                            'is_total': l.is_total,
                            'is_subtotal': l.is_subtotal,
                            'is_section_header': l.is_section_header,
                            'parent_id': l.parent_id,
                        }
                        for l in s.lines
                    ]
                }
                for s in self.sections
            ],
            'metadata': self.metadata,
        }


@dataclass
class ExportFinancialStatementDTO:
    """
    نتيجة تصدير قائمة مالية - DTO
    
    Attributes:
        success: هل نجحت عملية التصدير؟
        message: رسالة الحالة
        format: صيغة الملف المصدر
        statement_id: معرف القائمة المالية
        exported_by: من قام بالتصدير
        exported_at: وقت التصدير
        file_path: مسار الملف المصدر (اختياري)
        rows_exported: عدد الصفوف المصدرة (لـ CSV/Excel)
    """
    success: bool
    message: str
    format: str
    statement_id: str
    exported_by: str
    exported_at: datetime
    file_path: Optional[str] = None
    rows_exported: int = 0
    
    @property
    def is_success(self) -> bool:
        return self.success
    
    @property
    def file_name(self) -> str:
        """اسم الملف من المسار"""
        if self.file_path:
            return self.file_path.split('/')[-1].split('\\')[-1]
        return ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message': self.message,
            'file_path': self.file_path,
            'format': self.format,
            'statement_id': self.statement_id,
            'exported_by': self.exported_by,
            'exported_at': self.exported_at.isoformat(),
            'rows_exported': self.rows_exported,
        }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # DTOs الأساسية
    "StatementLineDTO",
    "StatementSectionDTO",
    
    # القوائم المالية
    "IncomeStatementDTO",
    "BalanceSheetDTO",
    "CashFlowItemDTO",
    "CashFlowStatementDTO",
    "EquityStatementDTO",
    "TrialBalanceDTO",
    
    # ✅ DTO العام (جديد)
    "FinancialStatementDTO",
    
    # ✅ DTO التصدير (جديد)
    "ExportFinancialStatementDTO",
]