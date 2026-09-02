# core/application/handlers/financial_statements/get_latest_balance_sheet_handler.py
"""
Get Latest Balance Sheet Handler - معالج استعلام جلب أحدث ميزانية عمومية
"""

import logging

from core.domain.financial_statements.value_objects import StatementType
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import GetLatestBalanceSheetQuery
from core.application.financial_statements.dtos import BalanceSheetDTO
from core.application.financial_statements.converters import balance_sheet_to_dto

logger = logging.getLogger(__name__)


class GetLatestBalanceSheetHandler(BaseQueryHandler[GetLatestBalanceSheetQuery, BalanceSheetDTO]):
    """
    معالج استعلام جلب أحدث ميزانية عمومية
    """

    def __init__(self, statement_repo):
        self._statement_repo = statement_repo

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetLatestBalanceSheetQuery, user_context: UserContext = None) -> BalanceSheetDTO:
        """
        تنفيذ جلب أحدث ميزانية عمومية
        
        Args:
            query: استعلام جلب أحدث ميزانية عمومية
        
        Returns:
            BalanceSheetDTO: أحدث ميزانية عمومية أو None
        """
        logger.debug(f"Fetching latest balance sheet for currency: {query.currency}")

        # جلب أحدث ميزانية عمومية
        statement = self._statement_repo.get_latest_by_type(
            statement_type=StatementType.BALANCE_SHEET
        )

        if not statement:
            logger.warning("No balance sheet found")
            return None

        return balance_sheet_to_dto(statement)