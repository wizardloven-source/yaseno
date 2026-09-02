"""
وحدة السنة المالية - تسجيل جميع خدمات السنة المالية
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class FiscalModule(Module):
    """وحدة السنة المالية - إدارة السنوات والفترات المالية"""
    
    name = "fiscal"
    description = "إدارة السنوات المالية، الفترات، والإقفال"
    dependencies = ["database"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات السنة المالية"""
        
        # ========== Repositories (Scoped) ==========
        container.register_scoped(
            "fiscal_year_repo",
            "core.infrastructure.db.postgres.fiscal_repository.PostgresFiscalYearRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "fiscal_period_repo",
            "core.infrastructure.db.postgres.fiscal_repository.PostgresFiscalPeriodRepository",
            dependencies=["session"]
        )
        
        # ========== Services (Scoped - جلسة لكل طلب) ==========
        container.register_scoped(
            "fiscal_service",
            "core.domain.fiscal.services.FiscalYearService",
            dependencies=["fiscal_year_repo"]
        )
        
        # ========== Handlers (Transient) ==========
        # ✅ إعادة تفعيل Handlers بعد إنشاء الملفات
        container.register_transient(
            "create_fiscal_year_handler",
            "core.application.handlers.fiscal.CreateFiscalYearHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "update_fiscal_year_handler",
            "core.application.handlers.fiscal.UpdateFiscalYearHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "close_fiscal_year_handler",
            "core.application.handlers.fiscal.CloseFiscalYearHandler",
            dependencies=["uow", "closing_service"]
        )
        container.register_transient(
            "open_fiscal_year_handler",
            "core.application.handlers.fiscal.OpenFiscalYearHandler",
            dependencies=["uow"]
        )
        
        # ========== Query Handlers (Transient) ==========
        container.register_transient(
            "get_fiscal_year_handler",
            "core.application.handlers.fiscal.GetFiscalYearHandler",
            dependencies=["fiscal_year_repo"]
        )
        container.register_transient(
            "list_fiscal_years_handler",
            "core.application.handlers.fiscal.ListFiscalYearsHandler",
            dependencies=["fiscal_year_repo"]
        )
        container.register_transient(
            "get_current_fiscal_year_handler",
            "core.application.handlers.fiscal.GetCurrentFiscalYearHandler",
            dependencies=["fiscal_year_repo"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreateFiscalYearCommand", "create_fiscal_year_handler")
                logger.info("✅ Registered CreateFiscalYearCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateFiscalYearCommand: {e}")
            
            try:
                command_bus.register("UpdateFiscalYearCommand", "update_fiscal_year_handler")
                logger.info("✅ Registered UpdateFiscalYearCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateFiscalYearCommand: {e}")
            
            try:
                command_bus.register("CloseFiscalYearCommand", "close_fiscal_year_handler")
                logger.info("✅ Registered CloseFiscalYearCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CloseFiscalYearCommand: {e}")
            
            try:
                command_bus.register("OpenFiscalYearCommand", "open_fiscal_year_handler")
                logger.info("✅ Registered OpenFiscalYearCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register OpenFiscalYearCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetFiscalYearQuery", "get_fiscal_year_handler")
                logger.info("✅ Registered GetFiscalYearQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetFiscalYearQuery: {e}")
            
            try:
                query_bus.register("ListFiscalYearsQuery", "list_fiscal_years_handler")
                logger.info("✅ Registered ListFiscalYearsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListFiscalYearsQuery: {e}")
            
            try:
                query_bus.register("GetCurrentFiscalYearQuery", "get_current_fiscal_year_handler")
                logger.info("✅ Registered GetCurrentFiscalYearQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCurrentFiscalYearQuery: {e}")