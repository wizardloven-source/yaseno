# core/application/handlers/inventory/stock_query_handlers.py
"""
Stock Query Handlers - ظ…ط¹ط§ظ„ط¬ط§طھ ط§ط³طھط¹ظ„ط§ظ…ط§طھ ط§ظ„ظ…ط®ط²ظˆظ†
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any

from core.domain.inventory.services import StockMovementService, InventoryValuationService
from core.domain.inventory.value_objects import EntityId, CostFlowMethod
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.inventory.commands import (
    GetStockQuantityQuery,
    GetStockMovementsQuery,
    GetStockValuationQuery,
    GetLowStockQuery,
)
from core.application.inventory.dtos import (
    StockMovementDTO,
    StockValuationDTO,
    StockSummaryDTO,
)
from core.application.inventory.converters import movements_to_dto_list

logger = logging.getLogger(__name__)


class GetStockQuantityHandler(BaseQueryHandler[GetStockQuantityQuery, Decimal]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظƒظ…ظٹط© ط§ظ„ظ…ط®ط²ظˆظ†
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow
    
    @property
    def _service(self):
        return StockMovementService(self._uow.stock_movements)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetStockQuantityQuery, user_context: UserContext = None) -> Decimal:
        logger.debug(f"Getting stock quantity for {query.entity_type}:{query.entity_id}")
        
        # âœ… ط£ط¶ظپ with self._uow:
        with self._uow:
            entity = EntityId(query.entity_type, query.entity_id)
            
            if query.as_of_date:
                quantity = self._service.get_quantity_at_date(entity, query.as_of_date)
            else:
                quantity = self._service.get_current_quantity(entity)
            
            logger.debug(f"Stock quantity: {quantity}")
            return quantity


class GetStockMovementsHandler(BaseQueryHandler[GetStockMovementsQuery, list]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ط­ط±ظƒط§طھ ط§ظ„ظ…ط®ط²ظˆظ†
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow
    
    @property
    def _service(self):
        return StockMovementService(self._uow.stock_movements)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetStockMovementsQuery, user_context: UserContext = None) -> list:
        logger.debug(f"Getting stock movements for {query.entity_type}:{query.entity_id}")
        
        # âœ… ط£ط¶ظپ with self._uow:
        with self._uow:
            entity = EntityId(query.entity_type, query.entity_id)
            
            movements = self._service.get_movements(
                entity=entity,
                from_date=query.from_date,
                to_date=query.to_date,
                limit=query.limit,
                offset=query.offset
            )
            
            return movements_to_dto_list(movements)


class GetStockValuationHandler(BaseQueryHandler[GetStockValuationQuery, StockValuationDTO]):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… طھظ‚ظٹظٹظ… ط§ظ„ظ…ط®ط²ظˆظ†
    
    ظٹط­ط³ط¨ ظ‚ظٹظ…ط© ط§ظ„ظ…ط®ط²ظˆظ† ط¨ط§ط³طھط®ط¯ط§ظ… ط·ط±ظٹظ‚ط© FIFO ط£ظˆ LIFO ط£ظˆ ط§ظ„ظ…طھظˆط³ط· ط§ظ„ظ…ط±ط¬ط­
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow
    
    @property
    def _valuation_service(self):
        return InventoryValuationService(self._uow.stock_movements)
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetStockValuationQuery, user_context: UserContext = None) -> StockValuationDTO:
        logger.debug(f"Getting stock valuation for {query.entity_type}:{query.entity_id}")
        
        # âœ… ط£ط¶ظپ with self._uow:
        with self._uow:
            entity = EntityId(query.entity_type, query.entity_id)
            method = CostFlowMethod(query.method)
            
            valuation = self._valuation_service.calculate_valuation(
                entity=entity,
                as_of_date=query.as_of_date,
                method=method
            )
            
            return StockValuationDTO(
                entity_type=query.entity_type,
                entity_id=query.entity_id,
                total_quantity=valuation.total_quantity,
                total_cost=valuation.total_cost.amount,
                average_cost=valuation.average_cost.amount,
                currency=valuation.currency,
                valuation_method=method.value,
                as_of_date=valuation.as_of_date
            )


class GetLowStockHandler(BaseQueryHandler):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ط§ظ„ظ…ظ†طھط¬ط§طھ ظ…ظ†ط®ظپط¶ط© ط§ظ„ظ…ط®ط²ظˆظ†
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow
    
    @property
    def _service(self):
        return StockMovementService(self._uow.stock_movements)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetLowStockQuery, user_context: UserContext = None) -> list:
        logger.debug(f"Getting low stock products with threshold: {query.threshold}")
        
        # âœ… ط£ط¶ظپ with self._uow:
        with self._uow:
            product_repo = self._uow.products
            products = product_repo.get_low_stock(
                threshold=query.threshold,
                limit=query.limit
            )
            
            result = []
            for product in products:
                entity = EntityId("product", str(product.id))
                current_quantity = self._service.get_current_quantity(entity)
                
                result.append({
                    'product_id': str(product.id),
                    'product_code': product.code.value,
                    'product_name': product.name,
                    'current_stock': float(current_quantity),
                    'threshold': query.threshold,
                    'shortage': float(max(0, query.threshold - current_quantity)),
                    'unit_price': float(product.unit_price.amount),
                    'currency': product.unit_price.currency,
                    'is_active': product.is_active,
                    'category': product.category
                })
            
            logger.info(f"Found {len(result)} low stock products")
            return result


class GetStockSummaryHandler(BaseQueryHandler):
    """
    ظ…ط¹ط§ظ„ط¬ ط§ط³طھط¹ظ„ط§ظ… ظ…ظ„ط®طµ ط§ظ„ظ…ط®ط²ظˆظ†
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        self._uow = uow
    
    @property
    def _service(self):
        return StockMovementService(self._uow.stock_movements)
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, entity_type: str, entity_id: str) -> StockSummaryDTO:
        logger.debug(f"Getting stock summary for {entity_type}:{entity_id}")
        
        # âœ… ط£ط¶ظپ with self._uow:
        with self._uow:
            entity = EntityId(entity_type, entity_id)
            
            current_quantity = self._service.get_current_quantity(entity)
            movements = self._service.get_movements(entity, limit=10000)
            
            total_inbound = sum(m.quantity for m in movements if m.is_inbound)
            total_outbound = sum(abs(m.quantity) for m in movements if m.is_outbound)
            
            total_cost = Decimal('0')
            currency = "USD"
            if movements:
                latest = movements[-1]
                total_cost = latest.unit_cost.amount * current_quantity if current_quantity > 0 else Decimal('0')
                currency = latest.unit_cost.currency
            
            batch_count = 0
            try:
                batch_repo = self._uow.stock_batches
                batches = batch_repo.get_by_entity(entity, limit=1000)
                batch_count = len(batches)
            except Exception:
                pass
            
            return StockSummaryDTO(
                entity_type=entity_type,
                entity_id=entity_id,
                current_quantity=current_quantity,
                total_inbound=total_inbound,
                total_outbound=total_outbound,
                net_movement=total_inbound - total_outbound,
                total_cost=total_cost,
                currency=currency,
                last_movement_date=movements[-1].created_at if movements else None,
                batch_count=batch_count
            )