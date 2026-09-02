# core/application/handlers/products/__init__.py

"""
Products Handlers - Organized by use case
"""

from .create_product_handler import CreateProductHandler
from .update_product_handler import UpdateProductHandler
from .delete_product_handler import DeleteProductHandler
from .update_stock_handler import UpdateStockHandler
from .get_product_query_handler import GetProductQueryHandler
from .get_product_by_code_query_handler import GetProductByCodeQueryHandler
from .list_products_query_handler import ListProductsQueryHandler
from .search_products_query_handler import SearchProductsQueryHandler
from .get_low_stock_products_query_handler import GetLowStockProductsQueryHandler

__all__ = [
    "CreateProductHandler",
    "UpdateProductHandler",
    "DeleteProductHandler",
    "UpdateStockHandler",
    "GetProductQueryHandler",
    "GetProductByCodeQueryHandler",
    "ListProductsQueryHandler",
    "SearchProductsQueryHandler",
    "GetLowStockProductsQueryHandler",
]