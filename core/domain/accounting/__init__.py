# core/domain/accounting/__init__.py
"""
Accounting Bounded Context - Double Entry Accounting System
"""

# استيراد العناصر المنقولة إلى الـ Shared Kernel
from core.domain.shared.value_objects import AccountCode, Money

# استيراد العناصر المحلية من ملفات الـ accounting
from .entities import JournalEntry, JournalLine
from .value_objects import (
    JournalEntryId, 
    EntryId,
    TransactionType,
    PostingStatus,
    PeriodReference
)
from .exceptions import (
    AccountingError,
    UnbalancedEntryError,
    AlreadyPostedError,
    NotPostedError,
    PostedEntryModificationError,
    CannotReverseUnpostedError,
    AlreadyReversedError,
    ClosedPeriodError,
    InvalidAccountError,
    EntryNotFoundError,
)
from .services import (
    PostingEngine,
    LedgerEngine,
    ReversalService,
    ClosingService,
    ClosingResult,
)
from .interfaces import (
    IJournalEntryRepository,
    ILedgerRepository,
    IAccountRepository,
    IFiscalPeriodRepository,
    IAuditRepository,
    IUnitOfWork,
    IEventBus,
)

__all__ = [
    # Entities
    "JournalEntry",
    "JournalLine",
    # Shared Value Objects
    "AccountCode",
    "Money",
    # Local Value Objects
    "JournalEntryId",
    "EntryId",
    "TransactionType",
    "PostingStatus",
    "PeriodReference",
    # Exceptions
    "AccountingError",
    "UnbalancedEntryError",
    "AlreadyPostedError",
    "NotPostedError",
    "PostedEntryModificationError",
    "CannotReverseUnpostedError",
    "AlreadyReversedError",
    "ClosedPeriodError",
    "InvalidAccountError",
    "EntryNotFoundError",
    # Services
    "PostingEngine",
    "LedgerEngine",
    "ReversalService",
    "ClosingService",
    "ClosingResult",
    # Interfaces
    "IJournalEntryRepository",
    "ILedgerRepository",
    "IAccountRepository",
    "IFiscalPeriodRepository",
    "IAuditRepository",
    "IUnitOfWork",
    "IEventBus",
]