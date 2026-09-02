# core/application/handlers/financial_statements/generate_equity_statement_handler.py
"""
Generate Equity Statement Handler - معالج توليد قائمة التغيرات في حقوق الملكية
"""

import logging
from datetime import date

from core.domain.financial_statements.services import FinancialStatementGenerator
from core.domain.financial_statements.value_objects import StatementPeriodInfo, StatementPeriod
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.value_objects import AccountCode

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import GenerateEquityStatementCommand
from core.application.financial_statements.dtos import EquityStatementDTO
from core.application.financial_statements.converters import equity_statement_to_dto

logger = logging.getLogger(__name__)


class GenerateEquityStatementHandler(BaseHandler[GenerateEquityStatementCommand, EquityStatementDTO]):
    """
    معالج توليد قائمة التغيرات في حقوق الملكية
    """

    def __init__(self, uow: IUnitOfWork, generator: FinancialStatementGenerator):
        super().__init__(uow)
        self._generator = generator

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command: GenerateEquityStatementCommand, user_context: UserContext) -> EquityStatementDTO:
        """
        تنفيذ توليد قائمة التغيرات في حقوق الملكية
        
        Args:
            command: أمر توليد القائمة
            user_context: سياق المستخدم
        
        Returns:
            EquityStatementDTO: قائمة التغيرات في حقوق الملكية
        """
        logger.info(f"Generating equity statement for period {command.period_start} to {command.period_end}")

        # إنشاء معلومات الفترة
        period_info = StatementPeriodInfo(
            period_type=StatementPeriod.CUSTOM,
            start_date=command.period_start,
            end_date=command.period_end,
            period_name=f"{command.period_start} - {command.period_end}",
            fiscal_year=command.period_end.year
        )

        # توليد القائمة وحفظها
        with self._uow:
            # ✅ ربط المستودع بجلسة الـ UoW الحالية لمنع تعارض الجلسات
            self._generator._ledger_repo = self._uow.ledger
            statement = self._generator.generate_equity_statement(
                period_info=period_info,
                currency=command.currency
            )
            self._uow.financial_statements.save(statement)
            self._commit()

        logger.info(f"Equity statement generated: {statement.id}")

        return equity_statement_to_dto(statement)