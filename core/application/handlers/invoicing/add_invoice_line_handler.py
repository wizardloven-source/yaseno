# core/application/handlers/invoicing/add_invoice_line_handler.py

"""
Add Invoice Line Handler - إضافة سطر إلى فاتورة موجودة
"""

import logging
from decimal import Decimal
from uuid import UUID

from core.domain.invoicing.entities import Invoice, InvoiceLine
from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.exceptions import InvoiceNotFoundError, CannotModifyPostedInvoiceError
from core.domain.shared.value_objects import Money
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.invoicing.commands import AddInvoiceLineCommand
from core.application.invoicing.dtos import InvoiceDTO

# ✅ تصحيح: استيراد من converters بدلاً من handlers
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class AddInvoiceLineHandler(BaseHandler[AddInvoiceLineCommand, InvoiceDTO]):
    """Handler for adding a line to an invoice"""
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: AddInvoiceLineCommand, user_context: UserContext) -> InvoiceDTO:
        with self._uow:
            invoice_repo = self._uow.invoices
            invoice_id = InvoiceId(UUID(command.invoice_id))
            
            invoice = invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise InvoiceNotFoundError(command.invoice_id)
            
            if invoice.is_posted:
                raise CannotModifyPostedInvoiceError(command.invoice_id)
            
            if command.quantity <= 0:
                raise ValueError(f"Quantity must be greater than zero, got {command.quantity}")
            
            if command.unit_price <= 0:
                raise ValueError(f"Unit price must be greater than zero, got {command.unit_price}")
            
            unit_price_money = Money(command.unit_price, command.currency)
            line = InvoiceLine(
                product_code=command.product_code,
                product_name=command.product_name,
                quantity=command.quantity,
                unit_price=unit_price_money,
                notes=command.notes
            )
            
            invoice.add_line(line)
            invoice_repo.save(invoice)
            self._commit()
            
            logger.info(f"Line added to invoice {invoice.number} by {user_context.user_id}")
            
            return invoice_to_dto(invoice)