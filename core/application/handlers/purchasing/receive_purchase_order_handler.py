# core/application/handlers/purchasing/receive_purchase_order_handler.py
"""
Receive Purchase Order Handler - استلام أمر شراء بالكامل
✅ جديد: معالج لاستلام جميع بنود أمر الشراء دفعة واحدة
✅ محدث: دعم Batch/Lot Tracking لكل سطر
✅ محدث: دعم Serial Numbers لكل سطر
✅ محدث: دعم Expiry Dates لكل سطر
✅ محدث: إنشاء حركات مخزون (StockMovement) لكل سطر
✅ محدث: تهيئة بطيئة (Lazy Initialization) لخدمة المخزون
"""

import logging
from typing import Dict, List, Optional
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
from core.application.purchasing.commands import ReceivePurchaseOrderCommand
from core.application.purchasing.dtos import PurchaseOrderDTO
from core.application.purchasing.converters import order_to_dto

logger = logging.getLogger(__name__)


class ReceivePurchaseOrderHandler(BaseHandler[ReceivePurchaseOrderCommand, PurchaseOrderDTO]):
    """
    معالج استلام أمر شراء بالكامل
    
    يقوم باستلام جميع بنود أمر الشراء دفعة واحدة مع:
        - إنشاء حركات مخزون (StockMovement) لكل سطر
        - دعم Batch/Lot Tracking لكل سطر
        - دعم Serial Numbers لكل سطر
        - دعم Expiry Dates لكل سطر
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
    def handle(self, command: ReceivePurchaseOrderCommand, user_context: UserContext) -> PurchaseOrderDTO:
        """
        معالجة استلام أمر الشراء
        
        Args:
            command: أمر استلام جميع بنود أمر الشراء
            user_context: سياق المستخدم
        
        Returns:
            PurchaseOrderDTO: أمر الشراء المحدث
        """
        order_id = command.order_id
        if not order_id:
            raise ValueError("order_id is required")
        
        logger.info(f"Receiving all items for purchase order {order_id} by {user_context.user_id}")
        
        with self._uow:
            order_repo = self._uow.purchase_orders
            order_id_obj = PurchaseOrderId(UUID(order_id))
            
            order = order_repo.get_by_id(order_id_obj)
            if not order:
                raise PurchaseOrderNotFoundError(order_id)
            
            # ========== 1. التحقق من إمكانية الاستلام ==========
            if not order.is_posted:
                from core.domain.purchasing.exceptions import CannotReceiveUnpostedPurchaseOrderError
                raise CannotReceiveUnpostedPurchaseOrderError(str(order_id_obj))
            
            if order.is_fully_received:
                logger.info(f"Purchase order {order.number} is already fully received")
                return order_to_dto(order)
            
            # ========== 2. استلام جميع البنود ==========
            received_lines = []
            stock_movements = []
            
            # استخراج تفاصيل المخزون من الأمر
            batch_numbers = command.batch_numbers or {}
            serial_numbers = command.serial_numbers or {}
            expiry_dates = command.expiry_dates or {}
            locations = command.locations or {}
            
            # ✅ الحصول على خدمة المخزون (تهيئة بطيئة)
            stock_service = self._get_stock_service()
            
            for line in order.lines:
                if line.is_fully_received:
                    continue
                
                remaining = line.remaining_quantity
                line_id = line.line_id
                
                # ========== 2a. إنشاء حركة مخزون ==========
                stock_movement_id = None
                try:
                    from core.domain.products.value_objects import ProductCode
                    product = self._uow.products.get_by_code(ProductCode(line.product_code))
                    if product:
                        entity = EntityId("product", str(product.id))
                        
                        movement = stock_service.create_inbound_movement(
                            entity=entity,
                            quantity=remaining,
                            unit_cost=InventoryMoney(
                                line.unit_price.amount,
                                line.unit_price.currency
                            ),
                            movement_type=StockMovementType.PURCHASE,
                            reference_type="PurchaseOrder",
                            reference_id=str(order.id),
                            batch_number=BatchNumber(batch_numbers.get(line_id)) if batch_numbers.get(line_id) else None,
                            expiry_date=ExpiryDate(expiry_dates.get(line_id)) if expiry_dates.get(line_id) else None,
                            location=locations.get(line_id),
                            notes=f"استلام كامل من أمر {order.number} - {line.product_name}",
                            created_by=user_context.user_id
                        )
                        
                        stock_movement_id = str(movement.id)
                        
                        stock_movements.append({
                            'line_id': line_id,
                            'product_code': line.product_code,
                            'movement_id': stock_movement_id,
                            'quantity': float(remaining),
                            'unit_cost': float(line.unit_price.amount),
                            'total_cost': float(line.total.amount),
                            'currency': line.currency,
                        })
                        
                except Exception as e:
                    logger.error(f"Error creating stock movement for line {line_id}: {e}")
                    # لا نمنع الاستلام، ولكن نسجل الخطأ
                
                # ========== 2b. استلام السطر ==========
                try:
                    received_line = order.receive_line(
                        line_id=line_id,
                        quantity=remaining,
                        received_by=user_context.user_id,
                        batch_number=batch_numbers.get(line_id),
                        serial_numbers=serial_numbers.get(line_id),
                        expiry_date=expiry_dates.get(line_id),
                        location=locations.get(line_id)
                    )
                    received_lines.append(received_line)
                    
                    # حفظ معرف حركة المخزون
                    if stock_movement_id:
                        order.add_stock_movement(stock_movement_id)
                        
                except ConcurrentModificationError as e:
                    logger.warning(f"Concurrent modification detected: {e}")
                    raise
            
            # ========== 3. حفظ التغييرات ==========
            order_repo.save(order)
            self._commit()
            
            logger.info(
                f"Purchase order {order.number} fully received "
                f"({len(received_lines)} lines, {len(stock_movements)} stock movements)"
            )
            
            # ========== 4. إرجاع النتيجة ==========
            from dataclasses import replace
            result = replace(order_to_dto(order), stock_movements=stock_movements)
        
        return order_to_dto(order)