# core/application/handlers/financial_statements/list_statements_handler.py
"""
List Financial Statements Handler - معالج استعلام قائمة القوائم المالية
"""

import logging
from typing import List, Dict, Any
from datetime import date

from core.domain.financial_statements.value_objects import StatementType
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.value_objects import AccountCode  # ✅ إضافة استيراد مفقود

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import ListFinancialStatementsQuery

# ✅ تصحيح الاستيراد - من application/financial_statements/converters
from core.application.financial_statements.converters import statement_to_dict

logger = logging.getLogger(__name__)


class ListFinancialStatementsHandler(BaseQueryHandler[ListFinancialStatementsQuery, List[Dict[str, Any]]]):
    """
    معالج استعلام قائمة القوائم المالية
    
    يقوم بجلب قائمة القوائم المالية مع خيارات التصفية والترقيم.
    """

    def __init__(self, statement_repo):
        self._statement_repo = statement_repo

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: ListFinancialStatementsQuery, user_context: UserContext = None) -> List[Dict[str, Any]]:
        """
        تنفيذ جلب قائمة القوائم المالية
        
        Args:
            query: استعلام قائمة القوائم المالية
        
        Returns:
            List[Dict[str, Any]]: قائمة القوائم المالية
        """
        logger.debug(f"Listing financial statements: type={query.statement_type}, limit={query.limit}")

        if query.statement_type:
            statement_type = StatementType(query.statement_type)
            statements = self._statement_repo.list_by_type(
                statement_type=statement_type,
                limit=query.limit,
                offset=query.offset
            )
        else:
            # استخدام تواريخ افتراضية إذا لم يتم تحديدها
            from_date = query.from_date or date(2000, 1, 1)
            to_date = query.to_date or date.today()

            statements = self._statement_repo.list_by_period(
                start_date=from_date,
                end_date=to_date,
                limit=query.limit
            )

            logger.info(f"Found {len(statements)} financial statements")

            return [statement_to_dict(s) for s in statements]