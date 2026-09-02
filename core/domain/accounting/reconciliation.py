# core/domain/accounting/reconciliation.py
"""
Bank Reconciliation - تسوية الحسابات البنكية
الإصدار: 1.0.0

الميزات:
    1. مطابقة الحركات البنكية مع دفتر الأستاذ
    2. كشف الفروقات (الحركات غير المطابقة)
    3. إنشاء قيود تسوية تلقائية
    4. تقارير التسوية
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID, uuid4

from core.domain.shared.value_objects import Money, AccountCode
from core.domain.accounting.entities import JournalEntry, JournalLine


class ReconciliationStatus(str, Enum):
    """حالة التسوية البنكية"""
    DRAFT = "draft"              # مسودة
    IN_PROGRESS = "in_progress"  # قيد التنفيذ
    RECONCILED = "reconciled"    # متطابقة
    PARTIAL = "partial"          # متطابقة جزئياً
    FAILED = "failed"            # فشلت
    CANCELLED = "cancelled"      # ملغية


class ReconciliationType(str, Enum):
    """نوع التسوية"""
    BANK = "bank"                # تسوية بنكية
    CASH = "cash"                # تسوية نقدية
    CUSTOMER = "customer"        # تسوية عملاء
    SUPPLIER = "supplier"        # تسوية موردين


class MatchingStatus(str, Enum):
    """حالة المطابقة"""
    MATCHED = "matched"          # متطابقة
    UNMATCHED = "unmatched"      # غير متطابقة
    PARTIAL = "partial"          # مطابقة جزئية
    MANUAL = "manual"            # مطابقة يدوية
    IGNORED = "ignored"          # تم تجاهلها


@dataclass
class BankStatementLine:
    """
    سطر في كشف حساب بنكي
    
    Attributes:
        id: معرف السطر
        transaction_date: تاريخ الحركة
        value_date: تاريخ القيد (تاريخ الاستحقاق)
        description: وصف الحركة
        amount: المبلغ (موجب للإيداع، سالب للسحب)
        currency: العملة
        reference: المرجع (رقم الشيك، التحويل، إلخ)
        counterparty: الطرف الآخر (اسم العميل/المورد)
        bank_reference: المرجع البنكي
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    transaction_date: datetime = field(default_factory=datetime.now)
    value_date: Optional[datetime] = None
    description: str = ""
    amount: Money = field(default_factory=lambda: Money.zero())
    currency: str = "USD"
    reference: Optional[str] = None
    counterparty: Optional[str] = None
    bank_reference: Optional[str] = None
    is_cleared: bool = False
    cleared_at: Optional[datetime] = None
    
    @property
    def is_debit(self) -> bool:
        """هل الحركة دائنة (سحب من الحساب)؟"""
        return self.amount.amount < 0
    
    @property
    def is_credit(self) -> bool:
        """هل الحركة مدينة (إيداع في الحساب)؟"""
        return self.amount.amount > 0
    
    @property
    def abs_amount(self) -> Decimal:
        """القيمة المطلقة للمبلغ"""
        return abs(self.amount.amount)


