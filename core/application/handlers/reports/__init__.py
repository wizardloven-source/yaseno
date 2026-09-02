# core/application/handlers/reports/__init__.py
"""
Reports Handlers - معالجات التقارير
"""

from .generate_report_handler import GenerateReportHandler
from .export_report_handler import ExportReportHandler
from .schedule_report_handler import ScheduleReportHandler
from .delete_scheduled_report_handler import DeleteScheduledReportHandler
from .run_scheduled_report_handler import RunScheduledReportHandler

# تقارير مالية
from .get_trial_balance_report_handler import GetTrialBalanceReportHandler
from .get_balance_sheet_report_handler import GetBalanceSheetReportHandler
from .get_income_statement_report_handler import GetIncomeStatementReportHandler
from .get_cash_flow_report_handler import GetCashFlowReportHandler
from .get_general_ledger_report_handler import GetGeneralLedgerReportHandler
from .get_subsidiary_ledger_report_handler import GetSubsidiaryLedgerReportHandler

# تقارير المبيعات والمشتريات
from .get_sales_report_handler import GetSalesReportHandler
from .get_purchases_report_handler import GetPurchasesReportHandler
from .get_customer_report_handler import GetCustomerReportHandler
from .get_supplier_report_handler import GetSupplierReportHandler

# تقارير المخزون
from .get_inventory_report_handler import GetInventoryReportHandler
from .get_inventory_valuation_report_handler import GetInventoryValuationReportHandler
from .get_low_stock_report_handler import GetLowStockReportHandler

# تقارير الضرائب
from .get_tax_report_handler import GetTaxReportHandler

# تقارير الأداء
from .get_profitability_report_handler import GetProfitabilityReportHandler
from .get_kpi_report_handler import GetKPIReportHandler

# تقارير العملاء والموردين
from .get_customer_statement_report_handler import GetCustomerStatementReportHandler
from .get_supplier_statement_report_handler import GetSupplierStatementReportHandler
from .get_aging_report_handler import GetAgingReportHandler

# تقارير عامة
from .list_reports_query_handler import ListReportsQueryHandler
from .get_scheduled_reports_query_handler import GetScheduledReportsQueryHandler
from .get_report_formats_query_handler import GetReportFormatsQueryHandler

__all__ = [
    # Command Handlers
    "GenerateReportHandler",
    "ExportReportHandler",
    "ScheduleReportHandler",
    "DeleteScheduledReportHandler",
    "RunScheduledReportHandler",
    
    # Financial Reports
    "GetTrialBalanceReportHandler",
    "GetBalanceSheetReportHandler",
    "GetIncomeStatementReportHandler",
    "GetCashFlowReportHandler",
    "GetGeneralLedgerReportHandler",
    "GetSubsidiaryLedgerReportHandler",
    
    # Sales & Purchases Reports
    "GetSalesReportHandler",
    "GetPurchasesReportHandler",
    "GetCustomerReportHandler",
    "GetSupplierReportHandler",
    
    # Inventory Reports
    "GetInventoryReportHandler",
    "GetInventoryValuationReportHandler",
    "GetLowStockReportHandler",
    
    # Tax Reports
    "GetTaxReportHandler",
    
    # Performance Reports
    "GetProfitabilityReportHandler",
    "GetKPIReportHandler",
    
    # Customer & Supplier Reports
    "GetCustomerStatementReportHandler",
    "GetSupplierStatementReportHandler",
    "GetAgingReportHandler",
    
    # General Reports
    "ListReportsQueryHandler",
    "GetScheduledReportsQueryHandler",
    "GetReportFormatsQueryHandler",
]