import logging
from uuid import UUID

from core.domain.purchasing.entities import PurchaseOrder
from core.domain.purchasing.value_objects import PurchaseOrderId, PaymentTerms
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.purchasing.commands import CreatePurchaseOrderCommand
from core.application.purchasing.dtos import PurchaseOrderDTO
from core.application.purchasing.converters import order_to_dto

logger = logging.getLogger(__name__)


class CreatePurchaseOrderHandler(BaseHandler[CreatePurchaseOrderCommand, PurchaseOrderDTO]):
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreatePurchaseOrderCommand, user_context: UserContext) -> PurchaseOrderDTO:
        with self._uow:
            order_repo = self._uow.purchase_orders
            
            payment_terms_map = {
                "cash": PaymentTerms.CASH,
                "net_15": PaymentTerms.NET_15,
                "net_30": PaymentTerms.NET_30,
                "net_45": PaymentTerms.NET_45,
                "net_60": PaymentTerms.NET_60,
            }
            payment_terms = payment_terms_map.get(command.payment_terms, PaymentTerms.NET_30)
            
            order = PurchaseOrder(
                supplier_id=command.supplier_id,
                supplier_name=command.supplier_name,
                site_id=command.site_id,
                site_name=command.site_name,
                currency=command.currency,
                payment_terms=payment_terms,
                expected_delivery_date=command.expected_delivery_date,
                notes=command.notes,
                created_by=user_context.user_id
            )
            
            next_number = order_repo.get_next_number()
            order.number = next_number
            
            order_repo.save(order)
            self._commit()
            
            return order_to_dto(order)