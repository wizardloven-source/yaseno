# core/application/handlers/invoicing/clear_invoice_lines_handler.py

"""
Clear Invoice Lines Handler - مسح جميع بنود الفاتورة
"""

import logging
from uuid import UUID

from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.exceptions import InvoiceNotFoundError, CannotModifyPostedInvoiceError
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.invoicing.commands import ClearInvoiceLinesCommand
from core.application.invoicing.dtos import InvoiceDTO

# ✅ تصحيح: استيراد من converters بدلاً من handlers
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class ClearInvoiceLinesHandler(BaseHandler[ClearInvoiceLinesCommand, InvoiceDTO]):
    """Handler for clearing all invoice lines"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ClearInvoiceLinesCommand, user_context: UserContext) -> InvoiceDTO:
        with self._uow:
            invoice_repo = self._uow.invoices
            invoice_id = InvoiceId(UUID(command.invoice_id))
            
            invoice = invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise InvoiceNotFoundError(command.invoice_id)
            
            if invoice.is_posted:
                raise CannotModifyPostedInvoiceError(command.invoice_id)
            
            previous_line_count = len(invoice.lines)
            invoice.clear_lines()
            invoice_repo.save(invoice)
            self._commit()
            
            logger.info(f"Cleared {previous_line_count} lines from invoice {invoice.number} by {user_context.user_id}")
            
            return invoice_to_dto(invoice)