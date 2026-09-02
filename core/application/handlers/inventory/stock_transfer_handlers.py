# core/application/handlers/inventory/stock_transfer_handlers.py
"""
Stock Transfer Handlers - معالجات تحويلات المخزون
"""

import logging
from decimal import Decimal
from datetime import datetime

from core.domain.inventory.entities import StockTransfer
from core.domain.inventory.value_objects import (
    EntityId,
    BatchNumber,
    Money,
    StockLocation,
    StockMovementType,
    SerialNumber,
    StockTransferId,
)
from core.domain.inventory.services import StockMovementService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.inventory.commands import (
    CreateStockTransferCommand,
    CompleteStockTransferCommand,
)
from core.application.inventory.dtos import StockTransferDTO
from core.application.inventory.converters import transfer_to_dto

logger = logging.getLogger(__name__)


class CreateStockTransferHandler(BaseHandler[CreateStockTransferCommand, StockTransferDTO]):
    """
    معالج إنشاء تحويل مخزون
    
    ينشئ تحويلاً من موقع إلى آخر (مستودع إلى مستودع)
    """
    
    def __init__(self, uow: IUnitOfWork, stock_service: StockMovementService):
        super().__init__(uow)
        self._stock_service = stock_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CreateStockTransferCommand, user_context: UserContext) -> StockTransferDTO:
        logger.info(f"Creating stock transfer: {command.quantity} from {command.from_location} to {command.to_location}")
        
        with self._uow:
            # rebind the singleton service repo to the current UoW session
            self._stock_service._repo = self._uow.stock_movements
            transfer_repo = self._uow.stock_transfers
            
            entity = EntityId(command.entity_type, command.entity_id)
            from_location = StockLocation.from_string(command.from_location)
            to_location = StockLocation.from_string(command.to_location)
            unit_cost = Money(command.unit_cost, command.currency)
            total_cost = Money(unit_cost.amount * command.quantity, command.currency)
            
            # التحقق من كفاية المخزون في الموقع المصدر
            # TODO: التحقق من المخزون في الموقع المحدد
            
            # إنشاء التحويل
            transfer = StockTransfer(
                entity=entity,
                quantity=command.quantity,
                unit_cost=unit_cost,
                total_cost=total_cost,
                from_location=from_location,
                to_location=to_location,
                reference_type="StockTransfer",
                reference_id=command.reference_id or f"TRF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                batch_number=BatchNumber(command.batch_number) if command.batch_number else None,
                serial_numbers=[SerialNumber(s) for s in (command.serial_numbers or [])],
                notes=command.notes,
                created_by=user_context.user_id,
                status="pending"
            )
            
            transfer_repo.save(transfer)
            self._commit()
            
            logger.info(f"Stock transfer created: {transfer.id} (Status: pending)")
            return transfer_to_dto(transfer)


class CompleteStockTransferHandler(BaseHandler[CompleteStockTransferCommand, StockTransferDTO]):
    """
    معالج إكمال تحويل المخزون
    
    يكمل عملية التحويل ويحدث المخزون في الموقعين
    """
    
    def __init__(self, uow: IUnitOfWork, stock_service: StockMovementService):
        super().__init__(uow)
        self._stock_service = stock_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CompleteStockTransferCommand, user_context: UserContext) -> StockTransferDTO:
        logger.info(f"Completing stock transfer: {command.transfer_id}")
        
        with self._uow:
            # rebind the singleton service repo to the current UoW session
            self._stock_service._repo = self._uow.stock_movements
            transfer_repo = self._uow.stock_transfers
            
            transfer = transfer_repo.get_by_id(StockTransferId.from_string(command.transfer_id))
            if not transfer:
                raise ValueError(f"Transfer not found: {command.transfer_id}")
            
            if transfer.status == "completed":
                raise ValueError(f"Transfer already completed: {command.transfer_id}")
            
            if transfer.status == "cancelled":
                raise ValueError(f"Transfer is cancelled: {command.transfer_id}")
            
            # إنشاء حركة صادرة من الموقع المصدر
            out_movement = self._stock_service.create_outbound_movement(
                entity=transfer.entity,
                quantity=transfer.quantity,
                unit_cost=transfer.unit_cost,
                movement_type=StockMovementType.TRANSFER_OUT,
                reference_type="StockTransfer",
                reference_id=str(transfer.id),
                batch_number=transfer.batch_number,
                location=str(transfer.from_location),
                notes=f"تحويل صادر إلى {transfer.to_location} - {transfer.notes}",
                created_by=user_context.user_id
            )
            
            # إنشاء حركة واردة إلى الموقع الهدف
            in_movement = self._stock_service.create_inbound_movement(
                entity=transfer.entity,
                quantity=transfer.quantity,
                unit_cost=transfer.unit_cost,
                movement_type=StockMovementType.TRANSFER_IN,
                reference_type="StockTransfer",
                reference_id=str(transfer.id),
                batch_number=transfer.batch_number,
                location=str(transfer.to_location),
                notes=f"تحويل وارد من {transfer.from_location} - {transfer.notes}",
                created_by=user_context.user_id
            )
            
            # إكمال التحويل
            transfer.complete(user_context.user_id)
            transfer_repo.save(transfer)
            
            self._commit()
            
            logger.info(f"Stock transfer completed: {transfer.id}")
            return transfer_to_dto(transfer)