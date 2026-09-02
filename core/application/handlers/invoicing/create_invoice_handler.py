# core/application/handlers/invoicing/create_invoice_handler.py

"""
Create Invoice Handler - Pure application layer handler
No infrastructure dependencies - only uses repositories via UoW
"""

from typing import Optional
from decimal import Decimal
from uuid import UUID

from core.domain.invoicing.entities import Invoice, InvoiceLine
from core.domain.invoicing.value_objects import InvoiceId, PaymentType, InvoiceNumber
from core.domain.invoicing.interfaces import IInvoiceRepository
from core.domain.invoicing.exceptions import InvoiceNotFoundError
from core.domain.shared.value_objects import Money
from core.domain.accounting.interfaces import IUnitOfWork
from core.application.invoicing.commands import CreateInvoiceCommand
from core.application.invoicing.dtos import InvoiceDTO, InvoiceLineDTO
from core.application.security.authorization import UserContext, require_permission, Permission
from ..base_handler import BaseHandler


class CreateInvoiceHandler(BaseHandler[CreateInvoiceCommand, InvoiceDTO]):
    """
    Handler for creating new invoices.
    
    This handler is responsible ONLY for:
        1. Creating the invoice aggregate
        2. Saving via repository
        3. Committing the transaction
    
    NO business logic here - all logic is in the domain entity.
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateInvoiceCommand, user_context: UserContext) -> InvoiceDTO:
        """
        Handle create invoice command.
        
        The Unit of Work manages the transaction automatically.
        """
        # Start transaction
        with self._uow:
            # Get repository from UoW
            invoice_repo = self._uow.invoices
            
            # Map payment type
            payment_type_map = {
                "cash": PaymentType.CASH,
                "credit": PaymentType.CREDIT,
                "check": PaymentType.CHECK,
                "transfer": PaymentType.TRANSFER,
            }
            payment_type = payment_type_map.get(command.payment_type, PaymentType.CASH)
            
            # Create domain aggregate (business logic inside entity)
            invoice = Invoice(
                customer_id=command.customer_id,
                customer_name=command.customer_name,
                site_id=command.site_id,
                site_name=command.site_name,
                currency=command.currency,
                payment_type=payment_type,
                fund_id=command.fund_id,
                notes=command.notes,
                created_by=user_context.user_id
            )
            
            # ✅ إضافة payment_currency إلى الفاتورة
            if hasattr(command, 'payment_currency'):
                invoice.payment_currency = command.payment_currency
            
            # Generate invoice number directly
            next_number = invoice_repo.get_next_number()
            invoice.number = next_number
            
            # Save aggregate
            invoice_repo.save(invoice)
            
            # Commit transaction (UoW handles events dispatch)
            self._commit()
            
            # Return DTO (never expose domain entity to UI)
            return self._to_dto(invoice)
    
    def _to_dto(self, invoice: Invoice) -> InvoiceDTO:
        """Convert domain entity to DTO - ✅ مصححة مع payment_currency"""
        
        # تحويل الأسطر إلى DTO
        lines = []
        for line in invoice.lines:
            lines.append(InvoiceLineDTO(
                line_id=line.line_id,
                product_code=line.product_code,
                product_name=line.product_name,
                quantity=line.quantity,
                unit_price=line.unit_price.amount,
                total=line.total.amount,
                currency=line.unit_price.currency,
                notes=line.notes
            ))
        
        # ✅ إضافة payment_currency مع قيمة افتراضية إذا لم تكن موجودة
        payment_currency = getattr(invoice, 'payment_currency', 'USD')
        
        return InvoiceDTO(
            id=str(invoice.id.value),
            number=str(invoice.number) if invoice.number else None,
            date=invoice.date,
            customer_id=invoice.customer_id,
            customer_name=invoice.customer_name,
            site_id=invoice.site_id,
            site_name=invoice.site_name,
            currency=invoice.currency,
            payment_currency=payment_currency,  # ✅ الحقل المفقود
            payment_type=invoice.payment_type.value,
            fund_id=invoice.fund_id,
            status=invoice.status.value,
            subtotal=invoice.subtotal.amount,
            tax_amount=invoice.tax_amount.amount,
            total=invoice.total.amount,
            notes=invoice.notes,
            lines=lines,
            journal_entry_id=invoice.journal_entry_id,
            created_at=invoice.created_at,
            created_by=invoice.created_by,
            posted_at=invoice.posted_at,
            posted_by=invoice.posted_by
        )
    
    def _line_to_dto(self, line):
        """Convert line to DTO"""
        return InvoiceLineDTO(
            line_id=line.line_id,
            product_code=line.product_code,
            product_name=line.product_name,
            quantity=line.quantity,
            unit_price=line.unit_price.amount,
            total=line.total.amount,
            currency=line.unit_price.currency,
            notes=line.notes
        )