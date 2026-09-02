# core/application/handlers/inventory/stock_movement_handlers.py
"""
Stock Movement Handlers - معالجات حركات المخزون
"""

import logging
from decimal import Decimal
from datetime import datetime

from core.domain.inventory.services import StockMovementService
from core.domain.inventory.value_objects import (
    EntityId,
    StockMovementType,
    BatchNumber,
    ExpiryDate,
    Money,
    StockLocation,
)
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.inventory.commands import (
    CreateStockMovementCommand,
    CreatePurchaseMovementCommand,
    CreateSaleMovementCommand,
    CreateAdjustmentMovementCommand,
)
from core.application.inventory.dtos import StockMovementDTO
from core.application.inventory.converters import movement_to_dto

logger = logging.getLogger(__name__)


class CreateStockMovementHandler(BaseHandler[CreateStockMovementCommand, StockMovementDTO]):
    """
    معالج إنشاء حركة مخزون عامة
    
    يمكن استخدامه لأي نوع من حركات المخزون (شراء، بيع، تعديل، تحويل، إلخ)
    """
    
    def __init__(self, uow: IUnitOfWork, stock_service: StockMovementService):
        super().__init__(uow)
        self._uow = uow
        self._stock_service = stock_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CreateStockMovementCommand, user_context: UserContext) -> StockMovementDTO:
        logger.info(f"Creating stock movement: {command.movement_type} for {command.entity_type}:{command.entity_id}")
        
        with self._uow:
            # rebind the singleton service repo to the current UoW session
            self._stock_service._repo = self._uow.stock_movements
            movement_type = StockMovementType(command.movement_type)
            entity = EntityId(command.entity_type, command.entity_id)
            
            # تحويل القيم
            unit_cost = Money(command.unit_cost, command.currency)
            batch_number = BatchNumber(command.batch_number) if command.batch_number else None
            expiry_date = ExpiryDate(command.expiry_date) if command.expiry_date else None
            location = StockLocation.from_string(command.location) if command.location else None
            
            # إنشاء الحركة حسب النوع
            if movement_type.is_inbound:
                movement = self._stock_service.create_inbound_movement(
                    entity=entity,
                    quantity=command.quantity,
                    unit_cost=unit_cost,
                    movement_type=movement_type,
                    reference_type=command.reference_type or movement_type.value,
                    reference_id=command.reference_id or f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    batch_number=batch_number,
                    expiry_date=expiry_date,
                    location=command.location,
                    notes=command.notes,
                    created_by=user_context.user_id
                )
            else:
                movement = self._stock_service.create_outbound_movement(
                    entity=entity,
                    quantity=command.quantity,
                    unit_cost=unit_cost,
                    movement_type=movement_type,
                    reference_type=command.reference_type or movement_type.value,
                    reference_id=command.reference_id or f"AUTO-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    batch_number=batch_number,
                    location=command.location,
                    notes=command.notes,
                    created_by=user_context.user_id
                )
            
            self._commit()
            
            logger.info(f"Stock movement created: {movement.id} ({movement.movement_type.value})")
            return movement_to_dto(movement)


class CreatePurchaseMovementHandler(BaseHandler[CreatePurchaseMovementCommand, StockMovementDTO]):
    """
    معالج إنشاء حركة شراء
    
    يتم استخدامه عند استلام بضاعة من مورد
    """
    
    def __init__(self, uow: IUnitOfWork, stock_service: StockMovementService):
        super().__init__(uow)
        self._uow = uow
        self._stock_service = stock_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CreatePurchaseMovementCommand, user_context: UserContext) -> StockMovementDTO:
        logger.info(f"Creating purchase movement: {command.quantity} of {command.entity_type}:{command.entity_id}")
        
        with self._uow:
            # rebind the singleton service repo to the current UoW session
            self._stock_service._repo = self._uow.stock_movements
            entity = EntityId(command.entity_type, command.entity_id)
            
            movement = self._stock_service.create_inbound_movement(
                entity=entity,
                quantity=command.quantity,
                unit_cost=Money(command.unit_cost, command.currency),
                movement_type=StockMovementType.PURCHASE,
                reference_type="PurchaseOrder",
                reference_id=command.purchase_order_id,
                batch_number=BatchNumber(command.batch_number) if command.batch_number else None,
                expiry_date=ExpiryDate(command.expiry_date) if command.expiry_date else None,
                location=command.location,
                notes=f"شراء - {command.notes}" if command.notes else "شراء",
                created_by=user_context.user_id
            )
            
            self._commit()
            
            logger.info(f"Purchase movement created: {movement.id} (Qty: {command.quantity})")
            return movement_to_dto(movement)


