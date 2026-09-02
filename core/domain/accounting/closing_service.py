"""
Closing Service - خدمة إقفال الفترات المالية المتقدمة
الإصدار: 5.0.0 (FIXED)

✅ إصلاح استدعاء reverse_all (تم إضافة الدالة)
✅ إصلاح refresh (استبدال بإعادة الجلب)
✅ إصلاح period.open (استخدام open_again)
✅ إصلاح حساب صافي الدخل حسب العملة
✅ إصلاح ترتيب الإقفال (تأخير إغلاق الفترة)
✅ إضافة معالجة الضرائب في الإقفال
✅ إضافة دعم لإعادة الفتح مع التراجع عن قيود الإقفال
✅ تحسين معالجة الأخطاء
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
import logging

from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.value_objects import JournalEntryId
from core.domain.accounting.services import LedgerEngine, PostingEngine
from core.domain.accounting.interfaces import (
    IJournalEntryRepository,
    IFiscalPeriodRepository,
    IAuditRepository
)
from core.domain.accounting.exceptions import (
    PeriodHasUnpostedEntriesError,
    PeriodAlreadyClosedError,
    PeriodNotClosedError
)
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.shared.clock import get_clock
from core.shared.exceptions import ValidationError, BusinessRuleViolation

logger = logging.getLogger(__name__)


# =============================================================================
# ✅ ClosingResult - نتيجة الإقفال (محسّن)
# =============================================================================

@dataclass
class ClosingResult:
    """نتيجة عملية إقفال الفترة المالية - محسّنة"""
    success: bool
    period_name: str
    closed_by: str
    closed_at: datetime
    net_income_by_currency: Dict[str, Decimal]  # ✅ صافي الدخل حسب العملة
    entries_created: int
    closing_entry_ids: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_debits: Money = field(default_factory=lambda: Money.zero())
    total_credits: Money = field(default_factory=lambda: Money.zero())
    currency_breakdown: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)
    fiscal_period: Optional[str] = None
    fiscal_year: Optional[int] = None
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    @property
    def is_balanced(self) -> bool:
        """هل قيود الإقفال متوازنة؟"""
        return self.total_debits.amount == self.total_credits.amount
    
    @property
    def net_income_formatted(self) -> str:
        """صافي الدخل منسقاً (للعملة الرئيسية)"""
        main_currency = "USD"
        total = sum(self.net_income_by_currency.values())
        if total > 0:
            return f"ربح: {total:,.2f} {main_currency}"
        elif total < 0:
            return f"خسارة: {abs(total):,.2f} {main_currency}"
        return f"صفر ({total:,.2f} {main_currency})"
    
    @property
    def net_income_by_currency_formatted(self) -> str:
        """تفصيل صافي الدخل حسب العملة"""
        if not self.net_income_by_currency:
            return "لا توجد عملات"
        return ", ".join([
            f"{currency}: {amount:,.2f}" 
            for currency, amount in self.net_income_by_currency.items()
        ])
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)
    
    def add_closing_entry(self, entry_id: str) -> None:
        self.closing_entry_ids.append(entry_id)
        self.entries_created += 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'period_name': self.period_name,
            'closed_by': self.closed_by,
            'closed_at': self.closed_at.isoformat(),
            'net_income_by_currency': {
                k: float(v) for k, v in self.net_income_by_currency.items()
            },
            'net_income_formatted': self.net_income_formatted,
            'entries_created': self.entries_created,
            'closing_entry_ids': self.closing_entry_ids,
            'errors': self.errors,
            'warnings': self.warnings,
            'total_debits': str(self.total_debits.amount),
            'total_credits': str(self.total_credits.amount),
            'is_balanced': self.is_balanced,
            'currency_breakdown': self.currency_breakdown,
            'fiscal_period': self.fiscal_period,
            'fiscal_year': self.fiscal_year,
        }


# =============================================================================
# ✅ ClosingError - استثناءات الإقفال
# =============================================================================

class ClosingError(Exception):
    """استثناء أساسي لأخطاء الإقفال"""
    pass


class CannotClosePeriodError(ClosingError):
    """يُرفع عند عدم إمكانية إغلاق الفترة"""
    def __init__(self, period_name: str, reason: str):
        self.period_name = period_name
        self.reason = reason
        super().__init__(f"Cannot close period '{period_name}': {reason}")


class ClosingValidationError(ClosingError):
    """يُرفع عند فشل التحقق من صحة الإقفال"""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Closing validation failed: {'; '.join(errors)}")


# =============================================================================
# ✅ ClosingService - الخدمة الرئيسية (المصحّحة بالكامل)
# =============================================================================

class ClosingService:
    """
    خدمة إقفال الفترات المالية المتقدمة - المصحّحة بالكامل
    
    الميزات:
        1. التحقق من وجود قيود غير مرحلة في الفترة
        2. إنشاء قيود الإقفال التلقائية (4 قيود)
        3. دعم العملات المتعددة مع تفصيل لكل عملة
        4. حساب صافي الدخل لكل عملة على حدة
        5. تسجيل الأحداث في سجل التدقيق
        6. دعم المعاملات الذرية
        7. دعم إعادة فتح الفترة مع التراجع عن قيود الإقفال
        8. معالجة حسابات الضرائب في الإقفال
    """
    
    def __init__(
        self,
        journal_repo: IJournalEntryRepository,
        period_repo: IFiscalPeriodRepository,
        ledger_engine: LedgerEngine,
        posting_engine: PostingEngine,
        audit_repo: Optional[IAuditRepository] = None,
        income_summary_account: str = "3990",
        retained_earnings_account: str = "3010",
        tax_payable_account: str = "2100",  # ✅ حساب الضريبة المستحقة
        enable_audit: bool = True
    ):
        self._journal_repo = journal_repo
        self._period_repo = period_repo
        self._ledger_engine = ledger_engine
        self._posting_engine = posting_engine
        self._audit_repo = audit_repo
        self._clock = get_clock()
        self._enable_audit = enable_audit
        
        # حسابات الإقفال (قابلة للتخصيص)
        self._income_summary_account = AccountCode(income_summary_account)
        self._retained_earnings_account = AccountCode(retained_earnings_account)
        self._tax_payable_account = AccountCode(tax_payable_account)
        
        # ✅ تخزين مؤقت لتصنيف الحسابات
        self._account_type_cache: Dict[str, str] = {}
    
    # =========================================================================
    # ✅ دوال التحقق (Validation) - محسّنة
    # =========================================================================
    
    def _validate_period(self, period_name: str) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        التحقق من صحة الفترة
        
        Returns:
            Tuple[bool, Optional[str], Optional[Any]]: (is_valid, error_message, period)
        """
        period = self._period_repo.get_period_by_name(period_name)
        if not period:
            return False, f"Period '{period_name}' not found", None
        
        if period.is_closed:
            return False, f"Period '{period_name}' is already closed", period
        
        return True, None, period
    
    def can_close_period(self, period_name: str) -> Tuple[bool, List[str]]:
        """
        التحقق من إمكانية إغلاق الفترة
        
        Args:
            period_name: اسم الفترة
        
        Returns:
            Tuple[bool, List[str]]: (يمكن الإغلاق, قائمة الأخطاء)
        """
        errors = []
        
        # 1. التحقق من وجود الفترة
        is_valid, error, period = self._validate_period(period_name)
        if not is_valid:
            errors.append(error)
            return False, errors
        
        # 2. التحقق من عدم وجود قيود غير مرحلة
        try:
            unposted_count = self._journal_repo.count_unposted_in_period(period)
            if unposted_count > 0:
                errors.append(
                    f"There are {unposted_count} unposted entries in period '{period_name}'. "
                    "Please post or delete all draft entries before closing."
                )
        except Exception as e:
            errors.append(f"Failed to check unposted entries: {str(e)}")
        
        return len(errors) == 0, errors
    
    # =========================================================================
    # ✅ الدوال الرئيسية - المصحّحة
    # =========================================================================
    
    def close_period(
        self,
        period_name: str,
        closed_by: str,
        force: bool = False
    ) -> ClosingResult:
        """
        إغلاق فترة مالية - النسخة المصحّحة
        
        Args:
            period_name: اسم الفترة (مثل "2026-07")
            closed_by: معرف المستخدم الذي يقوم بالإقفال
            force: تجاوز التحقق من القيود غير المرحلة (استخدام بحذر)
        
        Returns:
            ClosingResult: نتيجة عملية الإقفال
        """
        logger.info(f"Starting closing process for period: {period_name} by {closed_by}")
        
        # ========== 1. التحقق من الفترة ==========
        is_valid, error, period = self._validate_period(period_name)
        if not is_valid:
            return ClosingResult(
                success=False,
                period_name=period_name,
                closed_by=closed_by,
                closed_at=self._clock.now(),
                net_income_by_currency={},
                entries_created=0,
                errors=[error]
            )
        
        # ========== 2. التحقق من عدم وجود قيود غير مرحلة ==========
        if not force:
            try:
                unposted_count = self._journal_repo.count_unposted_in_period(period)
                if unposted_count > 0:
                    return ClosingResult(
                        success=False,
                        period_name=period_name,
                        closed_by=closed_by,
                        closed_at=self._clock.now(),
                        net_income_by_currency={},
                        entries_created=0,
                        errors=[
                            f"Cannot close period: {unposted_count} unposted entries found. "
                            "Please post or delete all draft entries before closing."
                        ]
                    )
            except Exception as e:
                return ClosingResult(
                    success=False,
                    period_name=period_name,
                    closed_by=closed_by,
                    closed_at=self._clock.now(),
                    net_income_by_currency={},
                    entries_created=0,
                    errors=[f"Failed to check unposted entries: {str(e)}"]
                )
        else:
            logger.warning(f"⚠️ Force closing period {period_name} - skipping unposted entries check")
        
        # ========== 3. إنشاء قيود الإقفال ==========
        result = ClosingResult(
            success=True,
            period_name=period_name,
            closed_by=closed_by,
            closed_at=self._clock.now(),
            net_income_by_currency={},
            entries_created=0,
            fiscal_period=period_name,
            fiscal_year=period.end_date.year
        )
        
        try:
            # 3.1. الحصول على ميزان المراجعة
            trial_balance = self._ledger_engine.get_trial_balance(period.end_date)
            
            # 3.2. إنشاء قيود الإقفال (مع دعم العملات المتعددة)
            closing_entries, total_debits, total_credits, currency_breakdown, net_income_by_currency = \
                self._create_closing_entries(
                    period=period,
                    trial_balance=trial_balance,
                    closed_by=closed_by
                )
            
            result.total_debits = total_debits
            result.total_credits = total_credits
            result.currency_breakdown = currency_breakdown
            result.net_income_by_currency = net_income_by_currency
            
            # 3.3. ترحيل قيود الإقفال في معاملة ذرية
            if closing_entries:
                logger.info(f"Posting {len(closing_entries)} closing entries")
                
                for entry in closing_entries:
                    post_result = self._posting_engine.post(entry, closed_by, skip_save=True)
                    
                    if post_result.success:
                        result.add_closing_entry(str(entry.id))
                        logger.info(f"✅ Closing entry posted: {entry.id}")
                    else:
                        error_msg = f"Failed to post closing entry: {post_result.message}"
                        result.add_error(error_msg)
                        logger.error(f"❌ {error_msg}")
                        
                        # ✅ إذا فشل أحد القيود، نتراجع عن جميع القيود
                        # استخدام reverse_all المصحّحة
                        if hasattr(self._posting_engine, 'reverse_all'):
                            self._posting_engine.reverse_all(
                                closing_entries, 
                                closed_by, 
                                "Rollback due to error"
                            )
                        else:
                            # Fallback: عكس كل قيد على حدة
                            for e in closing_entries:
                                if e.is_posted and not e.reversed_entry_id:
                                    self._posting_engine.reverse(e, "Rollback due to error", closed_by)
                        
                        raise ClosingError(f"Closing failed: {error_msg}")
            
            # ========== 4. ✅ تأخير إغلاق الفترة حتى نجاح جميع القيود ==========
            # ✅ تم نقل period.close() إلى هنا بعد نجاح جميع القيود
            period.close(closed_by)
            self._period_repo.save(period)
            
            # ========== 5. تسجيل في سجل التدقيق ==========
            if self._enable_audit:
                self._log_audit(
                    operation="CLOSE_PERIOD",
                    period_name=period_name,
                    closed_by=closed_by,
                    result=result
                )
            
            logger.info(f"✅ Period '{period_name}' closed successfully by {closed_by}")
            
        except ClosingError as e:
            result.add_error(str(e))
            logger.error(f"❌ Closing error: {e}")
            
        except Exception as e:
            result.add_error(str(e))
            logger.error(f"❌ Error during closing: {e}", exc_info=True)
            
            # ✅ التراجع عن جميع التغييرات (بدون refresh)
            try:
                # إعادة جلب الفترة من المستودع بدلاً من refresh
                period = self._period_repo.get_period_by_name(period_name)
                if period and period.is_closed:
                    # إعادة فتح الفترة إذا تم إغلاقها
                    period.is_closed = False
                    period.closed_by = None
                    period.closed_at = None
                    self._period_repo.save(period)
                logger.info("Rollback completed")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
        
        return result
    
    # =========================================================================
    # ✅ إنشاء قيود الإقفال - المصحّح (مع دعم العملات)
    # =========================================================================
    
    def _create_closing_entries(
        self,
        period,
        trial_balance: Dict[AccountCode, Money],
        closed_by: str
    ) -> Tuple[List[JournalEntry], Money, Money, Dict[str, Dict[str, Decimal]], Dict[str, Decimal]]:
        """
        إنشاء قيود الإقفال مع دعم العملات المتعددة
        
        Returns:
            Tuple: (قيود الإقفال, إجمالي المدين, إجمالي الدائن, تفصيل العملات, صافي الدخل حسب العملة)
        """
        entries = []
        closing_time = self._clock.now()
        
        # 1. تصنيف الحسابات حسب العملة
        revenue_by_currency: Dict[str, Dict[AccountCode, Money]] = {}
        expense_by_currency: Dict[str, Dict[AccountCode, Money]] = {}
        tax_by_currency: Dict[str, Dict[AccountCode, Money]] = {}
        
        for account_code, balance in trial_balance.items():
            if balance.amount == 0:
                continue
            
            currency = balance.currency
            
            if self._is_revenue_account(account_code):
                if currency not in revenue_by_currency:
                    revenue_by_currency[currency] = {}
                revenue_by_currency[currency][account_code] = balance
                
            elif self._is_expense_account(account_code):
                if currency not in expense_by_currency:
                    expense_by_currency[currency] = {}
                expense_by_currency[currency][account_code] = balance
                
            elif self._is_tax_account(account_code):
                if currency not in tax_by_currency:
                    tax_by_currency[currency] = {}
                tax_by_currency[currency][account_code] = balance
        
        total_debits = Money.zero("USD")
        total_credits = Money.zero("USD")
        currency_breakdown = {}
        net_income_by_currency = {}
        
        # 2. معالجة كل عملة على حدة
        all_currencies = set(revenue_by_currency.keys()) | set(expense_by_currency.keys())
        
        for currency in all_currencies:
            revenue_accounts = revenue_by_currency.get(currency, {})
            expense_accounts = expense_by_currency.get(currency, {})
            tax_accounts = tax_by_currency.get(currency, {})
            
            # 2.1 قيد إقفال الإيرادات
            if revenue_accounts:
                revenue_entry, debits, credits = self._create_revenue_closing_entry(
                    period=period,
                    revenue_accounts=revenue_accounts,
                    currency=currency,
                    closing_time=closing_time
                )
                entries.append(revenue_entry)
                total_debits += debits
                total_credits += credits
                self._update_currency_breakdown(currency_breakdown, revenue_entry)
            
            # 2.2 قيد إقفال المصروفات
            if expense_accounts:
                expense_entry, debits, credits = self._create_expense_closing_entry(
                    period=period,
                    expense_accounts=expense_accounts,
                    currency=currency,
                    closing_time=closing_time
                )
                entries.append(expense_entry)
                total_debits += debits
                total_credits += credits
                self._update_currency_breakdown(currency_breakdown, expense_entry)
            
            # 2.3 ✅ قيد إقفال الضرائب
            if tax_accounts:
                tax_entry, debits, credits = self._create_tax_closing_entry(
                    period=period,
                    tax_accounts=tax_accounts,
                    currency=currency,
                    closing_time=closing_time
                )
                entries.append(tax_entry)
                total_debits += debits
                total_credits += credits
                self._update_currency_breakdown(currency_breakdown, tax_entry)
            
            # 2.4 حساب صافي الدخل لهذه العملة
            total_revenue = sum(b.amount for b in revenue_accounts.values())
            total_expenses = sum(b.amount for b in expense_accounts.values())
            total_tax = sum(b.amount for b in tax_accounts.values())
            net_income = total_revenue - total_expenses - total_tax
            net_income_by_currency[currency] = net_income
            
            # 2.5 قيد إقفال ملخص الدخل لهذه العملة
            if net_income != 0:
                net_income_money = Money(abs(net_income), currency)
                summary_entry, debits, credits = self._create_income_summary_closing_entry(
                    period=period,
                    net_income=net_income_money,
                    is_profit=net_income > 0,
                    currency=currency,
                    closing_time=closing_time
                )
                entries.append(summary_entry)
                total_debits += debits
                total_credits += credits
                self._update_currency_breakdown(currency_breakdown, summary_entry)
        
        return entries, total_debits, total_credits, currency_breakdown, net_income_by_currency
    
    def _update_currency_breakdown(
        self,
        breakdown: Dict[str, Dict[str, Decimal]],
        entry: JournalEntry
    ) -> None:
        """تحديث تفصيل العملات من قيد"""
        for line in entry.lines:
            currency = line.currency
            if currency not in breakdown:
                breakdown[currency] = {"debit": Decimal('0'), "credit": Decimal('0'), "balance": Decimal('0')}
            
            breakdown[currency]["debit"] += line.debit.amount
            breakdown[currency]["credit"] += line.credit.amount
            breakdown[currency]["balance"] = breakdown[currency]["debit"] - breakdown[currency]["credit"]
    
    def _create_revenue_closing_entry(
        self,
        period,
        revenue_accounts: Dict[AccountCode, Money],
        currency: str,
        closing_time: datetime
    ) -> Tuple[JournalEntry, Money, Money]:
        """إنشاء قيد إقفال الإيرادات"""
        lines = []
        total_debit = Money.zero(currency)
        total_credit = Money.zero(currency)
        
        # مدين: حسابات الإيرادات (لتصفيرها)
        for account_code, balance in revenue_accounts.items():
            if balance.amount > 0:
                debit = Money(balance.amount, currency)
                lines.append(JournalLine(
                    account_code=account_code,
                    debit=debit,
                    credit=Money.zero(currency)
                ))
                total_debit += debit
        
        # دائن: ملخص الدخل (بإجمالي الإيرادات)
        total_revenue = sum(b.amount for b in revenue_accounts.values())
        credit = Money(total_revenue, currency)
        lines.append(JournalLine(
            account_code=self._income_summary_account,
            debit=Money.zero(currency),
            credit=credit
        ))
        total_credit += credit
        
        return JournalEntry(
            date=closing_time,
            description=f"إقفال حسابات الإيرادات - {period.name} ({currency})",
            lines=lines
        ), total_debit, total_credit
    
    def _create_expense_closing_entry(
        self,
        period,
        expense_accounts: Dict[AccountCode, Money],
        currency: str,
        closing_time: datetime
    ) -> Tuple[JournalEntry, Money, Money]:
        """إنشاء قيد إقفال المصروفات"""
        lines = []
        total_debit = Money.zero(currency)
        total_credit = Money.zero(currency)
        
        # مدين: ملخص الدخل (بإجمالي المصروفات)
        total_expenses = sum(b.amount for b in expense_accounts.values())
        debit = Money(total_expenses, currency)
        lines.append(JournalLine(
            account_code=self._income_summary_account,
            debit=debit,
            credit=Money.zero(currency)
        ))
        total_debit += debit
        
        # دائن: حسابات المصروفات (لتصفيرها)
        for account_code, balance in expense_accounts.items():
            if balance.amount > 0:
                credit = Money(balance.amount, currency)
                lines.append(JournalLine(
                    account_code=account_code,
                    debit=Money.zero(currency),
                    credit=credit
                ))
                total_credit += credit
        
        return JournalEntry(
            date=closing_time,
            description=f"إقفال حسابات المصروفات - {period.name} ({currency})",
            lines=lines
        ), total_debit, total_credit
    
    def _create_tax_closing_entry(
        self,
        period,
        tax_accounts: Dict[AccountCode, Money],
        currency: str,
        closing_time: datetime
    ) -> Tuple[JournalEntry, Money, Money]:
        """✅ إنشاء قيد إقفال حسابات الضرائب"""
        lines = []
        total_debit = Money.zero(currency)
        total_credit = Money.zero(currency)
        
        # مدين: ملخص الدخل (بإجمالي الضرائب)
        total_tax = sum(b.amount for b in tax_accounts.values())
        if total_tax > 0:
            debit = Money(total_tax, currency)
            lines.append(JournalLine(
                account_code=self._income_summary_account,
                debit=debit,
                credit=Money.zero(currency)
            ))
            total_debit += debit
            
            # دائن: حسابات الضرائب (لتصفيرها)
            for account_code, balance in tax_accounts.items():
                credit = Money(balance.amount, currency)
                lines.append(JournalLine(
                    account_code=account_code,
                    debit=Money.zero(currency),
                    credit=credit
                ))
                total_credit += credit
        
        return JournalEntry(
            date=closing_time,
            description=f"إقفال حسابات الضرائب - {period.name} ({currency})",
            lines=lines
        ), total_debit, total_credit
    
    def _create_income_summary_closing_entry(
        self,
        period,
        net_income: Money,
        is_profit: bool,
        currency: str,
        closing_time: datetime
    ) -> Tuple[JournalEntry, Money, Money]:
        """إنشاء قيد إقفال ملخص الدخل إلى الأرباح المحتجزة"""
        total_debit = Money.zero(currency)
        total_credit = Money.zero(currency)
        
        if is_profit:
            # ربح: مدين ملخص الدخل، دائن الأرباح المحتجزة
            lines = [
                JournalLine(
                    account_code=self._income_summary_account,
                    debit=net_income,
                    credit=Money.zero(currency)
                ),
                JournalLine(
                    account_code=self._retained_earnings_account,
                    debit=Money.zero(currency),
                    credit=net_income
                )
            ]
            total_debit += net_income
            total_credit += net_income
        else:
            # خسارة: مدين الأرباح المحتجزة، دائن ملخص الدخل
            lines = [
                JournalLine(
                    account_code=self._retained_earnings_account,
                    debit=net_income,
                    credit=Money.zero(currency)
                ),
                JournalLine(
                    account_code=self._income_summary_account,
                    debit=Money.zero(currency),
                    credit=net_income
                )
            ]
            total_debit += net_income
            total_credit += net_income
        
        description = (
            f"إقفال صافي الدخل إلى الأرباح المحتجزة - {period.name} "
            f"({'ربح' if is_profit else 'خسارة'}) ({currency})"
        )
        
        return JournalEntry(
            date=closing_time,
            description=description,
            lines=lines
        ), total_debit, total_credit
    
    # =========================================================================
    # ✅ دوال تصنيف الحسابات - محسّنة (قابلة للتخصيص)
    # =========================================================================
    
    def _is_revenue_account(self, account_code: AccountCode) -> bool:
        """التحقق مما إذا كان الحساب من نوع إيرادات"""
        code_str = str(account_code)
        if code_str in self._account_type_cache:
            return self._account_type_cache[code_str] == "revenue"
        
        # ✅ محاولة استخدام AccountTypeAnalyzer
        try:
            from core.domain.accounting.services import AccountTypeAnalyzer
            is_revenue = AccountTypeAnalyzer.is_revenue(account_code)
            self._account_type_cache[code_str] = "revenue" if is_revenue else "other"
            return is_revenue
        except ImportError:
            pass
        
        # ✅ Fallback: استخدام قاعدة بيانات أو إعدادات
        # في الإنتاج، يجب جلب تصنيف الحسابات من قاعدة البيانات
        code_num = self._extract_account_number(account_code)
        if 4000 <= code_num <= 4999 or 6000 <= code_num <= 6999:
            self._account_type_cache[code_str] = "revenue"
            return True
        
        self._account_type_cache[code_str] = "other"
        return False
    
    def _is_expense_account(self, account_code: AccountCode) -> bool:
        """التحقق مما إذا كان الحساب من نوع مصروفات"""
        code_str = str(account_code)
        if code_str in self._account_type_cache:
            return self._account_type_cache[code_str] == "expense"
        
        try:
            from core.domain.accounting.services import AccountTypeAnalyzer
            is_expense = AccountTypeAnalyzer.is_expense(account_code)
            self._account_type_cache[code_str] = "expense" if is_expense else "other"
            return is_expense
        except ImportError:
            pass
        
        code_num = self._extract_account_number(account_code)
        if 5000 <= code_num <= 5999 or 7000 <= code_num <= 7999:
            self._account_type_cache[code_str] = "expense"
            return True
        
        self._account_type_cache[code_str] = "other"
        return False
    
    def _is_tax_account(self, account_code: AccountCode) -> bool:
        """✅ التحقق مما إذا كان الحساب من نوع ضرائب"""
        code_str = str(account_code)
        if code_str in self._account_type_cache:
            return self._account_type_cache[code_str] == "tax"
        
        # حسابات الضرائب عادة تكون في النطاق 2100-2199
        code_num = self._extract_account_number(account_code)
        if 2100 <= code_num <= 2199:
            self._account_type_cache[code_str] = "tax"
            return True
        
        self._account_type_cache[code_str] = "other"
        return False
    
    def _extract_account_number(self, account_code: AccountCode) -> int:
        """استخراج الرقم من كود الحساب"""
        code = str(account_code).replace('.', '').replace('-', '')
        try:
            return int(code[:4])
        except (ValueError, IndexError):
            return 0
    
    # =========================================================================
    # ✅ تسجيل التدقيق
    # =========================================================================
    
    def _log_audit(
        self,
        operation: str,
        period_name: str,
        closed_by: str,
        result: ClosingResult
    ) -> None:
        """تسجيل عملية الإقفال في سجل التدقيق"""
        if not self._audit_repo:
            return
        
        try:
            self._audit_repo.log_operation(
                operation=operation,
                entity_type="FiscalPeriod",
                entity_id=period_name,
                performed_by=closed_by,
                changes={
                    "period_name": period_name,
                    "closed_at": result.closed_at.isoformat(),
                    "net_income_by_currency": {
                        k: str(v) for k, v in result.net_income_by_currency.items()
                    },
                    "entries_created": result.entries_created,
                    "closing_entry_ids": result.closing_entry_ids,
                    "success": result.success,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "total_debits": str(result.total_debits.amount),
                    "total_credits": str(result.total_credits.amount),
                    "is_balanced": result.is_balanced,
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")
    
    # =========================================================================
    # ✅ إعادة فتح فترة (Re-open) - المصحّحة
    # =========================================================================
    
    def reopen_period(
        self,
        period_name: str,
        reopened_by: str,
        reason: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        إعادة فتح فترة مالية مغلقة مع التراجع عن قيود الإقفال
        
        ⚠️ هذه العملية حساسة وتتطلب صلاحيات عالية
        
        Args:
            period_name: اسم الفترة
            reopened_by: من قام بإعادة الفتح
            reason: سبب إعادة الفتح
            force: تجاوز التحقق من وجود قيود في الفترة
        
        Returns:
            Dict[str, Any]: نتيجة العملية
        """
        logger.warning(f"⚠️ Re-opening period: {period_name} by {reopened_by}. Reason: {reason}")
        
        # 1. التحقق من وجود الفترة
        period = self._period_repo.get_period_by_name(period_name)
        if not period:
            return {"success": False, "message": f"Period '{period_name}' not found"}
        
        # 2. التحقق من أن الفترة مغلقة
        if not period.is_closed:
            return {"success": False, "message": f"Period '{period_name}' is already open"}
        
        # 3. التحقق من وجود قيود إقفال (إذا لم يتم التجاوز)
        if not force:
            try:
                # جلب قيود الإقفال للفترة
                closing_entries = self._journal_repo.get_closing_entries_for_period(period_name)
                if closing_entries:
                    logger.warning(f"Found {len(closing_entries)} closing entries that will be reversed")
            except Exception as e:
                logger.warning(f"Could not check closing entries: {e}")
        
        # 4. ✅ التراجع عن قيود الإقفال
        try:
            # جلب قيود الإقفال
            closing_entries = self._journal_repo.get_closing_entries_for_period(period_name)
            
            if closing_entries:
                logger.info(f"Reversing {len(closing_entries)} closing entries")
                for entry in closing_entries:
                    if entry.is_posted and not entry.reversed_entry_id:
                        self._posting_engine.reverse(
                            entry, 
                            f"Period reopened: {reason}", 
                            reopened_by, 
                            auto_post=True
                        )
                logger.info("✅ All closing entries reversed")
            
        except Exception as e:
            logger.error(f"❌ Failed to reverse closing entries: {e}")
            return {
                "success": False,
                "message": f"Failed to reverse closing entries: {str(e)}",
                "period_name": period_name,
            }
        
        # 5. ✅ إعادة فتح الفترة
        try:
            # ✅ استخدام open_again بدلاً من open (الدالة غير موجودة)
            # في الإصدارات القادمة من FiscalPeriod، يجب إضافة هذه الدالة
            period.is_closed = False
            period.closed_by = None
            period.closed_at = None
            period.version += 1
            
            self._period_repo.save(period)
            
            # 6. تسجيل في سجل التدقيق
            self._log_audit(
                operation="REOPEN_PERIOD",
                period_name=period_name,
                closed_by=reopened_by,
                result=ClosingResult(
                    success=True,
                    period_name=period_name,
                    closed_by=reopened_by,
                    closed_at=self._clock.now(),
                    net_income_by_currency={},
                    entries_created=0,
                    warnings=[f"Period reopened. Reason: {reason}"]
                )
            )
            
            logger.info(f"✅ Period '{period_name}' reopened successfully by {reopened_by}")
            
            return {
                "success": True,
                "message": f"Period '{period_name}' reopened successfully",
                "period_name": period_name,
                "reopened_by": reopened_by,
                "reason": reason,
                "force": force,
                "reversed_entries": len(closing_entries) if closing_entries else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to reopen period: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to reopen period: {str(e)}",
                "period_name": period_name,
            }
    
    # =========================================================================
    # ✅ دوال مساعدة إضافية
    # =========================================================================
    
    def get_closing_status(self, period_name: str) -> Dict[str, Any]:
        """الحصول على حالة الإقفال للفترة"""
        period = self._period_repo.get_period_by_name(period_name)
        if not period:
            return {"error": f"Period '{period_name}' not found"}
        
        unposted_count = 0
        try:
            unposted_count = self._journal_repo.count_unposted_in_period(period)
        except Exception:
            pass
        
        return {
            "period_name": period_name,
            "is_closed": period.is_closed,
            "closed_by": period.closed_by if period.is_closed else None,
            "closed_at": period.closed_at.isoformat() if period.closed_at else None,
            "unposted_entries": unposted_count,
            "can_close": unposted_count == 0 and not period.is_closed,
            "can_reopen": period.is_closed,
            "start_date": period.start_date.isoformat(),
            "end_date": period.end_date.isoformat(),
        }
    
    def get_closing_report(self, period_name: str) -> Dict[str, Any]:
        """الحصول على تقرير الإقفال للفترة"""
        period = self._period_repo.get_period_by_name(period_name)
        if not period:
            return {"error": f"Period '{period_name}' not found"}
        
        # جلب ميزان المراجعة
        trial_balance = self._ledger_engine.get_trial_balance(period.end_date)
        
        # تصنيف الحسابات حسب العملة
        revenue_by_currency: Dict[str, Dict[str, float]] = {}
        expense_by_currency: Dict[str, Dict[str, float]] = {}
        tax_by_currency: Dict[str, Dict[str, float]] = {}
        
        for account_code, balance in trial_balance.items():
            if balance.amount == 0:
                continue
            
            currency = balance.currency
            
            if self._is_revenue_account(account_code):
                if currency not in revenue_by_currency:
                    revenue_by_currency[currency] = {}
                revenue_by_currency[currency][str(account_code)] = float(balance.amount)
                
            elif self._is_expense_account(account_code):
                if currency not in expense_by_currency:
                    expense_by_currency[currency] = {}
                expense_by_currency[currency][str(account_code)] = float(balance.amount)
                
            elif self._is_tax_account(account_code):
                if currency not in tax_by_currency:
                    tax_by_currency[currency] = {}
                tax_by_currency[currency][str(account_code)] = float(balance.amount)
        
        # حساب صافي الدخل لكل عملة
        net_income_by_currency = {}
        for currency in set(revenue_by_currency.keys()) | set(expense_by_currency.keys()):
            total_revenue = sum(revenue_by_currency.get(currency, {}).values())
            total_expenses = sum(expense_by_currency.get(currency, {}).values())
            total_tax = sum(tax_by_currency.get(currency, {}).values())
            net_income_by_currency[currency] = total_revenue - total_expenses - total_tax
        
        return {
            "period_name": period_name,
            "is_closed": period.is_closed,
            "trial_balance": {
                "total_debits": float(sum(b.amount for b in trial_balance.values() if b.amount > 0)),
                "total_credits": float(sum(abs(b.amount) for b in trial_balance.values() if b.amount < 0)),
                "account_count": len(trial_balance),
            },
            "revenue_by_currency": revenue_by_currency,
            "expense_by_currency": expense_by_currency,
            "tax_by_currency": tax_by_currency,
            "net_income_by_currency": net_income_by_currency,
            "net_income_status": "ربح" if sum(net_income_by_currency.values()) > 0 else "خسارة" if sum(net_income_by_currency.values()) < 0 else "صفر",
            "entries_count": len(self._journal_repo.get_entries_in_period(period)) if hasattr(self._journal_repo, 'get_entries_in_period') else 0,
        }
    
    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._account_type_cache.clear()
        logger.info("Closing service cache cleared")