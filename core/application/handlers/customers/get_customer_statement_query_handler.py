# core/application/handlers/customers/get_customer_statement_query_handler.py

"""
Get Customer Statement Query Handler - استعلام لكشف حساب العميل
"""

import logging
from typing import Dict, Any
from decimal import Decimal

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.customers.commands import GetCustomerStatementQuery

logger = logging.getLogger(__name__)


class GetCustomerStatementQueryHandler(BaseQueryHandler[GetCustomerStatementQuery, Dict[str, Any]]):
    """
    معالج استعلام لكشف حساب العميل

    يقوم بإنشاء كشف حساب شامل لعميل معين يشمل جميع الفواتير والمدفوعات.
    """

    def __init__(self, uow: IUnitOfWork):
        # ✅ تمرير uow إلى BaseQueryHandler
        super().__init__(uow)
        self._uow = uow

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetCustomerStatementQuery) -> Dict[str, Any]:
        """
        تنفيذ جلب كشف حساب العميل

        Args:
            query: استعلام كشف حساب العميل

        Returns:
            Dict[str, Any]: كشف حساب العميل
        """
        logger.debug(f"Generating customer statement for: {query.customer_id}")

        with self._uow:
            # جلب العميل من المستودع عبر uow
            customer_repo = self._uow.customers
            customer = customer_repo.get_by_id(query.customer_id)
            if not customer:
                return {
                    "success": False,
                    "message": f"Customer '{query.customer_id}' not found"
                }

            # جلب فواتير العميل
            invoice_repo = self._uow.invoices
            invoices = invoice_repo.list_by_customer(
                customer_id=query.customer_id,
                limit=10000
            )

            # جلب دفعات العميل
            payment_repo = self._uow.payments
            payments = payment_repo.list_by_customer(
                customer_id=query.customer_id,
                limit=10000
            )

            # بناء كشف الحساب
            opening_balance = Decimal('0')
            transactions = []
            running_balance = opening_balance

            # إضافة الفواتير
            for invoice in invoices:
                if query.from_date and invoice.date.date() < query.from_date:
                    continue
                if query.to_date and invoice.date.date() > query.to_date:
                    continue

                running_balance += invoice.total.amount
                transactions.append({
                    'date': invoice.date.isoformat(),
                    'type': 'invoice',
                    'reference': str(invoice.number) if invoice.number else None,
                    'description': f"Invoice {invoice.number}",
                    'debit': float(invoice.total.amount),
                    'credit': 0,
                    'balance': float(running_balance),
                    'currency': invoice.currency
                })

            # إضافة الدفعات
            for payment in payments:
                if query.from_date and payment.date.date() < query.from_date:
                    continue
                if query.to_date and payment.date.date() > query.to_date:
                    continue

                running_balance -= payment.amount.amount
                transactions.append({
                    'date': payment.date.isoformat(),
                    'type': 'payment',
                    'reference': str(payment.code) if payment.code else None,
                    'description': f"Payment {payment.code}",
                    'debit': 0,
                    'credit': float(payment.amount.amount),
                    'balance': float(running_balance),
                    'currency': payment.currency
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
                "generated_at": query.generated_at.isoformat() if hasattr(query, 'generated_at') else None
            }