import logging
from uuid import UUID

from core.domain.purchasing.value_objects import PurchaseOrderId
from core.domain.purchasing.exceptions import PurchaseOrderNotFoundError, CannotModifyPostedPurchaseOrderError
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.purchasing.commands import ClearPurchaseLinesCommand
from core.application.purchasing.dtos import PurchaseOrderDTO
from core.application.purchasing.converters import order_to_dto

logger = logging.getLogger(__name__)


class ClearPurchaseLinesHandler(BaseHandler[ClearPurchaseLinesCommand, PurchaseOrderDTO]):
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ClearPurchaseLinesCommand, user_context: UserContext) -> PurchaseOrderDTO:
        with self._uow:
            order_repo = self._uow.purchase_orders
            order_id = PurchaseOrderId(UUID(command.order_id))
            
            order = order_repo.get_by_id(order_id)
            if not order:
                raise PurchaseOrderNotFoundError(command.order_id)
            
            if order.is_posted:
                raise CannotModifyPostedPurchaseOrderError(command.order_id)
            
            previous_line_count = len(order.lines)
            order.clear_lines()
            order_repo.save(order)
            self._commit()
            
            logger.info(f"Cleared {previous_line_count} lines from purchase order {order.number} by {user_context.user_id}")
            
            return order_to_dto(order)