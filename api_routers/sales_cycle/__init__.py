"""
Sales Cycle API Routes
"""

from fastapi import APIRouter

from .quotations_router import router as quotations_router
from .orders_router import router as orders_router
from .deliveries_router import router as deliveries_router

router = APIRouter(prefix="/sales", tags=["Sales Cycle"])

router.include_router(quotations_router, prefix="/quotations")
router.include_router(orders_router, prefix="/orders")
router.include_router(deliveries_router, prefix="/deliveries")

__all__ = ["router"]
