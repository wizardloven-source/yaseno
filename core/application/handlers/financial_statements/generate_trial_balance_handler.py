# core/application/handlers/financial_statements/generate_trial_balance_handler.py
"""
Generate Trial Balance Handler - معالج توليد ميزان المراجعة
"""

import logging
from datetime import date

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import LedgerEngine
from core.domain.shared.value_objects import AccountCode

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import GenerateTrialBalanceCommand
from core.application.financial_statements.dtos import TrialBalanceDTO

logger = logging.getLogger(__name__)


class GenerateTrialBalanceHandler(BaseHandler[GenerateTrialBalanceCommand, TrialBalanceDTO]):
    """
    معالج توليد ميزان المراجعة
    """

    def __init__(self, uow: IUnitOfWork, ledger_engine: LedgerEngine):
        super().__init__(uow)
        self._ledger_engine = ledger_engine

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command: GenerateTrialBalanceCommand, user_context: UserContext) -> TrialBalanceDTO:
        """
        تنفيذ توليد ميزان المراجعة
        
        Args:
            command: أمر توليد ميزان المراجعة
            user_context: سياق المستخدم
        
        Returns:
            TrialBalanceDTO: ميزان المراجعة
        """
        logger.info(f"Generating trial balance as of {command.as_of_date}")

        # توليد ميزان المراجعة
        trial_balance = self._ledger_engine.get_trial_balance(
            as_of=command.as_of_date,
            currency=command.currency
        )

        # بناء DTO
        balances = []
        for account_code, balance in trial_balance.items():
            balances.append({
                'account_code': account_code.code,
                'account_name': '',  # سيتم تعبئته من المستودع
                'debit': float(balance.amount) if balance.amount > 0 else 0,
                'credit': float(-balance.amount) if balance.amount < 0 else 0,
                'currency': balance.currency
            })

        total_debits = sum(b['debit'] for b in balances)
        total_credits = sum(b['credit'] for b in balances)

        return TrialBalanceDTO(
            as_of_date=command.as_of_date,
            currency=command.currency,
            accounts=balances,
            total_debits=total_debits,
            total_credits=total_credits,
            is_balanced=abs(total_debits - total_credits) < 0.01,
            difference=abs(total_debits - total_credits)
        )