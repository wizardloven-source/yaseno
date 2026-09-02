# core/application/handlers/reports/get_income_statement_report_handler.py
"""
Get Income Statement Report Handler - معالج تقرير قائمة الدخل
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetIncomeStatementReportHandler(BaseQueryHandler):
    """
    معالج تقرير قائمة الدخل
    
    يقوم بتوليد قائمة الدخل لفترة محددة
    """
    
    def __init__(self, financial_statement_generator):
        self._generator = financial_statement_generator
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد قائمة الدخل
        
        Args:
            query: GetIncomeStatementReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: قائمة الدخل
        """
        logger.info(f"Generating income statement for period: {query.period_start} to {query.period_end}")
        
        # إنشاء معلومات الفترة
        from core.domain.financial_statements.value_objects import StatementPeriodInfo, StatementPeriod
        
        period_info = StatementPeriodInfo(
            period_type=StatementPeriod.CUSTOM,
            start_date=query.period_start,
            end_date=query.period_end,
            period_name=f"{query.period_start} - {query.period_end}",
            fiscal_year=query.period_end.year,
            is_comparative=query.include_comparative
        )
        
        # توليد قائمة الدخل
        statement = self._generator.generate_income_statement(
            period_info=period_info,
            currency=query.currency
        )
        
        return {
            "success": True,
            "report_type": "income_statement",
            "period_start": query.period_start.isoformat(),
            "period_end": query.period_end.isoformat(),
            "currency": query.currency,
            "data": {
                "revenue": float(statement.revenue),
                "cogs": float(statement.cogs),
                "gross_profit": float(statement.gross_profit),
                "operating_expenses": float(statement.operating_expenses),
                "operating_profit": float(statement.operating_profit),
                "other_income": float(statement.other_income),
                "other_expenses": float(statement.other_expenses),
                "net_income_before_tax": float(statement.net_income_before_tax),
                "income_tax": float(statement.income_tax),
                "net_income": float(statement.net_income)
            },
            "margins": {
                "gross_margin": float(statement.gross_margin) if statement.gross_margin else None,
                "operating_margin": float(statement.operating_margin) if statement.operating_margin else None,
                "net_margin": float(statement.net_margin) if statement.net_margin else None
            },
            "generated_at": datetime.now().isoformat()
        }