# core/bootstrap/modules/tax.py
"""
وحدة الضرائب - تسجيل جميع خدمات الضرائب
مستخرجة من bootstrap.py
"""

import logging  # ✅ إضافة
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)  # ✅ إضافة


class TaxModule(Module):
    """
    وحدة الضرائب - محرك الضرائب المتقدم
    
    تشمل:
        1. قواعد ضريبية متعددة (VAT, GST, Sales Tax, Excise)
        2. أنماط حساب (Inclusive, Exclusive, Compound)
        3. إعفاءات ضريبية
        4. مجموعات ضريبية
        5. فترات ضريبية
        6. تقارير الضرائب
    """
    
    name = "tax"
    description = "محرك الضرائب - VAT، GST، إعفاءات، وتقارير ضريبية"
    dependencies = ["database", "accounting", "invoicing", "products"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الضرائب"""
        
        # ========== Repositories ==========
        # ✅ إضافة session كاعتماد لجميع Repositories
        container.register(
            "tax_repo",
            "core.infrastructure.db.postgres.tax_repository.PostgresTaxRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ إضافة session
        )
        container.register(
            "tax_group_repo",
            "core.infrastructure.db.postgres.tax_repository.PostgresTaxGroupRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ إضافة session
        )
        container.register(
            "tax_exemption_repo",
            "core.infrastructure.db.postgres.tax_repository.PostgresTaxExemptionRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ إضافة session
        )
        container.register(
            "tax_period_repo",
            "core.infrastructure.db.postgres.tax_repository.PostgresTaxPeriodRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ إضافة session
        )
        
        # ========== Domain Services ==========
        container.register(
            "tax_engine",
            "core.domain.tax.services.TaxEngine",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["tax_repo", "tax_group_repo", "tax_exemption_repo"]
        )
        container.register(
            "tax_calculator",
            "core.domain.tax.services.TaxCalculator",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["tax_engine"]
        )
        
        # ========== Application Services ==========
        container.register(
            "tax_service",
            "core.application.tax.services.TaxService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["tax_repo", "tax_engine", "uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_tax_rule_handler",
            "core.application.handlers.tax.CreateTaxRuleHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_tax_rule_handler",
            "core.application.handlers.tax.UpdateTaxRuleHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_tax_rule_handler",
            "core.application.handlers.tax.DeleteTaxRuleHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "create_tax_exemption_handler",
            "core.application.handlers.tax.CreateTaxExemptionHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_tax_exemption_handler",
            "core.application.handlers.tax.UpdateTaxExemptionHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_tax_exemption_handler",
            "core.application.handlers.tax.DeleteTaxExemptionHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "close_tax_period_handler",
            "core.application.handlers.tax.CloseTaxPeriodHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_tax_rule_handler",
            "core.application.handlers.tax.GetTaxRuleQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "list_tax_rules_handler",
            "core.application.handlers.tax.ListTaxRulesQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_tax_exemption_handler",
            "core.application.handlers.tax.GetTaxExemptionQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "list_tax_exemptions_handler",
            "core.application.handlers.tax.ListTaxExemptionsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_tax_period_handler",
            "core.application.handlers.tax.GetTaxPeriodQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "list_tax_periods_handler",
            "core.application.handlers.tax.ListTaxPeriodsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "calculate_tax_handler",
            "core.application.handlers.tax.CalculateTaxQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["tax_engine"]
        )
        container.register(
            "get_tax_report_handler",
            "core.application.handlers.tax.GetTaxReportQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["tax_repo", "tax_period_repo", "ledger_engine"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreateTaxRuleCommand", "create_tax_rule_handler")
                logger.info("✅ Registered CreateTaxRuleCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateTaxRuleCommand: {e}")
            
            try:
                command_bus.register("UpdateTaxRuleCommand", "update_tax_rule_handler")
                logger.info("✅ Registered UpdateTaxRuleCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateTaxRuleCommand: {e}")
            
            try:
                command_bus.register("DeleteTaxRuleCommand", "delete_tax_rule_handler")
                logger.info("✅ Registered DeleteTaxRuleCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteTaxRuleCommand: {e}")
            
            try:
                command_bus.register("CreateTaxExemptionCommand", "create_tax_exemption_handler")
                logger.info("✅ Registered CreateTaxExemptionCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateTaxExemptionCommand: {e}")
            
            try:
                command_bus.register("UpdateTaxExemptionCommand", "update_tax_exemption_handler")
                logger.info("✅ Registered UpdateTaxExemptionCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateTaxExemptionCommand: {e}")
            
            try:
                command_bus.register("DeleteTaxExemptionCommand", "delete_tax_exemption_handler")
                logger.info("✅ Registered DeleteTaxExemptionCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteTaxExemptionCommand: {e}")
            
            try:
                command_bus.register("CloseTaxPeriodCommand", "close_tax_period_handler")
                logger.info("✅ Registered CloseTaxPeriodCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CloseTaxPeriodCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetTaxRuleQuery", "get_tax_rule_handler")
                logger.info("✅ Registered GetTaxRuleQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetTaxRuleQuery: {e}")
            
            try:
                query_bus.register("ListTaxRulesQuery", "list_tax_rules_handler")
                logger.info("✅ Registered ListTaxRulesQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListTaxRulesQuery: {e}")
            
            try:
                query_bus.register("GetTaxExemptionQuery", "get_tax_exemption_handler")
                logger.info("✅ Registered GetTaxExemptionQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetTaxExemptionQuery: {e}")
            
            try:
                query_bus.register("ListTaxExemptionsQuery", "list_tax_exemptions_handler")
                logger.info("✅ Registered ListTaxExemptionsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListTaxExemptionsQuery: {e}")
            
            try:
                query_bus.register("GetTaxPeriodQuery", "get_tax_period_handler")
                logger.info("✅ Registered GetTaxPeriodQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetTaxPeriodQuery: {e}")
            
            try:
                query_bus.register("ListTaxPeriodsQuery", "list_tax_periods_handler")
                logger.info("✅ Registered ListTaxPeriodsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListTaxPeriodsQuery: {e}")
            
            try:
                query_bus.register("CalculateTaxQuery", "calculate_tax_handler")
                logger.info("✅ Registered CalculateTaxQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register CalculateTaxQuery: {e}")
            
            try:
                query_bus.register("GetTaxReportQuery", "get_tax_report_handler")
                logger.info("✅ Registered GetTaxReportQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetTaxReportQuery: {e}")