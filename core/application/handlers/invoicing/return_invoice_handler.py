# core/application/handlers/invoicing/return_invoice_handler.py

"""
Return Invoice Handler - إنشاء فاتورة مرتجع
"""

import logging
from uuid import UUID

from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.exceptions import InvoiceNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import PostingEngine
from core.domain.inventory.services import StockMovementService

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.invoicing.commands import ReturnInvoiceCommand
from core.application.invoicing.dtos import InvoiceDTO
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class ReturnInvoiceHandler(BaseHandler[ReturnInvoiceCommand, InvoiceDTO]):
    """معالج إنشاء فاتورة مرتجع"""
    
    def __init__(
        self, 
        uow: IUnitOfWork, 
        posting_engine: PostingEngine = None, 
        stock_service: StockMovementService = None
    ):
        super().__init__(uow)
        self._posting_engine = posting_engine
        self._stock_service = stock_service
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ReturnInvoiceCommand, user_context: UserContext) -> InvoiceDTO:
        with self._uow:
            invoice_repo = self._uow.invoices
            invoice_id = InvoiceId(UUID(command.invoice_id))
            
            invoice = invoice_repo.get_by_id(invoice_id)
            if not invoice:
                raise InvoiceNotFoundError(command.invoice_id)
            
            if not invoice.is_posted:
                raise ValueError("لا يمكن إنشاء مرتجع لفاتورة غير مرحلة")
            
            # إنشاء فاتورة مرتجع (تحتاج إلى إضافة هذه الدالة في كيان Invoice)
            # return_invoice = invoice.create_return(
            #     reason=command.reason,
            #     created_by=user_context.user_id
            # )
            
            # مؤقتاً: إنشاء فاتورة جديدة كمرتجع
            from core.domain.invoicing.entities import Invoice
            from core.domain.invoicing.value_objects import PaymentType
            
            return_invoice = Invoice(
                customer_id=invoice.customer_id,
                customer_name=invoice.customer_name,
                site_id=invoice.site_id,
                site_name=invoice.site_name,
                currency=invoice.currency,
                payment_type=PaymentType.CASH,
                notes=f"مرتجع من فاتورة {invoice.number} - {command.reason}",
                created_by=user_context.user_id
            )
            
            # نسخ الأسطر مع إشارة سالبة
            for line in invoice.lines:
                return_invoice.add_line(line)
                # جعل الكمية سالبة للمرتجع
                return_invoice.lines[-1].quantity = -line.quantity
            
            invoice_repo.save(return_invoice)
            self._commit()
            
            logger.info(f"✅ Return invoice {return_invoice.number} created from {invoice.number} by {user_context.user_id}")
            
            return invoice_to_dto(return_invoice)