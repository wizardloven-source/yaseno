# core/application/handlers/invoicing/search_invoices_query_handler.py

"""
Search Invoices Query Handler - استعلام للبحث عن الفواتير
"""

import logging
from typing import List

from core.domain.invoicing.interfaces import IInvoiceRepository
from core.domain.invoicing.value_objects import InvoiceStatus, PaymentType

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.invoicing.commands import SearchInvoicesQuery
from core.application.invoicing.dtos import InvoiceDTO
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class SearchInvoicesQueryHandler(BaseQueryHandler[SearchInvoicesQuery, List[InvoiceDTO]]):
    """معالج استعلام للبحث عن الفواتير"""
    
    def __init__(self, invoice_repo: IInvoiceRepository):
        self._invoice_repo = invoice_repo
    
    def handle(self, query: SearchInvoicesQuery) -> List[InvoiceDTO]:
        """تنفيذ استعلام البحث عن الفواتير"""
        # استخدام البحث النصي في المستودع
        invoices = self._invoice_repo.search_by_text(
            search_text=query.search_text,
            limit=query.limit,
            offset=query.offset
        )
        
        return [invoice_to_dto(inv) for inv in invoices]