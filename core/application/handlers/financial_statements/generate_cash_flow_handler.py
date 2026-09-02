# core/application/handlers/financial_statements/generate_cash_flow_handler.py
"""
Generate Cash Flow Statement Handler - معالج توليد قائمة التدفقات النقدية
"""

import logging
from datetime import date

from core.domain.financial_statements.services import FinancialStatementGenerator
from core.domain.financial_statements.value_objects import StatementPeriodInfo, StatementPeriod
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.value_objects import AccountCode

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import GenerateCashFlowCommand
from core.application.financial_statements.dtos import CashFlowStatementDTO

# ✅ استيراد صحيح
from core.application.financial_statements.converters import cash_flow_to_dto

logger = logging.getLogger(__name__)


class GenerateCashFlowHandler(BaseHandler[GenerateCashFlowCommand, CashFlowStatementDTO]):
    """
    معالج توليد قائمة التدفقات النقدية
    
    يقوم بإنشاء قائمة التدفقات النقدية لفترة مالية محددة،
    وتشمل التدفقات التشغيلية والاستثمارية والتمويلية.
    """

    # ✅ تعديل المُنشئ لاستقبال معاملين (uow و generator)
    def __init__(self, uow: IUnitOfWork, generator: FinancialStatementGenerator):
        super().__init__(uow)
        self._generator = generator

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command: GenerateCashFlowCommand, user_context: UserContext) -> CashFlowStatementDTO:
        """
        تنفيذ توليد قائمة التدفقات النقدية
        
        Args:
            command: أمر توليد قائمة التدفقات النقدية
            user_context: سياق المستخدم
        
        Returns:
            CashFlowStatementDTO: قائمة التدفقات النقدية
        """
        logger.info(f"Generating cash flow statement for period {command.period_start} to {command.period_end}")

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
            statement = self._generator.generate_cash_flow_statement(
                period_info=period_info,
                currency=command.currency
            )
            self._uow.financial_statements.save(statement)
            self._commit()

        logger.info(f"Cash flow statement generated: {statement.id}")

        return cash_flow_to_dto(statement)