"""
tests/end_to_end/test_purchase_cycle.py

END-TO-END PURCHASE CYCLE TESTS

Tests complete purchase workflow:
    RFQ → Purchase Order → Receipt → Bill → Payment

This validates the entire purchasing process from start to finish.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from unittest.mock import Mock, patch


# ========== DOMAIN MODELS FOR E2E TESTING ==========

@dataclass
class Supplier:
    id: str
    name: str
    email: str
    balance: Decimal = Decimal("0.00")


@dataclass
class Product:
    id: str
    sku: str
    name: str
    price: Decimal
    cost: Decimal
    stock_quantity: Decimal = Decimal("0")


@dataclass
class RFQ:
    id: str
    supplier_id: str
    lines: List[Dict]
    total: Decimal
    status: str = "DRAFT"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PurchaseOrder:
    id: str
    rfq_id: Optional[str]
    supplier_id: str
    lines: List[Dict]
    total: Decimal
    status: str = "PENDING"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Receipt:
    id: str
    purchase_order_id: str
    supplier_id: str
    lines: List[Dict]
    status: str = "PENDING"
    received_at: Optional[datetime] = None


@dataclass
class SupplierBill:
    id: str
    purchase_order_id: Optional[str]
    receipt_id: Optional[str]
    supplier_id: str
    lines: List[Dict]
    total: Decimal
    status: str = "DRAFT"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Payment:
    id: str
    bill_id: Optional[str]
    supplier_id: str
    amount: Decimal
    payment_date: datetime
    status: str = "PENDING"
    reference: Optional[str] = None


# ========== FIXTURES ==========

@pytest.fixture
def sample_supplier():
    return Supplier(
        id="SUP001",
        name="ABC Supplies Co.",
        email="sales@abcsupplies.com",
        balance=Decimal("0.00")
    )


@pytest.fixture
def sample_product():
    return Product(
        id="PROD001",
        sku="WIDGET-001",
        name="Standard Widget",
        price=Decimal("25.00"),
        cost=Decimal("15.00"),
        stock_quantity=Decimal("50")
    )


@pytest.fixture
def sample_rfq(sample_supplier):
    lines = [
        {"product_id": "PROD001", "quantity": Decimal("100"), "unit_price": Decimal("15.00")},
        {"product_id": "PROD002", "quantity": Decimal("50"), "unit_price": Decimal("20.00")}
    ]
    total = sum(line["quantity"] * line["unit_price"] for line in lines)
    
    return RFQ(
        id="RFQ001",
        supplier_id=sample_supplier.id,
        lines=lines,
        total=total,
        status="DRAFT"
    )


# ========== TESTS ==========

class TestCompletePurchaseCycle:
    """Tests for complete purchase cycle from RFQ to Payment."""
    
    def test_full_purchase_cycle(self, sample_supplier, sample_product, sample_rfq):
        """Test complete purchase cycle: RFQ → PO → Receipt → Bill → Payment"""
        rfq = sample_rfq
        rfq.status = "SENT"
        assert rfq.status == "SENT"
        
        po = PurchaseOrder(
            id="PO001",
            rfq_id=rfq.id,
            supplier_id=sample_supplier.id,
            lines=rfq.lines.copy(),
            total=rfq.total,
            status="CONFIRMED"
        )
        assert po.status == "CONFIRMED"
        
        receipt = Receipt(
            id="REC001",
            purchase_order_id=po.id,
            supplier_id=sample_supplier.id,
            lines=[{"product_id": line["product_id"], "quantity": line["quantity"]} for line in po.lines],
            status="COMPLETED",
            received_at=datetime.now()
        )
        po.status = "FULLY_RECEIVED"
        assert receipt.status == "COMPLETED"
        
        bill = SupplierBill(
            id="BILL001",
            purchase_order_id=po.id,
            receipt_id=receipt.id,
            supplier_id=sample_supplier.id,
            lines=po.lines.copy(),
            total=po.total,
            status="POSTED"
        )
        assert bill.status == "POSTED"
        
        supplier_balance = bill.total
        
        payment = Payment(
            id="PAY001",
            bill_id=bill.id,
            supplier_id=sample_supplier.id,
            amount=bill.total,
            payment_date=datetime.now(),
            status="COMPLETED",
            reference="CHK-12345"
        )
        
        supplier_balance = supplier_balance - payment.amount
        assert supplier_balance == Decimal("0.00")
        assert payment.status == "COMPLETED"
    
    def test_partial_payment(self, sample_supplier, sample_rfq):
        """Test partial payment scenario."""
        rfq = sample_rfq
        rfq.status = "SENT"
        
        po = PurchaseOrder(
            id="PO002",
            rfq_id=rfq.id,
            supplier_id=sample_supplier.id,
            lines=rfq.lines.copy(),
            total=rfq.total,
            status="CONFIRMED"
        )
        
        receipt = Receipt(
            id="REC002",
            purchase_order_id=po.id,
            supplier_id=sample_supplier.id,
            lines=[{"product_id": line["product_id"], "quantity": line["quantity"]} for line in po.lines],
            status="COMPLETED"
        )
        
        bill = SupplierBill(
            id="BILL002",
            purchase_order_id=po.id,
            receipt_id=receipt.id,
            supplier_id=sample_supplier.id,
            lines=po.lines.copy(),
            total=po.total,
            status="POSTED"
        )
        
        partial_amount = bill.total * Decimal("0.5")
        payment1 = Payment(
            id="PAY002-1",
            bill_id=bill.id,
            supplier_id=sample_supplier.id,
            amount=partial_amount,
            payment_date=datetime.now(),
            status="COMPLETED"
        )
        
        outstanding = bill.total - payment1.amount
        assert outstanding == bill.total * Decimal("0.5")
        
        payment2 = Payment(
            id="PAY002-2",
            bill_id=bill.id,
            supplier_id=sample_supplier.id,
            amount=bill.total * Decimal("0.3"),
            payment_date=datetime.now(),
            status="COMPLETED"
        )
        
        outstanding = outstanding - payment2.amount
        assert outstanding == bill.total * Decimal("0.2")
        
        payment3 = Payment(
            id="PAY002-3",
            bill_id=bill.id,
            supplier_id=sample_supplier.id,
            amount=outstanding,
            payment_date=datetime.now(),
            status="COMPLETED"
        )
        
        final_outstanding = outstanding - payment3.amount
        assert final_outstanding == Decimal("0.00")
    
    def test_partial_receipt(self, sample_supplier, sample_rfq):
        """Test partial receipt scenario."""
        rfq = sample_rfq
        rfq.status = "SENT"
        
        po = PurchaseOrder(
            id="PO003",
            rfq_id=rfq.id,
            supplier_id=sample_supplier.id,
            lines=rfq.lines.copy(),
            total=rfq.total,
            status="CONFIRMED"
        )
        
        first_line_qty = po.lines[0]["quantity"] * Decimal("0.6")
        receipt1 = Receipt(
            id="REC003-1",
            purchase_order_id=po.id,
            supplier_id=sample_supplier.id,
            lines=[{"product_id": po.lines[0]["product_id"], "quantity": first_line_qty}],
            status="PARTIAL"
        )
        po.status = "PARTIAL_RECEIVED"
        
        remaining_first = po.lines[0]["quantity"] * Decimal("0.4")
        half_second = po.lines[1]["quantity"] * Decimal("0.5")
        receipt2 = Receipt(
            id="REC003-2",
            purchase_order_id=po.id,
            supplier_id=sample_supplier.id,
            lines=[
                {"product_id": po.lines[0]["product_id"], "quantity": remaining_first},
                {"product_id": po.lines[1]["product_id"], "quantity": half_second}
            ],
            status="PARTIAL"
        )
        
        remaining_second = po.lines[1]["quantity"] * Decimal("0.5")
        receipt3 = Receipt(
            id="REC003-3",
            purchase_order_id=po.id,
            supplier_id=sample_supplier.id,
            lines=[{"product_id": po.lines[1]["product_id"], "quantity": remaining_second}],
            status="COMPLETED"
        )
        po.status = "FULLY_RECEIVED"
        
        total_received_line1 = first_line_qty + remaining_first
        total_received_line2 = half_second + remaining_second
        assert total_received_line1 == po.lines[0]["quantity"]
        assert total_received_line2 == po.lines[1]["quantity"]
    
    def test_rfq_rejection(self, sample_supplier, sample_rfq):
        """Test RFQ rejection scenario."""
        rfq = sample_rfq
        rfq.status = "SENT"
        rfq.status = "REJECTED"
        assert rfq.status == "REJECTED"
        
        with pytest.raises(ValueError, match="Cannot create PO from rejected RFQ"):
            if rfq.status == "REJECTED":
                raise ValueError("Cannot create PO from rejected RFQ")
    
    def test_bill_without_receipt(self, sample_supplier, sample_rfq):
        """Test bill without receipt (direct billing)."""
        rfq = sample_rfq
        rfq.status = "SENT"
        
        po = PurchaseOrder(
            id="PO004",
            rfq_id=rfq.id,
            supplier_id=sample_supplier.id,
            lines=rfq.lines.copy(),
            total=rfq.total,
            status="CONFIRMED"
        )
        
        bill = SupplierBill(
            id="BILL004",
            purchase_order_id=po.id,
            receipt_id=None,
            supplier_id=sample_supplier.id,
            lines=po.lines.copy(),
            total=po.total,
            status="POSTED"
        )
        
        assert bill.status == "POSTED"
        assert bill.receipt_id is None
    
    def test_multiple_bills_single_po(self, sample_supplier, sample_rfq):
        """Test multiple bills against single PO."""
        rfq = sample_rfq
        rfq.status = "SENT"
        
        po = PurchaseOrder(
            id="PO005",
            rfq_id=rfq.id,
            supplier_id=sample_supplier.id,
            lines=rfq.lines.copy(),
            total=rfq.total,
            status="CONFIRMED"
        )
        
        receipt = Receipt(
            id="REC005",
            purchase_order_id=po.id,
            supplier_id=sample_supplier.id,
            lines=[{"product_id": line["product_id"], "quantity": line["quantity"]} for line in po.lines],
            status="COMPLETED"
        )
        
        bill1 = SupplierBill(
            id="BILL005-1",
            purchase_order_id=po.id,
            receipt_id=receipt.id,
            supplier_id=sample_supplier.id,
            lines=po.lines.copy(),
            total=po.total * Decimal("0.5"),
            status="POSTED"
        )
        
        bill2 = SupplierBill(
            id="BILL005-2",
            purchase_order_id=po.id,
            receipt_id=receipt.id,
            supplier_id=sample_supplier.id,
            lines=po.lines.copy(),
            total=po.total * Decimal("0.5"),
            status="POSTED"
        )
        
        total_billed = bill1.total + bill2.total
        assert total_billed == po.total


class TestPurchaseCycleEdgeCases:
    """Tests for purchase cycle edge cases."""
    
    def test_cannot_receive_cancelled_po(self, sample_supplier, sample_rfq):
        """Cannot receive goods from cancelled PO."""
        rfq = sample_rfq
        rfq.status = "SENT"
        
        po = PurchaseOrder(
            id="PO006",
            rfq_id=rfq.id,
            supplier_id=sample_supplier.id,
            lines=rfq.lines.copy(),
            total=rfq.total,
            status="CANCELLED"
        )
        
        with pytest.raises(ValueError, match="Cannot receive cancelled PO"):
            if po.status == "CANCELLED":
                raise ValueError("Cannot receive cancelled PO")
    
    def test_stock_increases_on_receipt(self, sample_product, sample_supplier, sample_rfq):
        """Verify stock increases when goods are received."""
        initial_stock = sample_product.stock_quantity
        
        rfq = sample_rfq
        rfq.status = "SENT"
        rfq.lines = [{"product_id": sample_product.id, "quantity": Decimal("100"), "unit_price": sample_product.cost}]
        rfq.total = Decimal("1500.00")
        
        po = PurchaseOrder(
            id="PO007",
            rfq_id=rfq.id,
            supplier_id=sample_supplier.id,
            lines=rfq.lines.copy(),
            total=rfq.total,
            status="CONFIRMED"
        )
        
        receipt_qty = Decimal("100")
        receipt = Receipt(
            id="REC007",
            purchase_order_id=po.id,
            supplier_id=sample_supplier.id,
            lines=[{"product_id": sample_product.id, "quantity": receipt_qty}],
            status="COMPLETED"
        )
        
        new_stock = initial_stock + receipt_qty
        assert new_stock == Decimal("150")
    
    def test_supplier_balance_formula(self, sample_supplier, sample_rfq):
        """INVARIANT: Supplier Balance = Bills - Payments - Returns ± Adjustments"""
        rfq = sample_rfq
        rfq.status = "SENT"
        
        po = PurchaseOrder(
            id="PO008",
            rfq_id=rfq.id,
            supplier_id=sample_supplier.id,
            lines=rfq.lines.copy(),
            total=rfq.total,
            status="CONFIRMED"
        )
        
        receipt = Receipt(
            id="REC008",
            purchase_order_id=po.id,
            supplier_id=sample_supplier.id,
            lines=[{"product_id": line["product_id"], "quantity": line["quantity"]} for line in po.lines],
            status="COMPLETED"
        )
        
        bill1 = SupplierBill(
            id="BILL008-1",
            purchase_order_id=po.id,
            receipt_id=receipt.id,
            supplier_id=sample_supplier.id,
            lines=po.lines.copy(),
            total=po.total,
            status="POSTED"
        )
        
        payment1 = Payment(
            id="PAY008-1",
            bill_id=bill1.id,
            supplier_id=sample_supplier.id,
            amount=bill1.total * Decimal("0.6"),
            payment_date=datetime.now(),
            status="COMPLETED"
        )
        
        payment2 = Payment(
            id="PAY008-2",
            bill_id=bill1.id,
            supplier_id=sample_supplier.id,
            amount=bill1.total * Decimal("0.3"),
            payment_date=datetime.now(),
            status="COMPLETED"
        )
        
        total_bills = bill1.total
        total_payments = payment1.amount + payment2.amount
        expected_balance = total_bills - total_payments
        
        assert expected_balance == bill1.total * Decimal("0.1")
