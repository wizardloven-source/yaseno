# core/application/handlers/financial_statements/generate_income_statement_handler.py
"""
Generate Income Statement Handler - معالج توليد قائمة الدخل
"""

import logging
from datetime import date

from core.domain.financial_statements.services import FinancialStatementGenerator
from core.domain.financial_statements.value_objects import StatementPeriodInfo, StatementPeriod
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import GenerateIncomeStatementCommand
from core.application.financial_statements.dtos import IncomeStatementDTO
from core.application.financial_statements.converters import income_statement_to_dto

logger = logging.getLogger(__name__)


class GenerateIncomeStatementHandler(BaseHandler[GenerateIncomeStatementCommand, IncomeStatementDTO]):
    """
    معالج توليد قائمة الدخل
    
    يقوم بإنشاء قائمة الدخل لفترة مالية محددة،
    وتشمل الإيرادات والمصروفات وصافي الدخل.
    """

    def __init__(self, uow: IUnitOfWork, generator: FinancialStatementGenerator):
        super().__init__(uow)
        self._generator = generator

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command: GenerateIncomeStatementCommand, user_context: UserContext) -> IncomeStatementDTO:
        """
        تنفيذ توليد قائمة الدخل
        
        Args:
            command: أمر توليد قائمة الدخل
            user_context: سياق المستخدم
        
        Returns:
            IncomeStatementDTO: قائمة الدخل
        """
        logger.info(f"Generating income statement for period {command.period_start} to {command.period_end}")

        # إنشاء معلومات الفترة
        period_info = StatementPeriodInfo(
            period_type=StatementPeriod.CUSTOM,
            start_date=command.period_start,
            end_date=command.period_end,
            period_name=f"{command.period_start} - {command.period_end}",
            fiscal_year=command.period_end.year,
            is_comparative=command.include_comparative
        )

        # توليد القائمة وحفظها
        with self._uow:
            # ✅ ربط المستودع بجلسة الـ UoW الحالية لمنع تعارض الجلسات
            self._generator._ledger_repo = self._uow.ledger
            statement = self._generator.generate_income_statement(
                period_info=period_info,
                currency=command.currency
            )
            self._uow.financial_statements.save(statement)
            self._commit()

        logger.info(f"Income statement generated: {statement.id}")

        return income_statement_to_dto(statement)