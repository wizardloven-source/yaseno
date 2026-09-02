# core/domain/financial_statements/services.py
"""
Financial Statements Services - خدمات القوائم المالية
"""

from decimal import Decimal
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass

from core.domain.accounting.interfaces import ILedgerRepository
from core.domain.shared.value_objects import AccountCode
from core.domain.shared.value_objects import Money

from .entities import IncomeStatement, BalanceSheet, CashFlowStatement
from .value_objects import (
    StatementPeriodInfo, StatementPeriod, AccountCategory,
    StatementLine, StatementSection, CashFlowType,
    IncomeStatementItem, BalanceSheetItem, CashFlowItem
)


class AccountClassifier:
    """
    تصنيف الحسابات للقوائم المالية
    """
    
    # خريطة تصنيف الحسابات حسب النطاق الرقمي
    ACCOUNT_RANGES = {
        # قائمة الدخل
        range(4000, 5000): AccountCategory.REVENUE,
        range(5000, 5200): AccountCategory.COGS,
        range(5200, 5400): AccountCategory.OPERATING_EXPENSE,
        range(5400, 5600): AccountCategory.OTHER_INCOME,
        range(5600, 5800): AccountCategory.OTHER_EXPENSE,
        range(5800, 6000): AccountCategory.INCOME_TAX,
        
        # الميزانية العمومية - أصول
        range(1000, 1100): AccountCategory.CURRENT_ASSET,      # 1000-1099 نقد وصناديق
        range(1100, 1200): AccountCategory.CURRENT_ASSET,      # 1100-1199 حسابات مدينة
        range(1200, 1300): AccountCategory.CURRENT_ASSET,      # 1200-1299 مخزون
        range(1300, 1400): AccountCategory.CURRENT_ASSET,      # 1300-1399 أصول متداولة أخرى
        range(1500, 1600): AccountCategory.FIXED_ASSET,        # 1500-1599 أصول ثابتة
        range(1600, 1700): AccountCategory.INTANGIBLE_ASSET,   # 1600-1699 أصول غير ملموسة
        
        # الميزانية العمومية - خصوم
        range(2000, 2100): AccountCategory.CURRENT_LIABILITY,  # 2000-2099 خصوم متداولة
        range(2100, 2200): AccountCategory.LONG_TERM_LIABILITY, # 2100-2199 خصوم طويلة الأجل
        
        # الميزانية العمومية - حقوق ملكية
        range(3000, 3100): AccountCategory.EQUITY,             # 3000-3099 رأس المال
        range(3100, 3200): AccountCategory.EQUITY,             # 3100-3199 أرباح محتجزة
    }
    
    @classmethod
    def classify(cls, account_code: str) -> AccountCategory:
        """
        تصنيف الحساب بناءً على الكود
        
        Args:
            account_code: كود الحساب (مثل "1010")
        
        Returns:
            AccountCategory: تصنيف الحساب
        """
        try:
            code_num = int(account_code)
            for code_range, category in cls.ACCOUNT_RANGES.items():
                if code_num in code_range:
                    return category
        except (ValueError, TypeError):
            pass
        
        # تصنيف افتراضي
        if account_code.startswith('1'):
            return AccountCategory.CURRENT_ASSET
        elif account_code.startswith('2'):
            return AccountCategory.CURRENT_LIABILITY
        elif account_code.startswith('3'):
            return AccountCategory.EQUITY
        elif account_code.startswith('4'):
            return AccountCategory.REVENUE
        elif account_code.startswith('5'):
            return AccountCategory.OPERATING_EXPENSE
        
        return AccountCategory.OTHER_EXPENSE
    
    @classmethod
    def is_income_statement_account(cls, account_code: str) -> bool:
        """هل الحساب يظهر في قائمة الدخل؟"""
        category = cls.classify(account_code)
        return category in [
            AccountCategory.REVENUE, AccountCategory.COGS,
            AccountCategory.OPERATING_EXPENSE, AccountCategory.OTHER_INCOME,
            AccountCategory.OTHER_EXPENSE, AccountCategory.INCOME_TAX
        ]
    
    @classmethod
    def is_balance_sheet_account(cls, account_code: str) -> bool:
        """هل الحساب يظهر في الميزانية العمومية؟"""
        category = cls.classify(account_code)
        return category in [
            AccountCategory.CURRENT_ASSET, AccountCategory.FIXED_ASSET,
            AccountCategory.INTANGIBLE_ASSET, AccountCategory.CURRENT_LIABILITY,
            AccountCategory.LONG_TERM_LIABILITY, AccountCategory.EQUITY
        ]


