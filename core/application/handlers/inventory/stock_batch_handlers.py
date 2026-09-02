# core/application/handlers/inventory/stock_batch_handlers.py
"""
Stock Batch Handlers - معالجات دفعات المخزون
"""

import logging
from decimal import Decimal

from core.domain.inventory.entities import StockBatch
from core.domain.inventory.value_objects import (
    EntityId,
    BatchNumber,
    ExpiryDate,
    Money,
    StockLocation,
    StockBatchStatus,
    StockBatchId,
)
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.inventory.commands import (
    CreateStockBatchCommand,
    ConsumeStockBatchCommand,
)
from core.application.inventory.dtos import StockBatchDTO
from core.application.inventory.converters import batch_to_dto

logger = logging.getLogger(__name__)


class CreateStockBatchHandler(BaseHandler[CreateStockBatchCommand, StockBatchDTO]):
    """
    معالج إنشاء دفعة مخزون جديدة
    
    يستخدم لتتبع الدفعات (Batch/Lot Tracking)
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CreateStockBatchCommand, user_context: UserContext) -> StockBatchDTO:
        logger.info(f"Creating stock batch: {command.batch_number} for {command.entity_type}:{command.entity_id}")
        
        with self._uow:
            repo = self._uow.stock_batches
            
            entity = EntityId(command.entity_type, command.entity_id)
            batch_number = BatchNumber(command.batch_number)
            unit_cost = Money(command.unit_cost, command.currency)
            total_cost = Money(unit_cost.amount * command.quantity, command.currency)
            expiry_date = ExpiryDate(command.expiry_date) if command.expiry_date else None
            location = StockLocation.from_string(command.location) if command.location else None
            
            # إنشاء الدفعة
            batch = StockBatch(
                entity=entity,
                batch_number=batch_number,
                initial_quantity=command.quantity,
                current_quantity=command.quantity,
                unit_cost=unit_cost,
                total_cost=total_cost,
                production_date=command.production_date,
                expiry_date=expiry_date,
                location=location,
                status=StockBatchStatus.ACTIVE,
                notes=command.notes,
                created_by=user_context.user_id
            )
            
            repo.save(batch)
            self._commit()
            
            logger.info(f"Stock batch created: {batch.id} (Batch: {batch.batch_number})")
            return batch_to_dto(batch)


class ConsumeStockBatchHandler(BaseHandler[ConsumeStockBatchCommand, StockBatchDTO]):
    """
    معالج استهلاك دفعة مخزون
    
    يستخدم عند استخدام جزء من دفعة معينة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ConsumeStockBatchCommand, user_context: UserContext) -> StockBatchDTO:
        logger.info(f"Consuming stock batch: {command.batch_id} (Qty: {command.quantity})")
        
        with self._uow:
            repo = self._uow.stock_batches
            
            batch = repo.get_by_id(StockBatchId.from_string(command.batch_id))
            if not batch:
                raise ValueError(f"Batch not found: {command.batch_id}")
            
            if batch.current_quantity < command.quantity:
                raise ValueError(
                    f"Insufficient quantity in batch: {batch.current_quantity} < {command.quantity}"
                )
            
            batch.consume(
                command.quantity,
                reference_type=command.reference_type,
                reference_id=command.reference_id,
                consumed_by=command.consumed_by
            )
            
            # تسجيل الاستهلاك في الملاحظات
            batch.notes = f"{batch.notes}\nConsumed: {command.quantity} for {command.reference_type}:{command.reference_id} by {command.consumed_by}"
            
            repo.save(batch)
            self._commit()
            
            logger.info(f"Batch consumed: {batch.id} (Remaining: {batch.current_quantity})")
            return batch_to_dto(batch)