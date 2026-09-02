import logging
from uuid import UUID

from core.domain.purchasing.value_objects import PurchaseOrderId
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.purchasing.commands import GetPurchaseOrderQuery
from core.application.purchasing.dtos import PurchaseOrderDTO
from core.application.purchasing.converters import order_to_dto

logger = logging.getLogger(__name__)


class GetPurchaseOrderQueryHandler(BaseQueryHandler[GetPurchaseOrderQuery, PurchaseOrderDTO]):
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetPurchaseOrderQuery) -> PurchaseOrderDTO:
        with self._uow:
            order_repo = self._uow.purchase_orders
            order_id = PurchaseOrderId(UUID(query.order_id))
            
            order = order_repo.get_by_id(order_id)
            if not order:
                return None
            
            return order_to_dto(order)