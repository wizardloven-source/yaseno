# core/domain/accounting/events.py
"""
DOMAIN EVENTS - RECORD WHAT HAPPENED IN THE DOMAIN (YAseen ERP ENTERPRISE VERSION)

Domain events are immutable records of significant occurrences within the accounting domain.
They are raised by aggregates and domain services, then collected by the Unit of Work 
and dispatched to trigger side effects (notifications, audit logs, integration with sub-systems).

RULES:
    1. Events MUST be named in the past tense (e.g., EntryPostedEvent).
    2. Events MUST be fully immutable (frozen=True).
    3. All datetime fields MUST be Timezone-Aware (strictly UTC).
    4. Serialization mapping must be dynamic and auto-registered.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List, Type
from uuid import UUID

# ✅ استيرادات موحدة من موديول الـ Shared Kernel والقيم الوظيفية المحاسبية
from core.domain.shared.value_objects import AccountCode, BaseDomainEvent, Money, EntityId
from .value_objects import (
    EntryId, JournalEntryId, 
    TransactionType, PeriodReference
)


def _aware_utc_now() -> datetime:
    """دالة مساعدة لإنشاء توقيت UTC واعي بالمنطقة الزمنية لمنع Naive Datetime Bug."""
    return datetime.now(timezone.utc)


# قاموس التسجيل التلقائي للأحداث لدعم دوال التحويل ديناميكياً
_EVENT_REGISTRY: Dict[str, Type[BaseDomainEvent]] = {}


def register_event(cls):
    """Decorator لتسجيل أحداث الـ Domain تلقائياً فور قراءتها من المفسر."""
    instance = cls.__new__(cls)
    if hasattr(instance, 'get_event_name'):
        _EVENT_REGISTRY[instance.get_event_name()] = cls
    return cls


# ==============================================================================
# ========== JOURNAL ENTRY EVENTS (أحداث قيود اليومية) ===========================
# ==============================================================================

@dataclass(frozen=True)
@register_event
class EntryCreatedEvent(BaseDomainEvent):
    """يُرفع فور إنشاء قيد اليومية لأول مرة وحفظه كمسودة (Draft)."""
    entry_id: JournalEntryId
    description: str
    transaction_type: TransactionType
    date: datetime
    line_count: int
    created_by: str
    created_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.entry.created"


@dataclass(frozen=True)
@register_event
class EntryValidatedEvent(BaseDomainEvent):
    """يُرفع عندما يجتاز القيد كافة قيود التحقق البرمجية ويصبح جاهزاً تماماً للترحيل."""
    entry_id: JournalEntryId
    total_debit: Decimal
    total_credit: Decimal
    currency: str
    accounts_involved: List[str]
    validated_by: str
    validated_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.entry.validated"


@dataclass(frozen=True)
@register_event
class EntryPostedEvent(BaseDomainEvent):
    """
    الحدث الأهم في النظام: يُرفع فور ترحيل القيد وإدراجه قطعيّاً في دفتر الأستاذ.
    بعد هذا الحدث، يصبح القيد والسطور التابعة له محمية تماماً من التعديل أو الحذف.
    """
    entry_id: JournalEntryId
    posted_by: str
    total_debit: Decimal
    total_credit: Decimal
    currency: str
    entry_date: datetime
    line_count: int
    posted_at: datetime = field(default_factory=_aware_utc_now)
    transaction_type: Optional[TransactionType] = None
    reference_number: Optional[str] = None
    
    def get_event_name(self) -> str:
        return "accounting.entry.posted"
        
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit


@dataclass(frozen=True)
@register_event
class EntryReversedEvent(BaseDomainEvent):
    """يُرفع عند إصدار قيد عكسي لتسوية أو إلغاء تأثير قيد معتمد ومرحل سابقاً."""
    original_entry_id: JournalEntryId
    reversal_entry_id: JournalEntryId
    reversed_by: str
    reason: str
    total_amount: Money
    reversed_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.entry.reversed"


@dataclass(frozen=True)
@register_event
class EntryCanceledEvent(BaseDomainEvent):
    """يُرفع عند حذف أو إلغاء قيد في حالة مسودة (Soft-delete لأغراض الرقابة)."""
    entry_id: JournalEntryId
    canceled_by: str
    reason: Optional[str] = None
    canceled_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.entry.canceled"


@dataclass(frozen=True)
@register_event
class EntryModificationAttemptEvent(BaseDomainEvent):
    """حدث أمني حساس: يُرفع عند محاولة شخص أو نظام تعديل قيد مرحل ومغلق."""
    entry_id: JournalEntryId
    attempted_by: str
    attempted_operation: str
    attempted_at: datetime = field(default_factory=_aware_utc_now)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def get_event_name(self) -> str:
        return "accounting.entry.modification_attempted"


# ==============================================================================
# ========== LEDGER EVENTS (أحداث دفتر الأستاذ العام) ============================
# ==============================================================================

@dataclass(frozen=True)
@register_event
class LedgerEntryAddedEvent(BaseDomainEvent):
    """يُرفع لكل سطر حركه مالي ينبثق عن قيد اليومية أثناء ترحيله لدفتر الأستاذ."""
    ledger_entry_id: EntryId
    journal_entry_id: JournalEntryId
    account_code: AccountCode
    amount: Money
    is_debit: bool
    date: datetime
    posted_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.ledger.entry_added"


@dataclass(frozen=True)
@register_event
class BalanceCalculatedEvent(BaseDomainEvent):
    """يُرفع عند إعادة احتساب رصيد الحساب، مفيد جداً لتحديث الكاش الوميضي (Redis/Caching)."""
    account_code: AccountCode
    balance: Money
    as_of: datetime
    calculated_by: str
    calculated_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.ledger.balance_calculated"


# ==============================================================================
# ========== PERIOD EVENTS (أحداث الفترات والاقفالات المالية) =====================
# ==============================================================================

@dataclass(frozen=True)
@register_event
class PeriodClosedEvent(BaseDomainEvent):
    """يُرفع عند إغلاق الفترة المالية رسمياً وبث قفل الحسابات لجميع الفروع والموديولات."""
    period_name: PeriodReference
    closed_by: str
    net_income: Money
    entries_count: int
    start_date: datetime
    end_date: datetime
    closed_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.period.closed"


@dataclass(frozen=True)
@register_event
class PeriodOpenedEvent(BaseDomainEvent):
    """يُرفع عند فتح دورة مستندية وفترة مالية جديدة لتمكين الترحيل المحاسبي."""
    period_name: PeriodReference
    opened_by: str
    start_date: datetime
    end_date: datetime
    previous_period: Optional[PeriodReference] = None
    opened_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.period.opened"


@dataclass(frozen=True)
@register_event
class ClosingEntryCreatedEvent(BaseDomainEvent):
    """يُرفع عند توليد قيود الإقفال الآلية لحسابات الإيرادات والمصروفات في ملخص الدخل."""
    period_name: PeriodReference
    closing_entry_id: JournalEntryId
    entry_type: str
    amount: Money
    created_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.period.closing_entry_created"


# ==============================================================================
# ========== ACCOUNT EVENTS (أحداث شجرة الحسابات) ===============================
# ==============================================================================

@dataclass(frozen=True)
@register_event
class AccountCreatedEvent(BaseDomainEvent):
    """يُرفع عند إدراج حساب مالي جديد في الدليل المحاسبي للنظام."""
    account_code: AccountCode
    account_name: str
    account_type: str
    created_by: str
    parent_code: Optional[AccountCode] = None
    created_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.account.created"


@dataclass(frozen=True)
@register_event
class AccountDeactivatedEvent(BaseDomainEvent):
    """يُرفع عند إيقاف تنشيط الحساب لمنع استقبال أي قيود يومية جديدة عليه."""
    account_code: AccountCode
    deactivated_by: str
    reason: Optional[str] = None
    deactivated_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.account.deactivated"


@dataclass(frozen=True)
@register_event
class AccountReactivatedEvent(BaseDomainEvent):
    """يُرفع عند إعادة تنشيط الحساب المجمد بقرار إداري لتفعيل العمليات عليه مجدداً."""
    account_code: AccountCode
    reactivated_by: str
    reason: Optional[str] = None
    reactivated_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.account.reactivated"


# ==============================================================================
# ========== TRIAL BALANCE EVENTS (أحداث ميزان المراجعة) ========================
# ==============================================================================

@dataclass(frozen=True)
@register_event
class TrialBalanceGeneratedEvent(BaseDomainEvent):
    """يُرفع فور توليد تقرير ميزان المراجعة لتوثيق سلامة الأرصدة المستخرجة."""
    as_of: datetime
    total_debits: Money
    total_credits: Money
    currency: str
    is_balanced: bool
    difference: Decimal
    account_count: int
    generated_by: str
    generated_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.report.trial_balance_generated"


@dataclass(frozen=True)
@register_event
class TrialBalanceImbalanceEvent(BaseDomainEvent):
    """حدث أمني حسابي حرج جداً: يُرفع فوراً إذا تبين وجود خلل في توازن ميزان المراجعة."""
    as_of: datetime
    difference: Decimal
    total_debits: Money
    total_credits: Money
    currency: str
    detected_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.report.trial_balance_imbalanced"


# ==============================================================================
# ========== VALIDATION & AUDIT EVENTS ==========================================
# ==============================================================================

@dataclass(frozen=True)
@register_event
class ValidationFailedEvent(BaseDomainEvent):
    """يُرفع عند فشل القيد في اجتياز اختبارات السلامة اللوجستية والمحاسبية."""
    entry_id: JournalEntryId
    errors: List[str]
    attempted_by: str
    attempted_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.validation.failed"


@dataclass(frozen=True)
@register_event
class UnbalancedEntryAttemptEvent(BaseDomainEvent):
    """يُرفع عند محاولة مستخدم ترحيل قيد غير متوازن رقمياً."""
    entry_id: Optional[JournalEntryId]
    debit_total: Decimal
    credit_total: Decimal
    currency: str
    attempted_by: str
    attempted_at: datetime = field(default_factory=_aware_utc_now)
    lines_preview: List[Dict[str, Any]] = field(default_factory=list)
    
    def get_event_name(self) -> str:
        return "accounting.validation.unbalanced_attempt"


@dataclass(frozen=True)
@register_event
class AuditTrailEvent(BaseDomainEvent):
    """سجل التعقب التدقيقي العام والشامل لكافة العمليات السيادية في الدورة المحاسبية."""
    operation: str
    entity_type: str
    entity_id: str
    performed_by: str
    old_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    changes: Dict[str, Any] = field(default_factory=dict)
    performed_at: datetime = field(default_factory=_aware_utc_now)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def get_event_name(self) -> str:
        return "accounting.audit.trail"


# ==============================================================================
# ========== INTEGRATION EVENTS ================================================
# ==============================================================================

@dataclass(frozen=True)
@register_event
class EntryNeedsInventoryUpdateEvent(BaseDomainEvent):
    """يُرفع لربط المحاسبة بموديول المخازن."""
    journal_entry_id: JournalEntryId
    product_id: str
    quantity: int
    cost: Money
    movement_type: str
    account_code: AccountCode
    date: datetime
    
    def get_event_name(self) -> str:
        return "accounting.inventory.update_needed"


@dataclass(frozen=True)
@register_event
class EntryNeedsTaxCalculationEvent(BaseDomainEvent):
    """يُرفع لإشعار نظام الضرائب بضرورة احتساب قيم القيمة المضافة."""
    journal_entry_id: JournalEntryId
    taxable_amount: Money
    tax_rate: Decimal
    tax_jurisdiction: str
    date: datetime
    
    def get_event_name(self) -> str:
        return "accounting.tax.calculation_needed"


@dataclass(frozen=True)
@register_event
class ReportGenerationRequestedEvent(BaseDomainEvent):
    """يُرفع عند جدولة أو طلب إصدار تقرير مالي ثقيل."""
    report_type: str
    as_of: datetime
    requested_by: str
    format: str = "JSON"
    parameters: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "accounting.report.generation_requested"


# ==============================================================================
# ========== SERIALIZATION HELPERS =============================================
# ==============================================================================

def event_to_dict(event: BaseDomainEvent) -> Dict[str, Any]:
    """تحويل حدث الـ Domain إلى Dictionary."""
    result = {
        "event_type": event.get_event_name(),
        "occurred_at": event.occurred_at.isoformat() if hasattr(event, 'occurred_at') and event.occurred_at else _aware_utc_now().isoformat(),
    }
    
    for key, value in event.__dict__.items():
        if not key.startswith('_'):
            if hasattr(value, 'value'):
                result[key] = value.value
            elif isinstance(value, (datetime,)):
                result[key] = value.isoformat()
            elif isinstance(value, Decimal):
                result[key] = str(value)
            elif hasattr(value, '__dict__') and not isinstance(value, EntityId):
                result[key] = str(value)
            else:
                result[key] = value
                
    return result


def event_from_dict(data: Dict[str, Any]) -> BaseDomainEvent:
    """إعادة بناء كائن حدث من Dictionary."""
    raw_data = data.copy()
    event_type = raw_data.pop('event_type', None)
    
    if not event_type:
        raise ValueError("Deserialization Error: Missing 'event_type' field")
        
    event_class = _EVENT_REGISTRY.get(event_type)
    if not event_class:
        raise ValueError(f"Event type '{event_type}' not registered")
        
    raw_data.pop('occurred_at', None)
    
    # تحويل المعرفات
    if 'entry_id' in raw_data and isinstance(raw_data['entry_id'], str):
        raw_data['entry_id'] = JournalEntryId.from_string(raw_data['entry_id'])
    if 'journal_entry_id' in raw_data and isinstance(raw_data['journal_entry_id'], str):
        raw_data['journal_entry_id'] = JournalEntryId.from_string(raw_data['journal_entry_id'])
    if 'ledger_entry_id' in raw_data and isinstance(raw_data['ledger_entry_id'], str):
        raw_data['ledger_entry_id'] = EntryId.from_string(raw_data['ledger_entry_id'])
    if 'account_code' in raw_data and isinstance(raw_data['account_code'], str):
        raw_data['account_code'] = AccountCode(raw_data['account_code'])
    if 'period_name' in raw_data and isinstance(raw_data['period_name'], str):
        raw_data['period_name'] = PeriodReference.from_string(raw_data['period_name'])
        
    # تحويل الحقول العشرية
    if 'total_debit' in raw_data and raw_data['total_debit'] is not None:
        raw_data['total_debit'] = Decimal(str(raw_data['total_debit']))
    if 'total_credit' in raw_data and raw_data['total_credit'] is not None:
        raw_data['total_credit'] = Decimal(str(raw_data['total_credit']))
    if 'difference' in raw_data and raw_data['difference'] is not None:
        raw_data['difference'] = Decimal(str(raw_data['difference']))
        
    return event_class(**raw_data)


# ========== EXPORTS ==========

__all__ = [
    "EntryCreatedEvent",
    "EntryValidatedEvent",
    "EntryPostedEvent",
    "EntryReversedEvent",
    "EntryCanceledEvent",
    "EntryModificationAttemptEvent",
    "LedgerEntryAddedEvent",
    "BalanceCalculatedEvent",
    "PeriodClosedEvent",
    "PeriodOpenedEvent",
    "ClosingEntryCreatedEvent",
    "AccountCreatedEvent",
    "AccountDeactivatedEvent",
    "AccountReactivatedEvent",
    "TrialBalanceGeneratedEvent",
    "TrialBalanceImbalanceEvent",
    "ValidationFailedEvent",
    "UnbalancedEntryAttemptEvent",
    "AuditTrailEvent",
    "EntryNeedsInventoryUpdateEvent",
    "EntryNeedsTaxCalculationEvent",
    "ReportGenerationRequestedEvent",
    "event_to_dict",
    "event_from_dict"
]