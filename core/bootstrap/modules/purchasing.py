# core/bootstrap/modules/purchasing.py
"""
وحدة المشتريات - تسجيل جميع خدمات المشتريات
مستخرجة من bootstrap.py
"""

import logging
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class PurchasingModule(Module):
    """وحدة المشتريات - إدارة أوامر الشراء والموردين"""
    
    name = "purchasing"
    description = "إدارة أوامر الشراء، الاستلام، والموردين"
    dependencies = ["database", "accounting", "inventory", "suppliers"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات المشتريات"""
        
        # ========== Repositories ==========
        # ✅ التصحيح: إضافة session كاعتماد
        container.register(
            "purchase_order_repo",
            "core.infrastructure.db.postgres.repositories_purchase_order.PostgresPurchaseOrderRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ هذه هي الإضافة المطلوبة
        )
        container.register(
            "purchase_order_line_repo",
            "core.infrastructure.db.postgres.repositories_purchase_order.PostgresPurchaseOrderLineRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ هذه هي الإضافة المطلوبة
        )
        
        # ========== Services ==========
        container.register(
            "purchasing_service",
            "core.application.purchasing.services.PurchasingService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["purchase_order_repo", "uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_purchase_order_handler",
            "core.application.handlers.purchasing.CreatePurchaseOrderHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "add_purchase_line_handler",
            "core.application.handlers.purchasing.AddPurchaseLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_purchase_line_handler",
            "core.application.handlers.purchasing.UpdatePurchaseLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "remove_purchase_line_handler",
            "core.application.handlers.purchasing.RemovePurchaseLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "clear_purchase_lines_handler",
            "core.application.handlers.purchasing.ClearPurchaseLinesHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "post_purchase_order_handler",
            "core.application.handlers.purchasing.PostPurchaseOrderHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow", "accounting_orchestrator", "posting_engine"]
        )
        container.register(
            "delete_draft_purchase_order_handler",
            "core.application.handlers.purchasing.DeleteDraftPurchaseOrderHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "receive_purchase_line_handler",
            "core.application.handlers.purchasing.ReceivePurchaseLineHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "receive_purchase_order_handler",
            "core.application.handlers.purchasing.ReceivePurchaseOrderHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_purchase_order_handler",
            "core.application.handlers.purchasing.GetPurchaseOrderQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["purchase_order_repo"]  # ✅ هذا سيعمل الآن لأن purchase_order_repo له session
        )
        container.register(
            "list_purchase_orders_handler",
            "core.application.handlers.purchasing.ListPurchaseOrdersQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["purchase_order_repo"]
        )
        container.register(
            "get_supplier_orders_handler",
            "core.application.handlers.purchasing.GetSupplierOrdersQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["purchase_order_repo"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreatePurchaseOrderCommand", "create_purchase_order_handler")
                logger.info("✅ Registered CreatePurchaseOrderCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreatePurchaseOrderCommand: {e}")
            
            try:
                command_bus.register("AddPurchaseLineCommand", "add_purchase_line_handler")
                logger.info("✅ Registered AddPurchaseLineCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register AddPurchaseLineCommand: {e}")
            
            try:
                command_bus.register("UpdatePurchaseLineCommand", "update_purchase_line_handler")
                logger.info("✅ Registered UpdatePurchaseLineCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdatePurchaseLineCommand: {e}")
            
            try:
                command_bus.register("RemovePurchaseLineCommand", "remove_purchase_line_handler")
                logger.info("✅ Registered RemovePurchaseLineCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register RemovePurchaseLineCommand: {e}")
            
            try:
                command_bus.register("ClearPurchaseLinesCommand", "clear_purchase_lines_handler")
                logger.info("✅ Registered ClearPurchaseLinesCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ClearPurchaseLinesCommand: {e}")
            
            try:
                command_bus.register("PostPurchaseOrderCommand", "post_purchase_order_handler")
                logger.info("✅ Registered PostPurchaseOrderCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register PostPurchaseOrderCommand: {e}")
            
            try:
                command_bus.register("DeleteDraftPurchaseOrderCommand", "delete_draft_purchase_order_handler")
                logger.info("✅ Registered DeleteDraftPurchaseOrderCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteDraftPurchaseOrderCommand: {e}")
            
            try:
                command_bus.register("ReceivePurchaseLineCommand", "receive_purchase_line_handler")
                logger.info("✅ Registered ReceivePurchaseLineCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ReceivePurchaseLineCommand: {e}")
            
            try:
                command_bus.register("ReceivePurchaseOrderCommand", "receive_purchase_order_handler")
                logger.info("✅ Registered ReceivePurchaseOrderCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ReceivePurchaseOrderCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetPurchaseOrderQuery", "get_purchase_order_handler")
                logger.info("✅ Registered GetPurchaseOrderQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetPurchaseOrderQuery: {e}")
            
            try:
                query_bus.register("ListPurchaseOrdersQuery", "list_purchase_orders_handler")
                logger.info("✅ Registered ListPurchaseOrdersQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListPurchaseOrdersQuery: {e}")
            
            try:
                query_bus.register("GetSupplierOrdersQuery", "get_supplier_orders_handler")
                logger.info("✅ Registered GetSupplierOrdersQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetSupplierOrdersQuery: {e}")