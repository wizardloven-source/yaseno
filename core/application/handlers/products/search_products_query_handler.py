# core/application/handlers/products/search_products_query_handler.py

"""
Search Products Query Handler - استعلام للبحث عن المنتجات
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.products.commands import SearchProductsQuery
from core.application.products.dtos import ProductSummaryDTO

# ✅ استيراد من converters
from core.application.products.converters import product_to_summary_dto

logger = logging.getLogger(__name__)


class SearchProductsQueryHandler(BaseQueryHandler[SearchProductsQuery, List[ProductSummaryDTO]]):
    """Handler for searching products"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: SearchProductsQuery) -> List[ProductSummaryDTO]:
        with self._uow:
            product_repo = self._uow.products
            
            products = product_repo.search(
                search_text=query.search_text,
                category=query.category,
                limit=query.limit,
                offset=query.offset,
            )
            
            return [product_to_summary_dto(p) for p in products]