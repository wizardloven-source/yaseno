"""
Inventory Integration Handlers - معالجات تكامل المخزون
"""

import logging
from typing import Optional
from decimal import Decimal

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.domain.inventory.integration import (
    InventoryAccountingIntegration,
    StockIntegrationRequest,
    StockIntegrationResult
)

logger = logging.getLogger(__name__)


class ProcessSaleHandler(BaseHandler):
    """
    معالج معالجة عملية بيع مع تكامل المخزون
    """
    
    def __init__(self, integration: InventoryAccountingIntegration):
        self._integration = integration
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command, user_context: UserContext) -> StockIntegrationResult:
        """
        معالجة طلب البيع
        
        Args:
            command: ProcessSaleCommand
            user_context: سياق المستخدم
        
        Returns:
            StockIntegrationResult: نتيجة العملية
        """
        logger.info(f"Processing sale by {user_context.username}")
        
        request = StockIntegrationRequest(
            product_id=command.product_id,
            quantity=command.quantity,
            unit_cost=command.unit_cost,
            currency=command.currency,
            reference_type="Invoice",
            reference_id=command.invoice_id,
            movement_type="sale",
            cost_method=command.cost_method or "fifo",
            date=command.date,
            created_by=user_context.user_id,
            batch_number=command.batch_number,
            serial_numbers=command.serial_numbers,
            expiry_date=command.expiry_date,
            location=command.location,
            cost_center=command.cost_center,
            profit_center=command.profit_center
        )
        
        return self._integration.process_sale(request)


class ProcessPurchaseHandler(BaseHandler):
    """
    معالج معالجة عملية شراء مع تكامل المخزون
    """
    
    def __init__(self, integration: InventoryAccountingIntegration):
        self._integration = integration
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command, user_context: UserContext) -> StockIntegrationResult:
        """
        معالجة طلب الشراء
        
        Args:
            command: ProcessPurchaseCommand
            user_context: سياق المستخدم
        
        Returns:
            StockIntegrationResult: نتيجة العملية
        """
        logger.info(f"Processing purchase by {user_context.username}")
        
        request = StockIntegrationRequest(
            product_id=command.product_id,
            quantity=command.quantity,
            unit_cost=command.unit_cost,
            currency=command.currency,
            reference_type="PurchaseOrder",
            reference_id=command.purchase_order_id,
            movement_type="purchase",
            cost_method="fifo",  # الشراء دائماً بـ FIFO
            date=command.date,
            created_by=user_context.user_id,
            batch_number=command.batch_number,
            serial_numbers=command.serial_numbers,
            expiry_date=command.expiry_date,
            location=command.location,
            cost_center=command.cost_center,
            profit_center=command.profit_center
        )
        
        return self._integration.process_purchase(request)


class ProcessAdjustmentHandler(BaseHandler):
    """
    معالج معالجة تعديل المخزون
    """
    
    def __init__(self, integration: InventoryAccountingIntegration):
        self._integration = integration
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command, user_context: UserContext) -> StockIntegrationResult:
        """
        معالجة طلب التعديل
        
        Args:
            command: ProcessAdjustmentCommand
            user_context: سياق المستخدم
        
        Returns:
            StockIntegrationResult: نتيجة العملية
        """
        logger.info(f"Processing adjustment by {user_context.username}")
        
        request = StockIntegrationRequest(
            product_id=command.product_id,
            quantity=command.quantity,  # يمكن أن يكون موجباً أو سالباً
            unit_cost=command.unit_cost,
            currency=command.currency,
            reference_type="Adjustment",
            reference_id=command.adjustment_id,
            movement_type="adjustment",
            cost_method="fifo",
            date=command.date,
            created_by=user_context.user_id,
            batch_number=command.batch_number,
            serial_numbers=command.serial_numbers,
            expiry_date=command.expiry_date,
            location=command.location,
            cost_center=command.cost_center,
            profit_center=command.profit_center
        )
        
        return self._integration.process_adjustment(request)