# core/domain/accounting/interfaces.py
"""
REPOSITORY AND SERVICE INTERFACES (PORTS) - YAseen ERP ENTERPRISE VERSION
الإصدار المُصلح - v2.1.0

This module defines the clean operational boundaries (Ports) of the accounting domain.
It isolates core domain aggregates and contracts from concrete infrastructures 
(such as PostgreSQL, SQLAlchemy models, or specific API layers).

RULES:
    1. Domain structures contain pure entities and value objects (No ORM dependencies).
    2. All dates and timestamps MUST strictly respect Timezone settings (Timezone-Aware).
    3. Methods on frozen/immutable data structures must return new instances.
    4. Numeric operations handling balances MUST account for explicit Currency ISO codes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any, Union
from uuid import UUID

# ✅ استيراد موحد وصارم من طبقة الـ Shared Kernel
from core.domain.shared.value_objects import Money, EntityId, BaseDomainEvent, AccountCode

# ✅ استيرادات محلية آمنة
from .value_objects import (
    EntryId, JournalEntryId, 
    TransactionType, PeriodReference
)
from .entities import JournalEntry
from .exceptions import EntryNotFoundError, ConcurrentModificationError


# ==============================================================================
# ========== DOMAIN DATA STRUCTURES (PURE DOMAIN MODELS) ======================
# ==============================================================================

@dataclass(frozen=True)
class LedgerEntry:
    """
    تمثيل لسطر حقيقي مسجل في دفتر الأستاذ العام (Read-Only Ledger View).
    بنية بيانات نقية لحماية النزاهة التاريخية للقيود المحللة.
    """
    entry_id: EntryId
    journal_entry_id: JournalEntryId
    account_code: AccountCode
    debit: Money
    credit: Money
    date: datetime
    posted_at: datetime
    reference: Optional[str] = None
    
    @property
    def amount(self) -> Money:
        """الحصول على القيمة الصافية الموقعة (موجب للمدين، سالب للدائن)."""
        if self.debit.amount > 0:
            return self.debit
        return Money(-self.credit.amount, self.credit.currency)
        
    @property
    def is_debit(self) -> bool:
        return self.debit.amount > 0
        
    @property
    def is_credit(self) -> bool:
        return self.credit.amount > 0


@dataclass(frozen=True)
class Account:
    """
    الحساب المالي المحاسبي (شجرة الحسابات).
    كائن مجمد بالكامل لضمان تعديل الحالة عبر دوال مخصصة ونقية فقط.
    """
    code: AccountCode
    name: str
    account_type: str            # 'asset', 'liability', 'equity', 'revenue', 'expense'
    is_active: bool = True
    parent_code: Optional[AccountCode] = None
    description: Optional[str] = None
    currency: str = "USD"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def can_be_debited(self) -> bool:
        return self.account_type in ['asset', 'expense']
        
    def can_be_credited(self) -> bool:
        return self.account_type in ['liability', 'equity', 'revenue']
        
    def deactivate(self, current_time: datetime) -> 'Account':
        return Account(
            code=self.code, name=self.name, account_type=self.account_type,
            is_active=False, parent_code=self.parent_code, description=self.description,
            currency=self.currency, created_at=self.created_at, updated_at=current_time,
            version=self.version + 1
        )
        
    def activate(self, current_time: datetime) -> 'Account':
        return Account(
            code=self.code, name=self.name, account_type=self.account_type,
            is_active=True, parent_code=self.parent_code, description=self.description,
            currency=self.currency, created_at=self.created_at, updated_at=current_time,
            version=self.version + 1
        )


@dataclass(frozen=True)
class FiscalPeriod:
    """
    الفترة المالية للنظام (تتحكم في صلاحية قبول ترحيل وتعديل المعاملات).
    """
    name: PeriodReference
    start_date: date
    end_date: date
    is_closed: bool = False
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    opened_by: Optional[str] = None
    opened_at: Optional[datetime] = None
    
    def contains(self, dt: date) -> bool:
        return self.start_date <= dt <= self.end_date
        
    def close(self, closed_by: str, current_time: datetime) -> 'FiscalPeriod':
        if self.is_closed:
            raise ValueError(f"Accounting Violation: Period {self.name} is already closed.")
        return FiscalPeriod(
            name=self.name, start_date=self.start_date, end_date=self.end_date,
            is_closed=True, closed_by=closed_by, closed_at=current_time,
            opened_by=self.opened_by, opened_at=self.opened_at
        )
        
    def open_again(self, opened_by: str, current_time: datetime) -> 'FiscalPeriod':
        """إعادة فتح فترة مغلقة استثنائياً لأغراض التسويات الإدارية الفوقية"""
        return FiscalPeriod(
            name=self.name, start_date=self.start_date, end_date=self.end_date,
            is_closed=False, closed_by=None, closed_at=None,
            opened_by=opened_by, opened_at=current_time
        )
        
    def is_month(self) -> bool: return self.name.is_month()
    def is_quarter(self) -> bool: return self.name.is_quarter()
    def is_year(self) -> bool: return self.name.is_year()
    def get_month(self) -> Optional[int]: return self.name.get_month()
    def get_quarter(self) -> Optional[int]: return self.name.get_quarter()


@dataclass(frozen=True)
class ClosingResult:
    """التقرير الناتج عن إجراءات عملية إقفال الحسابات للفترة المالية"""
    period_name: str
    closed_by: str
    closed_at: datetime
    net_income: Money
    entries_created: int
    success: bool
    errors: List[str] = field(default_factory=list)
    closing_entries: List[JournalEntryId] = field(default_factory=list)


@dataclass(frozen=True)
class AuditRecord:
    """سجل التدقيق الأمني والمالي الحساس لكافة حركات التغيير داخل النظام"""
    id: str
    operation: str
    entity_type: str
    entity_id: str
    performed_by: str
    performed_at: datetime
    old_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    changes: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# ==============================================================================
# ========== ✅ INVOICE DOMAIN DATA STRUCTURES (مصلحة) ========================
# ==============================================================================

@dataclass(frozen=True)
class InvoiceSummary:
    """
    ملخص فاتورة - بنية بيانات نقية للقراءة فقط.
    تستخدم لعرض المعلومات الأساسية للفاتورة دون الحاجة لتحميل الكائن الكامل.
    
    ✅ مصلح: استخدام dataclass بشكل صحيح (بدون __init__ يدوي)
    """
    id: str
    number: str
    date: datetime
    customer_name: str
    total: Money
    status: str
    created_at: datetime
    
    @property
    def total_formatted(self) -> str:
        """إجمالي الفاتورة منسقاً"""
        return f"{self.total.amount:,.2f} {self.total.currency}"
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض للفاتورة"""
        return f"{self.number} - {self.customer_name}"


