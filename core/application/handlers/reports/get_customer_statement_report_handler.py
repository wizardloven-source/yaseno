# core/application/handlers/reports/get_customer_statement_report_handler.py
"""
Get Customer Statement Report Handler - معالج كشف حساب العميل
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetCustomerStatementReportHandler(BaseQueryHandler):
    """
    معالج كشف حساب العميل
    
    يقوم بتوليد كشف حساب شامل لعميل معين
    """
    
    def __init__(self, customer_repo, invoice_repo, payment_repo):
        self._customer_repo = customer_repo
        self._invoice_repo = invoice_repo
        self._payment_repo = payment_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد كشف حساب العميل
        
        Args:
            query: GetCustomerStatementReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: كشف حساب العميل
        """
        logger.info(f"Generating customer statement for: {query.customer_id}")
        
        # جلب العميل
        customer = self._customer_repo.get_by_id(query.customer_id)
        if not customer:
            return {
                "success": False,
                "message": f"Customer '{query.customer_id}' not found"
            }
        
        # جلب فواتير العميل
        invoices = self._invoice_repo.list_by_customer(
            customer_id=query.customer_id,
            limit=10000
        )
        
        # جلب دفعات العميل
        payments = self._payment_repo.list_by_customer(
            customer_id=query.customer_id,
            limit=10000
        )
        
        # بناء كشف الحساب
        opening_balance = Decimal('0')
        transactions = []
        running_balance = opening_balance
        
        # إضافة الفواتير
        for invoice in invoices:
            if query.from_date and invoice.date < query.from_date:
                continue
            if query.to_date and invoice.date > query.to_date:
                continue
            
            running_balance += invoice.total.amount
            transactions.append({
                'date': invoice.date.isoformat(),
                'type': 'invoice',
                'reference': str(invoice.number) if invoice.number else None,
                'description': f"Invoice {invoice.number}",
                'debit': float(invoice.total.amount),
                'credit': 0,
                'balance': float(running_balance)
            })
        
        # إضافة الدفعات
        for payment in payments:
            if query.from_date and payment.date < query.from_date:
                continue
            if query.to_date and payment.date > query.to_date:
                continue
            
            running_balance -= payment.amount.amount
            transactions.append({
                'date': payment.date.isoformat(),
                'type': 'payment',
                'reference': str(payment.code) if payment.code else None,
                'description': f"Payment {payment.code}",
                'debit': 0,
                'credit': float(payment.amount.amount),
                'balance': float(running_balance)
            })
        
        # ترتيب حسب التاريخ
        transactions.sort(key=lambda x: x['date'])
        
        return {
            "success": True,
            "report_type": "customer_statement",
            "customer": {
                'id': str(customer.id),
                'code': str(customer.code),
                'name': customer.name,
                'email': customer.contact_info.email,
                'phone': customer.contact_info.phone
            },
            "from_date": query.from_date.isoformat() if query.from_date else None,
            "to_date": query.to_date.isoformat() if query.to_date else None,
            "currency": query.currency,
            "opening_balance": float(opening_balance),
            "closing_balance": float(running_balance),
            "transactions": transactions,
            "summary": {
                "total_invoices": float(sum(t['debit'] for t in transactions if t['type'] == 'invoice')),
                "total_payments": float(sum(t['credit'] for t in transactions if t['type'] == 'payment')),
                "net_change": float(running_balance - opening_balance)
            },
            "generated_at": datetime.now().isoformat()
        }