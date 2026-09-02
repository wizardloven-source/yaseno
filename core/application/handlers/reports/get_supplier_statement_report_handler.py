# core/application/handlers/reports/get_supplier_statement_report_handler.py
"""
Get Supplier Statement Report Handler - معالج كشف حساب المورد
"""

import logging
from datetime import datetime
from decimal import Decimal

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission

logger = logging.getLogger(__name__)


class GetSupplierStatementReportHandler(BaseQueryHandler):
    """
    معالج كشف حساب المورد
    
    يقوم بتوليد كشف حساب شامل لمورد معين
    """
    
    def __init__(self, supplier_repo, purchase_order_repo, payment_repo):
        self._supplier_repo = supplier_repo
        self._purchase_order_repo = purchase_order_repo
        self._payment_repo = payment_repo
    
    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query, user_context: UserContext = None):
        """
        تنفيذ توليد كشف حساب المورد
        
        Args:
            query: GetSupplierStatementReportQuery
            user_context: سياق المستخدم
        
        Returns:
            dict: كشف حساب المورد
        """
        logger.info(f"Generating supplier statement for: {query.supplier_id}")
        
        # جلب المورد
        supplier = self._supplier_repo.get_by_id(query.supplier_id)
        if not supplier:
            return {
                "success": False,
                "message": f"Supplier '{query.supplier_id}' not found"
            }
        
        # جلب أوامر شراء المورد
        orders = self._purchase_order_repo.list_by_supplier(
            supplier_id=query.supplier_id,
            limit=10000
        )
        
        # جلب دفعات المورد
        payments = self._payment_repo.list_by_supplier(
            supplier_id=query.supplier_id,
            limit=10000
        )
        
        # بناء كشف الحساب
        opening_balance = Decimal('0')
        transactions = []
        running_balance = opening_balance        
        # إضافة أوامر الشراء
        for order in orders:
            if query.from_date and order.date < query.from_date:
                continue
            if query.to_date and order.date > query.to_date:
                continue
            
            running_balance += order.total.amount
            transactions.append({
                'date': order.date.isoformat(),
                'type': 'order',
                'reference': str(order.number) if order.number else None,
                'description': f"Purchase Order {order.number}",
                'debit': float(order.total.amount),
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
            "report_type": "supplier_statement",
            "supplier": {
                'id': str(supplier.id),
                'code': str(supplier.code),
                'name': supplier.name,
                'email': supplier.contact_info.email,
                'phone': supplier.contact_info.phone
            },
            "from_date": query.from_date.isoformat() if query.from_date else None,
            "to_date": query.to_date.isoformat() if query.to_date else None,
            "currency": query.currency,
            "opening_balance": float(opening_balance),
            "closing_balance": float(running_balance),
            "transactions": transactions,
            "summary": {
                "total_orders": float(sum(t['debit'] for t in transactions if t['type'] == 'order')),
                "total_payments": float(sum(t['credit'] for t in transactions if t['type'] == 'payment')),
                "net_change": float(running_balance - opening_balance)
            },
            "generated_at": datetime.now().isoformat()
        }