# core/domain/products/__init__.py
"""
Products Bounded Context - Product Management Module
نظام إدارة المنتجات - متكامل مع المحاسبة والمخزون
"""

from .entities import Product
from .value_objects import ProductId, ProductCode, ProductStatus, StockMovementType
from .events import (
    ProductCreatedEvent,
    ProductUpdatedEvent,
    ProductDeletedEvent,
    ProductReactivatedEvent,
    StockUpdatedEvent,
    LowStockAlertEvent,
    OutOfStockEvent,
)
from .exceptions import (
    ProductError,
    ProductNotFoundError,
    DuplicateCodeError,
    InvalidProductCodeError,
    InvalidStockQuantityError,
    ProductAlreadyActiveError,
    ProductAlreadyInactiveError,
    NegativeStockNotAllowedError,
    InsufficientStockError,
)
from .interfaces import IProductRepository

__all__ = [
    # Entities
    "Product",
    # Value Objects
    "ProductId",
    "ProductCode",
    "ProductStatus",
    "StockMovementType",
    # Events
    "ProductCreatedEvent",
    "ProductUpdatedEvent",
    "ProductDeletedEvent",
    "ProductReactivatedEvent",
    "StockUpdatedEvent",
    "LowStockAlertEvent",
    "OutOfStockEvent",
    # Exceptions
    "ProductError",
    "ProductNotFoundError",
    "DuplicateCodeError",
    "InvalidProductCodeError",
    "InvalidStockQuantityError",
    "ProductAlreadyActiveError",
    "ProductAlreadyInactiveError",
    "NegativeStockNotAllowedError",
    "InsufficientStockError",
    # Interfaces
    "IProductRepository",
]