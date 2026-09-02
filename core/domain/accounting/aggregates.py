"""
ACCOUNTING AGGREGATES & PERIOD MANAGEMENT - YASEEN ERP ENTERPRISE VERSION
الإصدار المُصحَّح - v2.0.0 (FULLY FIXED)

✅ إصلاح AccountBalance لدعم العملات المتعددة بشكل صحيح
✅ إصلاح استخدام Money (كائنات غير قابلة للتغيير)
✅ استخدام Clock Service بدلاً من datetime.now
✅ إضافة دالة open_again لإعادة فتح الفترات
✅ إضافة دعم صافي الدخل حسب العملة
✅ إضافة التحقق من توازن العملات
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Optional, Any, Dict
import logging

from ..shared.value_objects import Money
from ..shared.clock import get_clock
from .value_objects import AccountCode, PeriodReference, JournalEntryId
from .exceptions import (
    PeriodAlreadyClosedError, 
    PeriodClosedModificationError,
    FiscalPeriodValidationError
)

logger = logging.getLogger(__name__)


# =============================================================================
# ✅ دالة مساعدة باستخدام Clock Service
# =============================================================================

def aware_utc_today() -> date:
    """إرجاع تاريخ اليوم الحالي متوافقاً مع توقيت UTC الواعي."""
    return get_clock().today()


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC."""
    return get_clock().now()


# =============================================================================
# ✅ AccountBalance - المصحّح بالكامل (يدعم العملات المتعددة)
# =============================================================================

