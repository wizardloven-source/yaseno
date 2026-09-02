import logging
from typing import List

from core.domain.purchasing.value_objects import PurchaseOrderStatus
from core.domain.accounting.interfaces import IUnitOfWork
from core.infrastructure.db.models.purchase_order_model import PurchaseOrderModel
from core.infrastructure.db.postgres.repositories_purchase_order import _model_to_domain
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.purchasing.commands import ListPurchaseOrdersQuery
from core.application.purchasing.dtos import PurchaseOrderDTO
from core.application.purchasing.converters import order_to_dto

logger = logging.getLogger(__name__)


class ListPurchaseOrdersQueryHandler(BaseQueryHandler[ListPurchaseOrdersQuery, List[PurchaseOrderDTO]]):
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: ListPurchaseOrdersQuery) -> List[PurchaseOrderDTO]:
        with self._uow:
            order_repo = self._uow.purchase_orders
            
            if query.supplier_id:
                orders = order_repo.list_by_supplier(query.supplier_id, query.limit)
            elif query.status:
                try:
                    status_enum = PurchaseOrderStatus(query.status)
                    orders = order_repo.list_by_status(status_enum, query.limit)
                except ValueError:
                    orders = []
            elif query.from_date and query.to_date:
                orders = order_repo.list_by_date_range(
                    query.from_date.date(),
                    query.to_date.date(),
                    query.limit
                )
            else:
                models = self._uow.session.query(PurchaseOrderModel).order_by(
                    PurchaseOrderModel.created_at.desc()
                ).limit(query.limit).offset(query.offset).all()
                orders = [_model_to_domain(m) for m in models]
            
            orders = orders[query.offset:query.offset + query.limit]
            
            return [order_to_dto(order) for order in orders]