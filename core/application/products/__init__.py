# core/application/products/__init__.py (النسخة المصححة)

"""
Products Application Layer - Commands, Queries, DTOs
"""

from .commands import (
    CreateProductCommand,
    UpdateProductCommand,
    DeleteProductCommand,
    UpdateStockCommand,
    GetProductQuery,
    GetProductByCodeQuery,
    ListProductsQuery,
    SearchProductsQuery,
    GetLowStockProductsQuery,
)
from .dtos import (
    ProductDTO,
    CreateProductDTO,
    UpdateProductDTO,
    ProductListDTO,
    ProductSummaryDTO,
)

# ❌ لا نستورد handlers من هنا (تم نقلها إلى core.application.handlers.products)
# يتم استيراد الـ Handlers مباشرة من core.application.handlers.products

__all__ = [
    # Commands
    "CreateProductCommand",
    "UpdateProductCommand",
    "DeleteProductCommand",
    "UpdateStockCommand",
    # Queries
    "GetProductQuery",
    "GetProductByCodeQuery",
    "ListProductsQuery",
    "SearchProductsQuery",
    "GetLowStockProductsQuery",
    # DTOs
    "ProductDTO",
    "CreateProductDTO",
    "UpdateProductDTO",
    "ProductListDTO",
    "ProductSummaryDTO",
]