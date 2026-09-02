# core/application/handlers/financial_statements/generate_balance_sheet_handler.py
"""
Generate Balance Sheet Handler - معالج توليد الميزانية العمومية
"""

import logging
from datetime import date

from core.domain.financial_statements.services import FinancialStatementGenerator
from core.domain.financial_statements.value_objects import StatementPeriodInfo, StatementPeriod
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.value_objects import AccountCode

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import GenerateBalanceSheetCommand
from core.application.financial_statements.dtos import BalanceSheetDTO

# ✅ استيراد صحيح
from core.application.financial_statements.converters import balance_sheet_to_dto

logger = logging.getLogger(__name__)


class GenerateBalanceSheetHandler(BaseHandler[GenerateBalanceSheetCommand, BalanceSheetDTO]):
    """
    معالج توليد الميزانية العمومية
    
    يقوم بإنشاء الميزانية العمومية في تاريخ محدد،
    وتشمل الأصول والخصوم وحقوق الملكية.
    """

    # ✅ تعديل المُنشئ لاستقبال معاملين (uow و generator)
    def __init__(self, uow: IUnitOfWork, generator: FinancialStatementGenerator):
        super().__init__(uow)
        self._generator = generator

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command: GenerateBalanceSheetCommand, user_context: UserContext) -> BalanceSheetDTO:
        """
        تنفيذ توليد الميزانية العمومية
        
        Args:
            command: أمر توليد الميزانية العمومية
            user_context: سياق المستخدم
        
        Returns:
            BalanceSheetDTO: الميزانية العمومية
        """
        logger.info(f"Generating balance sheet as of {command.as_of_date}")

        # توليد القائمة وحفظها
        with self._uow:
            # ✅ ربط المستودع بجلسة الـ UoW الحالية لمنع تعارض الجلسات
            self._generator._ledger_repo = self._uow.ledger
            statement = self._generator.generate_balance_sheet(
                as_of_date=command.as_of_date,
                currency=command.currency
            )
            self._uow.financial_statements.save(statement)
            self._commit()

        logger.info(f"Balance sheet generated: {statement.id}")

        return balance_sheet_to_dto(statement)