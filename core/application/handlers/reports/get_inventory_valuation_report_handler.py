# core/application/handlers/reports/get_inventory_valuation_report_handler.py
"""
Get Inventory Valuation Report Handler - معالج تقرير تقييم المخزون
"""

import logging
from datetime import datetime

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetInventoryValuationReportHandler(BaseQueryHandler):
    """
    معالج تقرير تقييم المخزون
    
    يقوم بتقييم المخزون باستخدام طرق مختلفة (FIFO, LIFO, Average)
    """
    
    def __init__(self, product_repo, inventory_valuation_service):
        self._product_repo = product_repo
        self._valuation_service = inventory_valuation_service
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير تقييم المخزون
        
        Args:
            query: GetInventoryValuationReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقييم المخزون
        """
        logger.info(f"Generating inventory valuation report using {query.method}")
        
        # جلب جميع المنتجات
        products = self._product_repo.list_all(limit=10000)
        
        valuations = []
        total_value = 0
        
        for product in products:
            # حساب التقييم
            valuation = self._valuation_service.calculate_valuation(
                entity_id=str(product.id),
                as_of_date=query.as_of_date,
                method=query.method
            )
            
            valuations.append({
                'product_id': str(product.id),
                'product_code': product.code.value,
                'product_name': product.name,
                'quantity': float(valuation['total_quantity']),
                'unit_cost': float(valuation['average_cost']),
                'total_value': float(valuation['total_cost']),
                'currency': valuation['currency']
            })
            total_value += valuation['total_cost']
        
        return {
            "success": True,
            "report_type": "inventory_valuation",
            "as_of_date": query.as_of_date.isoformat(),
            "method": query.method,
            "data": valuations,
            "summary": {
                "total_products": len(valuations),
                "total_value": float(total_value),
                "currency": query.currency
            },
            "generated_at": datetime.now().isoformat()
        }