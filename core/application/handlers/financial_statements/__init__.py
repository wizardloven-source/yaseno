# core/application/handlers/financial_statements/__init__.py
"""
Financial Statements Handlers - معالجات القوائم المالية
"""

from .generate_income_statement_handler import GenerateIncomeStatementHandler
from .generate_balance_sheet_handler import GenerateBalanceSheetHandler
from .generate_cash_flow_handler import GenerateCashFlowHandler
from .generate_equity_statement_handler import GenerateEquityStatementHandler
from .generate_trial_balance_handler import GenerateTrialBalanceHandler
from .export_financial_statement_handler import ExportFinancialStatementHandler
from .print_financial_statement_handler import PrintFinancialStatementHandler  # ✅ إضافة
from .get_statement_handler import GetFinancialStatementHandler
from .list_statements_handler import ListFinancialStatementsHandler
from .get_latest_income_statement_handler import GetLatestIncomeStatementHandler  # ✅ إضافة
from .get_latest_balance_sheet_handler import GetLatestBalanceSheetHandler  # ✅ إضافة
from .get_financial_ratios_handler import GetFinancialRatiosHandler  # ✅ إضافة

__all__ = [
    "GenerateIncomeStatementHandler",
    "GenerateBalanceSheetHandler",
    "GenerateCashFlowHandler",
    "GenerateEquityStatementHandler",
    "GenerateTrialBalanceHandler",
    "ExportFinancialStatementHandler",
    "PrintFinancialStatementHandler",  # ✅ إضافة
    "GetFinancialStatementHandler",
    "ListFinancialStatementsHandler",
    "GetLatestIncomeStatementHandler",  # ✅ إضافة
    "GetLatestBalanceSheetHandler",  # ✅ إضافة
    "GetFinancialRatiosHandler",  # ✅ إضافة
]