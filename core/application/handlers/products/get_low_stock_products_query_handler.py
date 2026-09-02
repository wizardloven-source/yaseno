# core/application/handlers/products/get_low_stock_products_query_handler.py

"""
Get Low Stock Products Query Handler - استعلام لجلب المنتجات منخفضة المخزون
"""

import logging
from typing import List
from decimal import Decimal

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.products.commands import GetLowStockProductsQuery
from core.application.products.dtos import ProductSummaryDTO

# ✅ استيراد من converters بدلاً من search_products_query_handler
from core.application.products.converters import product_to_summary_dto

logger = logging.getLogger(__name__)


class GetLowStockProductsQueryHandler(BaseQueryHandler[GetLowStockProductsQuery, List[ProductSummaryDTO]]):
    """Handler for retrieving low stock products"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetLowStockProductsQuery) -> List[ProductSummaryDTO]:
        with self._uow:
            product_repo = self._uow.products
            
            products = product_repo.get_low_stock(
                threshold=int(query.threshold),
                limit=query.limit,
            )
            
            return [product_to_summary_dto(p) for p in products]