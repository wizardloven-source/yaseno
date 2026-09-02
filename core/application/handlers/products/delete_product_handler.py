# core/application/handlers/products/delete_product_handler.py (محدث)

"""
Delete Product Handler - حذف منتج (Soft Delete)
"""

import logging
from uuid import UUID

from core.domain.products.value_objects import ProductId
from core.domain.products.exceptions import ProductNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.products.commands import DeleteProductCommand

logger = logging.getLogger(__name__)


class DeleteProductHandler(BaseHandler[DeleteProductCommand, dict]):
    """Handler for deleting (deactivating) a product"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteProductCommand, user_context: UserContext) -> dict:
        with self._uow:
            product_repo = self._uow.products
            
            product = product_repo.get_by_id(ProductId(UUID(command.product_id)))
            if not product:
                raise ProductNotFoundError(command.product_id)
            
            product.deactivate(user_context.user_id)
            product_repo.save(product)
            self._commit()
            
            logger.info(f"Product deactivated: {product.code.value} - {product.name} by {user_context.user_id}")
            
            return {
                "success": True,
                "product_id": command.product_id,
                "message": f"Product {product.code.value} has been deactivated"
            }