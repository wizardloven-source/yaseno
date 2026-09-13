"""Sales Return Final Test"""
from decimal import Decimal
from datetime import date
from core.domain.sales.entities import SalesReturn, ReturnItem
from core.domain.sales.value_objects import ReturnStatus
from core.domain.customers.value_objects import CustomerId
from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.entities import CreditNote, CreditNoteLine

print("=" * 70)
print("YASEEN ERP - SALES RETURN TEST SUITE")
print("=" * 70)

# Test 1: Create Sales Return
print("\n=== TEST 1: Create Sales Return ===")
items = [ReturnItem(product_code="PROD001", product_name="منتج اختبار", quantity=Decimal("2.00"), unit_price=Decimal("100.00"), reason="تالف", condition="damaged", tax_rate=Decimal("15.00"), tax_amount=Decimal("30.00"))]
sales_return = SalesReturn.create(customer_id=CustomerId("CUST001"), customer_name="عميل اختبار", invoice_id=InvoiceId("INV001"), currency="SAR", items=items)
assert sales_return.status == ReturnStatus.DRAFT
print(f"✓ Return ID: {sales_return.return_id}")
print(f"✓ Status: {sales_return.status}")
print(f"✓ Total Amount: {sales_return.total_amount}")
print("✓ TEST 1 PASSED")

# Test 2-6: Full workflow
print("\n=== TEST 2-6: Full Workflow ===")
sales_return.submit()
print(f"✓ Submitted: {sales_return.status}")
sales_return.approve(approved_by="USER001", approval_date=date.today())
print(f"✓ Approved: {sales_return.status}")
sales_return.receive_goods(warehouse_id="WH001", received_by="USER002", received_date=date.today())
print(f"✓ Received: {sales_return.status}")
sales_return.inspect_items(inspected_by="USER003", inspection_date=date.today(), inspection_notes="تم الفحص")
print(f"✓ Inspected: {sales_return.status}")
sales_return.complete(completed_by="USER001")
print(f"✓ Completed: {sales_return.status}")
print("✓ TEST 2-6 PASSED")

# Test 7: Credit Note
print("\n=== TEST 7: Credit Note ===")
credit_note = CreditNote.create(customer_id=CustomerId("CUST001"), customer_name="عميل اختبار", currency="SAR", lines=[CreditNoteLine(product_code="PROD001", product_name="منتج اختبار", quantity=Decimal("2.00"), unit_price=Decimal("100.00"), tax_rate=Decimal("15.00"), tax_amount=Decimal("30.00"))], reason="إرجاع بضائع", original_invoice_id="INV001")
print(f"✓ Credit Note ID: {credit_note.credit_note_id}")
print(f"✓ Status: {credit_note.status}")
print("✓ TEST 7 PASSED")

print("\n" + "=" * 70)
print("✓✓✓ ALL SALES RETURN TESTS PASSED ✓✓✓")
print("=" * 70)
