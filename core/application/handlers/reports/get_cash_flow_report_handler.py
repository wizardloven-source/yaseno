# core/application/handlers/reports/get_cash_flow_report_handler.py
"""
Get Cash Flow Report Handler - معالج تقرير التدفقات النقدية
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetCashFlowReportHandler(BaseQueryHandler):
    """
    معالج تقرير التدفقات النقدية
    
    يقوم بتوليد قائمة التدفقات النقدية لفترة محددة
    """
    
    def __init__(self, financial_statement_generator):
        self._generator = financial_statement_generator
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد قائمة التدفقات النقدية
        
        Args:
            query: GetCashFlowReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: قائمة التدفقات النقدية
        """
        logger.info(f"Generating cash flow statement for period: {query.period_start} to {query.period_end}")
        
        # إنشاء معلومات الفترة
        from core.domain.financial_statements.value_objects import StatementPeriodInfo, StatementPeriod
        
        period_info = StatementPeriodInfo(
            period_type=StatementPeriod.CUSTOM,
            start_date=query.period_start,
            end_date=query.period_end,
            period_name=f"{query.period_start} - {query.period_end}",
            fiscal_year=query.period_end.year
        )
        
        # توليد قائمة التدفقات النقدية
        statement = self._generator.generate_cash_flow_statement(
            period_info=period_info,
            currency=query.currency
        )
        
        return {
            "success": True,
            "report_type": "cash_flow",
            "period_start": query.period_start.isoformat(),
            "period_end": query.period_end.isoformat(),
            "currency": query.currency,
            "method": query.method,
            "data": {
                "operating_cash_flow": float(statement.operating_cash_flow),
                "investing_cash_flow": float(statement.investing_cash_flow),
                "financing_cash_flow": float(statement.financing_cash_flow),
                "net_cash_flow": float(statement.net_cash_flow),
                "beginning_cash": float(statement.beginning_cash),
                "ending_cash": float(statement.ending_cash)
            },
            "free_cash_flow": float(statement.free_cash_flow) if statement.free_cash_flow else None,
            "generated_at": datetime.now().isoformat()
        }