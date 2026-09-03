# core/application/accounting/handlers.py

"""
USE CASE HANDLERS - ENTERPRISE GRADE
الإصدار المُصحَّح - v3.0.0
"""

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
import logging
from functools import wraps

from core.domain.shared.value_objects import AccountCode, Money
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.value_objects import JournalEntryId
from core.domain.accounting.services import (
    PostingEngine, ReversalService, LedgerEngine, ClosingService
)
from core.domain.accounting.exceptions import (
    UnbalancedEntryError, EntryNotFoundError, AlreadyPostedError,
    ClosedPeriodError, ConcurrentModificationError, InvalidAccountError
)
from core.domain.accounting.interfaces import (
    IUnitOfWork, Account as DomainAccount
)

from .commands import (
    CreateJournalEntryCommand, PostJournalEntryCommand, ReverseJournalEntryCommand,
    ClosePeriodCommand, OpenPeriodCommand, GetJournalEntryQuery, GetTrialBalanceQuery,
    GetAccountBalanceQuery, ListJournalEntriesQuery, GetPeriodStatusQuery,
    GetAuditLogQuery, ListAccountsQuery, GetAccountByCodeQuery, CreateAccountCommand,
    UpdateAccountCommand
)
from .dtos import (
    JournalLineDTO, CreateJournalEntryDTO, JournalLineResponseDTO,
    JournalEntryResponseDTO, AccountBalanceResponseDTO, TrialBalanceResponseDTO,
    ErrorResponseDTO, validate_create_journal_entry_dto, AccountDTO
)

# ✅ استيراد نظام الصلاحيات الجديد
from core.application.security.authorization import (
    require_permission, Permission, UserContext, PermissionDeniedError,
    PermissionManager
)
from core.application.handlers.base_handler import BaseHandler, BaseQueryHandler

logger = logging.getLogger(__name__)


# ============================================================
# ✅ إضافة الديكوراتورات المفقودة
# ============================================================

def handle_handler_exceptions(func):
    """
    Decorator لمعالجة الاستثناءات في المعالجات
    
    يقوم بالتقاط الاستثناءات وتحويلها إلى ErrorResponseDTO
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except EntryNotFoundError as e:
            logger.error(f"Entry not found: {e}")
            raise
        except UnbalancedEntryError as e:
            logger.error(f"Unbalanced entry: {e}")
            raise
        except AlreadyPostedError as e:
            logger.error(f"Already posted: {e}")
            raise
        except ClosedPeriodError as e:
            logger.error(f"Closed period: {e}")
            raise
        except ConcurrentModificationError as e:
            logger.error(f"Concurrent modification: {e}")
            raise
        except InvalidAccountError as e:
            logger.error(f"Invalid account: {e}")
            raise
        except PermissionDeniedError as e:
            logger.error(f"Permission denied: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper


def handle_query_exceptions(func):
    """
    Decorator لمعالجة الاستثناءات في استعلامات القراءة
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except EntryNotFoundError as e:
            logger.warning(f"Entry not found in query: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in query {func.__name__}: {e}", exc_info=True)
            raise
    return wrapper


# ============================================================
# JournalEntry Handlers
# ============================================================

class CreateJournalEntryHandler(BaseHandler[CreateJournalEntryCommand, JournalEntryResponseDTO]):
    """Handler for creating a new journal entry."""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @handle_handler_exceptions
    # @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateJournalEntryCommand, user_context: UserContext = None) -> JournalEntryResponseDTO:
        """Create a new journal entry."""
        logger.info(f"Creating journal entry by {command.created_by}")
        
        # التحقق من صحة البيانات
        errors = validate_create_journal_entry_dto(command)
        if errors:
            raise ValueError(f"Validation failed: {', '.join(errors)}")
        
        with self._uow:
            # تحويل الأسطر إلى كيانات Domain
            lines = []
            for line_data in command.lines:
                account_code = AccountCode(line_data['account_code'])
                line_currency = line_data.get('currency', 'USD') or 'USD'
                debit = Money(Decimal(str(line_data.get('debit', 0))), line_currency)
                credit = Money(Decimal(str(line_data.get('credit', 0))), line_currency)
                
                # التحقق من صحة الحساب
                account = self._uow.accounts.get_by_code(account_code)
                if not account:
                    raise InvalidAccountError(str(account_code), "Account not found")
                
                lines.append(JournalLine(
                    account_code=account_code,
                    debit=debit,
                    credit=credit
                ))
            
            # إنشاء القيد
            entry = JournalEntry(
                date=datetime.combine(command.date, datetime.min.time(), tzinfo=timezone.utc),
                description=command.description,
                lines=lines
            )
            
            # حفظ القيد
            self._uow.journal_entries.save(entry)
            if hasattr(self._uow, 'collect_events'):
                self._uow.collect_events(entry.pull_events())
            self._commit()
            
            # تحويل إلى DTO
            return journal_entry_to_response_dto(entry)


