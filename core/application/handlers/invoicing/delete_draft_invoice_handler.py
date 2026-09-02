# core/application/handlers/invoicing/delete_draft_invoice_handler.py

"""
Delete Draft Invoice Handler - حذف فاتورة مسودة
"""

import logging
from uuid import UUID

from core.domain.invoicing.value_objects import InvoiceId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.invoicing.commands import DeleteDraftInvoiceCommand

logger = logging.getLogger(__name__)


class DeleteDraftInvoiceHandler(BaseHandler[DeleteDraftInvoiceCommand, dict]):
    """Handler for deleting a draft invoice"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteDraftInvoiceCommand, user_context: UserContext) -> dict:
        with self._uow:
            invoice_repo = self._uow.invoices
            invoice_id = InvoiceId(UUID(command.invoice_id))
            
            invoice = invoice_repo.get_by_id(invoice_id)
            if not invoice:
                return {
                    "success": False,
                    "message": f"Invoice {command.invoice_id} not found",
                    "invoice_id": command.invoice_id
                }
            
            if invoice.is_posted:
                return {
                    "success": False,
                    "message": "Cannot delete posted invoice",
                    "invoice_id": command.invoice_id
                }
            
            result = invoice_repo.delete_draft(invoice_id)
            
            if result:
                self._commit()
                logger.info(f"Draft invoice {invoice.number} deleted by {user_context.user_id}")
            
            return {
                "success": result,
                "message": "Invoice deleted successfully" if result else "Failed to delete invoice",
                "invoice_id": command.invoice_id
            }