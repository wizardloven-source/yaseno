# core/application/handlers/products/get_product_by_code_query_handler.py

"""
Get Product By Code Query Handler - استعلام لجلب منتج بالكود
"""

import logging

from core.domain.products.value_objects import ProductCode
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.products.commands import GetProductByCodeQuery
from core.application.products.dtos import ProductDTO

# ✅ استيراد من converters
from core.application.products.converters import product_to_dto

logger = logging.getLogger(__name__)


class GetProductByCodeQueryHandler(BaseQueryHandler[GetProductByCodeQuery, ProductDTO]):
    """Handler for retrieving a single product by code"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetProductByCodeQuery) -> ProductDTO:
        with self._uow:
            product_repo = self._uow.products
            product = product_repo.get_by_code(ProductCode(query.code))
            
            if not product:
                return None
            
            return product_to_dto(product)