# core/application/handlers/invoicing/list_invoices_query_handler.py

"""
List Invoices Query Handler - استعلام لجلب قائمة الفواتير
"""

import logging
from datetime import datetime
from typing import List

from core.domain.invoicing.value_objects import InvoiceStatus
from core.domain.accounting.interfaces import IUnitOfWork
from core.infrastructure.db.models.invoice_model import InvoiceModel
from core.infrastructure.db.postgres.repositories_invoice import _model_to_domain

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.invoicing.commands import ListInvoicesQuery
from core.application.invoicing.dtos import InvoiceDTO

# ✅ تصحيح: استيراد من converters بدلاً من handlers
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class ListInvoicesQueryHandler(BaseQueryHandler[ListInvoicesQuery, List[InvoiceDTO]]):
    """Handler for listing invoices with filters"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: ListInvoicesQuery) -> List[InvoiceDTO]:
        with self._uow:
            from core.infrastructure.db.models.invoice_model import InvoiceModel
            db_query = self._uow.session.query(InvoiceModel)
            
            # إضافة الفلاتر حسب وجودها
            if query.site_id:
                db_query = db_query.filter(InvoiceModel.site_id == query.site_id)
            
            if query.customer_id:
                db_query = db_query.filter(InvoiceModel.customer_id == query.customer_id)
            
            if query.status:
                db_query = db_query.filter(InvoiceModel.status == query.status)
            
            if query.from_date:
                db_query = db_query.filter(InvoiceModel.invoice_date >= query.from_date)
            
            if query.to_date:
                db_query = db_query.filter(InvoiceModel.invoice_date <= query.to_date)
            
            # تنفيذ الاستعلام مع الترتيب والتصفح
            models = db_query.order_by(
                InvoiceModel.created_at.desc()
            ).limit(query.limit).offset(query.offset).all()
            
            invoices = [_model_to_domain(m) for m in models]
            
            return [invoice_to_dto(inv) for inv in invoices]