# core/infrastructure/db/postgres/reconciliation_repository.py
"""
Reconciliation Repository - مستودع التسوية البنكية
"""

from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session

from core.domain.accounting.reconciliation import (
    BankStatement,
    Reconciliation,
    ReconciliationMatch
)
from core.domain.accounting.reconciliation_interfaces import (
    IBankStatementRepository,
    IReconciliationRepository
)
from core.infrastructure.db.models.reconciliation_model import (
    BankStatementModel,
    ReconciliationModel,
    ReconciliationMatchModel
)


class PostgresBankStatementRepository(IBankStatementRepository):
    """مستودع كشوف الحسابات البنكية - PostgreSQL"""

    def __init__(self, session: Session):
        self._session = session

    def save(self, statement: BankStatement) -> None:
        # تحويل Domain إلى Model
        model = BankStatementModel(
            id=UUID(statement.id),
            account_code=statement.account_code.code,
            bank_name=statement.bank_name,
            account_number=statement.account_number,
            statement_date=statement.statement_date,
            opening_balance=statement.opening_balance.amount,
            closing_balance=statement.closing_balance.amount,
            currency=statement.currency,
            file_name=statement.file_name,
            uploaded_by=statement.uploaded_by
        )
        self._session.merge(model)

    def get_by_id(self, statement_id: str) -> Optional[BankStatement]:
        model = self._session.query(BankStatementModel).filter(
            BankStatementModel.id == UUID(statement_id)
        ).first()
        return self._to_domain(model) if model else None

    def list_by_account(self, account_code: str, limit: int = 100) -> List[BankStatement]:
        models = self._session.query(BankStatementModel).filter(
            BankStatementModel.account_code == account_code
        ).order_by(BankStatementModel.statement_date.desc()).limit(limit).all()
        return [self._to_domain(m) for m in models]

    def _to_domain(self, model: BankStatementModel) -> BankStatement:
        return BankStatement(
            id=str(model.id),
            account_code=model.account_code,
            bank_name=model.bank_name,
            account_number=model.account_number,
            statement_date=model.statement_date,
            opening_balance=model.opening_balance,
            closing_balance=model.closing_balance,
            currency=model.currency,
            file_name=model.file_name,
            uploaded_by=model.uploaded_by
        )