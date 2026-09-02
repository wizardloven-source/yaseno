# core/application/handlers/reports/get_kpi_report_handler.py
"""
Get KPI Report Handler - معالج تقرير مؤشرات الأداء
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetKPIReportHandler(BaseQueryHandler):
    """
    معالج تقرير مؤشرات الأداء (KPIs)
    
    يقوم بتوليد تقرير بمؤشرات الأداء الرئيسية
    """
    
    def __init__(self, invoice_repo, purchase_order_repo, ledger_engine):
        self._invoice_repo = invoice_repo
        self._purchase_order_repo = purchase_order_repo
        self._ledger_engine = ledger_engine
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير مؤشرات الأداء
        
        Args:
            query: GetKPIReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير مؤشرات الأداء
        """
        logger.info(f"Generating KPI report for period: {query.from_date} to {query.to_date}")
        
        # جلب الفواتير في الفترة
        invoices = self._invoice_repo.list_by_date_range(
            from_date=query.from_date,
            to_date=query.to_date,
            limit=10000
        )
        
        # جلب أوامر الشراء في الفترة
        purchase_orders = self._purchase_order_repo.list_by_date_range(
            from_date=query.from_date,
            to_date=query.to_date,
            limit=10000
        )
        
        # حساب المؤشرات
        total_sales = sum(inv.total.amount for inv in invoices)
        total_purchases = sum(po.total.amount for po in purchase_orders)
        total_invoices = len(invoices)
        total_orders = len(purchase_orders)
        
        # حساب متوسط قيمة الفاتورة
        avg_invoice = total_sales / total_invoices if total_invoices > 0 else Decimal('0')
        
        # حساب متوسط قيمة أمر الشراء
        avg_order = total_purchases / total_orders if total_orders > 0 else Decimal('0')
        
        # حساب عدد العملاء النشطين
        active_customers = len(set(inv.customer_id for inv in invoices))
        
        # حساب عدد الموردين النشطين
        active_suppliers = len(set(po.supplier_id for po in purchase_orders))
        
        return {
            "success": True,
            "report_type": "kpi",
            "from_date": query.from_date.isoformat(),
            "to_date": query.to_date.isoformat(),
            "currency": query.currency,
            "kpis": {
                "sales": {
                    "total_sales": float(total_sales),
                    "total_invoices": total_invoices,
                    "average_invoice_value": float(avg_invoice),
                    "active_customers": active_customers
                },
                "purchases": {
                    "total_purchases": float(total_purchases),
                    "total_orders": total_orders,
                    "average_order_value": float(avg_order),
                    "active_suppliers": active_suppliers
                },
                "ratios": {
                    "sales_to_purchases_ratio": float(total_sales / total_purchases) if total_purchases > 0 else 0,
                    "invoices_per_customer": float(total_invoices / active_customers) if active_customers > 0 else 0,
                    "orders_per_supplier": float(total_orders / active_suppliers) if active_suppliers > 0 else 0
                }
            },
            "generated_at": datetime.now().isoformat()
        }