# core/bootstrap/modules/settings.py
"""
وحدة الإعدادات - تسجيل جميع خدمات الإعدادات
مستخرجة من bootstrap.py
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class SettingsModule(Module):
    """وحدة الإعدادات - إدارة إعدادات النظام"""
    
    name = "settings"
    description = "إدارة إعدادات النظام، واجهة المستخدم، الطباعة، والنسخ الاحتياطي"
    dependencies = ["database"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الإعدادات"""
        
        # ========== Repository ==========
        container.register(
            "settings_repo",
            "core.infrastructure.db.postgres.settings_repository.PostgresSettingsRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ تم الإصلاح
        )
        
        # ========== Services ==========
        container.register(
            "settings_service",
            "core.application.settings.services.SettingsService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["settings_repo", "uow"]
        )
        container.register(
            "accounting_settings_service",
            "core.application.settings.accounting_settings_service.AccountingSettingsService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["uow"]
        )
        
        # ========== Handlers ==========
        container.register(
            "get_settings_handler",
            "core.application.handlers.settings.GetSettingsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_settings_handler",
            "core.application.handlers.settings.UpdateSettingsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_ui_settings_handler",
            "core.application.handlers.settings.GetUiSettingsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_ui_settings_handler",
            "core.application.handlers.settings.UpdateUiSettingsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "export_settings_handler",
            "core.application.handlers.settings.ExportSettingsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "import_settings_handler",
            "core.application.handlers.settings.ImportSettingsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_settings_query_handler",
            "core.application.handlers.settings.GetSettingsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_ui_settings_query_handler",
            "core.application.handlers.settings.GetUiSettingsQueryHandler",
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
                command_bus.register("UpdateAllSettingsCommand", "update_settings_handler")
                logger.info("✅ Registered UpdateAllSettingsCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateSettingsCommand: {e}")
            
            try:
                command_bus.register("UpdateUiSettingsCommand", "update_ui_settings_handler")
                logger.info("✅ Registered UpdateUiSettingsCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateUiSettingsCommand: {e}")
            
            try:
                command_bus.register("ExportSettingsCommand", "export_settings_handler")
                logger.info("✅ Registered ExportSettingsCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ExportSettingsCommand: {e}")
            
            try:
                command_bus.register("ImportSettingsCommand", "import_settings_handler")
                logger.info("✅ Registered ImportSettingsCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ImportSettingsCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetSettingsQuery", "get_settings_query_handler")
                logger.info("✅ Registered GetSettingsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSettingsQuery: {e}")
            
            try:
                query_bus.register("GetUiSettingsQuery", "get_ui_settings_query_handler")
                logger.info("✅ Registered GetUiSettingsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetUiSettingsQuery: {e}")