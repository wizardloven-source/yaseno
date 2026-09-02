"""
Get Customer Invoices Query Handler - استعلام لجلب فواتير العميل
"""

import logging
from uuid import UUID
from typing import List

from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.interfaces import IInvoiceRepository
from core.domain.invoicing.entities import Invoice

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.invoicing.commands import GetCustomerInvoicesQuery
from core.application.invoicing.dtos import InvoiceDTO
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class GetCustomerInvoicesQueryHandler(BaseQueryHandler[GetCustomerInvoicesQuery, List[InvoiceDTO]]):
    """معالج استعلام لجلب فواتير عميل معين"""
    
    def __init__(self, invoice_repo: IInvoiceRepository):
        self._invoice_repo = invoice_repo
    
    def handle(self, query: GetCustomerInvoicesQuery) -> List[InvoiceDTO]:
        """تنفيذ استعلام جلب فواتير العميل"""
        invoices = self._invoice_repo.list_by_customer(
            customer_id=query.customer_id,
            limit=query.limit,
            offset=query.offset
        )
        
        return [invoice_to_dto(inv) for inv in invoices]