# core/application/handlers/reports/get_purchases_report_handler.py
"""
Get Purchases Report Handler - معالج تقرير المشتريات
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetPurchasesReportHandler(BaseQueryHandler):
    """
    معالج تقرير المشتريات
    
    يقوم بتوليد تقرير المشتريات لفترة محددة
    """
    
    def __init__(self, purchase_order_repo):
        self._purchase_order_repo = purchase_order_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير المشتريات
        
        Args:
            query: GetPurchasesReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير المشتريات
        """
        logger.info(f"Generating purchases report for period: {query.from_date} to {query.to_date}")
        
        # جلب أوامر الشراء في الفترة
        orders = self._purchase_order_repo.list_by_date_range(
            from_date=query.from_date,
            to_date=query.to_date,
            limit=10000
        )
        
        # تجميع البيانات
        total_purchases = Decimal('0')
        total_orders = len(orders)
        
        purchases_by_supplier = {}
        purchases_by_product = {}
        
        for order in orders:
            total_purchases += order.total.amount
            
            # تجميع حسب المورد
            supplier_key = order.supplier_id
            if supplier_key not in purchases_by_supplier:
                purchases_by_supplier[supplier_key] = {
                    'supplier_id': supplier_key,
                    'supplier_name': order.supplier_name,
                    'total': Decimal('0'),
                    'count': 0
                }
            purchases_by_supplier[supplier_key]['total'] += order.total.amount
            purchases_by_supplier[supplier_key]['count'] += 1
            
            # تجميع حسب المنتج
            for line in order.lines:
                product_key = line.product_code
                if product_key not in purchases_by_product:
                    purchases_by_product[product_key] = {
                        'product_code': product_key,
                        'product_name': line.product_name,
                        'total': Decimal('0'),
                        'quantity': Decimal('0')
                    }
                purchases_by_product[product_key]['total'] += line.total.amount
                purchases_by_product[product_key]['quantity'] += line.quantity
        
        return {
            "success": True,
            "report_type": "purchases",
            "from_date": query.from_date.isoformat(),
            "to_date": query.to_date.isoformat(),
            "currency": query.currency,
            "summary": {
                "total_orders": total_orders,
                "total_purchases": float(total_purchases),
                "average_order": float(total_purchases / total_orders) if total_orders > 0 else 0
            },
            "by_supplier": list(purchases_by_supplier.values()),
            "by_product": list(purchases_by_product.values()),
            "generated_at": datetime.now().isoformat()
        }