class PostJournalEntryHandler(BaseHandler[PostJournalEntryCommand, JournalEntryResponseDTO]):
    """Handler for posting a journal entry."""
    
    def __init__(self, uow: IUnitOfWork, posting_engine: PostingEngine):
        super().__init__(uow)
        self._posting_engine = posting_engine
    
    @handle_handler_exceptions
    # @require_permission(Permission.POST_ENTRY)
    def handle(self, command: PostJournalEntryCommand, user_context: UserContext = None) -> JournalEntryResponseDTO:
        """Post a journal entry."""
        logger.info(f"Posting journal entry {command.entry_id} by {command.posted_by}")
        
        with self._uow:
            # جلب القيد
            entry_id = JournalEntryId.from_string(command.entry_id)
            entry = self._uow.journal_entries.get_by_id(entry_id)
            
            if not entry:
                raise EntryNotFoundError(command.entry_id)
            
            # ربط محرك الترحيل بجلسة المعاملة الحالية
            # (السبب: posting_engine مُسجل كـ Singleton قد يحمل جلسات قديمة من نطاقات سابقة)
            engine = self._posting_engine
            engine._journal_repo = self._uow.journal_entries
            engine._ledger_repo = self._uow.ledger
            engine._period_repo = self._uow.periods
            engine._account_repo = self._uow.accounts
            engine._uow = self._uow
            
            # ترحيل القيد
            result = engine.post(entry, command.posted_by, force=command.force)
            
            if not result.success:
                raise ValueError(f"Posting failed: {result.message}")
            
            if hasattr(self._uow, 'collect_events'):
                self._uow.collect_events(entry.pull_events())
            
            self._commit()
            
            return journal_entry_to_response_dto(entry)


class ReverseJournalEntryHandler(BaseHandler[ReverseJournalEntryCommand, JournalEntryResponseDTO]):
    """Handler for reversing a journal entry."""
    
    def __init__(self, uow: IUnitOfWork, reversal_service: ReversalService):
        super().__init__(uow)
        self._reversal_service = reversal_service
    
    @handle_handler_exceptions
    # @require_permission(Permission.REVERSE_ENTRY)
    def handle(self, command: ReverseJournalEntryCommand, user_context: UserContext = None) -> JournalEntryResponseDTO:
        """Reverse a journal entry."""
        logger.info(f"Reversing journal entry {command.entry_id} by {command.reversed_by}")
        
        with self._uow:
            # ربط خدمة الإلغاء بجلسة المعاملة الحالية
            # (السبب: reversal_service مُسجل كـ Singleton قد يحمل جلسات قديمة)
            service = self._reversal_service
            service._journal_repo = self._uow.journal_entries
            service._posting_engine._journal_repo = self._uow.journal_entries
            service._posting_engine._ledger_repo = self._uow.ledger
            service._posting_engine._period_repo = self._uow.periods
            service._posting_engine._account_repo = self._uow.accounts
            service._posting_engine._uow = self._uow
            
            # إنشاء القيد العكسي
            reversal = self._reversal_service.reverse_entry(
                original_entry_id=JournalEntryId.from_string(command.entry_id),
                reason=command.reason,
                posted_by=command.reversed_by,
                auto_post=True
            )
            
            if hasattr(self._uow, 'collect_events'):
                self._uow.collect_events(reversal.pull_events())
            
            self._commit()
            
            return journal_entry_to_response_dto(reversal)


