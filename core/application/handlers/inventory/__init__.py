# core/application/handlers/inventory/__init__.py
"""
Inventory Handlers - معالجات المخزون
"""

from .stock_movement_handlers import (
    CreateStockMovementHandler,
    CreatePurchaseMovementHandler,
    CreateSaleMovementHandler,
    CreateAdjustmentMovementHandler,
)
from .stock_batch_handlers import (
    CreateStockBatchHandler,
    ConsumeStockBatchHandler,
)
from .stock_transfer_handlers import (
    CreateStockTransferHandler,
    CompleteStockTransferHandler,
)
from .stock_query_handlers import (
    GetStockQuantityHandler,
    GetStockMovementsHandler,
    GetStockValuationHandler,
    GetLowStockHandler,
)

__all__ = [
    # Movement Handlers
    "CreateStockMovementHandler",
    "CreatePurchaseMovementHandler",
    "CreateSaleMovementHandler",
    "CreateAdjustmentMovementHandler",

    # Batch Handlers
    "CreateStockBatchHandler",
    "ConsumeStockBatchHandler",

    # Transfer Handlers
    "CreateStockTransferHandler",
    "CompleteStockTransferHandler",

    # Query Handlers
    "GetStockQuantityHandler",
    "GetStockMovementsHandler",
    "GetStockValuationHandler",
    "GetLowStockHandler",
]