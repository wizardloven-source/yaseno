# core/bootstrap/modules/suppliers.py
"""
وحدة الموردين - تسجيل جميع خدمات الموردين
مستخرجة من bootstrap.py
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class SuppliersModule(Module):
    """وحدة الموردين - إدارة الموردين والتقييم"""
    
    name = "suppliers"
    description = "إدارة الموردين، التقييم، الائتمان، وتاريخ المعاملات"
    dependencies = ["database"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات الموردين"""
        
        # ========== Repository ==========
        container.register(
            "supplier_repo",
            "core.infrastructure.db.postgres.supplier_repository.PostgresSupplierRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== Services ==========
        container.register(
            "supplier_service",
            "core.application.suppliers.services.SupplierService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["supplier_repo", "uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_supplier_handler",
            "core.application.handlers.suppliers.CreateSupplierHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_supplier_handler",
            "core.application.handlers.suppliers.UpdateSupplierHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "change_supplier_status_handler",
            "core.application.handlers.suppliers.ChangeSupplierStatusHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_supplier_handler",
            "core.application.handlers.suppliers.DeleteSupplierHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_supplier_handler",
            "core.application.handlers.suppliers.GetSupplierQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["supplier_repo"]
        )
        container.register(
            "list_suppliers_handler",
            "core.application.handlers.suppliers.ListSuppliersQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["supplier_repo"]
        )
        container.register(
            "search_suppliers_handler",
            "core.application.handlers.suppliers.SearchSuppliersQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["supplier_repo"]
        )
        
        # ✅ ✅ ✅ الإصلاح: معامل واحد فقط (uow)
        container.register(
            "get_supplier_statement_handler",
            "core.application.handlers.suppliers.GetSupplierStatementQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]  # ✅ معامل واحد فقط
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreateSupplierCommand", "create_supplier_handler")
                logger.info("✅ Registered CreateSupplierCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateSupplierCommand: {e}")
            
            try:
                command_bus.register("UpdateSupplierCommand", "update_supplier_handler")
                logger.info("✅ Registered UpdateSupplierCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateSupplierCommand: {e}")
            
            try:
                command_bus.register("ChangeSupplierStatusCommand", "change_supplier_status_handler")
                logger.info("✅ Registered ChangeSupplierStatusCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ChangeSupplierStatusCommand: {e}")
            
            try:
                command_bus.register("DeleteSupplierCommand", "delete_supplier_handler")
                logger.info("✅ Registered DeleteSupplierCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteSupplierCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetSupplierQuery", "get_supplier_handler")
                logger.info("✅ Registered GetSupplierQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSupplierQuery: {e}")
            
            try:
                query_bus.register("ListSuppliersQuery", "list_suppliers_handler")
                logger.info("✅ Registered ListSuppliersQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListSuppliersQuery: {e}")
            
            try:
                query_bus.register("SearchSuppliersQuery", "search_suppliers_handler")
                logger.info("✅ Registered SearchSuppliersQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register SearchSuppliersQuery: {e}")
            
            # ✅ ✅ ✅ الإصلاح: تسجيل GetSupplierStatementQuery مع uow فقط
            try:
                query_bus.register("GetSupplierStatementQuery", "get_supplier_statement_handler")
                logger.info("✅ Registered GetSupplierStatementQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSupplierStatementQuery: {e}")