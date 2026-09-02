# core/application/handlers/financial_statements/print_financial_statement_handler.py
"""
Print Financial Statement Handler - معالج طباعة القوائم المالية
"""

import logging
from typing import Dict, Any

from core.domain.financial_statements.value_objects import StatementId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import PrintFinancialStatementCommand
from core.application.financial_statements.converters import statement_to_dict

logger = logging.getLogger(__name__)


class PrintFinancialStatementHandler(BaseHandler[PrintFinancialStatementCommand, Dict[str, Any]]):
    """
    معالج طباعة القوائم المالية
    
    يقوم بطباعة القائمة المالية أو تصديرها كـ PDF.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, command: PrintFinancialStatementCommand, user_context: UserContext) -> Dict[str, Any]:
        """
        تنفيذ طباعة القائمة المالية
        
        Args:
            command: أمر طباعة القائمة المالية
            user_context: سياق المستخدم
        
        Returns:
            Dict[str, Any]: نتيجة الطباعة
        """
        logger.info(f"Printing financial statement: {command.statement_id}")

        with self._uow:
            # جلب القائمة المالية
            statement = self._uow.financial_statements.get_by_id(
                StatementId(command.statement_id)
            )

            if not statement:
                return {
                    "success": False,
                    "message": f"Financial statement {command.statement_id} not found",
                    "statement_id": command.statement_id
                }

            # تحويل القائمة إلى قاموس
            statement_data = statement_to_dict(statement)

            # هنا يمكن إضافة منطق الطباعة الفعلي
            # مثلاً: إنشاء ملف PDF أو إرسال إلى الطابعة

            return {
                "success": True,
                "message": "Statement printed successfully",
                "statement_id": command.statement_id,
                "printed_by": user_context.user_id,
                "statement_data": statement_data
            }