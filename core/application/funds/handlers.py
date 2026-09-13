"""
Handlers for Bank Reconciliation.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from core.application.funds.commands import (
    ImportBankStatementCommand,
    CreateBankReconciliationCommand,
    MatchTransactionCommand,
    UnmatchTransactionCommand,
    AddBankFeeCommand,
    AddDifferenceCommand,
    CompleteReconciliationCommand,
    CancelReconciliationCommand,
)
from core.domain.funds.entities import BankStatement, BankReconciliation
from core.domain.funds.interfaces import IBankReconciliationRepository
from core.infrastructure.db.uow import IUnitOfWork


class ImportBankStatementHandler:
    """Handler to import bank statements."""
    
    def __init__(self, uow: IUnitOfWork, repo: IBankReconciliationRepository):
        self.uow = uow
        self.repo = repo
    
    async def handle(self, command: ImportBankStatementCommand) -> BankStatement:
        """Import a bank statement."""
        async with self.uow:
            # Create bank statement
            statement = BankStatement.create(
                account_id=command.account_id,
                statement_date=command.statement_date,
                opening_balance=command.opening_balance,
                closing_balance=command.closing_balance,
                currency=command.currency,
                reference=command.reference,
            )
            
            # Add lines
            for line_data in command.lines:
                statement.add_line(
                    line_id=line_data.get('line_id'),
                    date=line_data.get('date'),
                    description=line_data.get('description'),
                    amount=Decimal(str(line_data.get('amount', 0))),
                    reference=line_data.get('reference'),
                    transaction_type=line_data.get('transaction_type'),
                )
            
            # Save
            await self.repo.add_statement(statement)
            await self.uow.commit()
            
            return statement


class CreateBankReconciliationHandler:
    """Handler to create bank reconciliation."""
    
    def __init__(self, uow: IUnitOfWork, repo: IBankReconciliationRepository):
        self.uow = uow
        self.repo = repo
    
    async def handle(self, command: CreateBankReconciliationCommand) -> BankReconciliation:
        """Create a new bank reconciliation."""
        async with self.uow:
            reconciliation = BankReconciliation.create(
                account_id=command.account_id,
                reconciliation_date=command.reconciliation_date,
                statement_id=command.statement_id,
                target_balance=command.target_balance,
            )
            
            await self.repo.add_reconciliation(reconciliation)
            await self.uow.commit()
            
            return reconciliation


class MatchTransactionHandler:
    """Handler to match transactions."""
    
    def __init__(self, uow: IUnitOfWork, repo: IBankReconciliationRepository):
        self.uow = uow
        self.repo = repo
    
    async def handle(self, command: MatchTransactionCommand):
        """Match a statement line with a system transaction."""
        async with self.uow:
            reconciliation = await self.repo.get_reconciliation(command.reconciliation_id)
            
            if not reconciliation:
                raise ValueError(f"Reconciliation {command.reconciliation_id} not found")
            
            reconciliation.match_transaction(
                statement_line_id=command.statement_line_id,
                transaction_type=command.transaction_type,
                transaction_id=command.transaction_id,
                amount=command.amount,
                date=command.date,
                reference=command.reference,
            )
            
            await self.repo.update_reconciliation(reconciliation)
            await self.uow.commit()


class UnmatchTransactionHandler:
    """Handler to unmatch transactions."""
    
    def __init__(self, uow: IUnitOfWork, repo: IBankReconciliationRepository):
        self.uow = uow
        self.repo = repo
    
    async def handle(self, command: UnmatchTransactionCommand):
        """Unmatch a previously matched transaction."""
        async with self.uow:
            reconciliation = await self.repo.get_reconciliation(command.reconciliation_id)
            
            if not reconciliation:
                raise ValueError(f"Reconciliation {command.reconciliation_id} not found")
            
            reconciliation.unmatch_transaction(command.match_id)
            
            await self.repo.update_reconciliation(reconciliation)
            await self.uow.commit()


class AddBankFeeHandler:
    """Handler to add bank fees."""
    
    def __init__(self, uow: IUnitOfWork, repo: IBankReconciliationRepository):
        self.uow = uow
        self.repo = repo
    
    async def handle(self, command: AddBankFeeCommand):
        """Add a bank fee during reconciliation."""
        async with self.uow:
            reconciliation = await self.repo.get_reconciliation(command.reconciliation_id)
            
            if not reconciliation:
                raise ValueError(f"Reconciliation {command.reconciliation_id} not found")
            
            reconciliation.add_bank_fee(
                amount=command.amount,
                description=command.description,
                account_code=command.account_code,
                date=command.date,
                reference=command.reference,
            )
            
            await self.repo.update_reconciliation(reconciliation)
            await self.uow.commit()


class AddDifferenceHandler:
    """Handler to add differences."""
    
    def __init__(self, uow: IUnitOfWork, repo: IBankReconciliationRepository):
        self.uow = uow
        self.repo = repo
    
    async def handle(self, command: AddDifferenceCommand):
        """Record a difference in reconciliation."""
        async with self.uow:
            reconciliation = await self.repo.get_reconciliation(command.reconciliation_id)
            
            if not reconciliation:
                raise ValueError(f"Reconciliation {command.reconciliation_id} not found")
            
            reconciliation.add_difference(
                amount=command.amount,
                reason=command.reason,
                account_code=command.account_code,
                date=command.date,
            )
            
            await self.repo.update_reconciliation(reconciliation)
            await self.uow.commit()


class CompleteReconciliationHandler:
    """Handler to complete reconciliation."""
    
    def __init__(self, uow: IUnitOfWork, repo: IBankReconciliationRepository):
        self.uow = uow
        self.repo = repo
    
    async def handle(self, command: CompleteReconciliationCommand):
        """Complete and post the bank reconciliation."""
        async with self.uow:
            reconciliation = await self.repo.get_reconciliation(command.reconciliation_id)
            
            if not reconciliation:
                raise ValueError(f"Reconciliation {command.reconciliation_id} not found")
            
            # Complete reconciliation (creates journal entries)
            reconciliation.complete(notes=command.notes)
            
            await self.repo.update_reconciliation(reconciliation)
            await self.uow.commit()


class CancelReconciliationHandler:
    """Handler to cancel reconciliation."""
    
    def __init__(self, uow: IUnitOfWork, repo: IBankReconciliationRepository):
        self.uow = uow
        self.repo = repo
    
    async def handle(self, command: CancelReconciliationCommand):
        """Cancel a bank reconciliation."""
        async with self.uow:
            reconciliation = await self.repo.get_reconciliation(command.reconciliation_id)
            
            if not reconciliation:
                raise ValueError(f"Reconciliation {command.reconciliation_id} not found")
            
            reconciliation.cancel(reason=command.reason)
            
            await self.repo.update_reconciliation(reconciliation)
            await self.uow.commit()