class FinancialStatementGenerator:
    """
    مولد القوائم المالية
    """
    
    def __init__(self, ledger_repository: ILedgerRepository):
        self._ledger_repo = ledger_repository
    
    # =========================================================================
    # قائمة الدخل
    # =========================================================================
    
    def generate_income_statement(
        self,
        period_info: StatementPeriodInfo,
        currency: str = "USD"
    ) -> IncomeStatement:
        """
        توليد قائمة الدخل
        
        Args:
            period_info: معلومات الفترة
            currency: العملة
        
        Returns:
            IncomeStatement: قائمة الدخل
        """
        statement = IncomeStatement(
            period_info=period_info,
            currency=currency
        )
        
        # جلب أرصدة الحسابات في الفترة
        balances = self._get_period_balances(period_info.start_date, period_info.end_date)
        
        # تصنيف الحسابات
        revenue_accounts = {}
        cogs_accounts = {}
        operating_expenses = {}
        other_income = {}
        other_expenses = {}
        income_tax = {}
        
        for account_code, balance in balances.items():
            category = AccountClassifier.classify(account_code)
            
            if category == AccountCategory.REVENUE:
                revenue_accounts[account_code] = balance
            elif category == AccountCategory.COGS:
                cogs_accounts[account_code] = balance
            elif category == AccountCategory.OPERATING_EXPENSE:
                operating_expenses[account_code] = balance
            elif category == AccountCategory.OTHER_INCOME:
                other_income[account_code] = balance
            elif category == AccountCategory.OTHER_EXPENSE:
                other_expenses[account_code] = balance
            elif category == AccountCategory.INCOME_TAX:
                income_tax[account_code] = balance
        
        # حساب الإجماليات
        revenue_total = sum(balances.values())
        cogs_total = sum(cogs_accounts.values())
        gross_profit = revenue_total - cogs_total
        operating_total = sum(operating_expenses.values())
        operating_profit = gross_profit - operating_total
        other_income_total = sum(other_income.values())
        other_expenses_total = sum(other_expenses.values())
        income_tax_total = sum(income_tax.values())
        
        net_income_before_tax = operating_profit + other_income_total - other_expenses_total
        net_income = net_income_before_tax - income_tax_total
        
        # تعيين الإجماليات
        statement.revenue = revenue_total
        statement.cogs = cogs_total
        statement.gross_profit = gross_profit
        statement.operating_expenses = operating_total
        statement.operating_profit = operating_profit
        statement.other_income = other_income_total
        statement.other_expenses = other_expenses_total
        statement.net_income_before_tax = net_income_before_tax
        statement.income_tax = income_tax_total
        statement.net_income = net_income
        statement.total = net_income
        
        # بناء الأقسام
        statement.sections = [
            self._create_section("الإيرادات", AccountCategory.REVENUE, revenue_accounts),
            self._create_section("تكلفة البضاعة المباعة", AccountCategory.COGS, cogs_accounts),
            self._create_section("مصروفات التشغيل", AccountCategory.OPERATING_EXPENSE, operating_expenses),
            self._create_section("إيرادات أخرى", AccountCategory.OTHER_INCOME, other_income),
            self._create_section("مصروفات أخرى", AccountCategory.OTHER_EXPENSE, other_expenses),
            self._create_section("ضريبة الدخل", AccountCategory.INCOME_TAX, income_tax),
        ]
        
        return statement
    
    # =========================================================================
    # الميزانية العمومية
    # =========================================================================
    
    def generate_balance_sheet(
        self,
        as_of_date: date,
        currency: str = "USD"
    ) -> BalanceSheet:
        """
        توليد الميزانية العمومية
        
        Args:
            as_of_date: التاريخ
            currency: العملة
        
        Returns:
            BalanceSheet: الميزانية العمومية
        """
        period_info = StatementPeriodInfo(
            period_type=StatementPeriod.CUSTOM,
            start_date=as_of_date,
            end_date=as_of_date,
            period_name=f"في {as_of_date}",
            fiscal_year=as_of_date.year
        )
        
        statement = BalanceSheet(
            period_info=period_info,
            currency=currency
        )
        
        # جلب أرصدة الحسابات في التاريخ
        balances = self._get_balances_as_of(as_of_date)
        
        # تصنيف الحسابات
        current_assets = {}
        fixed_assets = {}
        intangible_assets = {}
        other_assets = {}
        current_liabilities = {}
        long_term_liabilities = {}
        equity = {}
        
        for account_code, balance in balances.items():
            category = AccountClassifier.classify(account_code)
            
            if category == AccountCategory.CURRENT_ASSET:
                current_assets[account_code] = balance
            elif category == AccountCategory.FIXED_ASSET:
                fixed_assets[account_code] = balance
            elif category == AccountCategory.INTANGIBLE_ASSET:
                intangible_assets[account_code] = balance
            elif category == AccountCategory.CURRENT_LIABILITY:
                current_liabilities[account_code] = balance
            elif category == AccountCategory.LONG_TERM_LIABILITY:
                long_term_liabilities[account_code] = balance
            elif category == AccountCategory.EQUITY:
                equity[account_code] = balance
        
        # حساب الإجماليات
        statement.current_assets = sum(current_assets.values())
        statement.fixed_assets = sum(fixed_assets.values())
        statement.intangible_assets = sum(intangible_assets.values())
        statement.other_assets = sum(other_assets.values())
        statement.total_assets = (
            statement.current_assets + statement.fixed_assets +
            statement.intangible_assets + statement.other_assets
        )
        
        statement.current_liabilities = sum(current_liabilities.values())
        statement.long_term_liabilities = sum(long_term_liabilities.values())
        statement.total_liabilities = statement.current_liabilities + statement.long_term_liabilities
        
        statement.paid_in_capital = sum(equity.values())
        statement.retained_earnings = Decimal('0')  # سيتم حسابه من القيد
        statement.total_equity = statement.paid_in_capital + statement.retained_earnings
        statement.total = statement.total_assets
        
        # بناء الأقسام
        statement.sections = [
            self._create_section("الأصول المتداولة", AccountCategory.CURRENT_ASSET, current_assets),
            self._create_section("الأصول الثابتة", AccountCategory.FIXED_ASSET, fixed_assets),
            self._create_section("الأصول غير الملموسة", AccountCategory.INTANGIBLE_ASSET, intangible_assets),
            self._create_section("الخصوم المتداولة", AccountCategory.CURRENT_LIABILITY, current_liabilities),
            self._create_section("الخصوم طويلة الأجل", AccountCategory.LONG_TERM_LIABILITY, long_term_liabilities),
            self._create_section("حقوق الملكية", AccountCategory.EQUITY, equity),
        ]
        
        return statement
    
    # =========================================================================
    # قائمة التدفقات النقدية
    # =========================================================================
    
    def generate_cash_flow_statement(
        self,
        period_info: StatementPeriodInfo,
        currency: str = "USD"
    ) -> CashFlowStatement:
        """
        توليد قائمة التدفقات النقدية (طريقة غير مباشرة)
        
        Args:
            period_info: معلومات الفترة
            currency: العملة
        
        Returns:
            CashFlowStatement: قائمة التدفقات النقدية
        """
        statement = CashFlowStatement(
            period_info=period_info,
            currency=currency
        )
        
        # الحصول على الأرصدة
        start_balances = self._get_balances_as_of(period_info.start_date)
        end_balances = self._get_balances_as_of(period_info.end_date)
        
        # حساب التدفقات التشغيلية (طريقة غير مباشرة)
        net_income = self._get_net_income(period_info.start_date, period_info.end_date)
        
        # حساب التغيرات في الأصول والخصوم التشغيلية
        operating_activities = []
        
        # إضافة صافي الدخل
        operating_activities.append(CashFlowItem(
            code="NET_INCOME",
            name="صافي الدخل",
            amount=net_income,
            currency=currency,
            flow_type=CashFlowType.OPERATING
        ))
        
        # حساب التغيرات في الحسابات التشغيلية
        changes = self._calculate_working_capital_changes(start_balances, end_balances)
        
        for account_code, change in changes.items():
            category = AccountClassifier.classify(account_code)
            # عرض التغيرات في الأصول كسالب، والخصوم كموجب
            if category in [AccountCategory.CURRENT_ASSET]:
                operating_activities.append(CashFlowItem(
                    code=account_code,
                    name=f"تغير في {account_code}",
                    amount=-change,
                    currency=currency,
                    flow_type=CashFlowType.OPERATING
                ))
            elif category in [AccountCategory.CURRENT_LIABILITY]:
                operating_activities.append(CashFlowItem(
                    code=account_code,
                    name=f"تغير في {account_code}",
                    amount=change,
                    currency=currency,
                    flow_type=CashFlowType.OPERATING
                ))
        
        statement.operating_cash_flow = sum(item.amount for item in operating_activities)
        statement.operating_activities = operating_activities
        
        # حساب التدفقات الاستثمارية
        investing_cash_flow = self._calculate_investing_cash_flow(
            period_info.start_date,
            period_info.end_date
        )
        statement.investing_cash_flow = investing_cash_flow
        statement.investing_activities = []
        
        # حساب التدفقات التمويلية
        financing_cash_flow = self._calculate_financing_cash_flow(
            period_info.start_date,
            period_info.end_date
        )
        statement.financing_cash_flow = financing_cash_flow
        statement.financing_activities = []
        
        # الإجماليات
        statement.net_cash_flow = (
            statement.operating_cash_flow +
            statement.investing_cash_flow +
            statement.financing_cash_flow
        )
        
        # حساب الرصيد الافتتاحي والختامي
        statement.beginning_cash = self._get_cash_balance(period_info.start_date)
        statement.ending_cash = self._get_cash_balance(period_info.end_date)
        statement.total = statement.net_cash_flow
        
        return statement
    
    # =========================================================================
    # دوال مساعدة
    # =========================================================================
    
    def _get_period_balances(self, start_date: date, end_date: date) -> Dict[str, Decimal]:
        """الحصول على أرصدة الحسابات في الفترة"""
        # هذا يحتاج إلى تنفيذ يعتمد على المستودع
        return {}
    
    def _get_balances_as_of(self, as_of_date: date) -> Dict[str, Decimal]:
        """الحصول على أرصدة الحسابات في تاريخ معين"""
        return {}
    
    def _get_net_income(self, start_date: date, end_date: date) -> Decimal:
        """الحصول على صافي الدخل في الفترة"""
        return Decimal('0')
    
    def _get_cash_balance(self, as_of_date: date) -> Decimal:
        """الحصول على رصيد النقدية"""
        return Decimal('0')
    
    def _calculate_working_capital_changes(
        self,
        start_balances: Dict[str, Decimal],
        end_balances: Dict[str, Decimal]
    ) -> Dict[str, Decimal]:
        """حساب التغيرات في رأس المال العامل"""
        changes = {}
        all_accounts = set(start_balances.keys()) | set(end_balances.keys())
        
        for account_code in all_accounts:
            start = start_balances.get(account_code, Decimal('0'))
            end = end_balances.get(account_code, Decimal('0'))
            changes[account_code] = end - start
        
        return changes
    
    def _calculate_investing_cash_flow(self, start_date: date, end_date: date) -> Decimal:
        """حساب التدفقات الاستثمارية"""
        return Decimal('0')
    
    def _calculate_financing_cash_flow(self, start_date: date, end_date: date) -> Decimal:
        """حساب التدفقات التمويلية"""
        return Decimal('0')
    
    def _create_section(
        self,
        name: str,
        category: AccountCategory,
        accounts: Dict[str, Decimal]
    ) -> StatementSection:
        """إنشاء قسم من الحسابات"""
        lines = []
        total = Decimal('0')
        
        for account_code, balance in accounts.items():
            lines.append(StatementLine(
                id=account_code,
                code=account_code,
                name=self._get_account_name(account_code),
                amount=balance,
                currency="USD",
                category=category,
                level=1
            ))
            total += balance
        
        return StatementSection(
            id=category.value,
            name=name,
            category=category,
            lines=lines,
            total=total,
            currency="USD"
        )
    
    def _get_account_name(self, account_code: str) -> str:
        """الحصول على اسم الحساب"""
        # سيتم تنفيذها باستخدام AccountRepository
        return account_code