class ClosePeriodHandler(BaseHandler[ClosePeriodCommand, Dict[str, Any]]):
    """Handler for closing a fiscal period."""
    
    def __init__(self, uow: IUnitOfWork, closing_service: ClosingService):
        super().__init__(uow)
        self._closing_service = closing_service
    
    @handle_handler_exceptions
    # @require_permission(Permission.CLOSE_PERIOD)
    def handle(self, command: ClosePeriodCommand, user_context: UserContext = None) -> Dict[str, Any]:
        """Close a fiscal period."""
        logger.info(f"Closing period {command.period_name} by {command.closed_by}")
        
        with self._uow:
            result = self._closing_service.close_period(
                period_name=command.period_name,
                closed_by=command.closed_by,
                force=command.force
            )
            
            if result.success:
                self._commit()
            
            return result.to_dict() if hasattr(result, 'to_dict') else {
                'success': result.success,
                'period_name': command.period_name,
                'closed_by': command.closed_by,
                'message': result.message if hasattr(result, 'message') else "Period closed",
                'errors': result.errors if hasattr(result, 'errors') else []
            }


class OpenPeriodHandler(BaseHandler[OpenPeriodCommand, Dict[str, Any]]):
    """Handler for opening a fiscal period."""
    
    def __init__(self, uow: IUnitOfWork, closing_service: ClosingService):
        super().__init__(uow)
        self._closing_service = closing_service
    
    @handle_handler_exceptions
    # @require_permission(Permission.OPEN_PERIOD)
    def handle(self, command: OpenPeriodCommand, user_context: UserContext = None) -> Dict[str, Any]:
        """Open a fiscal period."""
        logger.info(f"Opening period {command.period_name} by {command.opened_by}")
        
        with self._uow:
            result = self._closing_service.reopen_period(
                period_name=command.period_name,
                reopened_by=command.opened_by,
                reason="Manual reopen"
            )
            
            if result.get('success', False):
                self._commit()
            
            return result


# ============================================================
# Account Handlers
# ============================================================

class CreateAccountCommandHandler(BaseHandler[CreateAccountCommand, AccountDTO]):
    """Handler for creating a new account."""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @handle_handler_exceptions
    def handle(self, command: CreateAccountCommand, user_context: UserContext = None) -> AccountDTO:
        """Create a new account."""
        from core.shared.exceptions import ValidationError

        with self._uow:
            code = AccountCode(command.code)
            if self._uow.accounts.get_by_code(code):
                raise ValidationError(
                    f"Account code already exists: {command.code}",
                    field="code",
                    value=command.code
                )

            now = datetime.now(timezone.utc)
            account = DomainAccount(
                code=code,
                name=command.name,
                account_type=command.account_type,
                is_active=command.is_active,
                parent_code=AccountCode(command.parent_code) if command.parent_code else None,
                description=command.description,
                currency=command.currency,
                created_at=now,
                updated_at=now,
            )

            self._uow.accounts.save(account)
            self._commit()

            return AccountDTO(
                code=account.code.code,
                name=account.name,
                account_type=account.account_type,
                is_active=account.is_active,
                currency=account.currency,
                parent_code=account.parent_code.code if account.parent_code else None,
                description=account.description,
                created_at=account.created_at,
                updated_at=account.updated_at,
                version=account.version,
            )


