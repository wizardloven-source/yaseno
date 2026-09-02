# core/bootstrap/modules/financial_statements.py
"""
وحدة القوائم المالية - تسجيل جميع خدمات القوائم المالية
مستخرجة من bootstrap.py
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class FinancialStatementsModule(Module):
    """
    وحدة القوائم المالية
    
    تشمل:
        1. قائمة الدخل (Income Statement)
        2. الميزانية العمومية (Balance Sheet)
        3. قائمة التدفقات النقدية (Cash Flow Statement)
        4. قائمة التغيرات في حقوق الملكية (Equity Statement)
        5. ميزان المراجعة (Trial Balance)
    """
    
    name = "financial_statements"
    description = "إدارة القوائم المالية - الدخل، الميزانية، التدفقات النقدية"
    dependencies = ["database", "accounting", "fiscal"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات القوائم المالية"""
        
        # ========== Repositories ==========
        container.register(
            "financial_statement_repo",
            "core.infrastructure.db.postgres.financial_statement_repository.PostgresFinancialStatementRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== Services ==========
        container.register(
            "financial_statement_generator",
            "core.domain.financial_statements.services.FinancialStatementGenerator",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["ledger_repo"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "generate_income_statement_handler",
            "core.application.handlers.financial_statements.GenerateIncomeStatementHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "financial_statement_generator"]
        )
        container.register(
            "generate_balance_sheet_handler",
            "core.application.handlers.financial_statements.GenerateBalanceSheetHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "financial_statement_generator"]
        )
        container.register(
            "generate_cash_flow_handler",
            "core.application.handlers.financial_statements.GenerateCashFlowHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "financial_statement_generator"]
        )
        container.register(
            "generate_equity_statement_handler",
            "core.application.handlers.financial_statements.GenerateEquityStatementHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "financial_statement_generator"]
        )
        container.register(
            "generate_trial_balance_handler",
            "core.application.handlers.financial_statements.GenerateTrialBalanceHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "ledger_engine"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_financial_statement_handler",
            "core.application.handlers.financial_statements.GetFinancialStatementHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["financial_statement_repo"]
        )
        container.register(
            "list_financial_statements_handler",
            "core.application.handlers.financial_statements.ListFinancialStatementsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["financial_statement_repo"]
        )
        container.register(
            "get_latest_income_statement_handler",
            "core.application.handlers.financial_statements.GetLatestIncomeStatementHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["financial_statement_repo"]
        )
        container.register(
            "get_latest_balance_sheet_handler",
            "core.application.handlers.financial_statements.GetLatestBalanceSheetHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["financial_statement_repo"]
        )
        # ✅ تم التصحيح: معامل واحد فقط
        container.register(
            "get_financial_ratios_handler",
            "core.application.handlers.financial_statements.GetFinancialRatiosHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["financial_statement_repo"]
        )
        
        # ========== Export Handlers ==========
        container.register(
            "export_financial_statement_handler",
            "core.application.handlers.financial_statements.ExportFinancialStatementHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "print_financial_statement_handler",
            "core.application.handlers.financial_statements.PrintFinancialStatementHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("GenerateIncomeStatementCommand", "generate_income_statement_handler")
                logger.info("✅ Registered GenerateIncomeStatementCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register GenerateIncomeStatementCommand: {e}")
            
            try:
                command_bus.register("GenerateBalanceSheetCommand", "generate_balance_sheet_handler")
                logger.info("✅ Registered GenerateBalanceSheetCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register GenerateBalanceSheetCommand: {e}")
            
            try:
                command_bus.register("GenerateCashFlowCommand", "generate_cash_flow_handler")
                logger.info("✅ Registered GenerateCashFlowCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register GenerateCashFlowCommand: {e}")
            
            try:
                command_bus.register("GenerateEquityStatementCommand", "generate_equity_statement_handler")
                logger.info("✅ Registered GenerateEquityStatementCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register GenerateEquityStatementCommand: {e}")
            
            try:
                command_bus.register("GenerateTrialBalanceCommand", "generate_trial_balance_handler")
                logger.info("✅ Registered GenerateTrialBalanceCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register GenerateTrialBalanceCommand: {e}")
            
            try:
                command_bus.register("ExportFinancialStatementCommand", "export_financial_statement_handler")
                logger.info("✅ Registered ExportFinancialStatementCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ExportFinancialStatementCommand: {e}")
            
            try:
                command_bus.register("PrintFinancialStatementCommand", "print_financial_statement_handler")
                logger.info("✅ Registered PrintFinancialStatementCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register PrintFinancialStatementCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetFinancialStatementQuery", "get_financial_statement_handler")
                logger.info("✅ Registered GetFinancialStatementQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetFinancialStatementQuery: {e}")
            
            try:
                query_bus.register("ListFinancialStatementsQuery", "list_financial_statements_handler")
                logger.info("✅ Registered ListFinancialStatementsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListFinancialStatementsQuery: {e}")
            
            try:
                query_bus.register("GetLatestIncomeStatementQuery", "get_latest_income_statement_handler")
                logger.info("✅ Registered GetLatestIncomeStatementQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetLatestIncomeStatementQuery: {e}")
            
            try:
                query_bus.register("GetLatestBalanceSheetQuery", "get_latest_balance_sheet_handler")
                logger.info("✅ Registered GetLatestBalanceSheetQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetLatestBalanceSheetQuery: {e}")
            
            try:
                query_bus.register("GetFinancialRatiosQuery", "get_financial_ratios_handler")
                logger.info("✅ Registered GetFinancialRatiosQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetFinancialRatiosQuery: {e}")