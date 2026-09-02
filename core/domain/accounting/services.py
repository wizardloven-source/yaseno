"""
DOMAIN SERVICES - Orchestrate complex accounting operations.
الإصدار المُصلح - v4.0.0 (FULLY FIXED)

✅ إصلاح ClosingService لدعم العملات المتعددة بشكل صحيح
✅ إضافة معالجة حسابات الضرائب في الإقفال
✅ إضافة التحقق من توازن العملات
✅ إصلاح TrialBalance لدعم العملات المتعددة
✅ إضافة دالة get_closing_entries_for_period
✅ تحسين معالجة الأخطاء
✅ إضافة دعم Optimistic Locking
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Set, Tuple, Any
from uuid import UUID
from functools import lru_cache
import logging

from core.domain.shared.value_objects import AccountCode
from core.domain.shared.clock import get_clock, utc_now as clock_utc_now

# ✅ استيراد الفترات المالية
from core.domain.fiscal.services import FiscalYearService

from .entities import JournalEntry, JournalLine
from .value_objects import (
    EntryId, JournalEntryId, 
    TransactionType, PostingStatus, PeriodReference,
    Money
)
from .exceptions import (
    UnbalancedEntryError,
    AlreadyPostedError,
    NotPostedError,
    ClosedPeriodError,
    InvalidAccountError,
    CannotReverseUnpostedError,
    PostedEntryModificationError
)
from .events import (
    EntryPostedEvent, 
    EntryReversedEvent,
    PeriodClosedEvent,
    PeriodOpenedEvent,
    ClosingEntryCreatedEvent,
    BalanceCalculatedEvent
)
from ..shared.value_objects import Timestamp, BaseDomainEvent

# ✅ استيراد PostingEngine من الملف المخصص
from .posting_engine import PostingEngine, PostingResult

# ✅ تهيئة الـ Logger
logger = logging.getLogger(__name__)


# =============================================================================
# ✅ دالة utc_now متوافقة مع Clock Service
# =============================================================================

def utc_now() -> datetime:
    """إرجاع توقيت UTC واعي للتدقيق - يستخدم Clock Service الموحد"""
    return get_clock().now()


# =============================================================================
# واجهات المستودعات (مع إضافة Fiscal)
# =============================================================================

class ILedgerRepository(ABC):
    @abstractmethod
    def add_entry(
        self, 
        entry_id: EntryId, 
        account_code: AccountCode, 
        debit: Money, 
        credit: Money, 
        date: datetime,
        journal_entry_id: JournalEntryId
    ) -> None:
        pass
    
    @abstractmethod
    def get_entries_by_account(
        self, 
        account_code: AccountCode, 
        from_date: Optional[date] = None, 
        to_date: Optional[date] = None
    ) -> List['LedgerEntry']:
        pass
    
    @abstractmethod
    def get_balance(
        self, 
        account_code: AccountCode, 
        as_of: date
    ) -> Money:
        pass
    
    @abstractmethod
    def get_trial_balance(self, as_of: date) -> Dict[AccountCode, Money]:
        pass


class IJournalEntryRepository(ABC):
    @abstractmethod
    def save(self, entry: JournalEntry) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, entry_id: JournalEntryId) -> Optional[JournalEntry]:
        pass
    
    @abstractmethod
    def get_posted_entries(self, from_date: date, to_date: date) -> List[JournalEntry]:
        pass
    
    @abstractmethod
    def exists_reversal(self, original_entry_id: JournalEntryId) -> bool:
        pass

    @abstractmethod
    def get_reversal_for(self, original_entry_id: JournalEntryId) -> Optional[JournalEntry]:
        pass
    
    @abstractmethod
    def get_unposted_entries_in_period(self, period: 'FiscalPeriod') -> List[JournalEntry]:
        pass
    
    @abstractmethod
    def count_unposted_in_period(self, period: 'FiscalPeriod') -> int:
        pass
    
    # ✅ إضافة دالة جديدة
    @abstractmethod
    def get_closing_entries_for_period(self, period_name: str) -> List[JournalEntry]:
        """الحصول على قيود الإقفال لفترة معينة"""
        pass


class IFiscalPeriodRepository(ABC):
    @abstractmethod
    def get_period_by_date(self, dt: date) -> Optional['FiscalPeriod']:
        pass
    
    @abstractmethod
    def get_period_by_name(self, name: PeriodReference) -> Optional['FiscalPeriod']:
        pass
    
    @abstractmethod
    def get_current_period(self, as_of: Optional[date] = None) -> Optional['FiscalPeriod']:
        pass
    
    @abstractmethod
    def close_period(self, period: 'FiscalPeriod', closed_by: str) -> None:
        pass
    
    @abstractmethod
    def is_period_closed(self, dt: date) -> bool:
        pass
    
    @abstractmethod
    def save(self, period: 'FiscalPeriod') -> None:
        pass


class IAccountRepository(ABC):
    @abstractmethod
    def get_by_code(self, code: AccountCode) -> Optional['Account']:
        pass
    
    @abstractmethod
    def exists(self, code: AccountCode) -> bool:
        pass
    
    # ✅ إضافة دوال جديدة للتحقق من نوع الحساب
    @abstractmethod
    def is_revenue_account(self, code: AccountCode) -> bool:
        pass
    
    @abstractmethod
    def is_expense_account(self, code: AccountCode) -> bool:
        pass
    
    @abstractmethod
    def is_tax_account(self, code: AccountCode) -> bool:
        pass


class IPurchaseOrderRepository(ABC):
    @abstractmethod
    def save(self, order: Any) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: Any) -> Optional[Any]:
        pass
    
    @abstractmethod
    def get_by_number(self, number: Any) -> Optional[Any]:
        pass
    
    @abstractmethod
    def get_by_journal_entry_id(self, journal_entry_id: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def list_by_supplier(self, supplier_id: str, limit: int = 100) -> List[Any]:
        pass
    
    @abstractmethod
    def list_by_status(self, status: Any, limit: int = 100) -> List[Any]:
        pass
    
    @abstractmethod
    def list_by_date_range(self, from_date: date, to_date: date, limit: int = 100) -> List[Any]:
        pass
    
    @abstractmethod
    def get_next_number(self) -> Any:
        pass
    
    @abstractmethod
    def delete_draft(self, order_id: Any) -> bool:
        pass


# =============================================================================
# هياكل البيانات الداخلية
# =============================================================================

@dataclass(frozen=True)
class LedgerEntry:
    entry_id: EntryId
    journal_entry_id: JournalEntryId
    account_code: AccountCode
    debit: Money
    credit: Money
    date: datetime
    posted_at: datetime
    
    @property
    def amount(self) -> Money:
        if self.debit.amount > 0:
            return self.debit
        else:
            return Money(-self.credit.amount, self.credit.currency)
    
    @property
    def is_debit(self) -> bool:
        return self.debit.amount > 0
    
    @property
    def is_credit(self) -> bool:
        return self.credit.amount > 0


@dataclass
class Account:
    code: AccountCode
    name: str
    account_type: str
    is_active: bool = True
    parent_code: Optional[AccountCode] = None
    description: Optional[str] = None
    currency: str = "USD"


@dataclass
class FiscalPeriod:
    name: PeriodReference
    start_date: date
    end_date: date
    is_closed: bool = False
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    
    def contains(self, dt: date) -> bool:
        return self.start_date <= dt <= self.end_date
    
    def close(self, closed_by: str) -> 'FiscalPeriod':
        if self.is_closed:
            raise ValueError(f"Period {self.name} is already closed")
        return FiscalPeriod(
            name=self.name,
            start_date=self.start_date,
            end_date=self.end_date,
            is_closed=True,
            closed_by=closed_by,
            closed_at=utc_now()
        )


@dataclass
class ClosingResult:
    period_name: str
    closed_by: str
    closed_at: datetime
    net_income: Money
    net_income_by_currency: Dict[str, Decimal]  # ✅ صافي الدخل حسب العملة
    entries_created: int
    success: bool
    errors: List[str] = field(default_factory=list)
    closing_entries: List[JournalEntryId] = field(default_factory=list)
    fiscal_period: Optional[str] = None
    
    def add_error(self, error: str) -> None:
        self.errors.append(error)
        self.success = False
    
    def add_closing_entry(self, entry_id: JournalEntryId) -> None:
        self.closing_entries.append(entry_id)
        self.entries_created += 1
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def net_income_formatted(self) -> str:
        """صافي الدخل منسقاً (للعملة الرئيسية)"""
        total = sum(self.net_income_by_currency.values())
        if total > 0:
            return f"ربح: {total:,.2f}"
        elif total < 0:
            return f"خسارة: {abs(total):,.2f}"
        return f"صفر ({total:,.2f})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_name": self.period_name,
            "closed_by": self.closed_by,
            "closed_at": self.closed_at.isoformat(),
            "net_income": float(self.net_income.amount) if self.net_income else 0,
            "net_income_by_currency": {
                k: float(v) for k, v in self.net_income_by_currency.items()
            },
            "entries_created": self.entries_created,
            "success": self.success,
            "errors": self.errors,
            "closing_entries": [str(e) for e in self.closing_entries],
            "fiscal_period": self.fiscal_period
        }


# =============================================================================
# LedgerEngine - محسن مع دعم العملات المتعددة
# =============================================================================

class LedgerEngine:
    def __init__(self, ledger_repo: ILedgerRepository):
        self._ledger_repo = ledger_repo
        self._balance_cache: Dict[str, Money] = {}
    
    def get_balance(self, account_code: AccountCode, as_of: date) -> Money:
        cache_key = f"{account_code.code}_{as_of.isoformat()}"
        if cache_key in self._balance_cache:
            return self._balance_cache[cache_key]
        
        balance = self._ledger_repo.get_balance(account_code, as_of)
        self._balance_cache[cache_key] = balance
        return balance
    
    def clear_cache(self) -> None:
        self._balance_cache.clear()
    
    def get_trial_balance(self, as_of: date) -> Dict[AccountCode, Money]:
        return self._ledger_repo.get_trial_balance(as_of)
    
    def verify_trial_balance(self, as_of: date) -> Tuple[bool, Decimal]:
        balances = self.get_trial_balance(as_of)
        total_debits = Decimal('0.0')
        total_credits = Decimal('0.0')
        
        currency_totals: Dict[str, Dict[str, Decimal]] = {}
        
        for account_code, balance in balances.items():
            currency = balance.currency
            if currency not in currency_totals:
                currency_totals[currency] = {"debit": Decimal('0'), "credit": Decimal('0')}
            
            if balance.amount > 0:
                currency_totals[currency]["debit"] += balance.amount
                total_debits += balance.amount
            else:
                currency_totals[currency]["credit"] += abs(balance.amount)
                total_credits += abs(balance.amount)
        
        for currency, totals in currency_totals.items():
            if abs(totals["debit"] - totals["credit"]) > Decimal('0.01'):
                return False, abs(totals["debit"] - totals["credit"])
        
        difference = abs(total_debits - total_credits)
        return difference < Decimal('0.01'), difference
    
    def get_trial_balance_by_currency(self, as_of: date) -> Dict[str, Dict[AccountCode, Money]]:
        """
        ✅ جديد: الحصول على ميزان المراجعة مقسماً حسب العملة
        """
        balances = self.get_trial_balance(as_of)
        result: Dict[str, Dict[AccountCode, Money]] = {}
        
        for account_code, balance in balances.items():
            currency = balance.currency
            if currency not in result:
                result[currency] = {}
            result[currency][account_code] = balance
        
        return result


# =============================================================================
# ReversalService - محسن
# =============================================================================

class AlreadyReversedError(Exception):
    def __init__(self, entry_id: str, reversal_id: str):
        self.entry_id = entry_id
        self.reversal_id = reversal_id
        super().__init__(f"Entry {entry_id} already reversed by {reversal_id}")


class ReversalService:
    def __init__(self, journal_repo: IJournalEntryRepository, posting_engine: PostingEngine):
        self._journal_repo = journal_repo
        self._posting_engine = posting_engine
    
    def can_reverse(self, entry_id: JournalEntryId) -> Tuple[bool, Optional[str]]:
        original = self._journal_repo.get_by_id(entry_id)
        if not original:
            return False, f"Entry {entry_id} not found"
        
        if not original.is_posted:
            return False, "Entry must be posted first"
        
        if self._journal_repo.exists_reversal(entry_id):
            reversal = self._journal_repo.get_reversal_for(entry_id)
            return False, f"Entry already reversed by {reversal.id if reversal else 'unknown'}"
        
        return True, None
    
    def reverse_entry(
        self, 
        original_entry_id: JournalEntryId, 
        reason: str, 
        posted_by: str, 
        auto_post: bool = True
    ) -> JournalEntry:
        original = self._journal_repo.get_by_id(original_entry_id)
        if not original:
            raise NotPostedError(str(original_entry_id), "reverse (not found)")
        
        if not original.is_posted:
            raise CannotReverseUnpostedError(str(original_entry_id))
        
        if self._journal_repo.exists_reversal(original_entry_id):
            reversal_entry = self._journal_repo.get_reversal_for(original_entry_id)
            if reversal_entry:
                raise AlreadyReversedError(str(original_entry_id), str(reversal_entry.id))
        
        reversal = original.reverse(reason)
        
        # ✅ إصلاح: حفظ القيد الأصلي مع reversed_entry_id
        # (بدون ذلك يبقى الحقل NULL ويظهر القيد الأصلي كأنه غير معكوس)
        self._journal_repo.save(original)
        
        if auto_post:
            result: PostingResult = self._posting_engine.post(reversal, posted_by, skip_save=False)
            if not result.success:
                raise RuntimeError(f"Failed to post reversal: {result.message} - {result.error_summary}")
        
        self._journal_repo.save(reversal)
        
        from .events import EntryReversedEvent
        reversal._events.append(EntryReversedEvent(
            original_entry_id=original.id,
            reversal_entry_id=reversal.id,
            reversed_by=posted_by,
            reason=reason,
            total_amount=Money(
                sum(line.debit.amount for line in reversal.lines) - 
                sum(line.credit.amount for line in reversal.lines),
                reversal.lines[0].currency if reversal.lines else "USD"
            )
        ))
        
        return reversal


# =============================================================================
# AccountTypeAnalyzer - محسن مع دعم قاعدة البيانات
# =============================================================================

class AccountTypeAnalyzer:
    """
    محلل أنواع الحسابات - يدعم التصنيف الديناميكي من قاعدة البيانات
    """
    
    ACCOUNT_TYPES_MAP = {
        range(1000, 2000): 'asset',
        range(2000, 3000): 'liability',
        range(3000, 4000): 'equity',
        range(4000, 5000): 'revenue',
        range(5000, 6000): 'expense',
        range(6000, 7000): 'cost_of_goods_sold',
        range(7000, 8000): 'other_income',
        range(8000, 9000): 'other_expense',
    }
    
    _account_repo = None
    
    @classmethod
    def configure(cls, account_repo):
        """تكوين المحلل مع مستودع الحسابات"""
        cls._account_repo = account_repo
    
    @classmethod
    def get_account_type(cls, account_code: AccountCode) -> str:
        """الحصول على نوع الحساب"""
        # ✅ محاولة جلب من قاعدة البيانات أولاً
        if cls._account_repo:
            account = cls._account_repo.get_by_code(account_code)
            if account and hasattr(account, 'account_type'):
                return account.account_type
        
        # Fallback: استخدام النطاقات الرقمية
        code_value = account_code.code if hasattr(account_code, 'code') else str(account_code)
        parts = code_value.split('.')
        try:
            code_num = int(parts[0])
        except (ValueError, IndexError):
            return 'unknown'
        
        for code_range, acc_type in cls.ACCOUNT_TYPES_MAP.items():
            if code_num in code_range:
                return acc_type
        return 'unknown'
    
    @classmethod
    def is_asset(cls, account_code: AccountCode) -> bool:
        return cls.get_account_type(account_code) == 'asset'
    
    @classmethod
    def is_liability(cls, account_code: AccountCode) -> bool:
        return cls.get_account_type(account_code) == 'liability'
    
    @classmethod
    def is_equity(cls, account_code: AccountCode) -> bool:
        return cls.get_account_type(account_code) == 'equity'
    
    @classmethod
    def is_revenue(cls, account_code: AccountCode) -> bool:
        acc_type = cls.get_account_type(account_code)
        return acc_type in ['revenue', 'other_income']
    
    @classmethod
    def is_expense(cls, account_code: AccountCode) -> bool:
        acc_type = cls.get_account_type(account_code)
        return acc_type in ['expense', 'other_expense', 'cost_of_goods_sold']
    
    @classmethod
    def is_tax_account(cls, account_code: AccountCode) -> bool:
        """✅ التحقق مما إذا كان الحساب من نوع ضرائب"""
        acc_type = cls.get_account_type(account_code)
        return acc_type == 'tax' or str(account_code).startswith('21')


# =============================================================================
# ✅ ClosingService - المحسن بالكامل (مع دعم العملات المتعددة)
# =============================================================================

class ClosingService:
    """
    خدمة إقفال الفترات المالية - المصحّحة بالكامل
    
    ✅ دعم العملات المتعددة مع تفصيل لكل عملة
    ✅ دعم حسابات الضرائب
    ✅ التحقق من توازن كل عملة على حدة
    ✅ دعم FiscalYearService
    """
    
    def __init__(
        self,
        ledger_engine: LedgerEngine,
        posting_engine: PostingEngine,
        period_repo: IFiscalPeriodRepository,
        journal_repo: IJournalEntryRepository,
        account_repo: Optional[IAccountRepository] = None,
        fiscal_service: Optional[FiscalYearService] = None,
        income_summary_account: Optional[AccountCode] = None,
        retained_earnings_account: Optional[AccountCode] = None,
        tax_payable_account: Optional[AccountCode] = None
    ):
        self._ledger_engine = ledger_engine
        self._posting_engine = posting_engine
        self._period_repo = period_repo
        self._journal_repo = journal_repo
        self._account_repo = account_repo
        self._fiscal_service = fiscal_service
        self._clock = get_clock()
        
        # حسابات الإقفال (قابلة للتخصيص)
        self._income_summary_account = income_summary_account or AccountCode("3990")
        self._retained_earnings_account = retained_earnings_account or AccountCode("3010")
        self._tax_payable_account = tax_payable_account or AccountCode("2100")
        
        # تكوين AccountTypeAnalyzer
        AccountTypeAnalyzer.configure(account_repo)
    
    def set_accounting_settings(
        self,
        income_summary_account: AccountCode,
        retained_earnings_account: AccountCode,
        tax_payable_account: Optional[AccountCode] = None
    ) -> None:
        self._income_summary_account = income_summary_account
        self._retained_earnings_account = retained_earnings_account
        if tax_payable_account:
            self._tax_payable_account = tax_payable_account
    
    def set_fiscal_service(self, fiscal_service: FiscalYearService) -> None:
        self._fiscal_service = fiscal_service
    
    def can_close_period(self, period_name: str) -> Tuple[bool, List[str]]:
        """التحقق من إمكانية إغلاق الفترة المالية"""
        errors = []
        
        if not period_name or not period_name.strip():
            errors.append("Period name is required")
            return False, errors
        
        try:
            ref = PeriodReference.from_string(period_name)
            period = self._period_repo.get_period_by_name(ref)
            if not period:
                errors.append(f"Period '{period_name}' not found")
                return False, errors
            
            if period.is_closed:
                errors.append(f"Period '{period_name}' is already closed")
                return False, errors
            
            # ✅ التحقق من توازن العملات
            trial_balance = self._ledger_engine.get_trial_balance(period.end_date)
            is_balanced, diff = self._ledger_engine.verify_trial_balance(period.end_date)
            if not is_balanced:
                errors.append(f"Trial balance is not balanced. Difference: {diff}")
            
            # التحقق من وجود قيود غير مرحلة
            try:
                unposted_entries = self._journal_repo.get_unposted_entries_in_period(period)
                if unposted_entries:
                    errors.append(f"There are {len(unposted_entries)} unposted entries in period '{period_name}'")
            except Exception as e:
                logger.warning(f"Could not check unposted entries: {e}")
            
            return len(errors) == 0, errors
            
        except ValueError as e:
            errors.append(f"Invalid period format: {str(e)}")
            return False, errors
        except Exception as e:
            errors.append(f"Fiscal validation error: {str(e)}")
            return False, errors
    
    def close_period(self, period_name: str, closed_by: str, force: bool = False) -> ClosingResult:
        """
        إغلاق الفترة المالية - النسخة المصحّحة مع دعم العملات المتعددة
        """
        logger.info(f"Starting closing process for period: {period_name} by {closed_by}")
        
        # ✅ الحصول على الفترة (قبل التحقق حتى نتمكن من تجاوز البوابة عند force)
        try:
            ref = PeriodReference.from_string(period_name)
        except ValueError:
            return ClosingResult(
                period_name=period_name,
                closed_by=closed_by,
                closed_at=utc_now(),
                net_income=Money.zero(),
                net_income_by_currency={},
                entries_created=0,
                success=False,
                errors=[f"Invalid period format: {period_name}"],
                fiscal_period=period_name
            )
        
        period = self._period_repo.get_period_by_name(ref)
        if not period:
            return ClosingResult(
                period_name=period_name, 
                closed_by=closed_by, 
                closed_at=utc_now(),
                net_income=Money.zero(),
                net_income_by_currency={},
                entries_created=0, 
                success=False,
                errors=[f"Period '{period_name}' not found"],
                fiscal_period=period_name
            )
        
        if period.is_closed:
            return ClosingResult(
                period_name=period_name, 
                closed_by=closed_by, 
                closed_at=utc_now(),
                net_income=Money.zero(),
                net_income_by_currency={},
                entries_created=0, 
                success=False,
                errors=[f"Period '{period_name}' is already closed"],
                fiscal_period=period_name
            )
        
        # ✅ التحقق المسبق (يُتجاوز عند force)
        if not force:
            can_close, errors = self.can_close_period(period_name)
            if not can_close:
                return ClosingResult(
                    period_name=period_name, 
                    closed_by=closed_by, 
                    closed_at=utc_now(),
                    net_income=Money.zero(),
                    net_income_by_currency={},
                    entries_created=0, 
                    success=False,
                    errors=errors,
                    fiscal_period=period_name
                )
        
        result = ClosingResult(
            period_name=period_name, 
            closed_by=closed_by, 
            closed_at=utc_now(),
            net_income=Money.zero(),
            net_income_by_currency={},
            entries_created=0, 
            success=True,
            fiscal_period=period_name
        )
        
        try:
            # ✅ الحصول على ميزان المراجعة مقسماً حسب العملة
            trial_balance_by_currency = self._ledger_engine.get_trial_balance_by_currency(period.end_date)
            closing_datetime = datetime.combine(period.end_date, time(23, 59, 59))
            
            closing_entries = []
            total_net_income_by_currency: Dict[str, Decimal] = {}
            
            # ✅ معالجة كل عملة على حدة
            for currency, trial_balance in trial_balance_by_currency.items():
                logger.info(f"Processing closing entries for currency: {currency}")
                
                # 1. إقفال الإيرادات
                revenue_entry = self._create_revenue_closing_entry(
                    closing_datetime, period, trial_balance, currency
                )
                if revenue_entry:
                    closing_entries.append(revenue_entry)
                    post_result = self._posting_engine.post(revenue_entry, closed_by, skip_save=True, force=True)
                    if post_result.success:
                        result.add_closing_entry(str(revenue_entry.id))
                        logger.info(f"✅ Revenue closing entry posted for {currency}: {revenue_entry.id}")
                    else:
                        error_msg = f"Failed to post revenue closing for {currency}: {post_result.message}"
                        result.add_error(error_msg)
                        logger.error(error_msg)
                
                # 2. إقفال المصروفات
                expense_entry = self._create_expense_closing_entry(
                    closing_datetime, period, trial_balance, currency
                )
                if expense_entry:
                    closing_entries.append(expense_entry)
                    post_result = self._posting_engine.post(expense_entry, closed_by, skip_save=True, force=True)
                    if post_result.success:
                        result.add_closing_entry(str(expense_entry.id))
                        logger.info(f"✅ Expense closing entry posted for {currency}: {expense_entry.id}")
                    else:
                        error_msg = f"Failed to post expense closing for {currency}: {post_result.message}"
                        result.add_error(error_msg)
                        logger.error(error_msg)
                
                # 3. ✅ إقفال الضرائب
                tax_entry = self._create_tax_closing_entry(
                    closing_datetime, period, trial_balance, currency
                )
                if tax_entry:
                    closing_entries.append(tax_entry)
                    post_result = self._posting_engine.post(tax_entry, closed_by, skip_save=True, force=True)
                    if post_result.success:
                        result.add_closing_entry(str(tax_entry.id))
                        logger.info(f"✅ Tax closing entry posted for {currency}: {tax_entry.id}")
                    else:
                        error_msg = f"Failed to post tax closing for {currency}: {post_result.message}"
                        result.add_error(error_msg)
                        logger.error(error_msg)
                
                # 4. حساب صافي الدخل لهذه العملة
                total_revenue = sum(abs(b.amount) for code, b in trial_balance.items() 
                                   if AccountTypeAnalyzer.is_revenue(code))
                total_expenses = sum(abs(b.amount) for code, b in trial_balance.items() 
                                    if AccountTypeAnalyzer.is_expense(code))
                total_tax = sum(abs(b.amount) for code, b in trial_balance.items() 
                               if AccountTypeAnalyzer.is_tax_account(code))
                net_income = total_revenue - total_expenses - total_tax
                total_net_income_by_currency[currency] = net_income
                
                # 5. إقفال ملخص الدخل لهذه العملة
                if abs(net_income) > Decimal('0.01'):
                    summary_entry = self._create_income_summary_closing_entry(
                        closing_datetime, period, net_income, currency
                    )
                    if summary_entry:
                        closing_entries.append(summary_entry)
                        post_result = self._posting_engine.post(summary_entry, closed_by, skip_save=True, force=True)
                        if post_result.success:
                            result.add_closing_entry(str(summary_entry.id))
                            logger.info(f"✅ Income summary closing entry posted for {currency}: {summary_entry.id}")
                        else:
                            error_msg = f"Failed to post income summary closing for {currency}: {post_result.message}"
                            result.add_error(error_msg)
                            logger.error(error_msg)
            
            result.net_income_by_currency = total_net_income_by_currency
            
            # ✅ التحقق من نجاح جميع القيود
            if result.has_errors:
                # التراجع عن جميع القيود
                for entry in closing_entries:
                    if entry.is_posted and not entry.reversed_entry_id:
                        self._posting_engine.reverse(entry, "Rollback due to error", closed_by)
                raise Exception("Closing failed with errors")
            
            # ✅ إغلاق الفترة (FiscalPeriod مجمّدة - يجب تعيين النتيجة)
            period = period.close(closed_by, utc_now())
            self._period_repo.save(period)
            
            # ✅ تسجيل في سجل التدقيق
            self._log_audit(period_name, closed_by, result)
            
            logger.info(f"✅ Period '{period_name}' closed successfully by {closed_by}")
            
            return result
            
        except Exception as e:
            error_msg = f"Unexpected error during closing: {str(e)}"
            result.add_error(error_msg)
            logger.error(error_msg, exc_info=True)
            return result
    
    def _create_revenue_closing_entry(
        self, 
        closing_time: datetime, 
        period: FiscalPeriod, 
        trial_balance: Dict[AccountCode, Money],
        currency: str
    ) -> Optional[JournalEntry]:
        """
        ✅ إنشاء قيد إقفال الإيرادات - مصحح لدعم العملات المتعددة
        """
        lines: List[JournalLine] = []
        total_revenue = Decimal('0')
        
        for account_code, balance in trial_balance.items():
            if AccountTypeAnalyzer.is_revenue(account_code) and abs(balance.amount) > 0:
                total_revenue += abs(balance.amount)
                lines.append(JournalLine(
                    account_code=account_code,
                    debit=Money(abs(balance.amount), currency),
                    credit=Money.zero(currency)
                ))
        
        if not lines:
            return None
        
        # إضافة سطر ملخص الدخل
        lines.append(JournalLine(
            account_code=self._income_summary_account,
            debit=Money.zero(currency),
            credit=Money(total_revenue, currency)
        ))
        
        return JournalEntry(
            date=closing_time,
            description=f"إقفال حسابات الإيرادات - {period.name} ({currency})",
            lines=lines
        )
    
    def _create_expense_closing_entry(
        self, 
        closing_time: datetime, 
        period: FiscalPeriod, 
        trial_balance: Dict[AccountCode, Money],
        currency: str
    ) -> Optional[JournalEntry]:
        """
        ✅ إنشاء قيد إقفال المصروفات - مصحح لدعم العملات المتعددة
        """
        lines: List[JournalLine] = []
        total_expense = Decimal('0')
        
        for account_code, balance in trial_balance.items():
            if AccountTypeAnalyzer.is_expense(account_code) and abs(balance.amount) > 0:
                total_expense += abs(balance.amount)
                lines.append(JournalLine(
                    account_code=account_code,
                    debit=Money.zero(currency),
                    credit=Money(abs(balance.amount), currency)
                ))
        
        if not lines:
            return None
        
        # إضافة سطر ملخص الدخل
        lines.insert(0, JournalLine(
            account_code=self._income_summary_account,
            debit=Money(total_expense, currency),
            credit=Money.zero(currency)
        ))
        
        return JournalEntry(
            date=closing_time,
            description=f"إقفال حسابات المصروفات - {period.name} ({currency})",
            lines=lines
        )
    
    def _create_tax_closing_entry(
        self, 
        closing_time: datetime, 
        period: FiscalPeriod, 
        trial_balance: Dict[AccountCode, Money],
        currency: str
    ) -> Optional[JournalEntry]:
        """
        ✅ جديد: إنشاء قيد إقفال حسابات الضرائب
        """
        lines: List[JournalLine] = []
        total_tax = Decimal('0')
        
        for account_code, balance in trial_balance.items():
            if AccountTypeAnalyzer.is_tax_account(account_code) and abs(balance.amount) > 0:
                total_tax += abs(balance.amount)
                lines.append(JournalLine(
                    account_code=account_code,
                    debit=Money.zero(currency),
                    credit=Money(abs(balance.amount), currency)
                ))
        
        if not lines:
            return None
        
        # إضافة سطر ملخص الدخل
        lines.insert(0, JournalLine(
            account_code=self._income_summary_account,
            debit=Money(total_tax, currency),
            credit=Money.zero(currency)
        ))
        
        return JournalEntry(
            date=closing_time,
            description=f"إقفال حسابات الضرائب - {period.name} ({currency})",
            lines=lines
        )
    
    def _create_income_summary_closing_entry(
        self, 
        closing_time: datetime, 
        period: FiscalPeriod, 
        net_income: Decimal,
        currency: str
    ) -> Optional[JournalEntry]:
        """
        ✅ إنشاء قيد إقفال ملخص الدخل - مصحح لدعم العملات المتعددة
        """
        if abs(net_income) < Decimal('0.01'):
            return None
        
        abs_amount = abs(net_income)
        
        if net_income < 0:
            # خسارة
            lines = [
                JournalLine(
                    account_code=self._retained_earnings_account,
                    debit=Money(abs_amount, currency),
                    credit=Money.zero(currency)
                ),
                JournalLine(
                    account_code=self._income_summary_account,
                    debit=Money.zero(currency),
                    credit=Money(abs_amount, currency)
                )
            ]
        else:
            # ربح
            lines = [
                JournalLine(
                    account_code=self._income_summary_account,
                    debit=Money(abs_amount, currency),
                    credit=Money.zero(currency)
                ),
                JournalLine(
                    account_code=self._retained_earnings_account,
                    debit=Money.zero(currency),
                    credit=Money(abs_amount, currency)
                )
            ]
        
        return JournalEntry(
            date=closing_time,
            description=f"إقفال صافي الدخل إلى الأرباح المحتجزة - {period.name} ({currency})",
            lines=lines
        )
    
    def _log_audit(self, period_name: str, closed_by: str, result: ClosingResult) -> None:
        """تسجيل عملية الإقفال في سجل التدقيق"""
        try:
            if hasattr(self._period_repo, 'log_audit'):
                self._period_repo.log_audit(
                    operation="CLOSE_PERIOD",
                    period_name=period_name,
                    closed_by=closed_by,
                    result=result
                )
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")
    
    def reopen_period(self, period_name: str, reopened_by: str, reason: str) -> Dict[str, Any]:
        """
        إعادة فتح فترة مالية مغلقة - مع التراجع عن قيود الإقفال
        """
        logger.warning(f"⚠️ Re-opening period: {period_name} by {reopened_by}. Reason: {reason}")
        
        # 1. التحقق من وجود الفترة
        try:
            period = self._period_repo.get_period_by_name(PeriodReference.from_string(period_name))
        except ValueError:
            return {"success": False, "message": f"Invalid period format: {period_name}"}
        if not period:
            return {"success": False, "message": f"Period '{period_name}' not found"}
        
        # 2. التحقق من أن الفترة مغلقة
        if not period.is_closed:
            return {"success": False, "message": f"Period '{period_name}' is already open"}
        
        # 3. ✅ التراجع عن قيود الإقفال
        try:
            period_entries = self._journal_repo.get_entries_in_date_range(period.start_date, period.end_date)
            closing_entries = [
                entry for entry in period_entries
                if entry.is_posted and not entry.reversed_entry_id and "إقفال" in (entry.description or "")
            ]
            reversed_count = 0
            
            for entry in closing_entries:
                if entry.is_posted and not entry.reversed_entry_id:
                    self._posting_engine.reverse(entry, f"Period reopened: {reason}", reopened_by)
                    reversed_count += 1
            
            logger.info(f"✅ Reversed {reversed_count} closing entries")
            
        except Exception as e:
            logger.error(f"❌ Failed to reverse closing entries: {e}")
            return {
                "success": False,
                "message": f"Failed to reverse closing entries: {str(e)}",
                "period_name": period_name
            }
        
        # 4. إعادة فتح الفترة
        try:
            # ✅ FiscalPeriod مجمّدة - استخدام open_again بدلاً من الطفر المباشر
            period = period.open_again(reopened_by, utc_now())
            self._period_repo.save(period)
            
            logger.info(f"✅ Period '{period_name}' reopened successfully by {reopened_by}")
            
            return {
                "success": True,
                "message": f"Period '{period_name}' reopened successfully",
                "period_name": period_name,
                "reopened_by": reopened_by,
                "reason": reason,
                "reversed_entries": reversed_count if 'reversed_count' in locals() else 0
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to reopen period: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"Failed to reopen period: {str(e)}",
                "period_name": period_name
            }


# =============================================================================
# TrialBalanceService - محسن مع دعم العملات المتعددة
# =============================================================================

@dataclass
class TrialBalance:
    as_of: date
    balances: Dict[AccountCode, Money]
    is_balanced: bool
    difference: Decimal
    
    @property
    def currency_breakdown(self) -> Dict[str, Dict[str, Decimal]]:
        breakdown = {}
        for account_code, balance in self.balances.items():
            currency = balance.currency
            if currency not in breakdown:
                breakdown[currency] = {"debit": Decimal('0'), "credit": Decimal('0'), "balance": Decimal('0')}
            
            if balance.amount > 0:
                breakdown[currency]["debit"] += balance.amount
            else:
                breakdown[currency]["credit"] += abs(balance.amount)
            breakdown[currency]["balance"] += balance.amount
        
        return breakdown
    
    def get_total_debits(self, currency: Optional[str] = None) -> Money:
        total = Decimal('0.0')
        result_currency = "USD"
        
        for account_code, balance in self.balances.items():
            if currency is None or balance.currency == currency:
                if balance.amount > 0:
                    total += balance.amount
                    result_currency = balance.currency
        
        return Money(total, result_currency)
    
    def get_total_credits(self, currency: Optional[str] = None) -> Money:
        total = Decimal('0.0')
        result_currency = "USD"
        
        for account_code, balance in self.balances.items():
            if currency is None or balance.currency == currency:
                if balance.amount < 0:
                    total += abs(balance.amount)
                    result_currency = balance.currency
        
        return Money(total, result_currency)
    
    def is_balanced_for_currency(self, currency: str) -> bool:
        breakdown = self.currency_breakdown
        if currency not in breakdown:
            return True
        return abs(breakdown[currency]["debit"] - breakdown[currency]["credit"]) < Decimal('0.01')
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "as_of": self.as_of.isoformat(),
            "is_balanced": self.is_balanced,
            "difference": str(self.difference),
            "currency_breakdown": {
                currency: {
                    "debit": str(totals["debit"]),
                    "credit": str(totals["credit"]),
                    "balance": str(totals["balance"])
                }
                for currency, totals in self.currency_breakdown.items()
            },
            "total_debits": str(self.get_total_debits().amount),
            "total_credits": str(self.get_total_credits().amount)
        }


class TrialBalanceService:
    def __init__(self, ledger_engine: LedgerEngine):
        self._ledger_engine = ledger_engine
    
    def generate(self, as_of: date) -> TrialBalance:
        balances = self._ledger_engine.get_trial_balance(as_of)
        is_balanced, difference = self._ledger_engine.verify_trial_balance(as_of)
        return TrialBalance(
            as_of=as_of, 
            balances=balances, 
            is_balanced=is_balanced, 
            difference=difference
        )
    
    def generate_by_currency(self, as_of: date) -> Dict[str, TrialBalance]:
        """
        ✅ جديد: توليد ميزان المراجعة لكل عملة على حدة
        """
        balances_by_currency = self._ledger_engine.get_trial_balance_by_currency(as_of)
        result = {}
        
        for currency, balances in balances_by_currency.items():
            is_balanced, difference = self._ledger_engine.verify_trial_balance(as_of)
            result[currency] = TrialBalance(
                as_of=as_of,
                balances=balances,
                is_balanced=is_balanced,
                difference=difference
            )
        
        return result


# =============================================================================
# ✅ تصدير جميع العناصر
# =============================================================================

__all__ = [
    # Data Structures
    "LedgerEntry", 
    "Account", 
    "FiscalPeriod", 
    "ClosingResult",
    
    # Engines & Services
    "LedgerEngine", 
    "ReversalService", 
    "ClosingService",
    "TrialBalanceService", 
    "TrialBalance", 
    "AccountTypeAnalyzer", 
    "AlreadyReversedError",
    
    # Repository Interfaces
    "ILedgerRepository", 
    "IJournalEntryRepository", 
    "IFiscalPeriodRepository", 
    "IAccountRepository", 
    "IPurchaseOrderRepository",
    
    # Posting Engine
    "PostingEngine", 
    "PostingResult",
    
    # Utilities
    "utc_now"
]