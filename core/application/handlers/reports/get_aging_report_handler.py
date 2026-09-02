# core/application/handlers/reports/get_aging_report_handler.py
"""
Get Aging Report Handler - معالج تقرير الأعمار
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetAgingReportHandler(BaseQueryHandler):
    """
    معالج تقرير الأعمار (Aging Report)
    
    يقوم بتوليد تقرير الأعمار للفواتير المستحقة
    """
    
    def __init__(self, invoice_repo, payment_repo):
        self._invoice_repo = invoice_repo
        self._payment_repo = payment_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد تقرير الأعمار
        
        Args:
            query: GetAgingReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: تقرير الأعمار
        """
        logger.info(f"Generating aging report as of: {query.as_of_date}")
        
        # جلب الفواتير المرحلة غير المدفوعة
        invoices = self._invoice_repo.list_by_status(
            status='posted',
            limit=10000
        )
        
        # تصفية الفواتير غير المدفوعة
        aging_data = []
        total_by_period = {
            '0-30': Decimal('0'),
            '31-60': Decimal('0'),
            '61-90': Decimal('0'),
            '90+': Decimal('0')
        }
        
        for invoice in invoices:
            # حساب عمر الفاتورة
            days_old = (query.as_of_date - invoice.date.date()).days
            
            # تحديد الفترة
            if days_old <= 30:
                period = '0-30'
            elif days_old <= 60:
                period = '31-60'
            elif days_old <= 90:
                period = '61-90'
            else:
                period = '90+'
            
            # حساب المبلغ المستحق (مبسط)
            amount = invoice.total.amount
            total_by_period[period] += amount
            
            aging_data.append({
                'invoice_id': str(invoice.id),
                'invoice_number': str(invoice.number) if invoice.number else None,
                'customer_name': invoice.customer_name,
                'invoice_date': invoice.date.isoformat(),
                'due_date': (invoice.date + timedelta(days=30)).isoformat(),
                'days_old': days_old,
                'amount': float(amount),
                'currency': invoice.currency,
                'period': period
            })
        
        return {
            "success": True,
            "report_type": "aging",
            "as_of_date": query.as_of_date.isoformat(),
            "currency": query.currency,
            "summary": {
                "total_0_30": float(total_by_period['0-30']),
                "total_31_60": float(total_by_period['31-60']),
                "total_61_90": float(total_by_period['61-90']),
                "total_90_plus": float(total_by_period['90+']),
                "total_outstanding": float(sum(total_by_period.values()))
            },
            "data": aging_data,
            "total_invoices": len(aging_data),
            "generated_at": datetime.now().isoformat()
        }