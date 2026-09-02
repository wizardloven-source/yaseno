# core/application/handlers/reports/get_balance_sheet_report_handler.py
"""
Get Balance Sheet Report Handler - معالج تقرير الميزانية العمومية
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetBalanceSheetReportHandler(BaseQueryHandler):
    """
    معالج تقرير الميزانية العمومية
    
    يقوم بتوليد الميزانية العمومية في تاريخ محدد
    """
    
    def __init__(self, financial_statement_generator):
        self._generator = financial_statement_generator
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد الميزانية العمومية
        
        Args:
            query: GetBalanceSheetReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: الميزانية العمومية
        """
        logger.info(f"Generating balance sheet as of: {query.as_of_date}")
        
        # توليد الميزانية العمومية
        statement = self._generator.generate_balance_sheet(
            as_of_date=query.as_of_date,
            currency=query.currency
        )
        
        return {
            "success": True,
            "report_type": "balance_sheet",
            "as_of_date": query.as_of_date.isoformat(),
            "currency": query.currency,
            "data": {
                "assets": {
                    "current_assets": float(statement.current_assets),
                    "fixed_assets": float(statement.fixed_assets),
                    "intangible_assets": float(statement.intangible_assets),
                    "other_assets": float(statement.other_assets),
                    "total_assets": float(statement.total_assets)
                },
                "liabilities": {
                    "current_liabilities": float(statement.current_liabilities),
                    "long_term_liabilities": float(statement.long_term_liabilities),
                    "total_liabilities": float(statement.total_liabilities)
                },
                "equity": {
                    "paid_in_capital": float(statement.paid_in_capital),
                    "retained_earnings": float(statement.retained_earnings),
                    "total_equity": float(statement.total_equity)
                }
            },
            "ratios": {
                "working_capital": float(statement.working_capital),
                "current_ratio": float(statement.current_ratio) if statement.current_ratio else None,
                "debt_to_equity": float(statement.debt_to_equity) if statement.debt_to_equity else None
            },
            "is_balanced": statement.is_balanced,
            "generated_at": datetime.now().isoformat()
        }