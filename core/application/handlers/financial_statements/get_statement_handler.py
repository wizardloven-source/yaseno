# core/application/handlers/financial_statements/get_statement_handler.py
"""
Get Financial Statement Handler - معالج استعلام جلب قائمة مالية
"""

import logging
from typing import Optional, Dict, Any

from core.domain.financial_statements.value_objects import StatementId
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.value_objects import AccountCode  # ✅ إضافة استيراد مفقود

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import GetFinancialStatementQuery

# ✅ تصحيح الاستيراد - من application/financial_statements/converters
from core.application.financial_statements.converters import statement_to_dict

logger = logging.getLogger(__name__)


class GetFinancialStatementHandler(BaseQueryHandler[GetFinancialStatementQuery, Optional[Dict[str, Any]]]):
    """
    معالج استعلام جلب قائمة مالية
    
    يقوم بجلب قائمة مالية محددة بواسطة المعرف.
    """

    def __init__(self, statement_repo):
        self._statement_repo = statement_repo

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetFinancialStatementQuery, user_context: UserContext = None) -> Optional[Dict[str, Any]]:
        """
        تنفيذ جلب القائمة المالية
        
        Args:
            query: استعلام جلب القائمة المالية
        
        Returns:
            Dict[str, Any]: بيانات القائمة المالية أو None
        """
        logger.debug(f"Fetching financial statement: {query.statement_id}")

        statement = self._statement_repo.get_by_id(
            StatementId(query.statement_id)
        )

        if not statement:
            logger.warning(f"Financial statement not found: {query.statement_id}")
            return None

        return statement_to_dict(statement)