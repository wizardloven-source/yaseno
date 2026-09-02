# core/bootstrap/modules/fixed_assets.py
"""
وحدة الأصول الثابتة - تسجيل خدمات الأصول الثابتة والإهلاك
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class FixedAssetsModule(Module):
    """وحدة الأصول الثابتة - إدارة الأصول الثابتة والإهلاك والتخلص"""

    name = "fixed_assets"
    description = "إدارة الأصول الثابتة، حساب الإهلاك، والتخلص من الأصول"
    dependencies = ["database", "accounting"]
    version = "1.0.0"

    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الأصول الثابتة"""

        # ========== Repositories ==========
        container.register(
            "fixed_asset_repo",
            "core.infrastructure.db.postgres.fixed_asset_repository.PostgresFixedAssetRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )

        # ========== Services ==========
        container.register(
            "asset_service",
            "core.domain.fixed_assets.services.FixedAssetService",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["uow", "posting_engine"]
        )

        # ========== Command Handlers ==========
        container.register(
            "create_asset_handler",
            "core.application.handlers.fixed_assets.CreateFixedAssetHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "asset_service"]
        )
        container.register(
            "dispose_asset_handler",
            "core.application.handlers.fixed_assets.DisposeFixedAssetHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "asset_service"]
        )
        container.register(
            "post_depreciation_handler",
            "core.application.handlers.fixed_assets.PostDepreciationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "asset_service"]
        )
        container.register(
            "run_monthly_depreciation_handler",
            "core.application.handlers.fixed_assets.RunMonthlyDepreciationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "asset_service"]
        )

        # ========== Query Handlers ==========
        container.register(
            "get_asset_query_handler",
            "core.application.handlers.fixed_assets.GetFixedAssetQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["asset_service"]
        )
        container.register(
            "list_assets_query_handler",
            "core.application.handlers.fixed_assets.ListFixedAssetsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["asset_service"]
        )

    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")

        # ✅ استخدام النطاق لحل المعالجات
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreateFixedAssetCommand", "create_asset_handler")
                logger.info("✅ Registered CreateFixedAssetCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateFixedAssetCommand: {e}")

            try:
                command_bus.register("DisposeFixedAssetCommand", "dispose_asset_handler")
                logger.info("✅ Registered DisposeFixedAssetCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DisposeFixedAssetCommand: {e}")

            try:
                command_bus.register("PostDepreciationCommand", "post_depreciation_handler")
                logger.info("✅ Registered PostDepreciationCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register PostDepreciationCommand: {e}")

            try:
                command_bus.register("RunMonthlyDepreciationCommand", "run_monthly_depreciation_handler")
                logger.info("✅ Registered RunMonthlyDepreciationCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register RunMonthlyDepreciationCommand: {e}")

            # ========== Query Handlers ==========
            try:
                query_bus.register("GetFixedAssetQuery", "get_asset_query_handler")
                logger.info("✅ Registered GetFixedAssetQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetFixedAssetQuery: {e}")

            try:
                query_bus.register("ListFixedAssetsQuery", "list_assets_query_handler")
                logger.info("✅ Registered ListFixedAssetsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListFixedAssetsQuery: {e}")