@dataclass
class BankStatement:
    """
    كشف حساب بنكي
    
    Attributes:
        id: معرف الكشف
        account_code: كود الحساب البنكي في شجرة الحسابات
        bank_name: اسم البنك
        account_number: رقم الحساب
        statement_date: تاريخ الكشف
        opening_balance: الرصيد الافتتاحي
        closing_balance: الرصيد الختامي
        lines: قائمة الحركات
        currency: العملة
        file_name: اسم الملف المصدر (للاستيراد)
        uploaded_at: تاريخ الاستيراد
        uploaded_by: من قام بالاستيراد
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    account_code: AccountCode = field(default_factory=lambda: AccountCode("1040"))
    bank_name: str = ""
    account_number: str = ""
    statement_date: date = field(default_factory=date.today)
    opening_balance: Money = field(default_factory=lambda: Money.zero())
    closing_balance: Money = field(default_factory=lambda: Money.zero())
    lines: List[BankStatementLine] = field(default_factory=list)
    currency: str = "USD"
    file_name: Optional[str] = None
    uploaded_at: datetime = field(default_factory=datetime.now)
    uploaded_by: str = "system"
    
    @property
    def total_credits(self) -> Decimal:
        """إجمالي الإيداعات"""
        return sum(abs(l.amount.amount) for l in self.lines if l.is_credit)
    
    @property
    def total_debits(self) -> Decimal:
        """إجمالي السحوبات"""
        return sum(abs(l.amount.amount) for l in self.lines if l.is_debit)
    
    @property
    def calculated_closing_balance(self) -> Decimal:
        """حساب الرصيد الختامي من الحركات"""
        balance = self.opening_balance.amount
        for line in self.lines:
            balance += line.amount.amount
        return balance
    
    @property
    def is_balanced(self) -> bool:
        """هل الكشف متوازن؟"""
        return abs(self.calculated_closing_balance - self.closing_balance.amount) < Decimal('0.01')
    
    @property
    def line_count(self) -> int:
        return len(self.lines)


@dataclass
class ReconciliationMatch:
    """
    سجل مطابقة بين حركة بنكية وحركة محاسبية
    
    Attributes:
        id: معرف المطابقة
        bank_line_id: معرف سطر الكشف البنكي
        ledger_entry_id: معرف حركة دفتر الأستاذ
        amount: المبلغ المطابق
        status: حالة المطابقة
        matched_by: من قام بالمطابقة
        matched_at: تاريخ المطابقة
        notes: ملاحظات
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    bank_line_id: str = ""
    ledger_entry_id: str = ""
    amount: Money = field(default_factory=lambda: Money.zero())
    status: MatchingStatus = MatchingStatus.MATCHED
    matched_by: str = "system"
    matched_at: datetime = field(default_factory=datetime.now)
    notes: Optional[str] = None


