# core/bootstrap/modules/centers.py
"""
وحدة مراكز التكلفة - تسجيل جميع خدمات مراكز التكلفة والربح
مستخرجة من bootstrap.py
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class CentersModule(Module):
    """وحدة مراكز التكلفة - إدارة مراكز التكلفة والربح والتوزيع"""
    
    name = "centers"
    description = "إدارة مراكز التكلفة والربح، التوزيع، والميزانيات"
    dependencies = ["database", "accounting"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات مراكز التكلفة"""
        
        # ========== Repositories ==========
        container.register(
            "center_repo",
            "core.infrastructure.db.postgres.center_repository.PostgresCenterRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        container.register(
            "allocation_repo",
            "core.infrastructure.db.postgres.center_repository.PostgresAllocationRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        container.register(
            "allocation_rule_repo",
            "core.infrastructure.db.postgres.center_repository.PostgresAllocationRuleRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== Services ==========
        container.register(
            "center_service",
            "core.domain.centers.services.CenterService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["center_repo", "allocation_repo", "allocation_rule_repo"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_center_handler",
            "core.application.handlers.centers.CreateCenterHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_center_handler",
            "core.application.handlers.centers.UpdateCenterHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "activate_center_handler",
            "core.application.handlers.centers.ActivateCenterHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "suspend_center_handler",
            "core.application.handlers.centers.SuspendCenterHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "close_center_handler",
            "core.application.handlers.centers.CloseCenterHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_center_handler",
            "core.application.handlers.centers.DeleteCenterHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "create_allocation_handler",
            "core.application.handlers.centers.CreateAllocationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "post_allocation_handler",
            "core.application.handlers.centers.PostAllocationHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]  # ✅ معامل واحد فقط (posting_engine اختياري)
        )
        
        # ========== Query Handlers ==========
        # ✅ جميع Query Handlers تعتمد على uow (متوافق مع BaseQueryHandler)
        container.register(
            "get_center_handler",
            "core.application.handlers.centers.GetCenterHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "list_centers_handler",
            "core.application.handlers.centers.ListCentersHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_center_tree_handler",
            "core.application.handlers.centers.GetCenterTreeHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_center_summary_handler",
            "core.application.handlers.centers.GetCenterSummaryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]  # ✅ متوافق مع المُنشئ الحالي
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreateCenterCommand", "create_center_handler")
                logger.info("✅ Registered CreateCenterCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateCenterCommand: {e}")
            
            try:
                command_bus.register("UpdateCenterCommand", "update_center_handler")
                logger.info("✅ Registered UpdateCenterCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateCenterCommand: {e}")
            
            try:
                command_bus.register("ActivateCenterCommand", "activate_center_handler")
                logger.info("✅ Registered ActivateCenterCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ActivateCenterCommand: {e}")
            
            try:
                command_bus.register("SuspendCenterCommand", "suspend_center_handler")
                logger.info("✅ Registered SuspendCenterCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register SuspendCenterCommand: {e}")
            
            try:
                command_bus.register("CloseCenterCommand", "close_center_handler")
                logger.info("✅ Registered CloseCenterCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CloseCenterCommand: {e}")
            
            try:
                command_bus.register("DeleteCenterCommand", "delete_center_handler")
                logger.info("✅ Registered DeleteCenterCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteCenterCommand: {e}")
            
            try:
                command_bus.register("CreateAllocationCommand", "create_allocation_handler")
                logger.info("✅ Registered CreateAllocationCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateAllocationCommand: {e}")
            
            try:
                command_bus.register("PostAllocationCommand", "post_allocation_handler")
                logger.info("✅ Registered PostAllocationCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register PostAllocationCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetCenterQuery", "get_center_handler")
                logger.info("✅ Registered GetCenterQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCenterQuery: {e}")
            
            try:
                query_bus.register("ListCentersQuery", "list_centers_handler")
                logger.info("✅ Registered ListCentersQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListCentersQuery: {e}")
            
            try:
                query_bus.register("GetCenterTreeQuery", "get_center_tree_handler")
                logger.info("✅ Registered GetCenterTreeQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCenterTreeQuery: {e}")
            
            try:
                query_bus.register("GetCenterSummaryQuery", "get_center_summary_handler")
                logger.info("✅ Registered GetCenterSummaryQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetCenterSummaryQuery: {e}")