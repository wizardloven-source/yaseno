# core/application/handlers/products/update_stock_handler.py
"""
Update Stock Handler - تحديث كمية المخزون
✅ محدث: Optimistic Locking لتحديث المخزون
✅ محدث: التحقق من الإصدار قبل التحديث
"""

import logging
from uuid import UUID

from core.domain.products.value_objects import ProductId
from core.domain.products.exceptions import ProductNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.products.commands import UpdateStockCommand
from core.application.products.dtos import ProductDTO
from core.application.products.converters import product_to_dto

logger = logging.getLogger(__name__)


class UpdateStockHandler(BaseHandler[UpdateStockCommand, ProductDTO]):
    """Handler for updating product stock quantity with Optimistic Locking"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateStockCommand, user_context: UserContext) -> ProductDTO:
        with self._uow:
            product_repo = self._uow.products
            
            product = product_repo.get_by_id(ProductId(UUID(command.product_id)))
            if not product:
                raise ProductNotFoundError(command.product_id)
            
            # ✅ التحقق من الإصدار (سيكون في Repository)
            # نقوم بحفظ الإصدار الحالي للتحقق
            old_version = product.version
            
            product.update_stock(
                quantity_change=int(command.quantity_change),
                reason=command.reason,
                updated_by=user_context.user_id
            )
            
            # ✅ حفظ مع Optimistic Locking
            try:
                product_repo.save(product)  # الـ Repository سيتحقق من الإصدار
                self._commit()
            except ConcurrentModificationError as e:
                logger.warning(f"Concurrent modification detected for product {product.code.value}")
                raise
            
            logger.info(f"Stock updated for {product.code.value}: {command.quantity_change:+.0f} → {product.stock_quantity:.0f}")
            
            return product_to_dto(product)