# core/application/handlers/products/get_product_query_handler.py

import logging
from uuid import UUID

from core.domain.products.value_objects import ProductId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.products.commands import GetProductQuery
from core.application.products.dtos import ProductDTO

from .create_product_handler import product_to_dto

logger = logging.getLogger(__name__)


class GetProductQueryHandler(BaseQueryHandler[GetProductQuery, ProductDTO]):
    """Handler for retrieving a single product by ID"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetProductQuery) -> ProductDTO:
        with self._uow:
            product_repo = self._uow.products
            product = product_repo.get_by_id(ProductId(UUID(query.product_id)))
            
            if not product:
                return None
            
            return product_to_dto(product)