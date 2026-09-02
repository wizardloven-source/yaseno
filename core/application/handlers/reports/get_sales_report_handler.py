# core/application/handlers/reports/get_sales_report_handler.py
"""
Get Sales Report Handler - معالج تقرير المبيعات
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetSalesReportHandler(BaseQueryHandler):
    """
    معالج تقرير المبيعات
    
    يقوم بتوليد تقرير المبيعات لفترة محددة
    """
    
    def __init__(self, invoice_repo):
        self._invoice_repo = invoice_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير المبيعات
        
        Args:
            query: GetSalesReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير المبيعات
        """
        logger.info(f"Generating sales report for period: {query.from_date} to {query.to_date}")
        
        # جلب الفواتير في الفترة
        invoices = self._invoice_repo.list_by_date_range(
            from_date=query.from_date,
            to_date=query.to_date,
            limit=10000
        )
        
        # تجميع البيانات
        total_sales = Decimal('0')
        total_tax = Decimal('0')
        total_invoices = len(invoices)
        
        sales_by_customer = {}
        sales_by_product = {}
        
        for invoice in invoices:
            total_sales += invoice.total.amount
            total_tax += invoice.tax_amount.amount
            
            # تجميع حسب العميل
            customer_key = invoice.customer_id
            if customer_key not in sales_by_customer:
                sales_by_customer[customer_key] = {
                    'customer_id': customer_key,
                    'customer_name': invoice.customer_name,
                    'total': Decimal('0'),
                    'count': 0
                }
            sales_by_customer[customer_key]['total'] += invoice.total.amount
            sales_by_customer[customer_key]['count'] += 1
            
            # تجميع حسب المنتج
            for line in invoice.lines:
                product_key = line.product_code
                if product_key not in sales_by_product:
                    sales_by_product[product_key] = {
                        'product_code': product_key,
                        'product_name': line.product_name,
                        'total': Decimal('0'),
                        'quantity': Decimal('0')
                    }
                sales_by_product[product_key]['total'] += line.total.amount
                sales_by_product[product_key]['quantity'] += line.quantity
        
        return {
            "success": True,
            "report_type": "sales",
            "from_date": query.from_date.isoformat(),
            "to_date": query.to_date.isoformat(),
            "currency": query.currency,
            "summary": {
                "total_invoices": total_invoices,
                "total_sales": float(total_sales),
                "total_tax": float(total_tax),
                "average_invoice": float(total_sales / total_invoices) if total_invoices > 0 else 0
            },
            "by_customer": list(sales_by_customer.values()),
            "by_product": list(sales_by_product.values()),
            "generated_at": datetime.now().isoformat()
        }