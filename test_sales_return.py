"""
Sales Return Test Suite - PHASE 1a
اختبار ميزة إرجاع المبيعات ومذكرات الدائنة
"""

import asyncio
from decimal import Decimal
from datetime import datetime, date

from core.domain.sales.entities import SalesReturn, ReturnItem
from core.domain.sales.value_objects import ReturnId, ReturnNumber, ReturnStatus, InvoiceId
from core.domain.shared.value_objects import CustomerId
from core.domain.invoicing.entities import CreditNote, CreditNoteLine


def test_create_sales_return():
    """اختبار إنشاء إرجاع مبيعات"""
    print("\n=== TEST: Create Sales Return ===")
    
    # إنشاء عناصر الإرجاع
    items = [
        ReturnItem(
            product_code="PROD001",
            product_name="منتج اختبار 1",
            quantity=Decimal("5.00"),
            unit_price=Decimal("100.00"),
            reason="تالف",
            condition="damaged",
            discount_percent=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("75.00")
        ),
        ReturnItem(
            product_code="PROD002",
            product_name="منتج اختبار 2",
            quantity=Decimal("3.00"),
            unit_price=Decimal("50.00"),
            reason="خطأ في الطلب",
            condition="good",
            discount_percent=Decimal("10.00"),
            discount_amount=Decimal("15.00"),
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("20.25")
        )
    ]
    
    # إنشاء الإرجاع
    sales_return = SalesReturn.create(
        customer_id=CustomerId("CUST001"),
        customer_name="عميل اختبار",
        invoice_id=InvoiceId("INV001"),
        currency="SAR",
        items=items,
        notes="إرجاع بضائع تالفة",
        internal_reference="RET2024001"
    )
    
    # التحقق من البيانات
    assert sales_return.customer_id.value == "CUST001"
    assert sales_return.customer_name == "عميل اختبار"
    assert sales_return.invoice_id.value == "INV001"
    assert sales_return.currency == "SAR"
    assert len(sales_return.items) == 2
    assert sales_return.status == ReturnStatus.DRAFT
    
    print(f"✓ Return ID: {sales_return.return_id}")
    print(f"✓ Return Number: {sales_return.return_number}")
    print(f"✓ Status: {sales_return.status}")
    print(f"✓ Items Count: {len(sales_return.items)}")
    print(f"✓ Subtotal: {sales_return.subtotal}")
    print(f"✓ Total Discount: {sales_return.total_discount}")
    print(f"✓ Total Tax: {sales_return.total_tax}")
    print(f"✓ Total Amount: {sales_return.total_amount}")
    print("✓ TEST PASSED\n")
    return sales_return


def test_submit_return():
    """اختبار تقديم الإرجاع للموافقة"""
    print("\n=== TEST: Submit Return ===")
    
    items = [
        ReturnItem(
            product_code="PROD001",
            product_name="منتج اختبار",
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
            reason="تالف",
            condition="damaged",
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("30.00")
        )
    ]
    
    sales_return = SalesReturn.create(
        customer_id=CustomerId("CUST001"),
        customer_name="عميل اختبار",
        invoice_id=InvoiceId("INV001"),
        currency="SAR",
        items=items
    )
    
    # تقديم للإرجاع
    sales_return.submit()
    
    assert sales_return.status == ReturnStatus.SUBMITTED
    print(f"✓ Status after submit: {sales_return.status}")
    print("✓ TEST PASSED\n")
    return sales_return


def test_approve_return():
    """اختبار الموافقة على الإرجاع"""
    print("\n=== TEST: Approve Return ===")
    
    items = [
        ReturnItem(
            product_code="PROD001",
            product_name="منتج اختبار",
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
            reason="تالف",
            condition="damaged",
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("30.00")
        )
    ]
    
    sales_return = SalesReturn.create(
        customer_id=CustomerId("CUST001"),
        customer_name="عميل اختبار",
        invoice_id=InvoiceId("INV001"),
        currency="SAR",
        items=items
    )
    
    sales_return.submit()
    sales_return.approve(approved_by="USER001", approval_date=date.today())
    
    assert sales_return.status == ReturnStatus.APPROVED
    assert sales_return.approved_by == "USER001"
    print(f"✓ Status after approve: {sales_return.status}")
    print(f"✓ Approved by: {sales_return.approved_by}")
    print("✓ TEST PASSED\n")
    return sales_return


def test_receive_goods():
    """اختبار استلام البضائع المرتجعة"""
    print("\n=== TEST: Receive Goods ===")
    
    items = [
        ReturnItem(
            product_code="PROD001",
            product_name="منتج اختبار",
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
            reason="تالف",
            condition="damaged",
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("30.00")
        )
    ]
    
    sales_return = SalesReturn.create(
        customer_id=CustomerId("CUST001"),
        customer_name="عميل اختبار",
        invoice_id=InvoiceId("INV001"),
        currency="SAR",
        items=items
    )
    
    sales_return.submit()
    sales_return.approve(approved_by="USER001", approval_date=date.today())
    sales_return.receive_goods(
        warehouse_id="WH001",
        received_by="USER002",
        received_date=date.today()
    )
    
    assert sales_return.status == ReturnStatus.RECEIVED
    assert sales_return.received_by == "USER002"
    print(f"✓ Status after receive: {sales_return.status}")
    print(f"✓ Received by: {sales_return.received_by}")
    print(f"✓ Warehouse: {sales_return.warehouse_id}")
    print("✓ TEST PASSED\n")
    return sales_return


