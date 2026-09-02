# core/application/handlers/financial_statements/get_financial_ratios_handler.py

"""
Get Financial Ratios Handler - معالج استعلام النسب المالية
"""

import logging
from typing import Dict, Any

from core.domain.financial_statements.value_objects import StatementType
from core.domain.financial_statements.interfaces import IFinancialStatementRepository
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import LedgerEngine

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.financial_statements.commands import GetFinancialRatiosQuery
from core.application.financial_statements.converters import (
    income_statement_to_dict,
    balance_sheet_to_dict
)

logger = logging.getLogger(__name__)


class GetFinancialRatiosHandler(BaseQueryHandler[GetFinancialRatiosQuery, Dict[str, Any]]):
    """
    معالج استعلام النسب المالية

    يقوم بحساب النسب المالية من القوائم المالية المتاحة.
    """

    def __init__(self, statement_repo: IFinancialStatementRepository):
        self._statement_repo = statement_repo
        # لا نستدعي super() لأننا لا نستخدم uow في هذا المعالج

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetFinancialRatiosQuery, user_context: UserContext = None) -> Dict[str, Any]:
        """
        تنفيذ جلب النسب المالية

        Args:
            query: استعلام النسب المالية

        Returns:
            Dict[str, Any]: النسب المالية
        """
        logger.debug("Fetching financial ratios")

        # جلب أحدث قائمة دخل وميزانية عمومية
        income_statement = self._statement_repo.get_latest_by_type(
            statement_type=StatementType.INCOME_STATEMENT
        )
        balance_sheet = self._statement_repo.get_latest_by_type(
            statement_type=StatementType.BALANCE_SHEET
        )

        ratios = {
            "liquidity_ratios": {},
            "profitability_ratios": {},
            "efficiency_ratios": {},
            "leverage_ratios": {}
        }

        # حساب نسب الربحية
        if income_statement:
            income_data = income_statement_to_dict(income_statement)
            revenue = income_data.get("revenue", 0)
            net_income = income_data.get("net_income", 0)
            gross_profit = income_data.get("gross_profit", 0)
            operating_profit = income_data.get("operating_profit", 0)

            if revenue > 0:
                ratios["profitability_ratios"] = {
                    "gross_margin": float((gross_profit / revenue) * 100) if revenue else 0,
                    "operating_margin": float((operating_profit / revenue) * 100) if revenue else 0,
                    "net_margin": float((net_income / revenue) * 100) if revenue else 0
                }

        # حساب نسب السيولة والرفع المالي
        if balance_sheet:
            balance_data = balance_sheet_to_dict(balance_sheet)
            current_assets = balance_data.get("current_assets", 0)
            current_liabilities = balance_data.get("current_liabilities", 0)
            total_assets = balance_data.get("total_assets", 0)
            total_liabilities = balance_data.get("total_liabilities", 0)
            total_equity = balance_data.get("total_equity", 0)

            if current_liabilities > 0:
                ratios["liquidity_ratios"] = {
                    "current_ratio": float(current_assets / current_liabilities)
                }

            if total_equity > 0:
                ratios["leverage_ratios"] = {
                    "debt_to_equity": float(total_liabilities / total_equity),
                    "debt_to_assets": float(total_liabilities / total_assets) if total_assets > 0 else 0
                }

        return {
            "success": True,
            "ratios": ratios,
            "period": {
                "income_period": income_statement.period_info.period_name if income_statement else None,
                "balance_period": balance_sheet.period_info.period_name if balance_sheet else None
            }
        }