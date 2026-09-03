"""
POSTGRESQL REPOSITORY IMPLEMENTATIONS - ENTERPRISE GRADE
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import select, and_, func, update, delete, text
from sqlalchemy.orm import Session, selectinload

from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.value_objects import EntryId, JournalEntryId, TransactionType, PeriodReference
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.accounting.exceptions import (
    EntryNotFoundError, ConcurrentModificationError, InvalidAccountError, InvalidPeriodError
)
from core.domain.accounting.interfaces import (
    IJournalEntryRepository, ILedgerRepository, IAccountRepository,
    IFiscalPeriodRepository, IAuditRepository,
    LedgerEntry as DomainLedgerEntry,
    Account as DomainAccount,
    FiscalPeriod as DomainFiscalPeriod,
    AuditRecord as DomainAuditRecord
)

from ..models.account_model import (
    AccountModel, JournalEntryModel, JournalLineModel,
    LedgerEntryModel, FiscalPeriodModel, AuditLogModel
)


# ========== HELPER FUNCTIONS ==========

def _get_id_value(id_obj) -> str:
    """استخراج قيمة المعرف النصية."""
    if id_obj is None:
        return None
    if hasattr(id_obj, 'value'):
        return str(id_obj.value)
    return str(id_obj)


def _domain_to_journal_entry_model(entry: JournalEntry) -> JournalEntryModel:
    """Convert domain JournalEntry to ORM model."""
    return JournalEntryModel(
        id=_get_id_value(entry.id),
        entry_date=entry.date,
        description=entry.description,
        is_posted=entry.is_posted,
        posted_at=entry.posted_at,
        posted_by=entry.posted_by,
        reversed_entry_id=_get_id_value(entry.reversed_entry_id),
        version=entry.version
    )


# ========== JOURNAL ENTRY REPOSITORY ==========

class PostgresJournalEntryRepository(IJournalEntryRepository):
    def __init__(self, session: Session):
        self._session = session
        self._account_cache: Dict[str, UUID] = {}

    def _get_account_id(self, account_code: AccountCode) -> UUID:
        """Get account ID from code with caching."""
        code_value = account_code.code if hasattr(account_code, 'code') else str(account_code)
        if code_value in self._account_cache:
            return self._account_cache[code_value]

        account = self._session.execute(
            select(AccountModel).where(AccountModel.code == code_value)
        ).scalar_one_or_none()

        if not account:
            raise InvalidAccountError(code_value)

        self._account_cache[code_value] = account.id
        return account.id

    def _model_to_domain(self, model: JournalEntryModel) -> JournalEntry:
        """Convert ORM model to domain entity."""
        lines = []
        for line_model in model.lines:
            account = self._session.get(AccountModel, line_model.account_id)
            if not account:
                raise InvalidAccountError(f"Account ID {line_model.account_id} not found")

            line = JournalLine(
                account_code=AccountCode(account.code),
                debit=Money(Decimal(str(line_model.debit_amount)), line_model.currency or (account.currency if account else "USD")),
                credit=Money(Decimal(str(line_model.credit_amount)), line_model.currency or (account.currency if account else "USD"))
            )
            lines.append(line)

        entry = JournalEntry(
            id=JournalEntryId(str(model.id)),
            date=model.entry_date,
            description=model.description,
            lines=lines,
            is_posted=model.is_posted,
            posted_at=model.posted_at,
            posted_by=model.posted_by,
            reversed_entry_id=JournalEntryId(str(model.reversed_entry_id)) if model.reversed_entry_id else None
        )
        entry.version = model.version
        return entry

    # ========== ✅ الدالة الأساسية: save() مع دعم الإدراج والتحديث ==========

    def save(self, entry: JournalEntry) -> None:
        """
        حفظ القيد المحاسبي (إدراج أو تحديث) مع Optimistic Locking.
        """
        entry_id_value = _get_id_value(entry.id)

        existing = self._session.execute(
            select(JournalEntryModel).where(JournalEntryModel.id == entry_id_value)
        ).scalar_one_or_none()

        if existing:
            self._update_existing_entry(existing, entry)
        else:
            self._create_new_entry(entry)

    def _update_existing_entry(self, existing: JournalEntryModel, entry: JournalEntry) -> None:
        """تحديث قيد موجود مع Optimistic Locking."""
        now = datetime.now(timezone.utc)
        new_version = existing.version + 1

        # 1. تحديث الحقول الأساسية مع التحقق من الإصدار
        result = self._session.execute(
            update(JournalEntryModel)
            .where(
                JournalEntryModel.id == existing.id,
                JournalEntryModel.version == entry.version  # ✅ Optimistic Locking
            )
            .values(
                entry_date=entry.date,
                description=entry.description,
                is_posted=entry.is_posted,
                posted_at=entry.posted_at,
                posted_by=entry.posted_by,
                reversed_entry_id=_get_id_value(entry.reversed_entry_id),
                version=new_version
            )
        )

        # 2. التحقق من عدم وجود تعارض
        if result.rowcount == 0:
            raise ConcurrentModificationError(
                "JournalEntry",
                str(entry.id),
                entry.version,
                existing.version
            )

        # 3. تحديث الإصدار في الكائن المحلي
        entry.version = new_version

        # 4. تحديث الأسطر (حذف + إدراج)
        self._update_lines(existing.id, entry)

    def _update_lines(self, entry_id: UUID, entry: JournalEntry) -> None:
        """تحديث أسطر القيد."""
        # حذف الأسطر القديمة من قاعدة البيانات
        self._session.execute(
            delete(JournalLineModel).where(JournalLineModel.journal_entry_id == entry_id)
        )

        # إزالة الأسطر المعلقة (غير المحفوظة) لنفس القيد من الجلسة
        # لمنع التكرار عند إعادة الحفظ داخل نفس المعاملة
        # (الأسطر المعلقة تخزن journal_entry_id كنص بينما entry_id كائن UUID)
        for obj in list(self._session.new):
            if isinstance(obj, JournalLineModel) and str(obj.journal_entry_id) == str(entry_id):
                self._session.expunge(obj)

        # إدراج الأسطر الجديدة
        for idx, line in enumerate(entry.lines):
            account_id = self._get_account_id(line.account_code)
            line_model = JournalLineModel(
                journal_entry_id=entry_id,
                account_id=account_id,
                debit_amount=line.debit.amount,
                credit_amount=line.credit.amount,
                currency=line.currency,
                line_order=idx
            )
            self._session.add(line_model)

    def _create_new_entry(self, entry: JournalEntry) -> None:
        """إنشاء قيد جديد."""
        entry_id_value = _get_id_value(entry.id)

        model = JournalEntryModel(
            id=entry_id_value,
            entry_date=entry.date,
            description=entry.description,
            is_posted=entry.is_posted,
            posted_at=entry.posted_at,
            posted_by=entry.posted_by,
            reversed_entry_id=_get_id_value(entry.reversed_entry_id),
            version=entry.version
        )
        self._session.add(model)
        self._session.flush()

        # إضافة الأسطر
        for idx, line in enumerate(entry.lines):
            account_id = self._get_account_id(line.account_code)
            line_model = JournalLineModel(
                journal_entry_id=entry_id_value,
                account_id=account_id,
                debit_amount=line.debit.amount,
                credit_amount=line.credit.amount,
                currency=line.currency,
                line_order=idx
            )
            self._session.add(line_model)

    # ========== باقي الدوال (بدون تغيير) ==========

    def get_by_id(self, entry_id: JournalEntryId) -> Optional[JournalEntry]:
        entry_id_value = _get_id_value(entry_id)
        model = self._session.execute(
            select(JournalEntryModel)
            .options(selectinload(JournalEntryModel.lines))
            .where(JournalEntryModel.id == entry_id_value)
        ).unique().scalar_one_or_none()
        return self._model_to_domain(model) if model else None

    def get_by_id_or_fail(self, entry_id: JournalEntryId) -> JournalEntry:
        entry = self.get_by_id(entry_id)
        if not entry:
            raise EntryNotFoundError(str(entry_id))
        return entry

    def list_all(self, limit: Optional[int] = None, offset: Optional[int] = None, is_posted: Optional[bool] = None) -> List[JournalEntry]:
        query = select(JournalEntryModel).options(selectinload(JournalEntryModel.lines))
        if is_posted is not None:
            query = query.where(JournalEntryModel.is_posted == is_posted)
        query = query.order_by(JournalEntryModel.entry_date.desc())
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        models = self._session.execute(query).unique().scalars().all()
        return [self._model_to_domain(model) for model in models]

    def get_posted_entries(self, from_date: date, to_date: date, transaction_type: Optional[TransactionType] = None) -> List[JournalEntry]:
        query = select(JournalEntryModel).where(
            and_(
                JournalEntryModel.is_posted == True,
                JournalEntryModel.entry_date >= from_date,
                JournalEntryModel.entry_date <= to_date
            )
        ).options(selectinload(JournalEntryModel.lines))
        models = self._session.execute(query).unique().scalars().all()
        return [self._model_to_domain(model) for model in models]

    def get_draft_entries(self, user_id: Optional[str] = None, limit: Optional[int] = None) -> List[JournalEntry]:
        query = select(JournalEntryModel).where(
            JournalEntryModel.is_posted == False
        ).options(selectinload(JournalEntryModel.lines))
        if user_id:
            query = query.where(JournalEntryModel.created_by == user_id)
        if limit:
            query = query.limit(limit)
        models = self._session.execute(query).unique().scalars().all()
        return [self._model_to_domain(model) for model in models]

    def exists_reversal(self, original_entry_id: JournalEntryId) -> bool:
        original_id_value = _get_id_value(original_entry_id)
        exists = self._session.execute(
            select(JournalEntryModel).where(
                JournalEntryModel.reversed_entry_id == original_id_value
            )
        ).scalar_one_or_none()
        return exists is not None

    def get_reversal_for(self, original_entry_id: JournalEntryId) -> Optional[JournalEntry]:
        original_id_value = _get_id_value(original_entry_id)
        model = self._session.execute(
            select(JournalEntryModel)
            .options(selectinload(JournalEntryModel.lines))
            .where(JournalEntryModel.reversed_entry_id == original_id_value)
        ).unique().scalar_one_or_none()
        return self._model_to_domain(model) if model else None

    def get_by_reference(self, reference_number: str) -> Optional[JournalEntry]:
        model = self._session.execute(
            select(JournalEntryModel)
            .options(selectinload(JournalEntryModel.lines))
            .where(JournalEntryModel.reference == reference_number)
        ).unique().scalar_one_or_none()
        return self._model_to_domain(model) if model else None

    def delete_draft(self, entry_id: JournalEntryId) -> bool:
        entry_id_value = _get_id_value(entry_id)
        model = self._session.execute(
            select(JournalEntryModel).where(JournalEntryModel.id == entry_id_value)
        ).scalar_one_or_none()
        if not model or model.is_posted:
            return False
        self._session.delete(model)
        return True

    def count_by_period(self, period: PeriodReference) -> int:
        return self._session.execute(
            select(func.count()).select_from(JournalEntryModel).where(
                JournalEntryModel.is_posted == True
            )
        ).scalar()

    def get_entries_in_date_range(self, start_date: date, end_date: date, include_unposted: bool = True) -> List[JournalEntry]:
        conditions = [
            JournalEntryModel.entry_date >= start_date,
            JournalEntryModel.entry_date <= end_date,
        ]
        if not include_unposted:
            conditions.append(JournalEntryModel.is_posted == True)

        models = self._session.execute(
            select(JournalEntryModel)
            .options(selectinload(JournalEntryModel.lines))
            .where(and_(*conditions))
            .order_by(JournalEntryModel.entry_date)
        ).unique().scalars().all()
        return [self._model_to_domain(model) for model in models]

    def get_unposted_entries_in_period(self, period) -> List[JournalEntry]:
        if hasattr(period, 'start_date') and hasattr(period, 'end_date'):
            start_date = period.start_date
            end_date = period.end_date
        else:
            start_date = period.start_date
            end_date = period.end_date

        models = self._session.execute(
            select(JournalEntryModel)
            .options(selectinload(JournalEntryModel.lines))
            .where(
                and_(
                    JournalEntryModel.entry_date >= start_date,
                    JournalEntryModel.entry_date <= end_date,
                    JournalEntryModel.is_posted == False
                )
            )
            .order_by(JournalEntryModel.entry_date)
        ).unique().scalars().all()
        return [self._model_to_domain(model) for model in models]

    def count_unposted_in_period(self, period) -> int:
        if hasattr(period, 'start_date') and hasattr(period, 'end_date'):
            start_date = period.start_date
            end_date = period.end_date
        else:
            start_date = period.start_date
            end_date = period.end_date

        result = self._session.execute(
            select(func.count())
            .select_from(JournalEntryModel)
            .where(
                and_(
                    JournalEntryModel.entry_date >= start_date,
                    JournalEntryModel.entry_date <= end_date,
                    JournalEntryModel.is_posted == False
                )
            )
        ).scalar()
        return result or 0



# ========== LEDGER REPOSITORY ==========

class PostgresLedgerRepository(ILedgerRepository):
    def __init__(self, session: Session):
        self._session = session
    
    def _model_to_domain(self, model: LedgerEntryModel, account_code: AccountCode) -> DomainLedgerEntry:
        """Convert ORM model to domain LedgerEntry."""
        return DomainLedgerEntry(
            entry_id=EntryId(str(model.id)),
            journal_entry_id=JournalEntryId(str(model.journal_entry_id)),
            account_code=account_code,
            debit=Money(Decimal(str(model.debit_amount)), model.currency or "USD"),
            credit=Money(Decimal(str(model.credit_amount)), model.currency or "USD"),
            date=model.entry_date,
            posted_at=model.posted_at,
            reference=model.reference
        )
    
    def add_entry(
        self, entry_id: EntryId, account_code: AccountCode, debit: Money, credit: Money,
        date: datetime, journal_entry_id: JournalEntryId, reference: Optional[str] = None
    ) -> None:
        """Add a ledger entry."""
        account = self._session.execute(
            select(AccountModel).where(AccountModel.code == account_code.code)
        ).scalar_one()
        
        line_currency = debit.currency if debit.amount > 0 else credit.currency
        ledger_entry = LedgerEntryModel(
            id=entry_id.value if hasattr(entry_id, 'value') else str(entry_id),
            journal_entry_id=journal_entry_id.value if hasattr(journal_entry_id, 'value') else str(journal_entry_id),
            account_id=account.id,
            debit_amount=debit.amount,
            credit_amount=credit.amount,
            currency=line_currency,
            entry_date=date,
            posted_at=datetime.utcnow(),
            reference=reference
        )
        self._session.add(ledger_entry)
    
    def get_entries_by_account(
        self, account_code: AccountCode, from_date: Optional[date] = None,
        to_date: Optional[date] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[DomainLedgerEntry]:
        """Get ledger entries by account with optional filters."""
        account = self._session.execute(
            select(AccountModel).where(AccountModel.code == account_code.code)
        ).scalar_one()
        
        query = select(LedgerEntryModel).where(
            LedgerEntryModel.account_id == account.id
        ).order_by(LedgerEntryModel.entry_date)
        
        if from_date:
            query = query.where(LedgerEntryModel.entry_date >= from_date)
        if to_date:
            query = query.where(LedgerEntryModel.entry_date <= to_date)
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        models = self._session.execute(query).scalars().all()
        
        return [self._model_to_domain(m, account_code) for m in models]
    
    def get_balance(self, account_code: AccountCode, as_of: date, currency: str = "USD") -> Money:
        """Get account balance as of a specific date."""
        account = self._session.execute(
            select(AccountModel).where(AccountModel.code == account_code.code)
        ).scalar_one()
        
        result = self._session.execute(
            select(
                func.sum(LedgerEntryModel.debit_amount),
                func.sum(LedgerEntryModel.credit_amount)
            ).where(
                and_(
                    LedgerEntryModel.account_id == account.id,
                    func.date(LedgerEntryModel.entry_date) <= as_of,
                    LedgerEntryModel.currency == currency
                )
            )
        ).one()
        
        total_debit = Decimal(str(result[0] or 0))
        total_credit = Decimal(str(result[1] or 0))
        balance = total_debit - total_credit
        
        return Money(balance, currency)
    
    def get_trial_balance(
        self, as_of: date, account_types: Optional[List[str]] = None, currency: str = "USD"
    ) -> Dict[AccountCode, Money]:
        """Get trial balance as of a specific date."""
        query = select(
            AccountModel.code,
            func.sum(LedgerEntryModel.debit_amount).label('total_debit'),
            func.sum(LedgerEntryModel.credit_amount).label('total_credit')
        ).join(
            LedgerEntryModel, AccountModel.id == LedgerEntryModel.account_id
        ).where(
            and_(
                func.date(LedgerEntryModel.entry_date) <= as_of,
                LedgerEntryModel.currency == currency
            )
        ).group_by(AccountModel.code)
        
        if account_types:
            query = query.where(AccountModel.account_type.in_(account_types))
        
        results = self._session.execute(query).all()
        
        balances = {}
        for code, total_debit, total_credit in results:
            debit = Decimal(str(total_debit or 0))
            credit = Decimal(str(total_credit or 0))
            balance = debit - credit
            balances[AccountCode(code)] = Money(balance, currency)
        
        return balances
    
    def get_account_history(self, account_code: AccountCode, from_date: date, to_date: date) -> List[DomainLedgerEntry]:
        """Get account history between dates."""
        return self.get_entries_by_account(account_code, from_date, to_date)
    
    def get_opening_balance(self, account_code: AccountCode, as_of: date, currency: str = "USD") -> Money:
        """Get opening balance as of a specific date."""
        from datetime import timedelta
        day_before = as_of - timedelta(days=1)
        return self.get_balance(account_code, day_before, currency)


# ========== ACCOUNT REPOSITORY ==========

# ========== ACCOUNT REPOSITORY ==========

class PostgresAccountRepository(IAccountRepository):
    def __init__(self, session: Session):
        self._session = session
    
    def _model_to_domain(self, model: AccountModel) -> DomainAccount:
        """Convert ORM model to domain Account."""
        return DomainAccount(
            code=AccountCode(model.code),
            name=model.name,
            account_type=model.account_type,
            is_active=model.is_active,
            parent_code=AccountCode(model.parent_code) if model.parent_code else None,
            description=model.description,
            currency=model.currency,
            created_at=model.created_at,
            updated_at=model.updated_at
        )
    
    def _domain_to_model(self, account: DomainAccount) -> AccountModel:
        """Convert domain Account to ORM model."""
        return AccountModel(
            code=account.code.code,
            name=account.name,
            account_type=account.account_type,
            is_active=account.is_active,
            parent_code=account.parent_code.code if account.parent_code else None,
            description=account.description,
            currency=account.currency
        )
    
    def _get_code_value(self, code) -> str:
        """استخراج قيمة الكود النصية من AccountCode أو string."""
        if hasattr(code, 'code'):
            return code.code
        return str(code)
    
    def get_by_code(self, code) -> Optional[DomainAccount]:
        """Get account by code (accepts AccountCode or string)."""
        code_value = self._get_code_value(code)
        
        model = self._session.execute(
            select(AccountModel).where(AccountModel.code == code_value)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_domain(model)
    
    def get_by_code_or_fail(self, code) -> DomainAccount:
        """Get account by code or raise error."""
        code_value = self._get_code_value(code)
        account = self.get_by_code(code_value)
        if not account:
            raise InvalidAccountError(code_value)
        return account
    
    def get_all_accounts(
        self, account_type: Optional[str] = None, include_inactive: bool = False
    ) -> List[DomainAccount]:
        """Get all accounts with optional filters."""
        query = select(AccountModel)
        
        if account_type:
            query = query.where(AccountModel.account_type == account_type)
        if not include_inactive:
            query = query.where(AccountModel.is_active == True)
        
        models = self._session.execute(query).scalars().all()
        return [self._model_to_domain(m) for m in models]
    
    def get_active_accounts(self) -> List[DomainAccount]:
        """Get only active accounts."""
        return self.get_all_accounts(include_inactive=False)
    
    def exists(self, code) -> bool:
        """Check if account exists (accepts AccountCode or string)."""
        code_value = self._get_code_value(code)
        return self.get_by_code(code_value) is not None
    
    def is_active(self, code) -> bool:
        """Check if account is active (accepts AccountCode or string)."""
        code_value = self._get_code_value(code)
        account = self.get_by_code(code_value)
        return account.is_active if account else False
    
    def save(self, account: DomainAccount) -> None:
        """Save account (create or update)."""
        existing = self._session.execute(
            select(AccountModel).where(AccountModel.code == account.code.code)
        ).scalar_one_or_none()
        
        if account.parent_code:
            parent_exists = self.exists(account.parent_code)
            if not parent_exists:
                raise InvalidAccountError(
                    account.parent_code.code, 
                    f"Parent account {account.parent_code.code} does not exist"
                )
        
        if existing:
            existing.name = account.name
            existing.account_type = account.account_type
            existing.is_active = account.is_active
            existing.parent_code = account.parent_code.code if account.parent_code else None
            existing.description = account.description
            existing.currency = account.currency
            existing.updated_at = datetime.utcnow()
            existing.version += 1
        else:
            model = self._domain_to_model(account)
            model.version = 1
            self._session.add(model)
    
    def deactivate(self, code, deactivated_by: str) -> None:
        """Deactivate an account (accepts AccountCode or string)."""
        code_value = self._get_code_value(code)
        model = self._session.execute(
            select(AccountModel).where(AccountModel.code == code_value)
        ).scalar_one()
        
        model.is_active = False
        model.updated_at = datetime.utcnow()
        model.version += 1
    
    def activate(self, code, activated_by: str) -> None:
        """Activate an account (accepts AccountCode or string)."""
        code_value = self._get_code_value(code)
        model = self._session.execute(
            select(AccountModel).where(AccountModel.code == code_value)
        ).scalar_one()
        
        model.is_active = True
        model.updated_at = datetime.utcnow()
        model.version += 1
    
    def get_children(self, parent_code) -> List[DomainAccount]:
        """Get child accounts of a parent (accepts AccountCode or string)."""
        parent_value = self._get_code_value(parent_code)
        
        models = self._session.execute(
            select(AccountModel).where(AccountModel.parent_code == parent_value)
        ).scalars().all()
        
        return [self._model_to_domain(m) for m in models]
    
    def get_root_accounts(self) -> List[DomainAccount]:
        """Get root level accounts (no parent)."""
        models = self._session.execute(
            select(AccountModel).where(AccountModel.parent_code.is_(None))
        ).scalars().all()
        
        return [self._model_to_domain(m) for m in models]


# ========== FISCAL PERIOD REPOSITORY ==========

class PostgresFiscalPeriodRepository(IFiscalPeriodRepository):
    def __init__(self, session: Session):
        self._session = session
    
    def _model_to_domain(self, model: FiscalPeriodModel) -> DomainFiscalPeriod:
        """Convert ORM model to domain FiscalPeriod."""
        return DomainFiscalPeriod(
            name=PeriodReference(model.year, model.period_number),
            start_date=model.start_date,
            end_date=model.end_date,
            is_closed=model.is_closed,
            closed_by=model.closed_by,
            closed_at=model.closed_at
        )
    
    def get_period_by_date(self, dt: date) -> Optional[DomainFiscalPeriod]:
        """Get fiscal period containing the given date."""
        model = self._session.execute(
            select(FiscalPeriodModel).where(
                and_(
                    FiscalPeriodModel.start_date <= dt,
                    FiscalPeriodModel.end_date >= dt
                )
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_domain(model)
    
    def get_period_by_name(self, name: PeriodReference) -> Optional[DomainFiscalPeriod]:
        """Get fiscal period by year and period number (name column holds localized names)."""
        period_number = name.get_month() or name.get_quarter() or 0
        model = self._session.execute(
            select(FiscalPeriodModel).where(
                FiscalPeriodModel.year == name.get_year(),
                FiscalPeriodModel.period_number == period_number
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_domain(model)
    
    def get_period_by_name_or_fail(self, name: PeriodReference) -> DomainFiscalPeriod:
        """Get fiscal period by name or raise error."""
        period = self.get_period_by_name(name)
        if not period:
            raise InvalidPeriodError(str(name))
        return period
    
    def get_all_periods(
        self, from_year: Optional[int] = None, to_year: Optional[int] = None, include_closed: bool = True
    ) -> List[DomainFiscalPeriod]:
        """Get all fiscal periods with optional filters."""
        query = select(FiscalPeriodModel).order_by(FiscalPeriodModel.year, FiscalPeriodModel.period_number)
        
        if from_year:
            query = query.where(FiscalPeriodModel.year >= from_year)
        if to_year:
            query = query.where(FiscalPeriodModel.year <= to_year)
        if not include_closed:
            query = query.where(FiscalPeriodModel.is_closed == False)
        
        models = self._session.execute(query).scalars().all()
        return [self._model_to_domain(m) for m in models]
    
    def get_current_period(self, as_of: Optional[date] = None) -> Optional[DomainFiscalPeriod]:
        """Get the current open fiscal period."""
        check_date = as_of or date.today()
        
        model = self._session.execute(
            select(FiscalPeriodModel).where(
                and_(
                    FiscalPeriodModel.start_date <= check_date,
                    FiscalPeriodModel.end_date >= check_date,
                    FiscalPeriodModel.is_closed == False
                )
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_domain(model)
    
    def save(self, period: DomainFiscalPeriod) -> None:
        """Save fiscal period (create or update)."""
        pn = period.name.get_month() or period.name.get_quarter() or 0
        result = self._session.execute(
            text("UPDATE fiscal_periods SET start_date=:sd, end_date=:ed, is_closed=:ic, closed_at=:ca, closed_by=:cb WHERE year=:y AND period_number=:pn"),
            {"sd": period.start_date, "ed": period.end_date, "ic": period.is_closed,
             "ca": period.closed_at, "cb": period.closed_by,
             "y": period.name.get_year(), "pn": pn}
        )
        if result.rowcount == 0:
            model = FiscalPeriodModel(
                name=str(period.name),
                year=period.name.get_year(),
                period_number=pn,
                start_date=period.start_date,
                end_date=period.end_date,
                period_type='MONTH' if period.is_month() else 'QUARTER' if period.is_quarter() else 'YEAR',
                is_closed=period.is_closed,
                closed_at=period.closed_at,
                closed_by=period.closed_by
            )
            self._session.add(model)
    
    def close_period(self, period: DomainFiscalPeriod, closed_by: str) -> None:
        """Close a fiscal period."""
        self._session.execute(
            text("UPDATE fiscal_periods SET is_closed=true, closed_at=NOW(), closed_by=:cb WHERE year=:y AND period_number=:pn"),
            {"cb": closed_by, "y": period.name.get_year(), "pn": period.name.get_month() or period.name.get_quarter() or 0}
        )
    
    def open_period(self, period: DomainFiscalPeriod, opened_by: str) -> None:
        """Open a closed fiscal period (admin only)."""
        self._session.execute(
            text("UPDATE fiscal_periods SET is_closed=false, closed_at=NULL, closed_by=NULL, opened_by=:ob, opened_at=NOW() WHERE year=:y AND period_number=:pn"),
            {"ob": opened_by, "y": period.name.get_year(), "pn": period.name.get_month() or period.name.get_quarter() or 0}
        )
    
    def is_period_closed(self, dt: date) -> bool:
        """Check if the period containing the given date is closed."""
        period = self.get_period_by_date(dt)
        return period.is_closed if period else False
    
    def get_next_period(self, current: PeriodReference) -> Optional[PeriodReference]:
        """Get the next fiscal period."""
        year = current.get_year()
        month = current.get_month()
        
        if month and month < 12:
            return PeriodReference(f"{year}-{month + 1:02d}")
        elif month == 12:
            return PeriodReference(f"{year + 1}-01")
        
        return None
    
    def get_previous_period(self, current: PeriodReference) -> Optional[PeriodReference]:
        """Get the previous fiscal period."""
        year = current.get_year()
        month = current.get_month()
        
        if month and month > 1:
            return PeriodReference(f"{year}-{month - 1:02d}")
        elif month == 1:
            return PeriodReference(f"{year - 1}-12")
        
        return None


# ========== AUDIT REPOSITORY ==========

class PostgresAuditRepository(IAuditRepository):
    def __init__(self, session: Session):
        self._session = session
    
    def _model_to_domain(self, model: AuditLogModel) -> DomainAuditRecord:
        """Convert ORM model to domain AuditRecord."""
        return DomainAuditRecord(
            id=str(model.id),
            operation=model.operation,
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            performed_by=model.user_id or "",
            performed_at=model.created_at,
            old_state=model.old_state,
            new_state=model.new_state,
            changes=model.changes,
            ip_address=model.ip_address,
            user_agent=model.user_agent
        )
    
    def log_operation(
        self, operation: str, entity_type: str, entity_id: str, performed_by: str,
        old_state: Optional[Dict] = None, new_state: Optional[Dict] = None,
        changes: Optional[Dict] = None, ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log an audit operation."""
        log = AuditLogModel(
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=performed_by,
            old_state=old_state,
            new_state=new_state,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        self._session.add(log)
    
    def get_audit_trail(
        self, entity_type: Optional[str] = None, entity_id: Optional[str] = None,
        from_date: Optional[datetime] = None, to_date: Optional[datetime] = None,
        performed_by: Optional[str] = None, limit: Optional[int] = None
    ) -> List[DomainAuditRecord]:
        """Get audit trail with filters."""
        query = select(AuditLogModel).order_by(AuditLogModel.created_at.desc())
        
        if entity_type:
            query = query.where(AuditLogModel.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditLogModel.entity_id == entity_id)
        if from_date:
            query = query.where(AuditLogModel.created_at >= from_date)
        if to_date:
            query = query.where(AuditLogModel.created_at <= to_date)
        if performed_by:
            query = query.where(AuditLogModel.user_id == performed_by)
        if limit:
            query = query.limit(limit)
        
        models = self._session.execute(query).scalars().all()
        
        return [self._model_to_domain(m) for m in models]
    
    def get_entity_history(self, entity_type: str, entity_id: str) -> List[DomainAuditRecord]:
        """Get complete history for a specific entity."""
        return self.get_audit_trail(entity_type=entity_type, entity_id=entity_id, limit=1000)


__all__ = [
    "PostgresJournalEntryRepository",
    "PostgresLedgerRepository",
    "PostgresAccountRepository",
    "PostgresFiscalPeriodRepository",
    "PostgresAuditRepository"
]