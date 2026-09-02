# core/bootstrap/modules/reports.py
"""
وحدة التقارير - تسجيل جميع خدمات التقارير
مستخرجة من bootstrap.py
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class ReportsModule(Module):
    """
    وحدة التقارير - نظام التقارير المتقدم
    
    تشمل:
        1. التقارير المالية:
           - ميزان المراجعة (Trial Balance)
           - الميزانية العمومية (Balance Sheet)
           - قائمة الدخل (Income Statement)
           - قائمة التدفقات النقدية (Cash Flow)
           - دفتر الأستاذ العام (General Ledger)
           - دفتر الأستاذ المساعد (Subsidiary Ledger)
           
        2. تقارير المبيعات:
           - تقارير المبيعات اليومية/الشهرية/السنوية
           - تقارير العملاء
           - تقارير المنتجات الأكثر مبيعاً
           
        3. تقارير المشتريات:
           - تقارير المشتريات
           - تقارير الموردين
           
        4. تقارير المخزون:
           - تقييم المخزون
           - حركات المخزون
           - المنتجات منخفضة المخزون
           
        5. تقارير الضرائب:
           - تقارير VAT/GST
           - تقارير المبيعات الخاضعة للضريبة
           
        6. تقارير العملاء والموردين:
           - كشف حساب العميل
           - كشف حساب المورد
           - تقارير الأعمار (Aging Reports)
           
        7. تقارير الأداء:
           - الربحية حسب المنتج/العميل/الفرع
           - مؤشرات الأداء الرئيسية (KPIs)
    """
    
    name = "reports"
    description = "نظام التقارير المتقدم - مالي، مبيعات، مشتريات، مخزون، ضرائب"
    dependencies = ["database", "accounting", "invoicing", "purchasing", "inventory", "customers", "suppliers"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات التقارير"""
        
        # ========== Repositories ==========
        # ✅ إضافة session كاعتماد
        container.register(
            "report_repo",
            "core.infrastructure.db.postgres.report_repository.PostgresReportRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ تم الإصلاح
        )
        container.register(
            "report_schedule_repo",
            "core.infrastructure.db.postgres.report_repository.PostgresReportScheduleRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ تم الإصلاح
        )
        
        # ========== Services ==========
        container.register(
            "report_service",
            "core.application.reports.services.ReportService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["report_repo", "uow"]
        )
        container.register(
            "report_generator",
            "core.application.reports.services.ReportGenerator",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["ledger_engine", "invoice_repo", "purchase_order_repo", "product_repo"]
        )
        container.register(
            "financial_report_generator",
            "core.application.reports.services.FinancialReportGenerator",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["ledger_engine", "financial_statement_generator"]
        )
        container.register(
            "report_export_service",
            "core.application.reports.services.ReportExportService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["report_service"]
        )
        container.register(
            "report_schedule_service",
            "core.application.reports.services.ReportScheduleService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["report_schedule_repo", "report_service", "uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "generate_report_handler",
            "core.application.handlers.reports.GenerateReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "report_generator"]
        )
        container.register(
            "export_report_handler",
            "core.application.handlers.reports.ExportReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "report_export_service"]
        )
        container.register(
            "schedule_report_handler",
            "core.application.handlers.reports.ScheduleReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "report_schedule_service"]
        )
        container.register(
            "delete_scheduled_report_handler",
            "core.application.handlers.reports.DeleteScheduledReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "run_scheduled_report_handler",
            "core.application.handlers.reports.RunScheduledReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "report_generator", "report_export_service"]
        )
        
        # ========== Query Handlers ==========
        # تقارير مالية
        container.register(
            "get_trial_balance_report_handler",
            "core.application.handlers.reports.GetTrialBalanceReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["ledger_engine"]
        )
        container.register(
            "get_balance_sheet_report_handler",
            "core.application.handlers.reports.GetBalanceSheetReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["financial_statement_generator"]
        )
        container.register(
            "get_income_statement_report_handler",
            "core.application.handlers.reports.GetIncomeStatementReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["financial_statement_generator"]
        )
        container.register(
            "get_cash_flow_report_handler",
            "core.application.handlers.reports.GetCashFlowReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["financial_statement_generator"]
        )
        container.register(
            "get_general_ledger_report_handler",
            "core.application.handlers.reports.GetGeneralLedgerReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["ledger_repo"]
        )
        container.register(
            "get_subsidiary_ledger_report_handler",
            "core.application.handlers.reports.GetSubsidiaryLedgerReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["ledger_repo"]
        )
        
        # تقارير المبيعات والمشتريات
        container.register(
            "get_sales_report_handler",
            "core.application.handlers.reports.GetSalesReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["invoice_repo"]
        )
        container.register(
            "get_purchases_report_handler",
            "core.application.handlers.reports.GetPurchasesReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["purchase_order_repo"]
        )
        container.register(
            "get_customer_report_handler",
            "core.application.handlers.reports.GetCustomerReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["customer_repo", "invoice_repo"]
        )
        container.register(
            "get_supplier_report_handler",
            "core.application.handlers.reports.GetSupplierReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["supplier_repo", "purchase_order_repo"]
        )
        
        # تقارير المخزون
        container.register(
            "get_inventory_report_handler",
            "core.application.handlers.reports.GetInventoryReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["product_repo", "stock_movement_repo"]
        )
        container.register(
            "get_inventory_valuation_report_handler",
            "core.application.handlers.reports.GetInventoryValuationReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["product_repo", "inventory_valuation_service"]
        )
        container.register(
            "get_low_stock_report_handler",
            "core.application.handlers.reports.GetLowStockReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["product_repo"]
        )
        
        # تقارير الضرائب
        container.register(
            "get_tax_report_handler",
            "core.application.handlers.reports.GetTaxReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["tax_repo", "tax_period_repo", "ledger_engine"]
        )
        
        # تقارير الأداء
        container.register(
            "get_profitability_report_handler",
            "core.application.handlers.reports.GetProfitabilityReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["ledger_engine", "invoice_repo", "purchase_order_repo"]
        )
        container.register(
            "get_kpi_report_handler",
            "core.application.handlers.reports.GetKPIReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["invoice_repo", "purchase_order_repo", "ledger_engine"]
        )
        
        # تقارير العملاء والموردين
        container.register(
            "get_customer_statement_report_handler",
            "core.application.handlers.reports.GetCustomerStatementReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["customer_repo", "invoice_repo", "payment_repo"]
        )
        container.register(
            "get_supplier_statement_report_handler",
            "core.application.handlers.reports.GetSupplierStatementReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["supplier_repo", "purchase_order_repo", "payment_repo"]
        )
        container.register(
            "get_aging_report_handler",
            "core.application.handlers.reports.GetAgingReportHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["invoice_repo", "payment_repo"]
        )
        
        # تقارير عامة
        container.register(
            "list_reports_handler",
            "core.application.handlers.reports.ListReportsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["report_repo"]
        )
        container.register(
            "get_scheduled_reports_handler",
            "core.application.handlers.reports.GetScheduledReportsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["report_schedule_repo"]
        )
        container.register(
            "get_report_formats_handler",
            "core.application.handlers.reports.GetReportFormatsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("GenerateReportCommand", "generate_report_handler")
                logger.info("✅ Registered GenerateReportCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register GenerateReportCommand: {e}")
            
            try:
                command_bus.register("ExportReportCommand", "export_report_handler")
                logger.info("✅ Registered ExportReportCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ExportReportCommand: {e}")
            
            try:
                command_bus.register("ScheduleReportCommand", "schedule_report_handler")
                logger.info("✅ Registered ScheduleReportCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ScheduleReportCommand: {e}")
            
            try:
                command_bus.register("DeleteScheduledReportCommand", "delete_scheduled_report_handler")
                logger.info("✅ Registered DeleteScheduledReportCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteScheduledReportCommand: {e}")
            
            try:
                command_bus.register("RunScheduledReportCommand", "run_scheduled_report_handler")
                logger.info("✅ Registered RunScheduledReportCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register RunScheduledReportCommand: {e}")
            
            # ========== Query Handlers ==========
            # تقارير مالية
            try:
                query_bus.register("GetTrialBalanceReportQuery", "get_trial_balance_report_handler")
                logger.info("✅ Registered GetTrialBalanceReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetTrialBalanceReportQuery: {e}")
            
            try:
                query_bus.register("GetBalanceSheetReportQuery", "get_balance_sheet_report_handler")
                logger.info("✅ Registered GetBalanceSheetReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetBalanceSheetReportQuery: {e}")
            
            try:
                query_bus.register("GetIncomeStatementReportQuery", "get_income_statement_report_handler")
                logger.info("✅ Registered GetIncomeStatementReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetIncomeStatementReportQuery: {e}")
            
            try:
                query_bus.register("GetCashFlowReportQuery", "get_cash_flow_report_handler")
                logger.info("✅ Registered GetCashFlowReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCashFlowReportQuery: {e}")
            
            try:
                query_bus.register("GetGeneralLedgerReportQuery", "get_general_ledger_report_handler")
                logger.info("✅ Registered GetGeneralLedgerReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetGeneralLedgerReportQuery: {e}")
            
            try:
                query_bus.register("GetSubsidiaryLedgerReportQuery", "get_subsidiary_ledger_report_handler")
                logger.info("✅ Registered GetSubsidiaryLedgerReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSubsidiaryLedgerReportQuery: {e}")
            
            # تقارير المبيعات والمشتريات
            try:
                query_bus.register("GetSalesReportQuery", "get_sales_report_handler")
                logger.info("✅ Registered GetSalesReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSalesReportQuery: {e}")
            
            try:
                query_bus.register("GetPurchasesReportQuery", "get_purchases_report_handler")
                logger.info("✅ Registered GetPurchasesReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetPurchasesReportQuery: {e}")
            
            try:
                query_bus.register("GetCustomerReportQuery", "get_customer_report_handler")
                logger.info("✅ Registered GetCustomerReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCustomerReportQuery: {e}")
            
            try:
                query_bus.register("GetSupplierReportQuery", "get_supplier_report_handler")
                logger.info("✅ Registered GetSupplierReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSupplierReportQuery: {e}")
            
            # تقارير المخزون
            try:
                query_bus.register("GetInventoryReportQuery", "get_inventory_report_handler")
                logger.info("✅ Registered GetInventoryReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetInventoryReportQuery: {e}")
            
            try:
                query_bus.register("GetInventoryValuationReportQuery", "get_inventory_valuation_report_handler")
                logger.info("✅ Registered GetInventoryValuationReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetInventoryValuationReportQuery: {e}")
            
            try:
                query_bus.register("GetLowStockReportQuery", "get_low_stock_report_handler")
                logger.info("✅ Registered GetLowStockReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetLowStockReportQuery: {e}")
            
            # تقارير الضرائب
            try:
                query_bus.register("GetTaxReportQuery", "get_tax_report_handler")
                logger.info("✅ Registered GetTaxReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetTaxReportQuery: {e}")
            
            # تقارير الأداء
            try:
                query_bus.register("GetProfitabilityReportQuery", "get_profitability_report_handler")
                logger.info("✅ Registered GetProfitabilityReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetProfitabilityReportQuery: {e}")
            
            try:
                query_bus.register("GetKPIReportQuery", "get_kpi_report_handler")
                logger.info("✅ Registered GetKPIReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetKPIReportQuery: {e}")
            
            # تقارير العملاء والموردين
            try:
                query_bus.register("GetCustomerStatementReportQuery", "get_customer_statement_report_handler")
                logger.info("✅ Registered GetCustomerStatementReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCustomerStatementReportQuery: {e}")
            
            try:
                query_bus.register("GetSupplierStatementReportQuery", "get_supplier_statement_report_handler")
                logger.info("✅ Registered GetSupplierStatementReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSupplierStatementReportQuery: {e}")
            
            try:
                query_bus.register("GetAgingReportQuery", "get_aging_report_handler")
                logger.info("✅ Registered GetAgingReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetAgingReportQuery: {e}")
            
            # تقارير عامة
            try:
                query_bus.register("ListReportsQuery", "list_reports_handler")
                logger.info("✅ Registered ListReportsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListReportsQuery: {e}")
            
            try:
                query_bus.register("GetScheduledReportsQuery", "get_scheduled_reports_handler")
                logger.info("✅ Registered GetScheduledReportsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetScheduledReportsQuery: {e}")
            
            try:
                query_bus.register("GetReportFormatsQuery", "get_report_formats_handler")
                logger.info("✅ Registered GetReportFormatsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetReportFormatsQuery: {e}")