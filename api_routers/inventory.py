# api_routers/inventory.py
"""
YAseen ERP - Inventory Router
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel

from api_routers.shared import (
    bootstrap, logger, ApiResponse, get_current_user,
)

router = APIRouter(prefix="", tags=["inventory"])


# =============================================================================
# Inventory - المخزون
# =============================================================================


class StockMovementRequest(BaseModel):
    entity_type: str
    entity_id: str
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    currency: str = "USD"
    reference_type: str = ""
    reference_id: str = ""
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""


class PurchaseMovementRequest(BaseModel):
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    purchase_order_id: str
    currency: str = "USD"
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""


class SaleMovementRequest(BaseModel):
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    invoice_id: str
    currency: str = "USD"
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    location: Optional[str] = None
    notes: str = ""


class AdjustmentMovementRequest(BaseModel):
    entity_type: str
    entity_id: str
    old_quantity: Decimal
    new_quantity: Decimal
    unit_cost: Decimal
    reason: str
    currency: str = "USD"
    location: Optional[str] = None
    notes: str = ""


class StockBatchRequest(BaseModel):
    entity_type: str
    entity_id: str
    batch_number: str
    quantity: Decimal
    unit_cost: Decimal
    currency: str = "USD"
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""


class ConsumeBatchRequest(BaseModel):
    quantity: Decimal
    reference_type: str
    reference_id: str


class StockTransferRequest(BaseModel):
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    from_location: str
    to_location: str
    currency: str = "USD"
    reference_id: str = ""
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    notes: str = ""


@router.post("/api/inventory/movements", response_model=ApiResponse)
async def create_stock_movement(
    request: StockMovementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateStockMovementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateStockMovementCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            movement_type=request.movement_type,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            currency=request.currency,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            batch_number=request.batch_number,
            serial_numbers=request.serial_numbers,
            expiry_date=request.expiry_date,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء حركة المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating stock movement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/inventory/movements/purchase", response_model=ApiResponse)
async def create_purchase_movement(
    request: PurchaseMovementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreatePurchaseMovementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreatePurchaseMovementCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            purchase_order_id=request.purchase_order_id,
            currency=request.currency,
            batch_number=request.batch_number,
            serial_numbers=request.serial_numbers,
            expiry_date=request.expiry_date,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تسجيل حركة مشتريات بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating purchase movement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/inventory/movements/sale", response_model=ApiResponse)
async def create_sale_movement(
    request: SaleMovementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateSaleMovementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateSaleMovementCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            invoice_id=request.invoice_id,
            currency=request.currency,
            batch_number=request.batch_number,
            serial_numbers=request.serial_numbers,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تسجيل حركة مبيعات بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating sale movement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/inventory/movements/adjustment", response_model=ApiResponse)
async def create_adjustment_movement(
    request: AdjustmentMovementRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateAdjustmentMovementCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateAdjustmentMovementCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            old_quantity=request.old_quantity,
            new_quantity=request.new_quantity,
            unit_cost=request.unit_cost,
            reason=request.reason,
            currency=request.currency,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم تسجيل حركة تسوية المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating adjustment movement: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/inventory/{entity_type}/{entity_id}/quantity", response_model=ApiResponse)
async def get_stock_quantity(
    entity_type: str,
    entity_id: str,
    as_of_date: Optional[date] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import GetStockQuantityQuery
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetStockQuantityQuery(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of_date=as_of_date,
        )
        quantity = query_bus.dispatch(query)
        return ApiResponse(success=True, message="تم جلب كمية المخزون بنجاح",
                           data={'entity_type': entity_type, 'entity_id': entity_id, 'quantity': float(quantity)})
    except Exception as e:
        logger.error(f"Error getting stock quantity: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/inventory/{entity_type}/{entity_id}/movements", response_model=ApiResponse)
async def get_stock_movements(
    entity_type: str,
    entity_id: str,
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    movement_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import GetStockMovementsQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetStockMovementsQuery(
            entity_type=entity_type,
            entity_id=entity_id,
            from_date=from_date,
            to_date=to_date,
            movement_type=movement_type,
            limit=limit,
            offset=offset,
        )
        movements = query_bus.dispatch(query) or []
        return ApiResponse(success=True, message="تم جلب حركات المخزون بنجاح",
                           data={'items': jsonable_encoder(movements), 'total': len(movements)})
    except Exception as e:
        logger.error(f"Error getting stock movements: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/inventory/{entity_type}/{entity_id}/valuation", response_model=ApiResponse)
async def get_stock_valuation(
    entity_type: str,
    entity_id: str,
    as_of_date: date = Query(...),
    method: str = Query("fifo"),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import GetStockValuationQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetStockValuationQuery(
            entity_type=entity_type,
            entity_id=entity_id,
            as_of_date=as_of_date,
            method=method,
        )
        valuation = query_bus.dispatch(query)
        return ApiResponse(success=True, message="تم جلب تقييم المخزون بنجاح", data=jsonable_encoder(valuation))
    except Exception as e:
        logger.error(f"Error getting stock valuation: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.get("/api/inventory/low-stock", response_model=ApiResponse)
async def get_low_stock(
    threshold: int = Query(10, ge=0),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import GetLowStockQuery
        from fastapi.encoders import jsonable_encoder
        query_bus = bootstrap.container.resolve("query_bus")
        query = GetLowStockQuery(threshold=threshold, limit=limit, offset=offset)
        items = query_bus.dispatch(query) or []
        return ApiResponse(success=True, message="تم جلب المنتجات منخفضة المخزون بنجاح",
                           data={'items': jsonable_encoder(items), 'total': len(items)})
    except Exception as e:
        logger.error(f"Error getting low stock: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/inventory/batches", response_model=ApiResponse)
async def create_stock_batch(
    request: StockBatchRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateStockBatchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateStockBatchCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            batch_number=request.batch_number,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            currency=request.currency,
            production_date=request.production_date,
            expiry_date=request.expiry_date,
            location=request.location,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء دفعة المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating stock batch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/inventory/batches/{batch_id}/consume", response_model=ApiResponse)
async def consume_stock_batch(
    batch_id: str,
    request: ConsumeBatchRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import ConsumeStockBatchCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = ConsumeStockBatchCommand(
            batch_id=batch_id,
            quantity=request.quantity,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            consumed_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم استهلاك الدفعة بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error consuming stock batch: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/inventory/transfers", response_model=ApiResponse)
async def create_stock_transfer(
    request: StockTransferRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CreateStockTransferCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CreateStockTransferCommand(
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            quantity=request.quantity,
            unit_cost=request.unit_cost,
            from_location=request.from_location,
            to_location=request.to_location,
            currency=request.currency,
            reference_id=request.reference_id,
            batch_number=request.batch_number,
            serial_numbers=request.serial_numbers,
            notes=request.notes,
            created_by=current_user["username"],
        )
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إنشاء تحويل المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error creating stock transfer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])


@router.post("/api/inventory/transfers/{transfer_id}/complete", response_model=ApiResponse)
async def complete_stock_transfer(
    transfer_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        from core.application.inventory.commands import CompleteStockTransferCommand
        from fastapi.encoders import jsonable_encoder
        command_bus = bootstrap.container.resolve("command_bus")
        command = CompleteStockTransferCommand(transfer_id=transfer_id, completed_by=current_user["username"])
        dto = command_bus.dispatch(command)
        return ApiResponse(success=True, message="تم إكمال تحويل المخزون بنجاح", data=jsonable_encoder(dto))
    except Exception as e:
        logger.error(f"Error completing stock transfer: {e}", exc_info=True)
        return ApiResponse(success=False, message=str(e), errors=[str(e)])
