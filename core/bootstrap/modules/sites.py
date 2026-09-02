# core/bootstrap/modules/sites.py
"""
وحدة المواقع - تسجيل جميع خدمات المواقع
مستخرجة من bootstrap.py
"""

import logging  # ✅ إضافة
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)  # ✅ إضافة


class SitesModule(Module):
    """
    وحدة المواقع - إدارة المواقع والفروع
    
    تشمل:
        1. مواقع متعددة (مستودعات، فروع، مكاتب)
        2. إعدادات خاصة بكل موقع (عملة، عنوان، مسؤول)
        3. ربط المواقع بالعملاء والموردين
        4. تقارير الأداء حسب الموقع
    """
    
    name = "sites"
    description = "إدارة المواقع والفروع - مستودعات، فروع، مكاتب"
    dependencies = ["database", "customers", "suppliers", "currency"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات المواقع"""
        
        # ========== Repository ==========
        # ✅ إضافة session كاعتماد
        container.register(
            "site_repo",
            "core.infrastructure.db.postgres.site_repository.PostgresSiteRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ إضافة session
        )
        
        # ========== Services ==========
        container.register(
            "site_service",
            "core.application.sites.services.SiteService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["site_repo", "uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_site_handler",
            "core.application.handlers.sites.CreateSiteHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_site_handler",
            "core.application.handlers.sites.UpdateSiteHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_site_handler",
            "core.application.handlers.sites.DeleteSiteHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "set_default_site_handler",
            "core.application.handlers.sites.SetDefaultSiteHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_site_handler",
            "core.application.handlers.sites.GetSiteQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "list_sites_handler",
            "core.application.handlers.sites.ListSitesQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_default_site_handler",
            "core.application.handlers.sites.GetDefaultSiteQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_site_statistics_handler",
            "core.application.handlers.sites.GetSiteStatisticsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "search_sites_handler",
            "core.application.handlers.sites.SearchSitesQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_sites_for_combo_handler",
            "core.application.handlers.sites.GetSitesForComboQueryHandler",
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
                command_bus.register("CreateSiteCommand", "create_site_handler")
                logger.info("✅ Registered CreateSiteCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateSiteCommand: {e}")
            
            try:
                command_bus.register("UpdateSiteCommand", "update_site_handler")
                logger.info("✅ Registered UpdateSiteCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateSiteCommand: {e}")
            
            try:
                command_bus.register("DeleteSiteCommand", "delete_site_handler")
                logger.info("✅ Registered DeleteSiteCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteSiteCommand: {e}")
            
            try:
                command_bus.register("SetDefaultSiteCommand", "set_default_site_handler")
                logger.info("✅ Registered SetDefaultSiteCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register SetDefaultSiteCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetSiteQuery", "get_site_handler")
                logger.info("✅ Registered GetSiteQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSiteQuery: {e}")
            
            try:
                query_bus.register("ListSitesQuery", "list_sites_handler")
                logger.info("✅ Registered ListSitesQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListSitesQuery: {e}")
            
            try:
                query_bus.register("GetDefaultSiteQuery", "get_default_site_handler")
                logger.info("✅ Registered GetDefaultSiteQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetDefaultSiteQuery: {e}")
            
            try:
                query_bus.register("GetSiteStatisticsQuery", "get_site_statistics_handler")
                logger.info("✅ Registered GetSiteStatisticsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSiteStatisticsQuery: {e}")
            
            try:
                query_bus.register("SearchSitesQuery", "search_sites_handler")
                logger.info("✅ Registered SearchSitesQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register SearchSitesQuery: {e}")
            
            try:
                query_bus.register("GetSitesForComboQuery", "get_sites_for_combo_handler")
                logger.info("✅ Registered GetSitesForComboQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSitesForComboQuery: {e}")