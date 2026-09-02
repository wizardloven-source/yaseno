# core/application/handlers/payments/get_payment_allocations_query_handler.py

"""
Get Payment Allocations Query Handler - استعلام لجلب توزيعات الدفعات
الإصدار: 2.0.0
✅ دعم التصفية حسب الحالة
✅ دعم Pagination
✅ دعم تضمين التوزيعات الملغاة
"""

import logging
from typing import List, Dict, Any

from core.domain.payments.value_objects import PaymentId
from core.domain.payments.exceptions import PaymentNotFoundError
from core.domain.payments.interfaces import IPaymentRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import GetPaymentAllocationsQuery
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class GetPaymentAllocationsQueryHandler(BaseQueryHandler[GetPaymentAllocationsQuery, List[Dict[str, Any]]]):
    """
    معالج استعلام لجلب توزيعات الدفعات
    
    يقوم بجلب جميع توزيعات الدفعة المحددة مع:
        1. تفاصيل الفواتير المرتبطة
        2. حالة كل توزيع
        3. المبالغ الموزعة
        4. تواريخ التوزيع
    """
    
    def __init__(self, payment_repo: IPaymentRepository):
        self._payment_repo = payment_repo
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetPaymentAllocationsQuery) -> List[Dict[str, Any]]:
        """
        تنفيذ جلب توزيعات الدفعة
        
        Args:
            query: استعلام جلب توزيعات الدفعة
        
        Returns:
            List[Dict[str, Any]]: قائمة التوزيعات
        """
        logger.debug(f"Fetching allocations for payment: {query.payment_id}")
        
        # 1. جلب الدفعة
        payment = self._payment_repo.get_by_id(PaymentId.from_string(query.payment_id))
        
        if not payment:
            logger.warning(f"Payment not found: {query.payment_id}")
            return []
        
        # 2. جلب التوزيعات من المستودع
        allocations = self._payment_repo.get_allocations(
            payment_id=query.payment_id,
            include_cancelled=query.include_cancelled
        )
        
        # 3. تنسيق النتائج
        result = []
        for allocation in allocations:
            # جلب تفاصيل الفاتورة
            invoice = None
            if allocation.get('invoice_id'):
                try:
                    invoice = self._payment_repo._session.query(
                        InvoiceModel
                    ).filter(
                        InvoiceModel.id == allocation['invoice_id']
                    ).first()
                except Exception as e:
                    logger.warning(f"Could not fetch invoice {allocation.get('invoice_id')}: {e}")
            
            result.append({
                'allocation_id': allocation.get('id'),
                'payment_id': str(payment.id),
                'payment_code': str(payment.code),
                'invoice_id': allocation.get('invoice_id'),
                'invoice_number': invoice.number if invoice else None,
                'invoice_date': invoice.invoice_date.isoformat() if invoice and invoice.invoice_date else None,
                'customer_name': invoice.customer_name if invoice else None,
                'amount': float(allocation.get('amount', 0)),
                'currency': allocation.get('currency', payment.currency),
                'status': allocation.get('status', 'pending'),
                'allocated_at': allocation.get('created_at').isoformat() if allocation.get('created_at') else None,
                'allocated_by': allocation.get('created_by'),
                'reversed_at': allocation.get('reversed_at').isoformat() if allocation.get('reversed_at') else None,
                'reversed_by': allocation.get('reversed_by'),
                'reversal_reason': allocation.get('reversal_reason'),
                'journal_entry_id': allocation.get('journal_entry_id'),
                'is_reversed': allocation.get('status') == 'reversed',
                'is_active': allocation.get('status') not in ['reversed', 'cancelled']
            })
        
        logger.info(f"Found {len(result)} allocations for payment {query.payment_id}")
        
        return result
    
    def get_allocation_summary(self, payment_id: str) -> Dict[str, Any]:
        """
        الحصول على ملخص توزيعات الدفعة
        
        Args:
            payment_id: معرف الدفعة
        
        Returns:
            Dict[str, Any]: ملخص التوزيعات
        """
        allocations = self.handle(GetPaymentAllocationsQuery(
            payment_id=payment_id,
            include_cancelled=False
        ))
        
        total_allocated = sum(a['amount'] for a in allocations)
        
        return {
            'payment_id': payment_id,
            'total_allocations': len(allocations),
            'total_allocated': total_allocated,
            'active_allocations': len([a for a in allocations if a['is_active']]),
            'reversed_allocations': len([a for a in allocations if a['is_reversed']]),
            'allocations': allocations
        }