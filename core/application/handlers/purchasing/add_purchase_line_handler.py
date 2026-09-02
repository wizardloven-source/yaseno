import logging
from decimal import Decimal
from uuid import UUID

from core.domain.purchasing.entities import PurchaseLine
from core.domain.purchasing.value_objects import PurchaseOrderId
from core.domain.purchasing.exceptions import PurchaseOrderNotFoundError, CannotModifyPostedPurchaseOrderError
from core.domain.shared.value_objects import Money
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.purchasing.commands import AddPurchaseLineCommand
from core.application.purchasing.dtos import PurchaseOrderDTO
from core.application.purchasing.converters import order_to_dto

logger = logging.getLogger(__name__)


class AddPurchaseLineHandler(BaseHandler[AddPurchaseLineCommand, PurchaseOrderDTO]):
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: AddPurchaseLineCommand, user_context: UserContext) -> PurchaseOrderDTO:
        with self._uow:
            order_repo = self._uow.purchase_orders
            order_id = PurchaseOrderId(UUID(command.order_id))
            
            order = order_repo.get_by_id(order_id)
            if not order:
                raise PurchaseOrderNotFoundError(command.order_id)
            
            if order.is_posted:
                raise CannotModifyPostedPurchaseOrderError(command.order_id)
            
            if command.quantity <= 0:
                raise ValueError(f"Quantity must be greater than zero, got {command.quantity}")
            
            if command.unit_price <= 0:
                raise ValueError(f"Unit price must be greater than zero, got {command.unit_price}")
            
            unit_price_money = Money(command.unit_price, command.currency)
            line = PurchaseLine(
                product_code=command.product_code,
                product_name=command.product_name,
                quantity=command.quantity,
                unit_price=unit_price_money,
                notes=command.notes
            )
            
            order.add_line(line)
            order_repo.save(order)
            self._commit()
            
            logger.info(f"Line added to purchase order {order.number} by {user_context.user_id}")
            
            return order_to_dto(order)