@dataclass
class Reconciliation:
    """
    عملية تسوية بنكية
    
    Attributes:
        id: معرف التسوية
        bank_statement_id: معرف كشف الحساب البنكي
        account_code: كود الحساب
        reconciliation_date: تاريخ التسوية
        status: حالة التسوية
        reconciliation_type: نوع التسوية
        opening_balance: الرصيد الافتتاحي (دفتر الأستاذ)
        closing_balance: الرصيد الختامي (دفتر الأستاذ)
        bank_opening_balance: الرصيد الافتتاحي (البنك)
        bank_closing_balance: الرصيد الختامي (البنك)
        matches: قائمة المطابقات
        unmatched_bank_lines: الحركات البنكية غير المطابقة
        unmatched_ledger_entries: الحركات المحاسبية غير المطابقة
        journal_entry_id: معرف قيد التسوية (إن وجد)
        notes: ملاحظات
        created_by: من قام بالإنشاء
        created_at: تاريخ الإنشاء
        completed_by: من قام بالإكمال
        completed_at: تاريخ الإكمال
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    bank_statement_id: str = ""
    account_code: AccountCode = field(default_factory=lambda: AccountCode("1040"))
    reconciliation_date: datetime = field(default_factory=datetime.now)
    status: ReconciliationStatus = ReconciliationStatus.DRAFT
    reconciliation_type: ReconciliationType = ReconciliationType.BANK
    
    # الأرصدة
    opening_balance: Money = field(default_factory=lambda: Money.zero())
    closing_balance: Money = field(default_factory=lambda: Money.zero())
    bank_opening_balance: Money = field(default_factory=lambda: Money.zero())
    bank_closing_balance: Money = field(default_factory=lambda: Money.zero())
    
    # المطابقات
    matches: List[ReconciliationMatch] = field(default_factory=list)
    unmatched_bank_lines: List[str] = field(default_factory=list)  # IDs
    unmatched_ledger_entries: List[str] = field(default_factory=list)  # IDs
    
    # القيد المحاسبي
    journal_entry_id: Optional[str] = None
    
    # بيانات إضافية
    notes: Optional[str] = None
    created_by: str = "system"
    created_at: datetime = field(default_factory=datetime.now)
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    # أحداث المجال
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def is_completed(self) -> bool:
        return self.status == ReconciliationStatus.RECONCILED
    
    @property
    def is_in_progress(self) -> bool:
        return self.status == ReconciliationStatus.IN_PROGRESS
    
    @property
    def total_matched(self) -> Decimal:
        """إجمالي المبالغ المطابقة"""
        return sum(m.amount.amount for m in self.matches)
    
    @property
    def difference(self) -> Decimal:
        """الفرق بين رصيد البنك ودفتر الأستاذ"""
        return abs(self.closing_balance.amount - self.bank_closing_balance.amount)
    
    @property
    def match_percentage(self) -> float:
        """نسبة المطابقة"""
        if not self.bank_closing_balance.amount:
            return 100.0
        total_bank = abs(self.bank_closing_balance.amount - self.bank_opening_balance.amount)
        if total_bank == 0:
            return 100.0
        matched = abs(self.total_matched)
        return float((matched / total_bank) * 100)
    
    def add_match(
        self,
        bank_line_id: str,
        ledger_entry_id: str,
        amount: Money,
        matched_by: str = "system",
        notes: Optional[str] = None
    ) -> ReconciliationMatch:
        """إضافة مطابقة جديدة"""
        match = ReconciliationMatch(
            bank_line_id=bank_line_id,
            ledger_entry_id=ledger_entry_id,
            amount=amount,
            matched_by=matched_by,
            notes=notes
        )
        self.matches.append(match)
        self.status = ReconciliationStatus.IN_PROGRESS
        
        # إزالة من القوائم غير المطابقة
        if bank_line_id in self.unmatched_bank_lines:
            self.unmatched_bank_lines.remove(bank_line_id)
        if ledger_entry_id in self.unmatched_ledger_entries:
            self.unmatched_ledger_entries.remove(ledger_entry_id)
        
        return match
    
    def complete(
        self,
        completed_by: str,
        journal_entry_id: Optional[str] = None
    ) -> None:
        """إكمال التسوية"""
        if self.status == ReconciliationStatus.RECONCILED:
            raise ValueError("Reconciliation is already completed")
        
        # التحقق من وجود فروقات
        if self.difference > Decimal('0.01'):
            raise ValueError(
                f"Cannot complete reconciliation: difference of {self.difference} "
                f"between bank and ledger balances"
            )
        
        self.status = ReconciliationStatus.RECONCILED
        self.completed_by = completed_by
        self.completed_at = datetime.now()
        self.journal_entry_id = journal_entry_id
        
        from .events import ReconciliationCompletedEvent
        self._events.append(ReconciliationCompletedEvent(
            reconciliation_id=self.id,
            account_code=self.account_code,
            completed_by=completed_by,
            difference=self.difference
        ))
    
    def cancel(self, cancelled_by: str, reason: Optional[str] = None) -> None:
        """إلغاء التسوية"""
        self.status = ReconciliationStatus.CANCELLED
        
        from .events import ReconciliationCancelledEvent
        self._events.append(ReconciliationCancelledEvent(
            reconciliation_id=self.id,
            cancelled_by=cancelled_by,
            reason=reason
        ))
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events


# =============================================================================
# أحداث التسوية
# =============================================================================

@dataclass(frozen=True)
class ReconciliationStartedEvent:
    """يُرفع عند بدء عملية التسوية"""
    reconciliation_id: str
    account_code: AccountCode
    started_by: str
    occurred_at: datetime = field(default_factory=datetime.now)
    
    def get_event_name(self) -> str:
        return "accounting.reconciliation.started"


@dataclass(frozen=True)
class ReconciliationCompletedEvent:
    """يُرفع عند إكمال التسوية"""
    reconciliation_id: str
    account_code: AccountCode
    completed_by: str
    difference: Decimal
    occurred_at: datetime = field(default_factory=datetime.now)
    
    def get_event_name(self) -> str:
        return "accounting.reconciliation.completed"


@dataclass(frozen=True)
class ReconciliationCancelledEvent:
    """يُرفع عند إلغاء التسوية"""
    reconciliation_id: str
    cancelled_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=datetime.now)
    
    def get_event_name(self) -> str:
        return "accounting.reconciliation.cancelled"