# ==============================================================================
# ========== ✅ PURCHASE ORDER DOMAIN DATA STRUCTURES (مصلحة) =================
# ==============================================================================

@dataclass(frozen=True)
class PurchaseOrderSummary:
    """
    ملخص أمر شراء - بنية بيانات نقية للقراءة فقط.
    تستخدم لعرض المعلومات الأساسية لأمر الشراء دون الحاجة لتحميل الكائن الكامل.
    
    ✅ مصلح: استخدام dataclass بشكل صحيح (بدون __init__ يدوي)
    """
    id: str
    number: str
    date: datetime
    supplier_name: str
    total: Money
    status: str
    created_at: datetime
    
    @property
    def total_formatted(self) -> str:
        """إجمالي أمر الشراء منسقاً"""
        return f"{self.total.amount:,.2f} {self.total.currency}"
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض لأمر الشراء"""
        return f"{self.number} - {self.supplier_name}"


# ==============================================================================
# ========== IInvoiceRepository INTERFACE ======================================
# ==============================================================================

class IInvoiceRepository(ABC):
    """
    واجهة مستودع الفواتير - معرفة في طبقة Domain.
    
    هذه الواجهة تحدد العقود التي يجب أن تنفذها البنية التحتية (Infrastructure)
    دون أن تعرف تفاصيل التنفيذ. هذا يسمح بفصل تام بين Domain و Infrastructure.
    
    المبادئ:
        1. تستخدم كائنات Domain فقط (لا ORM models)
        2. لا تحتوي على منطق أعمال (Business Logic)
        3. جميع الدالات تعمل مع Value Objects من Domain
    """
    
    @abstractmethod
    def save(self, invoice: Any) -> None:
        """حفظ الفاتورة (جديدة أو محدثة)."""
        pass
    
    @abstractmethod
    def get_by_id(self, invoice_id: Any) -> Optional[Any]:
        """الحصول على فاتورة بواسطة المعرف."""
        pass
    
    @abstractmethod
    def get_by_number(self, number: Any) -> Optional[Any]:
        """الحصول على فاتورة بواسطة الرقم."""
        pass
    
    @abstractmethod
    def get_by_journal_entry_id(self, journal_entry_id: str) -> Optional[Any]:
        """الحصول على فاتورة بواسطة معرف القيد المحاسبي."""
        pass
    
    @abstractmethod
    def list_by_customer(self, customer_id: str, limit: int = 100) -> List[Any]:
        """قائمة فواتير العميل."""
        pass
    
    @abstractmethod
    def list_by_status(self, status: Any, limit: int = 100) -> List[Any]:
        """قائمة فواتير حسب الحالة."""
        pass
    
    @abstractmethod
    def list_by_date_range(self, from_date: date, to_date: date, limit: int = 100) -> List[Any]:
        """قائمة فواتير في نطاق زمني."""
        pass
    
    @abstractmethod
    def get_next_number(self) -> Any:
        """الحصول على رقم الفاتورة التالي."""
        pass
    
    @abstractmethod
    def delete_draft(self, invoice_id: Any) -> bool:
        """حذف فاتورة مسودة (غير مرحّلة)."""
        pass
    
    @abstractmethod
    def get_summary_by_customer(self, customer_id: str, limit: int = 10) -> List[InvoiceSummary]:
        """الحصول على ملخص فواتير العميل (للقراءة فقط، أداء أفضل)."""
        pass
    
    @abstractmethod
    def count_by_status(self, status: Any) -> int:
        """حساب عدد الفواتير حسب الحالة."""
        pass
    
    @abstractmethod
    def get_total_by_customer(self, customer_id: str, status: Optional[Any] = None) -> Money:
        """حساب إجمالي فواتير العميل."""
        pass


# ==============================================================================
# ========== IPurchaseOrderRepository INTERFACE ================================
# ==============================================================================

class IPurchaseOrderRepository(ABC):
    """
    واجهة مستودع أوامر الشراء - معرفة في طبقة Domain.
    
    هذه الواجهة تحدد العقود التي يجب أن تنفذها البنية التحتية (Infrastructure)
    دون أن تعرف تفاصيل التنفيذ.
    
    المبادئ:
        1. تستخدم كائنات Domain فقط (لا ORM models)
        2. لا تحتوي على منطق أعمال (Business Logic)
        3. جميع الدالات تعمل مع Value Objects من Domain
    """
    
    @abstractmethod
    def save(self, order: Any) -> None:
        """حفظ أمر الشراء (جديد أو محدث)."""
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: Any) -> Optional[Any]:
        """الحصول على أمر شراء بواسطة المعرف."""
        pass
    
    @abstractmethod
    def get_by_number(self, number: Any) -> Optional[Any]:
        """الحصول على أمر شراء بواسطة الرقم."""
        pass
    
    @abstractmethod
    def get_by_journal_entry_id(self, journal_entry_id: str) -> Optional[Any]:
        """الحصول على أمر شراء بواسطة معرف القيد المحاسبي."""
        pass
    
    @abstractmethod
    def list_by_supplier(self, supplier_id: str, limit: int = 100) -> List[Any]:
        """قائمة أوامر شراء المورد."""
        pass
    
    @abstractmethod
    def list_by_status(self, status: Any, limit: int = 100) -> List[Any]:
        """قائمة أوامر شراء حسب الحالة."""
        pass
    
    @abstractmethod
    def list_by_date_range(self, from_date: date, to_date: date, limit: int = 100) -> List[Any]:
        """قائمة أوامر شراء في نطاق زمني."""
        pass
    
    @abstractmethod
    def get_next_number(self) -> Any:
        """الحصول على رقم أمر الشراء التالي."""
        pass
    
    @abstractmethod
    def delete_draft(self, order_id: Any) -> bool:
        """حذف أمر شراء مسودة (غير مرحّل)."""
        pass
    
    @abstractmethod
    def get_summary_by_supplier(self, supplier_id: str, limit: int = 10) -> List[PurchaseOrderSummary]:
        """الحصول على ملخص أوامر شراء المورد (للقراءة فقط، أداء أفضل)."""
        pass
    
    @abstractmethod
    def count_by_status(self, status: Any) -> int:
        """حساب عدد أوامر الشراء حسب الحالة."""
        pass
    
    @abstractmethod
    def get_total_by_supplier(self, supplier_id: str, status: Optional[Any] = None) -> Money:
        """حساب إجمالي أوامر شراء المورد."""
        pass


# ==============================================================================
# ========== REPOSITORY INTERFACES (PORTS) - CONTINUED =========================
# ==============================================================================

class ILedgerRepository(ABC):
    """عقد مستودع دفتر الأستاذ العام - الحركات والتحليلات المالية التراكمية"""
    
    @abstractmethod
    def add_entry(
        self, entry_id: EntryId, account_code: AccountCode, 
        debit: Money, credit: Money, date: datetime,
        journal_entry_id: JournalEntryId, reference: Optional[str] = None
    ) -> None:
        pass
        
    @abstractmethod
    def get_entries_by_account(
        self, account_code: AccountCode, from_date: Optional[date] = None, 
        to_date: Optional[date] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[LedgerEntry]:
        pass
        
    @abstractmethod
    def get_balance(self, account_code: AccountCode, as_of: date, currency: str = "USD") -> Money:
        pass
        
    @abstractmethod
    def get_trial_balance(self, as_of: date, account_types: Optional[List[str]] = None, currency: str = "USD") -> Dict[AccountCode, Money]:
        pass
        
    @abstractmethod
    def get_account_history(self, account_code: AccountCode, from_date: date, to_date: date) -> List[LedgerEntry]:
        pass
        
    @abstractmethod
    def get_opening_balance(self, account_code: AccountCode, as_of: date, currency: str = "USD") -> Money:
        pass


class IJournalEntryRepository(ABC):
    """عقد مستودع قيود اليومية - إدارة مسودات ووثائق القيود المزدوجة"""
    
    @abstractmethod
    def save(self, entry: JournalEntry) -> None:
        pass
        
    @abstractmethod
    def get_by_id(self, entry_id: JournalEntryId) -> Optional[JournalEntry]:
        pass
        
    @abstractmethod
    def get_by_id_or_fail(self, entry_id: JournalEntryId) -> JournalEntry:
        pass

    @abstractmethod
    def list_all(self, limit: Optional[int] = None, offset: Optional[int] = None, is_posted: Optional[bool] = None) -> List[JournalEntry]:
        pass
        
    @abstractmethod
    def get_posted_entries(self, from_date: date, to_date: date, transaction_type: Optional[TransactionType] = None) -> List[JournalEntry]:
        pass
        
    @abstractmethod
    def get_draft_entries(self, user_id: Optional[str] = None, limit: Optional[int] = None) -> List[JournalEntry]:
        pass
        
    @abstractmethod
    def exists_reversal(self, original_entry_id: JournalEntryId) -> bool:
        pass
        
    @abstractmethod
    def get_reversal_for(self, original_entry_id: JournalEntryId) -> Optional[JournalEntry]:
        pass
        
    @abstractmethod
    def get_by_reference(self, reference_number: str) -> Optional[JournalEntry]:
        pass
        
    @abstractmethod
    def delete_draft(self, entry_id: JournalEntryId) -> bool:
        pass
        
    @abstractmethod
    def count_by_period(self, period: PeriodReference) -> int:
        pass
        
    @abstractmethod
    def get_entries_in_date_range(self, start_date: date, end_date: date, include_unposted: bool = True) -> List[JournalEntry]:
        pass
        
    @abstractmethod
    def get_unposted_entries_in_period(self, period: FiscalPeriod) -> List[JournalEntry]:
        pass
        
    @abstractmethod
    def count_unposted_in_period(self, period: FiscalPeriod) -> int:
        pass


class IFiscalPeriodRepository(ABC):
    """عقد مستودع الفترات والدورات المستندية المالية"""
    
    @abstractmethod
    def get_period_by_date(self, dt: date) -> Optional[FiscalPeriod]:
        pass
        
    @abstractmethod
    def get_period_by_name(self, name: PeriodReference) -> Optional[FiscalPeriod]:
        pass
        
    @abstractmethod
    def get_period_by_name_or_fail(self, name: PeriodReference) -> FiscalPeriod:
        pass
        
    @abstractmethod
    def get_all_periods(self, from_year: Optional[int] = None, to_year: Optional[int] = None, include_closed: bool = True) -> List[FiscalPeriod]:
        pass
        
    @abstractmethod
    def get_current_period(self, as_of: Optional[date] = None) -> Optional[FiscalPeriod]:
        pass
        
    @abstractmethod
    def save(self, period: FiscalPeriod) -> None:
        pass
        
    @abstractmethod
    def is_period_closed(self, dt: date) -> bool:
        pass
        
    @abstractmethod
    def get_next_period(self, current: PeriodReference) -> Optional[PeriodReference]:
        pass
        
    @abstractmethod
    def get_previous_period(self, current: PeriodReference) -> Optional[PeriodReference]:
        pass


class IAccountRepository(ABC):
    """عقد مستودع الحسابات المالية لإدارة وضبط الدليل المحاسبي وشجرة الحسابات"""
    
    @abstractmethod
    def get_by_code(self, code: AccountCode) -> Optional[Account]:
        pass
        
    @abstractmethod
    def get_by_code_or_fail(self, code: AccountCode) -> Account:
        pass
        
    @abstractmethod
    def get_all_accounts(self, account_type: Optional[str] = None, include_inactive: bool = False) -> List[Account]:
        pass
        
    @abstractmethod
    def get_active_accounts(self) -> List[Account]:
        pass
        
    @abstractmethod
    def exists(self, code: AccountCode) -> bool:
        pass
        
    @abstractmethod
    def is_active(self, code: AccountCode) -> bool:
        pass
        
    @abstractmethod
    def save(self, account: Account) -> None:
        pass
        
    @abstractmethod
    def get_children(self, parent_code: AccountCode) -> List[Account]:
        pass
        
    @abstractmethod
    def get_root_accounts(self) -> List[Account]:
        pass


class IAuditRepository(ABC):
    """عقد مستودع سجلات الأمان والتعقب ونزاهة الحركات الوظيفية والمالية"""
    
    @abstractmethod
    def log_operation(
        self, operation: str, entity_type: str, entity_id: str, performed_by: str,
        old_state: Optional[Dict] = None, new_state: Optional[Dict] = None, changes: Optional[Dict] = None,
        ip_address: Optional[str] = None, user_agent: Optional[str] = None
    ) -> None:
        pass
        
    @abstractmethod
    def get_audit_trail(
        self, entity_type: Optional[str] = None, entity_id: Optional[str] = None,
        from_date: Optional[datetime] = None, to_date: Optional[datetime] = None,
        performed_by: Optional[str] = None, limit: Optional[int] = None
    ) -> List[AuditRecord]:
        pass
        
    @abstractmethod
    def get_entity_history(self, entity_type: str, entity_id: str) -> List[AuditRecord]:
        pass


# ==============================================================================
# ========== UNIT OF WORK INTERFACE (WITH INVOICES & PURCHASE ORDERS) ==========
# ==============================================================================

class IUnitOfWork(ABC):
    """
    واجهة إدارة سياق المعاملة الموحدة (Unit of Work).
    تضمن ترحيل أو إلغاء مجموعة العمليات ككتلة ذرية واحدة (Atomicity) لحفظ سلامة الحسابات.
    
    ✅ محدّث: الآن يتضمن IInvoiceRepository و IPurchaseOrderRepository
    """
    
    @abstractmethod
    def __enter__(self): pass
    
    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb): pass
    
    @abstractmethod
    def commit(self) -> None: pass
    
    @abstractmethod
    def rollback(self) -> None: pass
    
    @property
    @abstractmethod
    def journal_entries(self) -> IJournalEntryRepository:
        """مستودع قيود اليومية"""
        pass
    
    @property
    @abstractmethod
    def ledger(self) -> ILedgerRepository:
        """مستودع دفتر الأستاذ"""
        pass
    
    @property
    @abstractmethod
    def accounts(self) -> IAccountRepository:
        """مستودع شجرة الحسابات"""
        pass
    
    @property
    @abstractmethod
    def periods(self) -> IFiscalPeriodRepository:
        """مستودع الفترات المالية"""
        pass
    
    @property
    @abstractmethod
    def audit(self) -> IAuditRepository:
        """مستودع سجلات التدقيق"""
        pass
    
    @property
    @abstractmethod
    def invoices(self) -> IInvoiceRepository:
        """
        مستودع الفواتير - للربط بين Invoicing و Accounting.
        
        هذا يسمح لنا بالوصول إلى الفواتير من داخل وحدة المعاملة
        مما يمكننا من إنشاء قيود محاسبية عند ترحيل الفواتير.
        """
        pass
    
    @property
    @abstractmethod
    def purchase_orders(self) -> IPurchaseOrderRepository:
        """
        مستودع أوامر الشراء - للربط بين Purchasing و Accounting.
        
        هذا يسمح لنا بالوصول إلى أوامر الشراء من داخل وحدة المعاملة
        مما يمكننا من إنشاء قيود محاسبية عند ترحيل أوامر الشراء.
        """
        pass
    
    @abstractmethod
    def collect_event(self, event: BaseDomainEvent) -> None:
        """تجميع حدث Domain واحد لصرفه لاحقاً"""
        pass
    
    @abstractmethod
    def collect_events(self, events: List[BaseDomainEvent]) -> None:
        """تجميع قائمة أحداث Domain لصرفها لاحقاً"""
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """تنفيذ أي عمليات معلقة دون commit"""
        pass
    
    @abstractmethod
    def refresh(self, obj: Any) -> None:
        """تحديث كائن من قاعدة البيانات"""
        pass


# ==============================================================================
# ========== EVENT BUS INTERFACE ===============================================
# ==============================================================================

class IEventBus(ABC):
    """ناقل الأحداث الداخلي لتوزيع الـ Domain Events وفك الارتباط المتشابك بين الموديولات"""
    
    @abstractmethod
    def dispatch(self, event: BaseDomainEvent) -> None: pass
    
    @abstractmethod
    def dispatch_many(self, events: List[BaseDomainEvent]) -> None: pass
    
    @abstractmethod
    def add_handler(self, event_type: type, handler: callable) -> None: pass
    
    @abstractmethod
    def remove_handler(self, event_type: type, handler: callable) -> None: pass


# ==============================================================================
# ========== SERVICE INTERFACES (DOMAIN SERVICES) ==============================
# ==============================================================================

class IPostingEngine(ABC):
    """محرك الترحيل المحاسبي - التحقق الصارم من التوازن قبل التموضع الدائم في الجداول الختامية"""
    @abstractmethod
    def post(self, entry: JournalEntry, posted_by: str) -> None: pass
    
    @abstractmethod
    def validate_before_posting(self, entry: JournalEntry) -> List[str]: pass


class ILedgerEngine(ABC):
    """محرك الاستعلامات الحسابية لدفاتر الأستاذ العام وتوليد الموازين"""
    @abstractmethod
    def get_balance(self, account_code: AccountCode, as_of: date, currency: str = "USD") -> Money: pass
    
    @abstractmethod
    def get_trial_balance(self, as_of: date, currency: str = "USD") -> Dict[AccountCode, Money]: pass
    
    @abstractmethod
    def verify_trial_balance(self, as_of: date, currency: str = "USD") -> Tuple[bool, Decimal]: pass


class IReversalService(ABC):
    """الخدمة المسؤولة عن معالجة وإصدار القيود العكسية والتسويات المحاسبية"""
    @abstractmethod
    def reverse_entry(self, original_entry_id: JournalEntryId, reason: str, posted_by: str, auto_post: bool = True) -> JournalEntry: pass
    
    @abstractmethod
    def can_reverse(self, entry_id: JournalEntryId) -> Tuple[bool, Optional[str]]: pass


class IClosingService(ABC):
    """خدمة المعالجة الختامية للفترات المالية واحتساب الأرباح والخسائر المدورة"""
    @abstractmethod
    def close_period(self, period_name: str, closed_by: str) -> ClosingResult: pass
    
    @abstractmethod
    def can_close_period(self, period_name: str) -> Tuple[bool, List[str]]: pass


class IIdGenerator(ABC):
    """مزود إنشاء المعرفات الفريدة والآمنة للـ Aggregates"""
    @abstractmethod
    def generate_entry_id(self) -> EntryId: pass
    
    @abstractmethod
    def generate_journal_entry_id(self) -> JournalEntryId: pass
    
    @abstractmethod
    def generate_uuid(self) -> UUID: pass


class IClock(ABC):
    """مزود الوقت والتواريخ الموحد للنظام بالكامل لمنع ثغرات التوقيت الساذج والمحلي"""
    @abstractmethod
    def now(self) -> datetime:
        """إرجاع كائن datetime مدعوم بالمنطقة الزمنية العالمية الموحدة لحفظ حركات التدقيق بحسم"""
        pass
        
    @abstractmethod
    def today(self) -> date: pass


# ==============================================================================
# ========== EXPORTS EXPLICITLY DEFINED ========================================
# ==============================================================================

__all__ = [
    # Domain data structures
    "LedgerEntry",
    "Account", 
    "FiscalPeriod",
    "ClosingResult",
    "AuditRecord",
    "InvoiceSummary",
    "PurchaseOrderSummary",
    
    # Repository interfaces
    "ILedgerRepository",
    "IJournalEntryRepository",
    "IFiscalPeriodRepository",
    "IAccountRepository",
    "IAuditRepository",
    "IInvoiceRepository",
    "IPurchaseOrderRepository",
    
    # Unit of Work
    "IUnitOfWork",
    
    # Event Bus
    "IEventBus",
    
    # Service interfaces
    "IPostingEngine",
    "ILedgerEngine",
    "IReversalService",
    "IClosingService",
    "IIdGenerator",
    "IClock",
]