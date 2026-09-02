# core/application/handlers/payments/list_payments_query_handler.py
"""
List Payments Query Handler - معالج استعلام لجلب قائمة الدفعات
"""

import logging
from typing import List

from core.domain.payments.value_objects import PaymentType, PaymentStatus
from core.domain.accounting.interfaces import IUnitOfWork

from .base_handler import BasePaymentQueryHandler
from core.application.payments.commands import ListPaymentsQuery
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto

logger = logging.getLogger(__name__)


class ListPaymentsQueryHandler(BasePaymentQueryHandler[ListPaymentsQuery, List[PaymentDTO]]):
    """
    معالج استعلام لجلب قائمة الدفعات مع فلترة وتصفح
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: ListPaymentsQuery) -> List[PaymentDTO]:
        with self._uow:
            repo = self._uow.payments
            
            # تحويل الفلاتر
            payment_type = None
            if query.payment_type:
                type_map = {
                    "receive": PaymentType.RECEIVE,
                    "pay": PaymentType.PAY,
                    "transfer": PaymentType.TRANSFER,
                }
                payment_type = type_map.get(query.payment_type)
            
            status = None
            if query.status:
                status_map = {
                    "draft": PaymentStatus.DRAFT,
                    "pending": PaymentStatus.PENDING,
                    "approved": PaymentStatus.APPROVED,
                    "completed": PaymentStatus.COMPLETED,
                    "rejected": PaymentStatus.REJECTED,
                    "cancelled": PaymentStatus.CANCELLED,
                }
                status = status_map.get(query.status)
            
            # جلب الدفعات من المستودع
            payments = repo.list_by_date_range(
                from_date=query.from_date,
                to_date=query.to_date,
                payment_type=payment_type,
                limit=query.limit
            )
            
            # فلترة إضافية حسب الحالة
            if status:
                payments = [p for p in payments if p.status == status]
            
            # فلترة حسب العميل أو المورد
            if query.customer_id:
                payments = [p for p in payments if p.customer_id == query.customer_id]
            
            if query.supplier_id:
                payments = [p for p in payments if p.supplier_id == query.supplier_id]
            
            # Pagination يدوي
            offset = query.offset or 0
            limit = query.limit or 100
            paginated_payments = payments[offset:offset + limit]
            
            logger.debug(f"Listed {len(paginated_payments)} payments")
            
            return [payment_to_dto(payment) for payment in paginated_payments]