# core/application/handlers/products/create_product_handler.py (محدث)

"""
Create Product Handler - إنشاء منتج جديد
"""

import logging
from decimal import Decimal

from core.domain.products.entities import Product
from core.domain.products.value_objects import ProductCode
from core.domain.products.exceptions import DuplicateCodeError
from core.domain.shared.value_objects import Money
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.products.commands import CreateProductCommand
from core.application.products.dtos import ProductDTO

# ✅ استيراد من converters
from core.application.products.converters import product_to_dto

logger = logging.getLogger(__name__)


class CreateProductHandler(BaseHandler[CreateProductCommand, ProductDTO]):
    """Handler for creating a new product"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateProductCommand, user_context: UserContext) -> ProductDTO:
        with self._uow:
            product_repo = self._uow.products
            
            # Check for duplicate code
            existing = product_repo.get_by_code(ProductCode(command.code))
            if existing:
                raise DuplicateCodeError(command.code)
            
            # Create product using factory method
            product = Product.create(
                code=ProductCode(command.code),
                name=command.name,
                unit_price=Money(command.unit_price, command.currency),
                description=command.description,
                category=command.category,
                tax_rate=command.tax_rate,
                stock_quantity=int(command.stock_quantity) if command.stock_quantity else 0,
                created_by=user_context.user_id
            )
            
            product_repo.save(product)
            self._commit()
            
            logger.info(f"Product created: {product.code.value} - {product.name} by {user_context.user_id}")
            
            return product_to_dto(product)