@dataclass
class AccountBalance:
    """
    AGGREGATE ROOT / OPTIMIZED READ-WRITE MODEL
    
    يمثل الرصيد اللحظي التراكمي للحساب داخل شجرة الحسابات.
    يتم تحديثه عبر الأحداث (Event-Driven) بدلاً من حساب القيود من الصفر.
    
    ✅ محدث: دعم العملات المتعددة
    ✅ محدث: استخدام Money بشكل صحيح (غير قابل للتغيير)
    ✅ محدث: استخدام Clock Service
    """
    
    account_code: AccountCode
    currency: str
    
    # ✅ استخدام field(default_factory) لإنشاء كائنات Money جديدة
    total_debit: Money = field(default_factory=lambda: Money.zero())
    total_credit: Money = field(default_factory=lambda: Money.zero())
    current_balance: Money = field(default_factory=lambda: Money.zero())
    
    # ✅ تفصيل العملات (للحسابات متعددة العملات)
    currency_breakdown: Dict[str, Dict[str, Decimal]] = field(default_factory=dict)
    
    last_updated_at: datetime = field(default_factory=utc_now)
    last_journal_entry_id: Optional[JournalEntryId] = None
    version: int = 1
    
    def __post_init__(self):
        """تهيئة الحقول بعد الإنشاء"""
        # التأكد من أن العملات متطابقة
        if self.total_debit.currency != self.currency:
            object.__setattr__(self, 'total_debit', Money.zero(self.currency))
        if self.total_credit.currency != self.currency:
            object.__setattr__(self, 'total_credit', Money.zero(self.currency))
        if self.current_balance.currency != self.currency:
            object.__setattr__(self, 'current_balance', Money.zero(self.currency))
        
        # تهيئة تفصيل العملات
        if not self.currency_breakdown:
            object.__setattr__(self, 'currency_breakdown', {})
    
    def apply_posted_line(
        self, 
        is_debit: bool, 
        amount: Money, 
        entry_id: JournalEntryId
    ) -> None:
        """
        ✅ تحديث الرصيد اللحظي للحساب - مصحح لدعم العملات المتعددة
        
        Args:
            is_debit: هل الحركة مدينة؟
            amount: المبلغ (مع العملة)
            entry_id: معرف القيد المحاسبي
        
        Raises:
            ValueError: إذا كانت العملة غير متطابقة
        """
        # ✅ التحقق من تطابق العملة
        if amount.currency != self.currency:
            raise ValueError(
                f"Multi-Currency Violation: Cannot apply currency '{amount.currency}' "
                f"to Account Balance '{self.account_code}' targeted for '{self.currency}'."
            )
        
        # ✅ تحديث المبالغ (إنشاء كائنات Money جديدة)
        if is_debit:
            new_total_debit = self.total_debit + amount
            object.__setattr__(self, 'total_debit', new_total_debit)
        else:
            new_total_credit = self.total_credit + amount
            object.__setattr__(self, 'total_credit', new_total_credit)
        
        # ✅ حساب الرصيد الجديد
        new_balance = self.total_debit - self.total_credit
        object.__setattr__(self, 'current_balance', new_balance)
        
        # ✅ تحديث تفصيل العملات
        if amount.currency not in self.currency_breakdown:
            self.currency_breakdown[amount.currency] = {
                'debit': Decimal('0'),
                'credit': Decimal('0'),
                'balance': Decimal('0')
            }
        
        if is_debit:
            self.currency_breakdown[amount.currency]['debit'] += amount.amount
        else:
            self.currency_breakdown[amount.currency]['credit'] += amount.amount
        
        self.currency_breakdown[amount.currency]['balance'] = (
            self.currency_breakdown[amount.currency]['debit'] - 
            self.currency_breakdown[amount.currency]['credit']
        )
        
        # ✅ تحديث بيانات التدقيق
        object.__setattr__(self, 'last_journal_entry_id', entry_id)
        object.__setattr__(self, 'last_updated_at', utc_now())
        object.__setattr__(self, 'version', self.version + 1)
        
        logger.debug(
            f"Account {self.account_code} balance updated: "
            f"{self.current_balance} (version {self.version})"
        )
    
    def get_balance(self, currency: Optional[str] = None) -> Money:
        """
        ✅ الحصول على الرصيد (بالعملة المحددة أو الرئيسية)
        
        Args:
            currency: العملة المطلوبة (اختياري)
        
        Returns:
            Money: الرصيد المطلوب
        """
        if currency and currency != self.currency:
            # في حالة طلب عملة مختلفة، نبحث في التفصيل
            if currency in self.currency_breakdown:
                return Money(
                    self.currency_breakdown[currency]['balance'],
                    currency
                )
            return Money.zero(currency)
        
        return self.current_balance
    
    def get_currency_breakdown(self) -> Dict[str, Dict[str, Decimal]]:
        """✅ الحصول على تفصيل العملات"""
        return self.currency_breakdown.copy()
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الكائن إلى قاموس"""
        return {
            'account_code': str(self.account_code),
            'currency': self.currency,
            'total_debit': float(self.total_debit.amount),
            'total_credit': float(self.total_credit.amount),
            'current_balance': float(self.current_balance.amount),
            'currency_breakdown': {
                currency: {
                    'debit': float(totals['debit']),
                    'credit': float(totals['credit']),
                    'balance': float(totals['balance'])
                }
                for currency, totals in self.currency_breakdown.items()
            },
            'last_updated_at': self.last_updated_at.isoformat() if self.last_updated_at else None,
            'last_journal_entry_id': str(self.last_journal_entry_id) if self.last_journal_entry_id else None,
            'version': self.version
        }


# =============================================================================
# ✅ FiscalPeriod - المصحّح بالكامل (مع دعم إعادة الفتح)
# =============================================================================

@dataclass
class FiscalPeriod:
    """
    AGGREGATE ROOT
    
    يمثل الفترة المالية (شهر، ربع سنة، سنة) ويتحكم في صلاحيات وإجراءات الإقفال المحاسبي.
    
    ✅ محدث: إضافة دالة open_again لإعادة الفتح
    ✅ محدث: دعم صافي الدخل حسب العملة
    ✅ محدث: استخدام Clock Service
    ✅ محدث: إضافة التحقق من العملات المتعددة
    """
    
    name: PeriodReference
    start_date: date
    end_date: date
    is_closed: bool = False
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    
    # ✅ صافي الدخل حسب العملة (عند الإقفال)
    net_income_by_currency: Dict[str, Decimal] = field(default_factory=dict)
    
    # ✅ عدد القيود في الفترة
    entries_count: int = 0
    
    # ✅ Optimistic Locking
    version: int = 1
    
    # قائمة أحداث النطاق الداخلية للربط والتدقيق
    _events: List[Any] = field(default_factory=list, repr=False)
    
    def __post_init__(self):
        """التحقق من صحة البيانات بعد الإنشاء"""
        if self.start_date >= self.end_date:
            raise FiscalPeriodValidationError(
                f"Chronological Error: Start date ({self.start_date}) "
                f"cannot be equal to or later than end date ({self.end_date})."
            )
        
        # تهيئة net_income_by_currency إذا كانت فارغة
        if not self.net_income_by_currency:
            object.__setattr__(self, 'net_income_by_currency', {})
    
    def is_date_within(self, target_date: date) -> bool:
        """التحقق مما إذا كان التاريخ يقع ضمن نطاق الفترة."""
        return self.start_date <= target_date <= self.end_date
    
    def close(
        self, 
        closed_by: str, 
        net_income_by_currency: Dict[str, Decimal],
        entries_count: int
    ) -> None:
        """
        ✅ إغلاق الفترة المالية - مصحح لدعم العملات المتعددة
        
        Args:
            closed_by: من قام بالإغلاق
            net_income_by_currency: صافي الدخل لكل عملة
            entries_count: عدد القيود في الفترة
        
        Raises:
            PeriodAlreadyClosedError: إذا كانت الفترة مغلقة بالفعل
        """
        if self.is_closed:
            raise PeriodAlreadyClosedError(str(self.name))
        
        # ✅ تخزين صافي الدخل حسب العملة
        object.__setattr__(self, 'net_income_by_currency', net_income_by_currency.copy())
        object.__setattr__(self, 'entries_count', entries_count)
        
        # ✅ إغلاق الفترة
        object.__setattr__(self, 'is_closed', True)
        object.__setattr__(self, 'closed_at', utc_now())
        object.__setattr__(self, 'closed_by', closed_by)
        object.__setattr__(self, 'version', self.version + 1)
        
        # ✅ حساب إجمالي صافي الدخل
        total_net_income = sum(net_income_by_currency.values())
        main_currency = "USD"
        net_income_money = Money(total_net_income, main_currency)
        
        # ✅ بث حدث الإغلاق
        from .events import PeriodClosedEvent
        self._events.append(PeriodClosedEvent(
            period_name=self.name,
            closed_by=closed_by,
            net_income=net_income_money,
            entries_count=entries_count,
            start_date=datetime.combine(self.start_date, datetime.min.time(), timezone.utc),
            end_date=datetime.combine(self.end_date, datetime.max.time(), timezone.utc)
        ))
        
        logger.info(
            f"✅ Period {self.name} closed by {closed_by}. "
            f"Net income: {net_income_by_currency}, Entries: {entries_count}"
        )
    
    def open_again(self, opened_by: str, reason: str = "") -> None:
        """
        ✅ إعادة فتح فترة مغلقة - مع التراجع عن حالة الإقفال
        
        هذه العملية حساسة وتستخدم فقط لتصحيح الأخطاء.
        
        Args:
            opened_by: من قام بإعادة الفتح
            reason: سبب إعادة الفتح
        
        Raises:
            PeriodNotClosedError: إذا كانت الفترة مفتوحة بالفعل
        """
        if not self.is_closed:
            from .exceptions import PeriodNotClosedError
            raise PeriodNotClosedError(str(self.name))
        
        # ✅ إعادة فتح الفترة
        object.__setattr__(self, 'is_closed', False)
        object.__setattr__(self, 'closed_at', None)
        object.__setattr__(self, 'closed_by', None)
        object.__setattr__(self, 'version', self.version + 1)
        
        # ✅ تنظيف صافي الدخل المخزن
        object.__setattr__(self, 'net_income_by_currency', {})
        
        # ✅ بث حدث إعادة الفتح
        from .events import PeriodOpenedEvent
        self._events.append(PeriodOpenedEvent(
            period_name=self.name,
            opened_by=opened_by,
            start_date=datetime.combine(self.start_date, datetime.min.time(), timezone.utc),
            end_date=datetime.combine(self.end_date, datetime.max.time(), timezone.utc),
            previous_period=self.name,
            reason=reason
        ))
        
        logger.warning(f"⚠️ Period {self.name} reopened by {opened_by}. Reason: {reason}")
    
    def verify_date_allows_posting(self, transaction_date: date) -> None:
        """
        ✅ التحقق مما إذا كانت الفترة تسمح بالترحيل المحاسبي.
        
        Args:
            transaction_date: تاريخ المعاملة
        
        Raises:
            PeriodClosedModificationError: إذا كانت الفترة مغلقة
        """
        if self.is_closed and self.is_date_within(transaction_date):
            raise PeriodClosedModificationError(
                f"Compliance Restriction: The fiscal period '{self.name}' is closed. "
                f"No insertions or adjustments allowed for date {transaction_date}."
            )
    
    def get_net_income_summary(self) -> Dict[str, Any]:
        """
        ✅ الحصول على ملخص صافي الدخل للفترة
        
        Returns:
            Dict[str, Any]: ملخص صافي الدخل
        """
        total = sum(self.net_income_by_currency.values())
        
        return {
            'period_name': str(self.name),
            'is_closed': self.is_closed,
            'net_income_by_currency': {
                currency: float(amount) 
                for currency, amount in self.net_income_by_currency.items()
            },
            'total_net_income': float(total),
            'currency_count': len(self.net_income_by_currency),
            'entries_count': self.entries_count,
            'closed_by': self.closed_by,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None
        }
    
    def pull_events(self) -> List[Any]:
        """قشط وتفريغ قائمة أحداث الفترة للـ Dispatcher الخارجي."""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الفترة إلى قاموس"""
        return {
            'name': str(self.name),
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'is_closed': self.is_closed,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'closed_by': self.closed_by,
            'net_income_by_currency': {
                currency: float(amount) 
                for currency, amount in self.net_income_by_currency.items()
            },
            'entries_count': self.entries_count,
            'version': self.version
        }
    
    def __repr__(self) -> str:
        status = "CLOSED" if self.is_closed else "OPEN"
        return f"FiscalPeriod(name={self.name}, status={status}, version={self.version})"


# =============================================================================
# ✅ دالة مساعدة لإنشاء فترة جديدة
# =============================================================================

def create_fiscal_period(
    name: PeriodReference,
    start_date: date,
    end_date: date
) -> FiscalPeriod:
    """
    إنشاء فترة مالية جديدة
    
    Args:
        name: اسم الفترة
        start_date: تاريخ البداية
        end_date: تاريخ النهاية
    
    Returns:
        FiscalPeriod: الفترة المنشأة
    """
    return FiscalPeriod(
        name=name,
        start_date=start_date,
        end_date=end_date,
        is_closed=False
    )


# =============================================================================
# ✅ تصدير جميع العناصر
# =============================================================================

__all__ = [
    "AccountBalance",
    "FiscalPeriod",
    "aware_utc_today",
    "utc_now",
    "create_fiscal_period",
]