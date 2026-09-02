# core/application/handlers/reports/get_supplier_report_handler.py
"""
Get Supplier Report Handler - معالج تقرير الموردين
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetSupplierReportHandler(BaseQueryHandler):
    """
    معالج تقرير الموردين
    
    يقوم بتوليد تقرير شامل عن الموردين
    """
    
    def __init__(self, supplier_repo, purchase_order_repo):
        self._supplier_repo = supplier_repo
        self._purchase_order_repo = purchase_order_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير الموردين
        
        Args:
            query: GetSupplierReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير الموردين
        """
        logger.info(f"Generating supplier report: {query.supplier_id or 'all'}")
        
        # جلب الموردين
        if query.supplier_id:
            suppliers = [self._supplier_repo.get_by_id(query.supplier_id)]
        else:
            suppliers = self._supplier_repo.list_all(limit=1000)
        
        supplier_data = []
        for supplier in suppliers:
            if not supplier:
                continue
            
            # جلب أوامر شراء المورد
            orders = self._purchase_order_repo.list_by_supplier(
                supplier_id=str(supplier.id),
                limit=10000
            )
            
            total_orders = len(orders)
            total_amount = sum(order.total.amount for order in orders)
            
            supplier_data.append({
                'supplier_id': str(supplier.id),
                'supplier_code': str(supplier.code),
                'supplier_name': supplier.name,
                'email': supplier.contact_info.email,
                'phone': supplier.contact_info.phone,
                'status': supplier.status.value,
                'total_orders': total_orders,
                'total_amount': float(total_amount),
                'credit_limit': float(supplier.credit_limit),
                'currency': supplier.currency,
                'last_order_date': max(order.date for order in orders).isoformat() if orders else None
            })
        
        return {
            "success": True,
            "report_type": "supplier_report",
            "data": supplier_data,
            "total_suppliers": len(supplier_data),
            "generated_at": datetime.now().isoformat()
        }