# core/application/handlers/suppliers/get_supplier_statement_query_handler.py

"""
Get Supplier Statement Query Handler - استعلام لكشف حساب المورد
"""

import logging
from typing import Dict, Any
from decimal import Decimal

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.suppliers.commands import GetSupplierStatementQuery

logger = logging.getLogger(__name__)


class GetSupplierStatementQueryHandler(BaseQueryHandler[GetSupplierStatementQuery, Dict[str, Any]]):
    """
    معالج استعلام لكشف حساب المورد

    يقوم بإنشاء كشف حساب شامل لمورد معين يشمل جميع أوامر الشراء والمدفوعات.
    """

    def __init__(self, uow: IUnitOfWork):  # ✅ معامل واحد فقط
        super().__init__(uow)
        self._uow = uow

    @require_permission(Permission.VIEW_TRIAL_BALANCE)
    def handle(self, query: GetSupplierStatementQuery) -> Dict[str, Any]:
        """
        تنفيذ جلب كشف حساب المورد

        Args:
            query: استعلام كشف حساب المورد

        Returns:
            Dict[str, Any]: كشف حساب المورد
        """
        logger.debug(f"Generating supplier statement for: {query.supplier_id}")

        with self._uow:  # ✅ استخدام uow
            # جلب المورد من المستودع عبر uow
            supplier_repo = self._uow.suppliers
            supplier = supplier_repo.get_by_id(query.supplier_id)
            if not supplier:
                return {
                    "success": False,
                    "message": f"Supplier '{query.supplier_id}' not found"
                }

            # جلب أوامر شراء المورد
            purchase_order_repo = self._uow.purchase_orders
            orders = purchase_order_repo.list_by_supplier(
                supplier_id=query.supplier_id,
                limit=10000
            )

            # جلب دفعات المورد
            payment_repo = self._uow.payments
            payments = payment_repo.list_by_supplier(
                supplier_id=query.supplier_id,
                limit=10000
            )

            # بناء كشف الحساب
            opening_balance = Decimal('0')
            transactions = []
            running_balance = opening_balance

            # إضافة أوامر الشراء
            for order in orders:
                if query.from_date and order.date.date() < query.from_date:
                    continue
                if query.to_date and order.date.date() > query.to_date:
                    continue

                running_balance += order.total.amount
                transactions.append({
                    'date': order.date.isoformat(),
                    'type': 'order',
                    'reference': str(order.number) if order.number else None,
                    'description': f"Purchase Order {order.number}",
                    'debit': float(order.total.amount),
                    'credit': 0,
                    'balance': float(running_balance),
                    'currency': order.currency
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
                "generated_at": query.generated_at.isoformat() if hasattr(query, 'generated_at') else None
            }