class UpdateAccountCommandHandler(BaseHandler[UpdateAccountCommand, AccountDTO]):
    """Handler for updating an existing account."""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @handle_handler_exceptions
    def handle(self, command: UpdateAccountCommand, user_context: UserContext = None) -> AccountDTO:
        """Update an existing account."""
        from core.domain.accounting.exceptions import InvalidAccountError
        from core.shared.exceptions import ValidationError

        with self._uow:
            code = AccountCode(command.code)
            account = self._uow.accounts.get_by_code(code)
            if not account:
                raise InvalidAccountError(command.code, "Account not found")

            if command.parent_code:
                if not self._uow.accounts.get_by_code(AccountCode(command.parent_code)):
                    raise ValidationError(
                        f"Parent account {command.parent_code} does not exist",
                        field="parent_code",
                        value=command.parent_code
                    )

            updated = DomainAccount(
                code=account.code,
                name=command.name,
                account_type=command.account_type,
                is_active=command.is_active,
                parent_code=AccountCode(command.parent_code) if command.parent_code else account.parent_code,
                description=command.description if command.description is not None else account.description,
                currency=command.currency,
                created_at=account.created_at,
                updated_at=datetime.now(timezone.utc),
                version=command.version,
            )

            self._uow.accounts.save(updated)
            self._commit()

            return AccountDTO(
                code=updated.code.code,
                name=updated.name,
                account_type=updated.account_type,
                is_active=updated.is_active,
                currency=updated.currency,
                parent_code=updated.parent_code.code if updated.parent_code else None,
                description=updated.description,
                created_at=updated.created_at,
                updated_at=updated.updated_at,
                version=updated.version,
            )


# ============================================================
# JournalEntry Query Handlers
# ============================================================

class GetJournalEntryQueryHandler(BaseQueryHandler[GetJournalEntryQuery, Optional[JournalEntryResponseDTO]]):
    """Handler for getting a journal entry by ID."""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @handle_query_exceptions
    def handle(self, query: GetJournalEntryQuery) -> Optional[JournalEntryResponseDTO]:
        """Get a journal entry by ID."""
        logger.debug(f"Fetching journal entry {query.entry_id}")
        
        with self._uow:
            entry_id = JournalEntryId.from_string(query.entry_id)
            entry = self._uow.journal_entries.get_by_id(entry_id)
            
            if not entry:
                return None
            
            return journal_entry_to_response_dto(entry)


class GetTrialBalanceQueryHandler(BaseQueryHandler[GetTrialBalanceQuery, TrialBalanceResponseDTO]):
    """Handler for getting trial balance."""
    
    def __init__(self, uow: IUnitOfWork, ledger_engine: LedgerEngine):
        super().__init__(uow)
        self._ledger_engine = ledger_engine
    
    @handle_query_exceptions
    def handle(self, query: GetTrialBalanceQuery) -> TrialBalanceResponseDTO:
        """Get trial balance."""
        logger.debug(f"Fetching trial balance as of {query.as_of_date}")
        
        # جلب ميزان المراجعة من LedgerEngine
        balances = self._ledger_engine.get_trial_balance(query.as_of_date)
        
        accounts = []
        total_debits = Decimal('0')
        total_credits = Decimal('0')
        
        for account_code, balance in balances.items():
            if balance.amount > 0:
                total_debits += balance.amount
            else:
                total_credits += abs(balance.amount)
            
            accounts.append(AccountBalanceResponseDTO(
                account_code=str(account_code),
                account_name="",  # سيتم تعبئته من قاعدة البيانات
                balance=balance.amount,
                currency=balance.currency,
                as_of_date=datetime.combine(query.as_of_date, datetime.min.time(), tzinfo=timezone.utc),
                total_debit=balance.amount if balance.amount > 0 else Decimal('0'),
                total_credit=abs(balance.amount) if balance.amount < 0 else Decimal('0')
            ))
        
        return TrialBalanceResponseDTO(
            as_of_date=datetime.combine(query.as_of_date, datetime.min.time(), tzinfo=timezone.utc),
            currency=query.currency,
            accounts=accounts,
            total_debits=total_debits,
            total_credits=total_credits,
            is_balanced=abs(total_debits - total_credits) < Decimal('0.01'),
            difference=abs(total_debits - total_credits),
            account_count=len(accounts)
        )


