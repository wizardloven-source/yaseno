"""Sales Return Simple Test"""
from decimal import Decimal
from datetime import date
from core.domain.sales.entities import SalesReturn, ReturnItem
from core.domain.sales.value_objects import ReturnId, ReturnNumber, ReturnStatus
from core.domain.shared.value_objects import CustomerId
from core.domain.invoicing.value_objects import InvoiceId
from core.domain.invoicing.entities import CreditNote, CreditNoteLine

print("=" * 70)
print("YASEEN ERP - SALES RETURN TEST SUITE")
print("=" * 70)

# Test 1: Create Sales Return
print("\n=== TEST 1: Create Sales Return ===")
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

assert sales_return.status == ReturnStatus.DRAFT
print(f"✓ Return ID: {sales_return.return_id}")
print(f"✓ Status: {sales_return.status}")
print(f"✓ Total Amount: {sales_return.total_amount}")
print("✓ TEST 1 PASSED")

# Test 2: Submit Return
print("\n=== TEST 2: Submit Return ===")
sales_return.submit()
assert sales_return.status == ReturnStatus.SUBMITTED
print(f"✓ Status after submit: {sales_return.status}")
print("✓ TEST 2 PASSED")

# Test 3: Approve Return
print("\n=== TEST 3: Approve Return ===")
sales_return.approve(approved_by="USER001", approval_date=date.today())
assert sales_return.status == ReturnStatus.APPROVED
print(f"✓ Status after approve: {sales_return.status}")
print("✓ TEST 3 PASSED")

# Test 4: Receive Goods
print("\n=== TEST 4: Receive Goods ===")
sales_return.receive_goods(warehouse_id="WH001", received_by="USER002", received_date=date.today())
assert sales_return.status == ReturnStatus.RECEIVED
print(f"✓ Status after receive: {sales_return.status}")
print("✓ TEST 4 PASSED")

# Test 5: Inspect Items
print("\n=== TEST 5: Inspect Items ===")
sales_return.inspect_items(inspected_by="USER003", inspection_date=date.today(), inspection_notes="تم الفحص")
assert sales_return.status == ReturnStatus.INSPECTED
print(f"✓ Status after inspect: {sales_return.status}")
print("✓ TEST 5 PASSED")

# Test 6: Complete Return
print("\n=== TEST 6: Complete Return ===")
sales_return.complete(completed_by="USER001")
assert sales_return.status == ReturnStatus.COMPLETED
print(f"✓ Status after complete: {sales_return.status}")
print("✓ TEST 6 PASSED")

# Test 7: Credit Note Creation
print("\n=== TEST 7: Credit Note Creation ===")
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
    reason="إرجاع بضائع",
    original_invoice_id="INV001"
)
assert credit_note.status.value == "DRAFT"
print(f"✓ Credit Note ID: {credit_note.credit_note_id}")
print(f"✓ Status: {credit_note.status}")
print("✓ TEST 7 PASSED")

print("\n" + "=" * 70)
print("✓✓✓ ALL SALES RETURN TESTS PASSED ✓✓✓")
print("=" * 70)
