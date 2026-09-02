# core/application/handlers/payments/get_supplier_payments_query_handler.py
"""
Get Supplier Payments Query Handler - استعلام لجلب دفعات المورد
"""

import logging
from typing import List

from core.domain.payments.interfaces import IPaymentRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.payments.commands import GetSupplierPaymentsQuery
from core.application.payments.dtos import PaymentDTO
from core.application.payments.converters import payment_to_dto
from core.domain.accounting.posting_engine import PostingEngine

logger = logging.getLogger(__name__)


class GetSupplierPaymentsQueryHandler(BaseQueryHandler[GetSupplierPaymentsQuery, List[PaymentDTO]]):
    """
    معالج استعلام لجلب دفعات المورد
    
    يقوم بجلب جميع دفعات مورد معين مع خيارات التصفية والترقيم.
    """
    
    def __init__(self, payment_repo: IPaymentRepository):
        self._payment_repo = payment_repo
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetSupplierPaymentsQuery) -> List[PaymentDTO]:
        """
        تنفيذ جلب دفعات المورد
        
        Args:
            query: استعلام جلب دفعات المورد
        
        Returns:
            List[PaymentDTO]: قائمة دفعات المورد
        """
        logger.debug(f"Fetching payments for supplier: {query.supplier_id}")
        
        # جلب دفعات المورد
        payments = self._payment_repo.list_by_supplier(
            supplier_id=query.supplier_id,
            limit=query.limit,
            offset=query.offset
        )
        
        logger.info(f"Found {len(payments)} payments for supplier {query.supplier_id}")
        
        return [payment_to_dto(payment) for payment in payments]