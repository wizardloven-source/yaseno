"""
وحدة المخزون - تسجيل جميع خدمات المخزون مع التكامل المحاسبي
الإصدار: 2.1.1 - مع دعم التكامل المحاسبي الكامل
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class InventoryModule(Module):
    """
    وحدة المخزون - إدارة المنتجات، الدفعات، والحركات مع التكامل المحاسبي
    
    الميزات:
        1. إدارة حركات المخزون (دخول/خروج)
        2. تتبع الدفعات (Batch/Lot Tracking)
        3. تتبع الأرقام التسلسلية (Serial Numbers)
        4. تحويلات المخزون بين المواقع
        5. ✅ تكامل كامل مع المحاسبة (FIFO, LIFO, Weighted Average)
        6. ✅ حساب COGS تلقائياً
        7. ✅ دعم Optimistic Locking
        8. ✅ دعم العملات المتعددة
    """
    
    name = "inventory"
    description = "إدارة المخزون، الدفعات، الأرقام التسلسلية، والتحويلات مع التكامل المحاسبي"
    dependencies = ["database", "products", "accounting"]
    version = "2.1.1"  # ✅ تحديث الإصدار
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات المخزون"""
        
        # ========== Repositories (Scoped - تعتمد على session) ==========
        container.register_scoped(
            "stock_movement_repo",
            "core.infrastructure.db.postgres.repositories_inventory.PostgresStockMovementRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "stock_batch_repo",
            "core.infrastructure.db.postgres.repositories_inventory.PostgresStockBatchRepository",
            dependencies=["session"]
        )
        container.register_scoped(
            "stock_transfer_repo",
            "core.infrastructure.db.postgres.repositories_inventory.PostgresStockTransferRepository",
            dependencies=["session"]
        )
        
        # ========== Domain Services (Scoped - جلسة لكل طلب) ==========
        container.register_scoped(
            "stock_service",
            "core.domain.inventory.services.StockMovementService",
            dependencies=["stock_movement_repo"]
        )
        container.register_scoped(
            "inventory_valuation_service",
            "core.domain.inventory.services.InventoryValuationService",
            dependencies=["stock_movement_repo"]
        )
        
        # ========== ✅ Integration Service (جديد) ==========
        container.register_scoped(
            "inventory_accounting_integration",
            "core.domain.inventory.integration.InventoryAccountingIntegration",
            dependencies=[
                "uow",
                "posting_engine",
                "product_repo",
                "stock_service",
                "inventory_valuation_service"
            ]
        )
        
        # ========== Stock Movement Handlers (موجود) ==========
        container.register_transient(
            "create_stock_movement_handler",
            "core.application.handlers.inventory.stock_movement_handlers.CreateStockMovementHandler",
            dependencies=["uow", "stock_service"]
        )
        container.register_transient(
            "create_purchase_movement_handler",
            "core.application.handlers.inventory.stock_movement_handlers.CreatePurchaseMovementHandler",
            dependencies=["uow", "stock_service"]
        )
        container.register_transient(
            "create_sale_movement_handler",
            "core.application.handlers.inventory.stock_movement_handlers.CreateSaleMovementHandler",
            dependencies=["uow", "stock_service"]
        )
        container.register_transient(
            "create_adjustment_movement_handler",
            "core.application.handlers.inventory.stock_movement_handlers.CreateAdjustmentMovementHandler",
            dependencies=["uow", "stock_service"]
        )
        
        # ========== ✅ Integration Handlers (جديد) ==========
        container.register_transient(
            "process_sale_handler",
            "core.application.handlers.inventory.integration_handlers.ProcessSaleHandler",
            dependencies=["inventory_accounting_integration"]
        )
        container.register_transient(
            "process_purchase_handler",
            "core.application.handlers.inventory.integration_handlers.ProcessPurchaseHandler",
            dependencies=["inventory_accounting_integration"]
        )
        container.register_transient(
            "process_adjustment_handler",
            "core.application.handlers.inventory.integration_handlers.ProcessAdjustmentHandler",
            dependencies=["inventory_accounting_integration"]
        )
        
        # ========== Stock Batch Handlers ==========
        container.register_transient(
            "create_stock_batch_handler",
            "core.application.handlers.inventory.stock_batch_handlers.CreateStockBatchHandler",
            dependencies=["uow"]
        )
        container.register_transient(
            "consume_stock_batch_handler",
            "core.application.handlers.inventory.stock_batch_handlers.ConsumeStockBatchHandler",
            dependencies=["uow"]
        )
        
        # ========== Stock Transfer Handlers ==========
        container.register_transient(
            "create_stock_transfer_handler",
            "core.application.handlers.inventory.stock_transfer_handlers.CreateStockTransferHandler",
            dependencies=["uow", "stock_service"]
        )
        container.register_transient(
            "complete_stock_transfer_handler",
            "core.application.handlers.inventory.stock_transfer_handlers.CompleteStockTransferHandler",
            dependencies=["uow", "stock_service"]
        )
        
        # ========== Query Handlers ==========
        # ✅ جميع Query Handlers تحتاج إلى uow فقط
        container.register_transient(
            "get_stock_quantity_handler",
            "core.application.handlers.inventory.stock_query_handlers.GetStockQuantityHandler",
            dependencies=["uow"]  # ✅ معامل واحد
        )
        container.register_transient(
            "get_stock_movements_handler",
            "core.application.handlers.inventory.stock_query_handlers.GetStockMovementsHandler",
            dependencies=["uow"]  # ✅ معامل واحد
        )
        # ✅ تم الإصلاح: معامل واحد فقط
        container.register_transient(
            "get_stock_valuation_handler",
            "core.application.handlers.inventory.stock_query_handlers.GetStockValuationHandler",
            dependencies=["uow"]  # ✅ معامل واحد (تم إزالة inventory_valuation_service)
        )
        container.register_transient(
            "get_low_stock_handler",
            "core.application.handlers.inventory.stock_query_handlers.GetLowStockHandler",
            dependencies=["uow"]  # ✅ معامل واحد
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """
        تسجيل Handlers في Command/Query Bus
        
        ✅ محدث: إضافة Integration Handlers
        """
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            
            # =================================================================
            # Stock Movement Command Handlers
            # =================================================================
            try:
                command_bus.register("CreateStockMovementCommand", "create_stock_movement_handler")
                logger.info("✅ Registered CreateStockMovementCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateStockMovementCommand: {e}")
            
            try:
                command_bus.register("CreatePurchaseMovementCommand", "create_purchase_movement_handler")
                logger.info("✅ Registered CreatePurchaseMovementCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreatePurchaseMovementCommand: {e}")
            
            try:
                command_bus.register("CreateSaleMovementCommand", "create_sale_movement_handler")
                logger.info("✅ Registered CreateSaleMovementCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateSaleMovementCommand: {e}")
            
            try:
                command_bus.register("CreateAdjustmentMovementCommand", "create_adjustment_movement_handler")
                logger.info("✅ Registered CreateAdjustmentMovementCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateAdjustmentMovementCommand: {e}")
            
            # =================================================================
            # ✅ Integration Command Handlers (جديد)
            # =================================================================
            try:
                command_bus.register("ProcessSaleCommand", "process_sale_handler")
                logger.info("✅ Registered ProcessSaleCommand (with accounting integration)")
            except Exception as e:
                logger.error(f"❌ Failed to register ProcessSaleCommand: {e}")
            
            try:
                command_bus.register("ProcessPurchaseCommand", "process_purchase_handler")
                logger.info("✅ Registered ProcessPurchaseCommand (with accounting integration)")
            except Exception as e:
                logger.error(f"❌ Failed to register ProcessPurchaseCommand: {e}")
            
            try:
                command_bus.register("ProcessAdjustmentCommand", "process_adjustment_handler")
                logger.info("✅ Registered ProcessAdjustmentCommand (with accounting integration)")
            except Exception as e:
                logger.error(f"❌ Failed to register ProcessAdjustmentCommand: {e}")
            
            # =================================================================
            # Stock Batch Command Handlers
            # =================================================================
            try:
                command_bus.register("CreateStockBatchCommand", "create_stock_batch_handler")
                logger.info("✅ Registered CreateStockBatchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateStockBatchCommand: {e}")
            
            try:
                command_bus.register("ConsumeStockBatchCommand", "consume_stock_batch_handler")
                logger.info("✅ Registered ConsumeStockBatchCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register ConsumeStockBatchCommand: {e}")
            
            # =================================================================
            # Stock Transfer Command Handlers
            # =================================================================
            try:
                command_bus.register("CreateStockTransferCommand", "create_stock_transfer_handler")
                logger.info("✅ Registered CreateStockTransferCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateStockTransferCommand: {e}")
            
            try:
                command_bus.register("CompleteStockTransferCommand", "complete_stock_transfer_handler")
                logger.info("✅ Registered CompleteStockTransferCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CompleteStockTransferCommand: {e}")
            
            # =================================================================
            # Query Handlers
            # =================================================================
            try:
                query_bus.register("GetStockQuantityQuery", "get_stock_quantity_handler")
                logger.info("✅ Registered GetStockQuantityQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetStockQuantityQuery: {e}")
            
            try:
                query_bus.register("GetStockMovementsQuery", "get_stock_movements_handler")
                logger.info("✅ Registered GetStockMovementsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetStockMovementsQuery: {e}")
            
            try:
                query_bus.register("GetStockValuationQuery", "get_stock_valuation_handler")
                logger.info("✅ Registered GetStockValuationQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetStockValuationQuery: {e}")
            
            try:
                query_bus.register("GetLowStockQuery", "get_low_stock_handler")
                logger.info("✅ Registered GetLowStockQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetLowStockQuery: {e}")