class CreateSaleMovementHandler(BaseHandler[CreateSaleMovementCommand, StockMovementDTO]):
    """
    معالج إنشاء حركة بيع
    
    يتم استخدامه عند بيع بضاعة للعميل
    يتم حساب التكلفة باستخدام FIFO تلقائياً
    """
    
    def __init__(self, uow: IUnitOfWork, stock_service: StockMovementService):
        super().__init__(uow)
        self._uow = uow
        self._stock_service = stock_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CreateSaleMovementCommand, user_context: UserContext) -> StockMovementDTO:
        logger.info(f"Creating sale movement: {command.quantity} of {command.entity_type}:{command.entity_id}")
        
        with self._uow:
            # rebind the singleton service repo to the current UoW session
            self._stock_service._repo = self._uow.stock_movements
            entity = EntityId(command.entity_type, command.entity_id)
            
            # التحقق من كفاية المخزون
            current_quantity = self._stock_service.get_current_quantity(entity)
            if current_quantity < command.quantity:
                raise ValueError(
                    f"Insufficient stock: {current_quantity} < {command.quantity} for {command.entity_type}:{command.entity_id}"
                )
            
            movement = self._stock_service.create_outbound_movement(
                entity=entity,
                quantity=command.quantity,
                unit_cost=Money(command.unit_cost, command.currency),
                movement_type=StockMovementType.SALE,
                reference_type="Invoice",
                reference_id=command.invoice_id,
                batch_number=BatchNumber(command.batch_number) if command.batch_number else None,
                location=command.location,
                notes=f"بيع - {command.notes}" if command.notes else "بيع",
                created_by=user_context.user_id
            )
            
            self._commit()
            
            logger.info(f"Sale movement created: {movement.id} (Qty: {command.quantity}, Cost: {command.unit_cost})")
            return movement_to_dto(movement)


class CreateAdjustmentMovementHandler(BaseHandler[CreateAdjustmentMovementCommand, StockMovementDTO]):
    """
    معالج إنشاء حركة تعديل
    
    يستخدم لتعديل كمية المخزون يدوياً (زيادة أو نقصان)
    """
    
    def __init__(self, uow: IUnitOfWork, stock_service: StockMovementService):
        super().__init__(uow)
        self._uow = uow
        self._stock_service = stock_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CreateAdjustmentMovementCommand, user_context: UserContext) -> StockMovementDTO:
        logger.info(f"Creating adjustment movement for {command.entity_type}:{command.entity_id}")
        
        with self._uow:
            # rebind the singleton service repo to the current UoW session
            self._stock_service._repo = self._uow.stock_movements
            entity = EntityId(command.entity_type, command.entity_id)
            quantity_change = command.new_quantity - command.old_quantity
            
            if quantity_change == 0:
                raise ValueError("No change in quantity")
            
            reference_id = f"ADJ-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            unit_cost = Money(command.unit_cost, command.currency)
            
            if quantity_change > 0:
                # زيادة المخزون
                movement = self._stock_service.create_inbound_movement(
                    entity=entity,
                    quantity=quantity_change,
                    unit_cost=unit_cost,
                    movement_type=StockMovementType.ADJUSTMENT_IN,
                    reference_type="Adjustment",
                    reference_id=reference_id,
                    location=command.location,
                    notes=f"تعديل إيجابي: {command.reason} - {command.notes}" if command.notes else f"تعديل إيجابي: {command.reason}",
                    created_by=user_context.user_id
                )
            else:
                # نقصان المخزون
                movement = self._stock_service.create_outbound_movement(
                    entity=entity,
                    quantity=abs(quantity_change),
                    unit_cost=unit_cost,
                    movement_type=StockMovementType.ADJUSTMENT_OUT,
                    reference_type="Adjustment",
                    reference_id=reference_id,
                    location=command.location,
                    notes=f"تعديل سلبي: {command.reason} - {command.notes}" if command.notes else f"تعديل سلبي: {command.reason}",
                    created_by=user_context.user_id
                )
            
            self._commit()
            
            logger.info(f"Adjustment movement created: {movement.id} (Change: {quantity_change})")
            return movement_to_dto(movement)