class GetAccountBalanceQueryHandler(BaseQueryHandler[GetAccountBalanceQuery, AccountBalanceResponseDTO]):
    """Handler for getting account balance."""
    
    def __init__(self, uow: IUnitOfWork, ledger_engine: LedgerEngine):
        super().__init__(uow)
        self._ledger_engine = ledger_engine
    
    @handle_query_exceptions
    def handle(self, query: GetAccountBalanceQuery) -> AccountBalanceResponseDTO:
        """Get account balance."""
        logger.debug(f"Fetching balance for account {query.account_code}")
        
        account_code = AccountCode(query.account_code)
        balance = self._ledger_engine.get_balance(account_code, query.as_of_date)
        
        # جلب اسم الحساب
        account = self._uow.accounts.get_by_code(account_code)
        account_name = account.name if account else query.account_code
        
        return AccountBalanceResponseDTO(
            account_code=query.account_code,
            account_name=account_name,
            balance=balance.amount,
            currency=balance.currency,
            as_of_date=datetime.combine(query.as_of_date, datetime.min.time(), tzinfo=timezone.utc),
            total_debit=balance.amount if balance.amount > 0 else Decimal('0'),
            total_credit=abs(balance.amount) if balance.amount < 0 else Decimal('0')
        )


class ListJournalEntriesQueryHandler(BaseQueryHandler[ListJournalEntriesQuery, List[JournalEntryResponseDTO]]):
    """Handler for listing journal entries."""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @handle_query_exceptions
    def handle(self, query: ListJournalEntriesQuery) -> List[JournalEntryResponseDTO]:
        """List journal entries with filters."""
        logger.debug(f"Listing journal entries (limit={query.limit})")
        
        with self._uow:
            entries = self._uow.journal_entries.list_all(
                limit=query.limit,
                offset=query.offset
            )
            
            # تطبيق الفلاتر
            if query.is_posted is not None:
                entries = [e for e in entries if e.is_posted == query.is_posted]
            if query.from_date:
                entries = [e for e in entries if e.date.date() >= query.from_date]
            if query.to_date:
                entries = [e for e in entries if e.date.date() <= query.to_date]
            
            return [journal_entry_to_response_dto(e) for e in entries]


class GetPeriodStatusQueryHandler(BaseQueryHandler[GetPeriodStatusQuery, Dict[str, Any]]):
    """Handler for getting period status."""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @handle_query_exceptions
    def handle(self, query: GetPeriodStatusQuery) -> Dict[str, Any]:
        """Get period status."""
        logger.debug(f"Fetching status for period {query.period_name}")
        
        with self._uow:
            from core.domain.accounting.value_objects import PeriodReference
            try:
                ref = PeriodReference.from_string(query.period_name)
            except ValueError:
                return {
                    'period_name': query.period_name,
                    'exists': False,
                    'is_closed': True,
                    'message': f"Invalid period format: {query.period_name}"
                }
            period = self._uow.periods.get_period_by_name(ref)
            
            if not period:
                return {
                    'period_name': query.period_name,
                    'exists': False,
                    'is_closed': True,
                    'message': f"Period {query.period_name} not found"
                }
            
            return {
                'period_name': query.period_name,
                'exists': True,
                'is_closed': period.is_closed,
                'start_date': period.start_date.isoformat(),
                'end_date': period.end_date.isoformat(),
                'closed_by': period.closed_by,
                'closed_at': period.closed_at.isoformat() if period.closed_at else None,
            }


class GetAuditLogQueryHandler(BaseQueryHandler[GetAuditLogQuery, List[Dict[str, Any]]]):
    """Handler for getting audit log."""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @handle_query_exceptions
    def handle(self, query: GetAuditLogQuery) -> List[Dict[str, Any]]:
        """Get audit log."""
        logger.debug(f"Fetching audit log (limit={query.limit})")
        
        with self._uow:
            records = self._uow.audit.get_audit_trail(
                entity_type=query.entity_type,
                entity_id=query.entity_id,
                from_date=query.from_date,
                to_date=query.to_date,
                limit=query.limit
            )
            
            return [
                {
                    'id': record.id,
                    'operation': record.operation,
                    'entity_type': record.entity_type,
                    'entity_id': record.entity_id,
                    'performed_by': record.performed_by,
                    'performed_at': record.performed_at.isoformat(),
                    'changes': record.changes,
                    'old_state': record.old_state,
                    'new_state': record.new_state,
                }
                for record in records
            ]


# ============================================================
# Helper Functions
# ============================================================

