# core/application/accounting/__init__.py
"""
Accounting Application Layer - Commands, Queries, Handlers
"""

from .commands import (
    CreateJournalEntryCommand,
    PostJournalEntryCommand,
    ReverseJournalEntryCommand,
    ClosePeriodCommand,
    GetJournalEntryQuery,
    GetTrialBalanceQuery,
    GetAccountBalanceQuery,
    ListJournalEntriesQuery,
    GetPeriodStatusQuery,
)

from .dtos import (
    JournalEntryResponseDTO,
    JournalLineResponseDTO,
    AccountBalanceResponseDTO,
    TrialBalanceResponseDTO,
    ErrorResponseDTO,
)

# ✅ استيراد المعالجات كسولاً (Lazy) عبر __getattr__ لتجنب الاستيراد الدائري
# (accounting.handlers -> handlers.base_handler -> handlers/__init__ -> accounting.handlers)
_HANDLER_NAMES = {
    "CreateJournalEntryHandler",
    "PostJournalEntryHandler",
    "ReverseJournalEntryHandler",
    "ClosePeriodHandler",
    "OpenPeriodHandler",
    "GetJournalEntryQueryHandler",
    "GetTrialBalanceQueryHandler",
    "GetAccountBalanceQueryHandler",
    "ListJournalEntriesQueryHandler",
    "GetPeriodStatusQueryHandler",
    "create_handlers",
}


def __getattr__(name):
    if name in _HANDLER_NAMES:
        from . import handlers
        return getattr(handlers, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Commands
    "CreateJournalEntryCommand",
    "PostJournalEntryCommand",
    "ReverseJournalEntryCommand",
    "ClosePeriodCommand",
    # Queries
    "GetJournalEntryQuery",
    "GetTrialBalanceQuery",
    "GetAccountBalanceQuery",
    "ListJournalEntriesQuery",
    "GetPeriodStatusQuery",
    # DTOs
    "JournalEntryResponseDTO",
    "JournalLineResponseDTO",
    "AccountBalanceResponseDTO",
    "TrialBalanceResponseDTO",
    "ErrorResponseDTO",
    # Handlers
    "CreateJournalEntryHandler",
    "PostJournalEntryHandler",
    "ReverseJournalEntryHandler",
    "ClosePeriodHandler",
    "GetJournalEntryQueryHandler",
    "GetTrialBalanceQueryHandler",
    "GetAccountBalanceQueryHandler",
    "ListJournalEntriesQueryHandler",
    "GetPeriodStatusQueryHandler",
    "create_handlers",
]