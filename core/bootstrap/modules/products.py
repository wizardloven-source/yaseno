# core/bootstrap/modules/products.py
"""
وحدة المنتجات - تسجيل جميع خدمات المنتجات
مستخرجة من bootstrap.py
"""

import logging  # ✅ إضافة
from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)  # ✅ إضافة


class ProductsModule(Module):
    """وحدة المنتجات - إدارة المنتجات والخدمات"""
    
    name = "products"
    description = "إدارة المنتجات، الأسعار، التصنيفات، والمخزون"
    dependencies = ["database"]
    version = "2.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات المنتجات"""
        
        # ========== Repository ==========
        # ✅ إضافة session كاعتماد
        container.register(
            "product_repo",
            "core.infrastructure.db.postgres.repositories_product.PostgresProductRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]  # ✅ إضافة session
        )
        
        # ========== Services ==========
        container.register(
            "product_service",
            "core.application.products.services.ProductService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["product_repo", "uow"]
        )
        container.register(
            "price_list_service",
            "core.application.pricing.price_list_service.PriceListService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["uow"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_product_handler",
            "core.application.handlers.products.CreateProductHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_product_handler",
            "core.application.handlers.products.UpdateProductHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_product_handler",
            "core.application.handlers.products.DeleteProductHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_stock_handler",
            "core.application.handlers.products.UpdateStockHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Query Handlers ==========
        # ✅ Query Handlers تعتمد على product_repo (الذي يحتاج session)
        container.register(
            "get_product_handler",
            "core.application.handlers.products.GetProductQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["product_repo"]
        )
        container.register(
            "get_product_by_code_handler",
            "core.application.handlers.products.GetProductByCodeQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["product_repo"]
        )
        container.register(
            "list_products_handler",
            "core.application.handlers.products.ListProductsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["product_repo"]
        )
        container.register(
            "search_products_handler",
            "core.application.handlers.products.SearchProductsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["product_repo"]
        )
        container.register(
            "get_low_stock_products_handler",
            "core.application.handlers.products.GetLowStockProductsQueryHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["product_repo"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        # ✅ استخدام النطاق لحل المعالجات التي تعتمد على uow
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            try:
                command_bus.register("CreateProductCommand", "create_product_handler")
                logger.info("✅ Registered CreateProductCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register CreateProductCommand: {e}")
            
            try:
                command_bus.register("UpdateProductCommand", "update_product_handler")
                logger.info("✅ Registered UpdateProductCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateProductCommand: {e}")
            
            try:
                command_bus.register("DeleteProductCommand", "delete_product_handler")
                logger.info("✅ Registered DeleteProductCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register DeleteProductCommand: {e}")
            
            try:
                command_bus.register("UpdateStockCommand", "update_stock_handler")
                logger.info("✅ Registered UpdateStockCommand")
            except Exception as e:
                logger.error(f"❌ Failed to register UpdateStockCommand: {e}")
            
            # ========== Query Handlers ==========
            try:
                query_bus.register("GetProductQuery", "get_product_handler")
                logger.info("✅ Registered GetProductQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetProductQuery: {e}")
            
            try:
                query_bus.register("GetProductByCodeQuery", "get_product_by_code_handler")
                logger.info("✅ Registered GetProductByCodeQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetProductByCodeQuery: {e}")
            
            try:
                query_bus.register("ListProductsQuery", "list_products_handler")
                logger.info("✅ Registered ListProductsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register ListProductsQuery: {e}")
            
            try:
                query_bus.register("SearchProductsQuery", "search_products_handler")
                logger.info("✅ Registered SearchProductsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register SearchProductsQuery: {e}")
            
            try:
                query_bus.register("GetLowStockProductsQuery", "get_low_stock_products_handler")
                logger.info("✅ Registered GetLowStockProductsQuery")
            except Exception as e:
                logger.error(f"❌ Failed to register GetLowStockProductsQuery: {e}")