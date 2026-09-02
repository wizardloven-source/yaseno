# core/domain/financial_statements/value_objects.py
"""
Financial Statements Value Objects - كائنات القيمة للقوائم المالية
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any


class StatementType(Enum):
    """نوع القائمة المالية"""
    INCOME_STATEMENT = "income_statement"           # قائمة الدخل
    BALANCE_SHEET = "balance_sheet"                 # الميزانية العمومية
    CASH_FLOW = "cash_flow"                         # قائمة التدفقات النقدية
    EQUITY_STATEMENT = "equity_statement"           # قائمة التغيرات في حقوق الملكية
    TRIAL_BALANCE = "trial_balance"                 # ميزان المراجعة


class StatementPeriod(Enum):
    """فترة القائمة المالية"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class CashFlowType(Enum):
    """نوع التدفق النقدي"""
    OPERATING = "operating"      # تشغيلي
    INVESTING = "investing"      # استثماري
    FINANCING = "financing"      # تمويلي


class AccountCategory(Enum):
    """تصنيف الحسابات للقوائم المالية"""
    # قائمة الدخل
    REVENUE = "revenue"
    COGS = "cogs"                    # تكلفة البضاعة المباعة
    OPERATING_EXPENSE = "operating_expense"
    OTHER_INCOME = "other_income"
    OTHER_EXPENSE = "other_expense"
    INCOME_TAX = "income_tax"
    
    # الميزانية العمومية
    CURRENT_ASSET = "current_asset"
    FIXED_ASSET = "fixed_asset"
    INTANGIBLE_ASSET = "intangible_asset"
    CURRENT_LIABILITY = "current_liability"
    LONG_TERM_LIABILITY = "long_term_liability"
    EQUITY = "equity"
    
    # التدفقات النقدية
    CASH_OPERATING = "cash_operating"
    CASH_INVESTING = "cash_investing"
    CASH_FINANCING = "cash_financing"


@dataclass(frozen=True)
class StatementId:
    """معرف القائمة المالية"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("StatementId cannot be empty")
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> 'StatementId':
        return cls(value)


@dataclass(frozen=True)
class FinancialLine:
    """سطر مالي في القائمة"""
    code: str                          # كود الحساب
    name: str                          # اسم الحساب/البند
    amount: Decimal                    # المبلغ
    currency: str                      # العملة
    category: AccountCategory          # التصنيف
    parent_code: Optional[str] = None  # كود الحساب الأب
    level: int = 0                     # مستوى التبويب
    is_total: bool = False             # هل هو سطر إجمالي؟
    is_subtotal: bool = False          # هل هو سطر مجموع فرعي?
    
    def __post_init__(self):
        if self.amount is None:
            object.__setattr__(self, 'amount', Decimal('0'))


@dataclass(frozen=True)
class StatementLine:
    """سطر في القائمة المالية"""
    id: str
    code: str
    name: str
    amount: Decimal
    currency: str
    category: AccountCategory
    level: int = 0
    parent_id: Optional[str] = None
    is_total: bool = False
    is_subtotal: bool = False
    is_section_header: bool = False
    
    @property
    def amount_formatted(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"
    
    @property
    def indent(self) -> str:
        """المسافة البادئة حسب المستوى"""
        return "  " * self.level


@dataclass(frozen=True)
class StatementSection:
    """قسم من القائمة المالية"""
    id: str
    name: str
    category: AccountCategory
    lines: List[StatementLine]
    total: Decimal
    currency: str
    
    @property
    def total_formatted(self) -> str:
        return f"{self.total:,.2f} {self.currency}"
    
    @property
    def line_count(self) -> int:
        return len(self.lines)


@dataclass
class StatementPeriodInfo:
    """معلومات فترة القائمة"""
    period_type: StatementPeriod
    start_date: date
    end_date: date
    period_name: str
    fiscal_year: int
    is_comparative: bool = False
    previous_period_start: Optional[date] = None
    previous_period_end: Optional[date] = None


@dataclass(frozen=True)
class IncomeStatementItem:
    """بند في قائمة الدخل"""
    code: str
    name: str
    amount: Decimal
    currency: str
    category: AccountCategory
    is_subtotal: bool = False
    children: List['IncomeStatementItem'] = field(default_factory=list)
    
    @property
    def amount_formatted(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"


@dataclass(frozen=True)
class BalanceSheetItem:
    """بند في الميزانية العمومية"""
    code: str
    name: str
    amount: Decimal
    currency: str
    category: AccountCategory
    is_subtotal: bool = False
    children: List['BalanceSheetItem'] = field(default_factory=list)
    
    @property
    def amount_formatted(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"


@dataclass(frozen=True)
class CashFlowItem:
    """بند في قائمة التدفقات النقدية"""
    code: str
    name: str
    amount: Decimal
    currency: str
    flow_type: CashFlowType
    is_subtotal: bool = False
    children: List['CashFlowItem'] = field(default_factory=list)
    
    @property
    def amount_formatted(self) -> str:
        return f"{self.amount:,.2f} {self.currency}"