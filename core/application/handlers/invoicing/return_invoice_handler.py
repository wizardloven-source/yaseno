# core/application/handlers/invoicing/return_invoice_handler.py

"""
Return Invoice Handler - إنشاء فاتورة مرتجع مع قيد عكسي وإعادة مخزون
"""

import logging
from uuid import UUID
from decimal import Decimal

from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.exceptions import InvoiceNotFoundError
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import PostingEngine
from core.domain.accounting.journal_entry import JournalEntry, JournalLine
from core.domain.accounting.value_objects import AccountCode, JournalEntryRequest
from core.domain.inventory.services import StockMovementService
from core.domain.inventory.entities import StockMovementType

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.invoicing.commands import ReturnInvoiceCommand
from core.application.invoicing.dtos import InvoiceDTO
from core.application.invoicing.converters import invoice_to_dto

logger = logging.getLogger(__name__)


class ReturnInvoiceHandler(BaseHandler[ReturnInvoiceCommand, InvoiceDTO]):
    """معالج إنشاء فاتورة مرتجع — يُنشئ قيد عكسي ويُعيد المخزون"""
    
    def __init__(
        self, 
        uow: IUnitOfWork, 
        posting_engine: PostingEngine = None, 
        stock_service: StockMovementService = None
    ):
        super().__init__(uow)
        self._posting_engine = posting_engine
        self._stock_service = stock_service
    
    def _get_accounting_settings(self) -> dict:
        settings_repo = self._uow.settings
        settings = settings_repo.get_accounting_settings()
        if settings:
            return {
                'cash_account': getattr(settings, 'cash_account', '1010'),
                'receivables_account': getattr(settings, 'receivables_account', '1020'),
                'revenue_account': getattr(settings, 'revenue_account', '4010'),
                'tax_payable_account': getattr(settings, 'tax_payable_account', '2100'),
                'cogs_account': getattr(settings, 'cogs_account', '5010'),
                'inventory_account': getattr(settings, 'inventory_account', '1030'),
                'fund_id': getattr(settings, 'default_fund_id', None),
            }
        return {
            'cash_account': '1010', 'receivables_account': '1020',
            'revenue_account': '4010', 'tax_payable_account': '2100',
            'cogs_account': '5010', 'inventory_account': '1030',
            'fund_id': None,
        }
    
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
            
            settings = self._get_accounting_settings()
            
            # 1. إنشاء فاتورة مرتجع بكميات سالبة
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
            
            for line in invoice.lines:
                return_invoice.add_line(line)
                return_invoice.lines[-1].quantity = -line.quantity
                if line.tax_rate:
                    return_invoice.lines[-1].tax_amount = -(line.tax_amount or Decimal('0'))
            
            # 2. إنشاء قيد محاسبي عكسي (عكس الفاتورة الأصلية)
            reversable_amount = invoice.total
            reverse_amount = reversable_amount * Decimal('-1')
            
            receivables_account = AccountCode(settings['receivables_account'])
            revenue_account = AccountCode(settings['revenue_account'])
            tax_payable_account = AccountCode(settings['tax_payable_account'])
            cogs_account = AccountCode(settings['cogs_account'])
            inventory_account = AccountCode(settings['inventory_account'])
            
            reverse_lines = []
            # عكس الإيداع: Dr Revenue / Cr Accounts Receivable
            for line in invoice.lines:
                reverse_lines.append(JournalLine(
                    account_code=revenue_account,
                    debit_amount=line.total,
                    credit_amount=Decimal('0'),
                    currency=invoice.currency,
                    description=f"عكس بيع - {line.description or line.product_name}"
                ))
            
            reverse_lines.append(JournalLine(
                account_code=receivables_account,
                debit_amount=Decimal('0'),
                credit_amount=sum(l.total for l in invoice.lines),
                currency=invoice.currency,
                description=f"عكس مستحقات - فاتورة {invoice.number}"
            ))
            
            if invoice.tax_amount and invoice.tax_amount > 0:
                reverse_lines.append(JournalLine(
                    account_code=tax_payable_account,
                    debit_amount=invoice.tax_amount,
                    credit_amount=Decimal('0'),
                    currency=invoice.currency,
                    description=f"عكس ضريبة - فاتورة {invoice.number}"
                ))
            
            # عكس تكلفة البضاعة المباعة
            for line in invoice.lines:
                if hasattr(line, 'unit_cost') and line.unit_cost:
                    cost_total = line.unit_cost * line.quantity
                    reverse_lines.append(JournalLine(
                        account_code=cogs_account,
                        debit_amount=Decimal('0'),
                        credit_amount=abs(cost_total),
                        currency=invoice.currency,
                        description=f"عكس تكلفة بيع - {line.product_name}"
                    ))
                    reverse_lines.append(JournalLine(
                        account_code=inventory_account,
                        debit_amount=abs(cost_total),
                        credit_amount=Decimal('0'),
                        currency=invoice.currency,
                        description=f"إعادة مخزون - {line.product_name}"
                    ))
            
            reverse_request = JournalEntryRequest(
                entry_date=invoice.invoice_date,
                description=f"قيد عكسي لمرتجع فاتورة {invoice.number}",
                source_type="InvoiceReturn",
                source_id=str(return_invoice.id) if hasattr(return_invoice, 'id') else None,
                currency=invoice.currency,
                lines=reverse_lines
            )
            
            # 3. ترحيل القيد العكسي عبر PostingEngine
            if self._posting_engine:
                journal_entry = JournalEntry(
                    entry_date=invoice.invoice_date,
                    description=f"قيد عكسي لمرتجع فاتورة {invoice.number}",
                    source_type="InvoiceReturn",
                    source_id=str(return_invoice.id) if hasattr(return_invoice, 'id') else None,
                    currency=invoice.currency,
                    created_by=user_context.user_id
                )
                for rl in reverse_lines:
                    journal_entry.add_line(rl)
                
                engine = self._posting_engine
                engine._journal_repo = self._uow.journal_entries
                engine._ledger_repo = self._uow.ledger
                engine._period_repo = self._uow.periods
                engine._account_repo = self._uow.accounts
                engine._uow = self._uow
                
                engine.post(journal_entry, user_context.user_id, commit=False)
            
            # 4. إعادة المخزون (حركة واردة)
            if self._stock_service:
                for line in invoice.lines:
                    if hasattr(line, 'product_id') and line.product_id:
                        self._stock_service.create_inbound_movement(
                            entity=UUID(line.product_id) if isinstance(line.product_id, str) else line.product_id,
                            quantity=abs(line.quantity),
                            unit_cost=line.unit_cost if hasattr(line, 'unit_cost') and line.unit_cost else line.unit_price,
                            movement_type=StockMovementType.PURCHASE_RETURN,
                            reference_type="InvoiceReturn",
                            reference_id=str(return_invoice.id) if hasattr(return_invoice, 'id') else str(command.invoice_id),
                            notes=f"إعادة مخزون من مرتجع فاتورة {invoice.number}",
                            created_by=user_context.user_id
                        )
            
            invoice_repo.save(return_invoice)
            self._commit()
            
            logger.info(f"✅ Return invoice {return_invoice.number} created from {invoice.number} by {user_context.user_id}")
            
            return invoice_to_dto(return_invoice)