import logging
from uuid import UUID

from core.domain.purchasing.value_objects import PurchaseOrderId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.purchasing.commands import DeleteDraftPurchaseOrderCommand

logger = logging.getLogger(__name__)


class DeleteDraftPurchaseOrderHandler(BaseHandler[DeleteDraftPurchaseOrderCommand, dict]):
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteDraftPurchaseOrderCommand, user_context: UserContext) -> dict:
        with self._uow:
            order_repo = self._uow.purchase_orders
            order_id = PurchaseOrderId(UUID(command.order_id))
            
            order = order_repo.get_by_id(order_id)
            if not order:
                return {
                    "success": False,
                    "message": f"Purchase order {command.order_id} not found",
                    "order_id": command.order_id
                }
            
            if order.is_posted:
                return {
                    "success": False,
                    "message": "Cannot delete posted purchase order",
                    "order_id": command.order_id
                }
            
            result = order_repo.delete_draft(order_id)
            
            if result:
                self._commit()
                logger.info(f"Draft purchase order {order.number} deleted by {user_context.user_id}")
            
            return {
                "success": result,
                "message": "Purchase order deleted successfully" if result else "Failed to delete purchase order",
                "order_id": command.order_id
            }