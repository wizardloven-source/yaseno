# core/application/handlers/reports/get_low_stock_report_handler.py
"""
Get Low Stock Report Handler - معالج تقرير المخزون المنخفض
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetLowStockReportHandler(BaseQueryHandler):
    """
    معالج تقرير المخزون المنخفض
    
    يقوم بتوليد تقرير بالمنتجات التي وصلت إلى حد الطلب
    """
    
    def __init__(self, product_repo):
        self._product_repo = product_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير المخزون المنخفض
        
        Args:
            query: GetLowStockReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير المخزون المنخفض
        """
        logger.info(f"Generating low stock report with threshold: {query.threshold}")
        
        # جلب المنتجات منخفضة المخزون
        products = self._product_repo.get_low_stock(
            threshold=query.threshold,
            limit=query.limit or 1000
        )
        
        low_stock_items = []
        for product in products:
            low_stock_items.append({
                'product_id': str(product.id),
                'product_code': product.code.value,
                'product_name': product.name,
                'category': product.category,
                'current_stock': float(product.stock_quantity),
                'min_stock': float(product.min_stock),
                'max_stock': float(product.max_stock),
                'unit_price': float(product.unit_price.amount),
                'currency': product.unit_price.currency,
                'shortage': float(product.min_stock - product.stock_quantity) if product.stock_quantity < product.min_stock else 0
            })
        
        return {
            "success": True,
            "report_type": "low_stock",
            "threshold": query.threshold,
            "data": low_stock_items,
            "summary": {
                "total_items": len(low_stock_items),
                "critical_items": len([i for i in low_stock_items if i['stock_quantity'] == 0])
            },
            "generated_at": datetime.now().isoformat()
        }