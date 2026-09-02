# tests/integration/test_invoice_integration.py
"""Integration tests for Invoice module with Accounting core"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from core.domain.invoicing.entities import Invoice, InvoiceLine
from core.domain.invoicing.value_objects import InvoiceId, InvoiceNumber, PaymentType
from core.domain.shared.value_objects import Money


class TestInvoiceToJournalEntry:
    """اختبار تحويل الفاتورة إلى قيد محاسبي"""
    
    def test_invoice_to_journal_entry_cash_sale(self):
        """فاتورة بيع نقدي - يجب أن يظهر حساب الصندوق مديناً"""
        
        # إنشاء فاتورة
        invoice = Invoice(
            customer_id="CUST001",
            customer_name="عميل تجريبي",
            currency="USD",
            payment_type=PaymentType.CASH
        )
        
        # إضافة سطر
        line = InvoiceLine(
            product_code="PROD001",
            product_name="منتج تجريبي",
            quantity=Decimal('2'),
            unit_price=Money(Decimal('100'), "USD")
        )
        invoice.add_line(line)
        
        # تحويل إلى أسطر قيد محاسبي
        journal_lines = invoice.to_journal_entry_lines()
        
        # التحقق: يجب أن يكون هناك سطرين (مدين للصندوق، دائن للإيراد)
        assert len(journal_lines) == 2
        
        # السطر الأول: مدين للصندوق
        debit_account, debit_amount, credit_amount, currency = journal_lines[0]
        assert str(debit_account) == "1010"  # حساب الصندوق
        assert debit_amount == Decimal('200')  # 2 * 100
        assert credit_amount == Decimal('0')
        
        # السطر الثاني: دائن للإيراد
        credit_account, debit_amount, credit_amount, currency = journal_lines[1]
        assert str(credit_account) == "4010"  # حساب الإيرادات
        assert debit_amount == Decimal('0')
        assert credit_amount == Decimal('200')
    
    def test_invoice_to_journal_entry_credit_sale(self):
        """فاتورة بيع آجل - يجب أن يظهر حساب المدينين مديناً"""
        
        invoice = Invoice(
            customer_id="CUST001",
            customer_name="عميل تجريبي",
            currency="USD",
            payment_type=PaymentType.CREDIT  # آجل
        )
        
        line = InvoiceLine(
            product_code="PROD001",
            product_name="منتج تجريبي",
            quantity=Decimal('1'),
            unit_price=Money(Decimal('500'), "USD")
        )
        invoice.add_line(line)
        
        journal_lines = invoice.to_journal_entry_lines()
        
        # السطر الأول: مدين لحساب المدينين (ليس الصندوق)
        debit_account, debit_amount, credit_amount, currency = journal_lines[0]
        assert str(debit_account) == "1020"  # حساب المدينين
        assert debit_amount == Decimal('500')
    
    def test_invoice_balance_check(self):
        """التحقق من توازن القيد المحاسبي الناتج عن الفاتورة"""
        
        invoice = Invoice(
            customer_id="CUST001",
            customer_name="عميل تجريبي",
            currency="USD",
            payment_type=PaymentType.CASH
        )
        
        # إضافة منتجين
        invoice.add_line(InvoiceLine(
            product_code="P1", product_name="Product 1",
            quantity=Decimal('2'), unit_price=Money(Decimal('100'), "USD")
        ))
        invoice.add_line(InvoiceLine(
            product_code="P2", product_name="Product 2",
            quantity=Decimal('1'), unit_price=Money(Decimal('50'), "USD")
        ))
        
        journal_lines = invoice.to_journal_entry_lines()
        
        # حساب إجمالي المدينين والدائنين
        total_debit = sum(line[1] for line in journal_lines)
        total_credit = sum(line[2] for line in journal_lines)
        
        assert total_debit == total_credit
        assert total_debit == Decimal('250')  # 200 + 50


class TestInvoiceAccountingIntegration:
    """اختبار تكامل الفاتورة مع المحاسبة"""
    
    def test_invoice_total_matches_journal_entry(self):
        """الإجمالي في الفاتورة يجب أن يساوي إجمالي القيد المحاسبي"""
        
        invoice = Invoice(
            customer_id="CUST001",
            customer_name="عميل تجريبي",
            currency="USD",
            payment_type=PaymentType.CASH
        )
        
        invoice.add_line(InvoiceLine(
            product_code="P1", product_name="Product 1",
            quantity=Decimal('3'), unit_price=Money(Decimal('75.50'), "USD")
        ))
        
        journal_lines = invoice.to_journal_entry_lines()
        journal_total = sum(line[1] for line in journal_lines)  # sum of debits
        
        assert invoice.total.amount == journal_total
        assert invoice.total.amount == Decimal('226.50')
    
    def test_generate_journal_entry_description(self):
        """اختبار توليد وصف القيد المحاسبي"""
        
        invoice = Invoice(
            customer_id="CUST001",
            customer_name="شركة الاختبار",
            currency="USD",
            payment_type=PaymentType.CASH
        )
        invoice.number = InvoiceNumber("INV-001")
        
        invoice.add_line(InvoiceLine(
            product_code="P1", product_name="Product 1",
            quantity=Decimal('2'), unit_price=Money(Decimal('100'), "USD")
        ))
        
        description = invoice.generate_journal_entry_description()
        
        assert "INVOICE INV-001" in description
        assert "شركة الاختبار" in description
        assert "1 items" in description or "items" in description


def run_invoice_tests():
    """تشغيل اختبارات الفواتير"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_invoice_tests()