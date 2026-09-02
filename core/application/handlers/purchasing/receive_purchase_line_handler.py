# core/application/handlers/purchasing/receive_purchase_line_handler.py
"""
Receive Purchase Line Handler - استلام سطر من أمر الشراء
✅ محدث: إنشاء حركات مخزون (StockMovement) عند الاستلام
✅ محدث: دعم Batch/Lot Tracking
✅ محدث: دعم Serial Numbers
✅ محدث: دعم Expiry Dates
✅ محدث: Optimistic Locking
✅ محدث: تهيئة بطيئة (Lazy Initialization) لخدمة المخزون
"""

import logging
from decimal import Decimal
from uuid import UUID
from datetime import datetime, timezone

from core.domain.purchasing.value_objects import PurchaseOrderId
from core.domain.purchasing.exceptions import PurchaseOrderNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

# ✅ استيراد محرك المخزون الجديد
from core.domain.inventory.services import StockMovementService
from core.domain.inventory.value_objects import (
    EntityId,
    StockMovementType,
    BatchNumber,
    SerialNumber,
    ExpiryDate,
    Money as InventoryMoney,
    StockLocation,
)

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.purchasing.commands import ReceivePurchaseLineCommand
from core.application.purchasing.dtos import PurchaseOrderDTO
from core.application.purchasing.converters import order_to_dto

logger = logging.getLogger(__name__)


class ReceivePurchaseLineHandler(BaseHandler[ReceivePurchaseLineCommand, PurchaseOrderDTO]):
    """
    معالج استلام سطر من أمر الشراء
    
    ✅ محدث: إنشاء حركات مخزون (StockMovement) عند الاستلام
    ✅ محدث: دعم Batch/Lot Tracking
    ✅ محدث: دعم Serial Numbers
    ✅ محدث: دعم Expiry Dates
    ✅ محدث: تهيئة بطيئة (Lazy Initialization) لخدمة المخزون
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        # ✅ تهيئة بطيئة (Lazy Initialization) - لن يتم إنشاؤها حتى الحاجة
        self._stock_service = None
    
    # =========================================================================
    # ✅ تهيئة خدمة المخزون عند الحاجة (Lazy Initialization)
    # =========================================================================
    
    def _get_stock_service(self):
        """
        تهيئة خدمة المخزون عند الحاجة فقط (Lazy Initialization)
        
        هذه الطريقة تمنع إنشاء الخدمة في مرحلة تسجيل المعالجات (Bootstrap)
        وتؤجل الإنشاء إلى وقت التنفيذ الفعلي للأمر.
        """
        if self._stock_service is None:
            # ✅ استخدام getattr بأمان للوصول إلى stock_movements
            stock_movements = getattr(self._uow, 'stock_movements', None)
            if stock_movements:
                self._stock_service = StockMovementService(stock_movements)
            else:
                logger.warning("stock_movements not available in UoW")
                # ✅ إنشاء service وهمي (dummy) لتجنب None checks في كل مكان
                self._stock_service = StockMovementService(None)
        return self._stock_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ReceivePurchaseLineCommand, user_context: UserContext) -> PurchaseOrderDTO:
        logger.info(
            f"Receiving line {command.line_id} for purchase order {command.order_id} "
            f"(Qty: {command.quantity}) by {user_context.user_id}"
        )
        
        with self._uow:
            order_repo = self._uow.purchase_orders
            order_id = PurchaseOrderId(UUID(command.order_id))
            
            order = order_repo.get_by_id(order_id)
            if not order:
                raise PurchaseOrderNotFoundError(command.order_id)
            
            # ========== 1. التحقق من إمكانية الاستلام ==========
            if not order.is_posted:
                from core.domain.purchasing.exceptions import CannotReceiveUnpostedPurchaseOrderError
                raise CannotReceiveUnpostedPurchaseOrderError(str(order_id))
            
            # البحث عن السطر
            target_line = None
            for line in order.lines:
                if line.line_id == command.line_id:
                    target_line = line
                    break
            
            if not target_line:
                raise ValueError(f"Line {command.line_id} not found in purchase order")
            
            # التحقق من الكمية
            if command.quantity <= 0:
                raise ValueError("Received quantity must be greater than zero")
            
            if target_line.received_quantity + command.quantity > target_line.quantity:
                raise ValueError(
                    f"Cannot receive more than ordered quantity. "
                    f"Ordered: {target_line.quantity}, "
                    f"Already received: {target_line.received_quantity}"
                )
            
            # ========== 2. ✅ إنشاء حركة مخزون للاستلام ==========
            stock_movement_id = None
            
            # ✅ الحصول على خدمة المخزون (تهيئة بطيئة)
            stock_service = self._get_stock_service()
            
            try:
                # الحصول على المنتج
                product = self._uow.products.get_by_code(target_line.product_code)
                if not product:
                    logger.warning(f"Product {target_line.product_code} not found, skipping stock movement")
                else:
                    # إنشاء كيان المخزون
                    entity = EntityId("product", str(product.id))
                    
                    # إنشاء حركة شراء (تزيد المخزون)
                    movement = stock_service.create_inbound_movement(
                        entity=entity,
                        quantity=command.quantity,
                        unit_cost=InventoryMoney(
                            target_line.unit_price.amount,
                            target_line.unit_price.currency
                        ),
                        movement_type=StockMovementType.PURCHASE,
                        reference_type="PurchaseOrder",
                        reference_id=str(order.id),
                        batch_number=BatchNumber(command.batch_number) if command.batch_number else None,
                        expiry_date=ExpiryDate(command.expiry_date) if command.expiry_date else None,
                        location=command.location,
                        notes=f"استلام من أمر {order.number} - {target_line.product_name}",
                        created_by=user_context.user_id
                    )
                    
                    stock_movement_id = str(movement.id)
                    
                    logger.info(
                        f"Stock movement created for {target_line.product_code}: "
                        f"{command.quantity} units at {target_line.unit_price.amount} {target_line.unit_price.currency}"
                    )
                    
            except Exception as e:
                logger.error(f"Error creating stock movement: {e}", exc_info=True)
                # لا نمنع الاستلام إذا فشل إنشاء حركة المخزون، ولكن نسجل الخطأ
                # يمكن تغيير هذا السلوك حسب الحاجة
            
            # ========== 3. استلام السطر في أمر الشراء ==========
            try:
                received_line = order.receive_line(
                    line_id=command.line_id,
                    quantity=command.quantity,
                    received_by=user_context.user_id,
                    batch_number=command.batch_number,
                    serial_numbers=command.serial_numbers,
                    expiry_date=command.expiry_date,
                    location=command.location
                )
            except ConcurrentModificationError as e:
                logger.warning(f"Concurrent modification detected: {e}")
                raise
            
            # ========== 4. حفظ معرف حركة المخزون في الأمر ==========
            if stock_movement_id:
                order.add_stock_movement(stock_movement_id)
            
            # ========== 5. حفظ التغييرات ==========
            order_repo.save(order)
            self._commit()
            
            logger.info(
                f"Line {command.line_id} received for purchase order {order.number} "
                f"(Qty: {command.quantity}, Total received: {received_line.received_quantity})"
            )
            
            return order_to_dto(order)