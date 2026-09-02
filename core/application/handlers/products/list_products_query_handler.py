# core/application/handlers/products/list_products_query_handler.py

import logging
from typing import List

from core.domain.products.entities import Product
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.products.commands import ListProductsQuery
from core.application.products.dtos import ProductDTO, ProductListDTO

from .create_product_handler import product_to_dto

logger = logging.getLogger(__name__)


class ListProductsQueryHandler(BaseQueryHandler[ListProductsQuery, ProductListDTO]):
    """Handler for listing products with pagination"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: ListProductsQuery) -> ProductListDTO:
        with self._uow:
            product_repo = self._uow.products
            
            products = product_repo.list_all(
                include_inactive=query.include_inactive,
                category=query.category,
                limit=query.limit,
                offset=query.offset,
            )
            
            total_count = product_repo.count_all(
                include_inactive=query.include_inactive,
                category=query.category,
            )
            
            return ProductListDTO(
                products=[product_to_dto(p) for p in products],
                total_count=total_count,
                page=(query.offset // query.limit) + 1 if query.limit > 0 else 1,
                page_size=query.limit,
            )