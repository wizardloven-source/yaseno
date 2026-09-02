# core/application/handlers/invoicing/cancel_invoice_handler.py

"""
Cancel Invoice Handler - إلغاء فاتورة
"""

import logging
from uuid import UUID

from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.exceptions import InvoiceNotFoundError, CannotCancelPostedInvoiceError
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import PostingEngine

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.invoicing.commands import CancelInvoiceCommand
from core.application.invoicing.dtos import InvoiceDTO
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class CancelInvoiceHandler(BaseHandler[CancelInvoiceCommand, InvoiceDTO]):
    """معالج إلغاء فاتورة"""
    
    def __init__(self, uow: IUnitOfWork, posting_engine: PostingEngine = None):
        super().__init__(uow)
        self._posting_engine = posting_engine
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CancelInvoiceCommand, user_context: UserContext) -> InvoiceDTO:
        with self._uow:
            invoice_repo = self._uow.invoices
            invoice_id = InvoiceId(UUID(command.invoice_id))
            
            invoice = invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise InvoiceNotFoundError(command.invoice_id)
            
            if invoice.is_posted:
                raise CannotCancelPostedInvoiceError(command.invoice_id, "لا يمكن إلغاء فاتورة مرحلة")
            
            # إلغاء الفاتورة
            invoice.status = "cancelled"
            invoice_repo.save(invoice)
            self._commit()
            
            logger.info(f"✅ Invoice {invoice.number} cancelled by {user_context.user_id}")
            
            return invoice_to_dto(invoice)