def journal_entry_to_response_dto(entry: JournalEntry) -> JournalEntryResponseDTO:
    """Convert domain JournalEntry to JournalEntryResponseDTO."""
    if not entry:
        return None
    
    lines = []
    for line in entry.lines:
        account = None
        if hasattr(entry, '_account_cache') and str(line.account_code) in entry._account_cache:
            account = entry._account_cache[str(line.account_code)]
        
        lines.append(JournalLineResponseDTO(
            line_id=str(line.line_id) if hasattr(line, 'line_id') else "",
            account_code=str(line.account_code),
            account_name=account.name if account else "",
            debit=line.debit.amount,
            credit=line.credit.amount,
            description=getattr(line, 'description', None),
            currency=line.debit.currency if line.debit.amount > 0 else line.credit.currency,
        ))
    
    return JournalEntryResponseDTO(
        id=str(entry.id),
        date=entry.date,
        description=entry.description,
        is_posted=entry.is_posted,
        total_debit=sum(line.debit.amount for line in entry.lines),
        total_credit=sum(line.credit.amount for line in entry.lines),
        lines=lines,
        version=entry.version,
        created_at=entry.created_at if hasattr(entry, 'created_at') else datetime.now(timezone.utc),
        created_by=entry.created_by if hasattr(entry, 'created_by') else "system",
        notes=getattr(entry, 'notes', None),
        posted_at=entry.posted_at if hasattr(entry, 'posted_at') else None,
        posted_by=entry.posted_by if hasattr(entry, 'posted_by') else None,
        reversed_entry_id=str(entry.reversed_entry_id) if hasattr(entry, 'reversed_entry_id') and entry.reversed_entry_id else None,
        reverses_entry_id=str(entry.reverses_entry_id) if hasattr(entry, 'reverses_entry_id') and entry.reverses_entry_id else None,
        currency="USD",  # يمكن استخراجها من أول سطر
    )


# ============================================================
# Factory Function
# ============================================================

def create_handlers(
    uow: IUnitOfWork,
    posting_engine: PostingEngine,
    reversal_service: ReversalService,
    ledger_engine: LedgerEngine,
    closing_service: ClosingService
) -> Dict[str, Any]:
    """
    Create all accounting handlers.
    
    Returns:
        Dict[str, Any]: Dictionary of handlers
    """
    return {
        'create_journal_entry': CreateJournalEntryHandler(uow),
        'post_journal_entry': PostJournalEntryHandler(uow, posting_engine),
        'reverse_journal_entry': ReverseJournalEntryHandler(uow, reversal_service),
        'close_period': ClosePeriodHandler(uow, closing_service),
        'open_period': OpenPeriodHandler(uow, closing_service),
        'get_journal_entry': GetJournalEntryQueryHandler(uow),
        'get_trial_balance': GetTrialBalanceQueryHandler(uow, ledger_engine),
        'get_account_balance': GetAccountBalanceQueryHandler(uow, ledger_engine),
        'list_journal_entries': ListJournalEntriesQueryHandler(uow),
        'get_period_status': GetPeriodStatusQueryHandler(uow),
        'get_audit_log': GetAuditLogQueryHandler(uow),
        'list_accounts': ListAccountsQueryHandler(uow),
        'get_account_by_code': GetAccountByCodeQueryHandler(uow),
        'create_account': CreateAccountCommandHandler(uow),
        'update_account': UpdateAccountCommandHandler(uow),
    }


# ============================================================
# __all__ Export
# ============================================================

__all__ = [
    # Handlers
    'CreateJournalEntryHandler',
    'PostJournalEntryHandler',
    'ReverseJournalEntryHandler',
    'ClosePeriodHandler',
    'OpenPeriodHandler',
    'GetJournalEntryQueryHandler',
    'GetTrialBalanceQueryHandler',
    'GetAccountBalanceQueryHandler',
    'ListJournalEntriesQueryHandler',
    'GetPeriodStatusQueryHandler',
    'GetAuditLogQueryHandler',
    'ListAccountsQueryHandler',
    'GetAccountByCodeQueryHandler',
    'CreateAccountCommandHandler',
    'UpdateAccountCommandHandler',
    # Factory
    'create_handlers',
    # Helper
    'journal_entry_to_response_dto',
]