# core/domain/accounting/tax_integration.py
"""
Tax Integration with Accounting - ربط الضرائب مع المحاسبة
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any

from .entities import JournalEntry, JournalLine
from .value_objects import AccountCode, Money
from core.domain.tax.services import TaxEngine, TaxContext
from core.domain.tax.value_objects import TaxCalculationResult, TaxRule
from core.domain.invoicing.entities import Invoice, InvoiceLine


class TaxJournalBuilder:
    """
    بناء قيود محاسبية للضرائب
    يضيف حسابات الضريبة إلى القيود المحاسبية
    """
    
    def __init__(self, tax_engine: TaxEngine, tax_payable_account: AccountCode, tax_receivable_account: AccountCode):
        self._tax_engine = tax_engine
        self._tax_payable_account = tax_payable_account      # ضريبة مستحقة الدفع (مصروفات)
        self._tax_receivable_account = tax_receivable_account  # ضريبة مستحقة التحصيل (إيرادات)

    def add_tax_lines_to_invoice(self, invoice: Invoice) -> List[JournalLine]:
        """
        إضافة أسطر الضريبة إلى قيد الفاتورة
        """
        tax_lines = []
        
        if not invoice.lines:
            return tax_lines

        # حساب الضريبة لكل سطر
        for line in invoice.lines:
            context = TaxContext(
                product_code=line.product_code,
                product_category=None,  # يمكن إضافة تصنيف المنتج
                customer_id=invoice.customer_id,
                customer_group=None,    # يمكن إضافة مجموعة العميل
                amount=line.total.amount,
                date=invoice.date.date()
            )
            
            result = self._tax_engine.calculate_tax(line.total.amount, context)
            
            if result.tax_amount > 0:
                # إضافة حساب الضريبة
                tax_line = JournalLine(
                    account_code=self._tax_receivable_account if invoice.payment_type == "cash" else self._tax_payable_account,
                    debit=Money(result.tax_amount, line.currency),
                    credit=Money(Decimal('0'), line.currency)
                )
                tax_lines.append(tax_line)
                
                # تحديث سطر الفاتورة بالضريبة
                line.tax_amount = Money(result.tax_amount, line.currency)

        return tax_lines

    def create_tax_journal_entry(self, invoice: Invoice) -> Optional[JournalEntry]:
        """
        إنشاء قيد محاسبي للضريبة فقط
        """
        tax_lines = self.add_tax_lines_to_invoice(invoice)
        
        if not tax_lines:
            return None
        
        # إضافة سطر دائن للضريبة
        total_tax = sum(line.debit.amount for line in tax_lines if line.debit.amount > 0)
        if total_tax > 0:
            tax_lines.append(
                JournalLine(
                    account_code=self._tax_receivable_account if invoice.payment_type == "cash" else self._tax_payable_account,
                    debit=Money(Decimal('0'), invoice.currency),
                    credit=Money(total_tax, invoice.currency)
                )
            )

        return JournalEntry(
            date=invoice.date,
            description=f"Tax entry for invoice {invoice.number}",
            lines=tax_lines
        )


class TaxPostingEngine:
    """
    محرك ترحيل الضرائب - يدمج TaxEngine مع PostingEngine
    """
    
    def __init__(self, posting_engine, tax_engine: TaxEngine):
        self._posting_engine = posting_engine
        self._tax_engine = tax_engine

    def post_invoice_with_tax(self, invoice: Invoice, posted_by: str) -> Dict[str, Any]:
        """
        ترحيل فاتورة مع حساب الضريبة تلقائياً
        """
        # حساب الضريبة لكل سطر
        tax_total = Decimal('0')
        tax_breakdown = {}
        
        for line in invoice.lines:
            context = TaxContext(
                product_code=line.product_code,
                amount=line.total.amount,
                customer_id=invoice.customer_id,
                date=invoice.date.date()
            )
            
            result = self._tax_engine.calculate_tax(line.total.amount, context)
            line.tax_amount = Money(result.tax_amount, line.currency)
            tax_total += result.tax_amount
            
            for rule in result.applied_rules:
                key = str(rule.code)
                if key not in tax_breakdown:
                    tax_breakdown[key] = Decimal('0')
                tax_breakdown[key] += result.breakdown.get(key, Decimal('0'))

        # تحديث إجمالي الضريبة في الفاتورة
        invoice.tax_amount = Money(tax_total, invoice.currency)
        invoice.total_with_tax = Money(invoice.total.amount + tax_total, invoice.currency)

        # إنشاء القيد المحاسبي مع الضريبة
        journal_lines = invoice.to_journal_entry_lines()
        
        # إضافة سطور الضريبة
        if tax_total > 0:
            # حساب الضريبة المستحقة
            tax_account = AccountCode("2100")  # حساب الضريبة المستحقة
            journal_lines.append((
                tax_account,
                Decimal('0'),  # لا مدين
                tax_total,     # دائن
                invoice.currency
            ))

        # ترحيل القيد
        result = self._posting_engine.post(invoice, posted_by)
        
        return {
            'success': result.success,
            'tax_total': str(tax_total),
            'tax_breakdown': tax_breakdown,
            'journal_entry_id': result.journal_entry_id if result.success else None,
            'message': result.message
        }