def test_inspect_items():
    """اختبار فحص البضائع المرتجعة"""
    print("\n=== TEST: Inspect Items ===")
    
    items = [
        ReturnItem(
            product_code="PROD001",
            product_name="منتج اختبار",
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
            reason="تالف",
            condition="damaged",
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("30.00")
        )
    ]
    
    sales_return = SalesReturn.create(
        customer_id=CustomerId("CUST001"),
        customer_name="عميل اختبار",
        invoice_id=InvoiceId("INV001"),
        currency="SAR",
        items=items
    )
    
    sales_return.submit()
    sales_return.approve(approved_by="USER001", approval_date=date.today())
    sales_return.receive_goods(
        warehouse_id="WH001",
        received_by="USER002",
        received_date=date.today()
    )
    sales_return.inspect_items(
        inspected_by="USER003",
        inspection_date=date.today(),
        inspection_notes="تم فحص البضائع وتأكيد التلف"
    )
    
    assert sales_return.status == ReturnStatus.INSPECTED
    assert sales_return.inspected_by == "USER003"
    print(f"✓ Status after inspect: {sales_return.status}")
    print(f"✓ Inspected by: {sales_return.inspected_by}")
    print("✓ TEST PASSED\n")
    return sales_return


def test_complete_return():
    """اختبار إكمال الإرجاع"""
    print("\n=== TEST: Complete Return ===")
    
    items = [
        ReturnItem(
            product_code="PROD001",
            product_name="منتج اختبار",
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
            reason="تالف",
            condition="damaged",
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("30.00")
        )
    ]
    
    sales_return = SalesReturn.create(
        customer_id=CustomerId("CUST001"),
        customer_name="عميل اختبار",
        invoice_id=InvoiceId("INV001"),
        currency="SAR",
        items=items
    )
    
    sales_return.submit()
    sales_return.approve(approved_by="USER001", approval_date=date.today())
    sales_return.receive_goods(
        warehouse_id="WH001",
        received_by="USER002",
        received_date=date.today()
    )
    sales_return.inspect_items(
        inspected_by="USER003",
        inspection_date=date.today(),
        inspection_notes="تم الفحص"
    )
    sales_return.complete(completed_by="USER001")
    
    assert sales_return.status == ReturnStatus.COMPLETED
    assert sales_return.completed_by == "USER001"
    print(f"✓ Status after complete: {sales_return.status}")
    print(f"✓ Completed by: {sales_return.completed_by}")
    print("✓ TEST PASSED\n")
    return sales_return


def test_cancel_return():
    """اختبار إلغاء الإرجاع"""
    print("\n=== TEST: Cancel Return ===")
    
    items = [
        ReturnItem(
            product_code="PROD001",
            product_name="منتج اختبار",
            quantity=Decimal("2.00"),
            unit_price=Decimal("100.00"),
            reason="تالف",
            condition="damaged",
            tax_rate=Decimal("15.00"),
            tax_amount=Decimal("30.00")
        )
    ]
    
    sales_return = SalesReturn.create(
        customer_id=CustomerId("CUST001"),
        customer_name="عميل اختبار",
        invoice_id=InvoiceId("INV001"),
        currency="SAR",
        items=items
    )
    
    sales_return.submit()
    sales_return.cancel(cancelled_by="USER001", reason="طلب العميل الإلغاء")
    
    assert sales_return.status == ReturnStatus.CANCELLED
    assert sales_return.cancelled_by == "USER001"
    print(f"✓ Status after cancel: {sales_return.status}")
    print(f"✓ Cancelled by: {sales_return.cancelled_by}")
    print("✓ TEST PASSED\n")
    return sales_return


def test_credit_note_creation():
    """اختبار إنشاء مذكرة الدائن"""
    print("\n=== TEST: Credit Note Creation ===")
    
    credit_note = CreditNote.create(
        customer_id=CustomerId("CUST001"),
        customer_name="عميل اختبار",
        currency="SAR",
        lines=[
            CreditNoteLine(
                product_code="PROD001",
                product_name="منتج اختبار",
                quantity=Decimal("2.00"),
                unit_price=Decimal("100.00"),
                tax_rate=Decimal("15.00"),
                tax_amount=Decimal("30.00")
            )
        ],
        reason="إرجاع بضائع تالفة",
        original_invoice_id="INV001"
    )
    
    assert credit_note.customer_id.value == "CUST001"
    assert credit_note.status.value == "DRAFT"
    assert len(credit_note.lines) == 1
    print(f"✓ Credit Note ID: {credit_note.credit_note_id}")
    print(f"✓ Credit Note Number: {credit_note.credit_note_number}")
    print(f"✓ Status: {credit_note.status}")
    print(f"✓ Total Amount: {credit_note.total_amount}")
    print("✓ TEST PASSED\n")
    return credit_note


if __name__ == "__main__":
    print("=" * 70)
    print("YASEEN ERP - SALES RETURN TEST SUITE")
    print("PHASE 1a: Sales Returns & Credit Notes")
    print("=" * 70)
    
    try:
        test_create_sales_return()
        test_submit_return()
        test_approve_return()
        test_receive_goods()
        test_inspect_items()
        test_complete_return()
        test_cancel_return()
        test_credit_note_creation()
        
        print("=" * 70)
        print("✓✓✓ ALL SALES RETURN TESTS PASSED ✓✓✓")
        print("=" * 70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise
