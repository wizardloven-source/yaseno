# core/domain/financial_statements/entities.py
"""
Financial Statements Entities - كيانات القوائم المالية
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import uuid4

from .value_objects import (
    StatementId, StatementType, StatementPeriod, StatementPeriodInfo,
    StatementLine, StatementSection, IncomeStatementItem,
    BalanceSheetItem, CashFlowItem, AccountCategory, CashFlowType
)


def utc_now() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc)


@dataclass
class FinancialStatement:
    """
    AGGREGATE ROOT - القائمة المالية
    """
    id: StatementId = field(default_factory=lambda: StatementId(str(uuid4())))
    statement_type: StatementType = StatementType.INCOME_STATEMENT
    period_info: StatementPeriodInfo = field(default_factory=StatementPeriodInfo)
    currency: str = "USD"
    
    # الأقسام
    sections: List[StatementSection] = field(default_factory=list)
    
    # الإجماليات
    total: Decimal = Decimal('0')
    total_previous: Optional[Decimal] = None
    
    # بيانات التدقيق
    generated_at: datetime = field(default_factory=utc_now)
    generated_by: str = ""
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def display_name(self) -> str:
        name_map = {
            StatementType.INCOME_STATEMENT: "قائمة الدخل",
            StatementType.BALANCE_SHEET: "الميزانية العمومية",
            StatementType.CASH_FLOW: "قائمة التدفقات النقدية",
            StatementType.EQUITY_STATEMENT: "قائمة التغيرات في حقوق الملكية"
        }
        return name_map.get(self.statement_type, str(self.statement_type))
    
    @property
    def period_display(self) -> str:
        return f"{self.period_info.start_date} إلى {self.period_info.end_date}"
    
    @property
    def is_comparative(self) -> bool:
        return self.period_info.is_comparative
    
    @property
    def total_formatted(self) -> str:
        return f"{self.total:,.2f} {self.currency}"
    
    @property
    def variance(self) -> Optional[Decimal]:
        """الفرق بين الفترة الحالية والسابقة"""
        if self.total_previous is not None:
            return self.total - self.total_previous
        return None
    
    @property
    def variance_percent(self) -> Optional[Decimal]:
        """نسبة التغير بين الفترة الحالية والسابقة"""
        if self.total_previous and self.total_previous != 0:
            return ((self.total - self.total_previous) / self.total_previous) * 100
        return None
    
    def add_section(self, section: StatementSection) -> None:
        """إضافة قسم إلى القائمة"""
        self.sections.append(section)
    
    def add_sections(self, sections: List[StatementSection]) -> None:
        """إضافة أقسام متعددة"""
        self.sections.extend(sections)
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events


@dataclass
class IncomeStatement(FinancialStatement):
    """قائمة الدخل - وراثة من FinancialStatement مع خصائص إضافية"""
    
    def __init__(self, **kwargs):
        super().__init__(statement_type=StatementType.INCOME_STATEMENT, **kwargs)
    
    # إجماليات محددة لقائمة الدخل
    revenue: Decimal = Decimal('0')
    cogs: Decimal = Decimal('0')
    gross_profit: Decimal = Decimal('0')
    operating_expenses: Decimal = Decimal('0')
    operating_profit: Decimal = Decimal('0')
    other_income: Decimal = Decimal('0')
    other_expenses: Decimal = Decimal('0')
    net_income_before_tax: Decimal = Decimal('0')
    income_tax: Decimal = Decimal('0')
    net_income: Decimal = Decimal('0')
    
    @property
    def gross_margin(self) -> Optional[Decimal]:
        """هامش الربح الإجمالي"""
        if self.revenue and self.revenue != 0:
            return (self.gross_profit / self.revenue) * 100
        return None
    
    @property
    def operating_margin(self) -> Optional[Decimal]:
        """هامش الربح التشغيلي"""
        if self.revenue and self.revenue != 0:
            return (self.operating_profit / self.revenue) * 100
        return None
    
    @property
    def net_margin(self) -> Optional[Decimal]:
        """هامش الربح الصافي"""
        if self.revenue and self.revenue != 0:
            return (self.net_income / self.revenue) * 100
        return None


@dataclass
class BalanceSheet(FinancialStatement):
    """الميزانية العمومية"""
    
    def __init__(self, **kwargs):
        super().__init__(statement_type=StatementType.BALANCE_SHEET, **kwargs)
    
    # إجماليات الميزانية
    total_assets: Decimal = Decimal('0')
    total_liabilities: Decimal = Decimal('0')
    total_equity: Decimal = Decimal('0')
    
    # تفصيل الأصول
    current_assets: Decimal = Decimal('0')
    fixed_assets: Decimal = Decimal('0')
    intangible_assets: Decimal = Decimal('0')
    other_assets: Decimal = Decimal('0')
    
    # تفصيل الخصوم
    current_liabilities: Decimal = Decimal('0')
    long_term_liabilities: Decimal = Decimal('0')
    
    # حقوق الملكية
    paid_in_capital: Decimal = Decimal('0')
    retained_earnings: Decimal = Decimal('0')
    
    @property
    def is_balanced(self) -> bool:
        """هل الميزانية متوازنة؟"""
        return abs(self.total_assets - (self.total_liabilities + self.total_equity)) < 1
    
    @property
    def working_capital(self) -> Decimal:
        """رأس المال العامل"""
        return self.current_assets - self.current_liabilities
    
    @property
    def current_ratio(self) -> Optional[Decimal]:
        """نسبة التداول"""
        if self.current_liabilities and self.current_liabilities != 0:
            return self.current_assets / self.current_liabilities
        return None
    
    @property
    def debt_to_equity(self) -> Optional[Decimal]:
        """نسبة الدين إلى حقوق الملكية"""
        if self.total_equity and self.total_equity != 0:
            return self.total_liabilities / self.total_equity
        return None


@dataclass
class CashFlowStatement(FinancialStatement):
    """قائمة التدفقات النقدية"""
    
    def __init__(self, **kwargs):
        super().__init__(statement_type=StatementType.CASH_FLOW, **kwargs)
    
    # التدفقات التشغيلية
    operating_cash_flow: Decimal = Decimal('0')
    operating_activities: List[CashFlowItem] = field(default_factory=list)
    
    # التدفقات الاستثمارية
    investing_cash_flow: Decimal = Decimal('0')
    investing_activities: List[CashFlowItem] = field(default_factory=list)
    
    # التدفقات التمويلية
    financing_cash_flow: Decimal = Decimal('0')
    financing_activities: List[CashFlowItem] = field(default_factory=list)
    
    # الإجماليات
    net_cash_flow: Decimal = Decimal('0')
    beginning_cash: Decimal = Decimal('0')
    ending_cash: Decimal = Decimal('0')
    
    @property
    def free_cash_flow(self) -> Decimal:
        """التدفق النقدي الحر"""
        return self.operating_cash_flow + self.investing_cash_flow
    
    @property
    def cash_flow_to_debt(self) -> Optional[Decimal]:
        """نسبة التدفق النقدي إلى الدين"""
        if self.ending_cash and self.ending_cash != 0:
            return self.operating_cash_flow / self.ending_cash
        return None


@dataclass
class EquityStatement(FinancialStatement):
    """قائمة التغيرات في حقوق الملكية"""
    
    def __init__(self, **kwargs):
        super().__init__(statement_type=StatementType.EQUITY_STATEMENT, **kwargs)
    
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
    
    @property
    def total_beginning_equity_formatted(self) -> str:
        return f"{self.total_beginning_equity:,.2f} {self.currency}"
    
    @property
    def total_ending_equity_formatted(self) -> str:
        return f"{self.total_ending_equity:,.2f} {self.currency}"
    
    @property
    def equity_change(self) -> Decimal:
        """التغير في حقوق الملكية"""
        return self.total_ending_equity - self.total_beginning_equity
    
    @property
    def equity_change_percent(self) -> Optional[Decimal]:
        """نسبة التغير في حقوق الملكية"""
        if self.total_beginning_equity and self.total_beginning_equity != 0:
            return (self.equity_change / self.total_beginning_equity) * 100
        return None


# استيراد مفقود - تم نقله إلى الأعلى
# from uuid import uuid4