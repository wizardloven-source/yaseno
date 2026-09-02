# core/application/handlers/reports/get_customer_report_handler.py
"""
Get Customer Report Handler - معالج تقرير العملاء
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetCustomerReportHandler(BaseQueryHandler):
    """
    معالج تقرير العملاء
    
    يقوم بتوليد تقرير شامل عن العملاء
    """
    
    def __init__(self, customer_repo, invoice_repo):
        self._customer_repo = customer_repo
        self._invoice_repo = invoice_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير العملاء
        
        Args:
            query: GetCustomerReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير العملاء
        """
        logger.info(f"Generating customer report: {query.customer_id or 'all'}")
        
        # جلب العملاء
        if query.customer_id:
            customers = [self._customer_repo.get_by_id(query.customer_id)]
        else:
            customers = self._customer_repo.list_all(limit=1000)
        
        customer_data = []
        for customer in customers:
            if not customer:
                continue
            
            # جلب فواتير العميل
            invoices = self._invoice_repo.list_by_customer(
                customer_id=str(customer.id),
                limit=10000
            )
            
            total_invoices = len(invoices)
            total_amount = sum(inv.total.amount for inv in invoices)
            total_paid = sum(inv.paid_amount.amount if hasattr(inv, 'paid_amount') else Decimal('0') for inv in invoices)
            
            customer_data.append({
                'customer_id': str(customer.id),
                'customer_code': str(customer.code),
                'customer_name': customer.name,
                'email': customer.contact_info.email,
                'phone': customer.contact_info.phone,
                'status': customer.status.value,
                'total_invoices': total_invoices,
                'total_amount': float(total_amount),
                'total_paid': float(total_paid),
                'balance': float(total_amount - total_paid),
                'credit_limit': float(customer.credit_limit),
                'currency': customer.currency,
                'last_invoice_date': max(inv.date for inv in invoices).isoformat() if invoices else None
            })
        
        return {
            "success": True,
            "report_type": "customer_report",
            "data": customer_data,
            "total_customers": len(customer_data),
            "generated_at": datetime.now().isoformat()
        }