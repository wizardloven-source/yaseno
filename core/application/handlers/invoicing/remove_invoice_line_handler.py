# core/application/handlers/invoicing/remove_invoice_line_handler.py

"""
Remove Invoice Line Handler - حذف سطر من الفاتورة
"""

import logging
from uuid import UUID

from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.exceptions import InvoiceNotFoundError, CannotModifyPostedInvoiceError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.invoicing.commands import RemoveInvoiceLineCommand
from core.application.invoicing.dtos import InvoiceDTO

# ✅ تصحيح: استيراد من converters بدلاً من handlers
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class RemoveInvoiceLineHandler(BaseHandler[RemoveInvoiceLineCommand, InvoiceDTO]):
    """Handler for removing an invoice line"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: RemoveInvoiceLineCommand, user_context: UserContext) -> InvoiceDTO:
        with self._uow:
            invoice_repo = self._uow.invoices
            invoice_id = InvoiceId(UUID(command.invoice_id))
            
            invoice = invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise InvoiceNotFoundError(command.invoice_id)
            
            if invoice.is_posted:
                raise CannotModifyPostedInvoiceError(command.invoice_id)
            
            removed = invoice.remove_line(command.line_id)
            if not removed:
                raise ValueError(f"Line {command.line_id} not found in invoice")
            
            invoice_repo.save(invoice)
            self._commit()
            
            logger.info(f"Line {command.line_id} removed from invoice {invoice.number} by {user_context.user_id}")
            
            return invoice_to_dto(invoice)