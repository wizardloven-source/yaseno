# core/application/handlers/invoicing/get_invoice_query_handler.py

"""
Get Invoice Query Handler - استعلام لجلب فاتورة واحدة
"""

import logging
from uuid import UUID

from core.domain.invoicing.value_objects import InvoiceId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.invoicing.commands import GetInvoiceQuery
from core.application.invoicing.dtos import InvoiceDTO

# ✅ تصحيح: استيراد من converters بدلاً من handlers
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class GetInvoiceQueryHandler(BaseQueryHandler[GetInvoiceQuery, InvoiceDTO]):
    """Handler for retrieving a single invoice"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetInvoiceQuery) -> InvoiceDTO:
        with self._uow:
            invoice_repo = self._uow.invoices
            invoice_id = InvoiceId(UUID(query.invoice_id))
            
            invoice = invoice_repo.get_by_id(invoice_id)
            if not invoice:
                return None
            
            return invoice_to_dto(invoice)