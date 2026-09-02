# core/application/handlers/reports/get_inventory_report_handler.py
"""
Get Inventory Report Handler - معالج تقرير المخزون
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetInventoryReportHandler(BaseQueryHandler):
    """
    معالج تقرير المخزون
    
    يقوم بتوليد تقرير شامل عن المخزون
    """
    
    def __init__(self, product_repo, stock_movement_repo):
        self._product_repo = product_repo
        self._stock_movement_repo = stock_movement_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير المخزون
        
        Args:
            query: GetInventoryReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير المخزون
        """
        logger.info(f"Generating inventory report")
        
        # جلب جميع المنتجات
        products = self._product_repo.list_all(include_inactive=query.include_inactive, limit=10000)
        
        inventory_data = []
        total_stock_value = Decimal('0')
        
        for product in products:
            stock_value = product.unit_price.amount * Decimal(str(product.stock_quantity))
            total_stock_value += stock_value
            
            inventory_data.append({
                'product_id': str(product.id),
                'product_code': product.code.value,
                'product_name': product.name,
                'category': product.category,
                'stock_quantity': float(product.stock_quantity),
                'unit_price': float(product.unit_price.amount),
                'stock_value': float(stock_value),
                'currency': product.unit_price.currency,
                'is_active': product.is_active,
                'status': 'active' if product.is_active else 'inactive'
            })
        
        return {
            "success": True,
            "report_type": "inventory",
            "data": inventory_data,
            "summary": {
                "total_products": len(inventory_data),
                "total_stock_value": float(total_stock_value),
                "active_products": len([p for p in inventory_data if p['is_active']]),
                "inactive_products": len([p for p in inventory_data if not p['is_active']])
            },
            "generated_at": datetime.now().isoformat()
        }