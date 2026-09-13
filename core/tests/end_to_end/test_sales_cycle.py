"""
tests/end_to_end/test_sales_cycle.py

END-TO-END SALES CYCLE TESTS

Tests complete sales workflow:
    Quote → Sales Order → Delivery → Invoice → Payment

This validates the entire sales process from start to finish.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from unittest.mock import Mock, patch


# ========== DOMAIN MODELS FOR E2E TESTING ==========

@dataclass
class Customer:
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
class Quotation:
    id: str
    customer_id: str
    lines: List[Dict]
    total: Decimal
    status: str = "DRAFT"  # DRAFT, SENT, ACCEPTED, REJECTED
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SalesOrder:
    id: str
    quotation_id: Optional[str]
    customer_id: str
    lines: List[Dict]
    total: Decimal
    status: str = "PENDING"  # PENDING, CONFIRMED, DELIVERED, INVOICED, COMPLETED
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Delivery:
    id: str
    sales_order_id: str
    customer_id: str
    lines: List[Dict]
    status: str = "PENDING"  # PENDING, PARTIAL, COMPLETED
    shipped_at: Optional[datetime] = None


@dataclass
class SalesInvoice:
    id: str
    sales_order_id: Optional[str]
    delivery_id: Optional[str]
    customer_id: str
    lines: List[Dict]
    total: Decimal
    status: str = "DRAFT"  # DRAFT, POSTED, PAID, CANCELLED
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Payment:
    id: str
    invoice_id: str
    customer_id: str
    amount: Decimal
    method: str = "CASH"  # CASH, BANK_TRANSFER, CHECK
    status: str = "PENDING"  # PENDING, COMPLETED
    paid_at: Optional[datetime] = None


class SalesCycleService:
    """Service for managing the complete sales cycle."""
    
    def __init__(self):
        self.customers = {}
        self.products = {}
        self.quotations = {}
        self.sales_orders = {}
        self.deliveries = {}
        self.invoices = {}
        self.payments = {}
        
        self._quote_counter = 0
        self._order_counter = 0
        self._delivery_counter = 0
        self._invoice_counter = 0
        self._payment_counter = 0
    
    def create_customer(self, customer_id: str, name: str, email: str) -> Customer:
        """Create a new customer."""
        customer = Customer(id=customer_id, name=name, email=email)
        self.customers[customer_id] = customer
        return customer
    
    def create_product(self, product_id: str, sku: str, name: str, 
                       price: Decimal, cost: Decimal, stock: Decimal) -> Product:
        """Create a new product with initial stock."""
        product = Product(
            id=product_id, sku=sku, name=name,
            price=price, cost=cost, stock_quantity=stock
        )
        self.products[product_id] = product
        return product
    
    def create_quotation(self, customer_id: str, lines: List[Dict]) -> Quotation:
        """Create a new quotation."""
        self._quote_counter += 1
        quote_id = f"QUO-{self._quote_counter:04d}"
        
        total = Decimal("0")
        for line in lines:
            product = self.products.get(line["product_id"])
            if product:
                line["unit_price"] = product.price
                line["line_total"] = product.price * line["quantity"]
                total += line["line_total"]
        
        quotation = Quotation(
            id=quote_id,
            customer_id=customer_id,
            lines=lines,
            total=total
        )
        self.quotations[quote_id] = quotation
        return quotation
    
    def accept_quotation(self, quotation_id: str) -> SalesOrder:
        """Convert accepted quotation to sales order."""
        quotation = self.quotations.get(quotation_id)
        if not quotation:
            raise ValueError(f"Quotation {quotation_id} not found")
        
        if quotation.status != "DRAFT":
            raise ValueError(f"Quotation {quotation_id} cannot be accepted")
        
        # Update quotation status
        quotation.status = "ACCEPTED"
        
        # Create sales order
        self._order_counter += 1
        order_id = f"SO-{self._order_counter:04d}"
        
        sales_order = SalesOrder(
            id=order_id,
            quotation_id=quotation_id,
            customer_id=quotation.customer_id,
            lines=quotation.lines,
            total=quotation.total
        )
        self.sales_orders[order_id] = sales_order
        
        # Reserve stock
        for line in sales_order.lines:
            product = self.products.get(line["product_id"])
            if product:
                product.stock_quantity -= line["quantity"]
        
        return sales_order
    
    def create_delivery(self, sales_order_id: str) -> Delivery:
        """Create delivery from sales order."""
        sales_order = self.sales_orders.get(sales_order_id)
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        self._delivery_counter += 1
        delivery_id = f"DEL-{self._delivery_counter:04d}"
        
        delivery = Delivery(
            id=delivery_id,
            sales_order_id=sales_order_id,
            customer_id=sales_order.customer_id,
            lines=sales_order.lines,
            status="COMPLETED",
            shipped_at=datetime.now()
        )
        self.deliveries[delivery_id] = delivery
        
        # Update sales order status
        sales_order.status = "DELIVERED"
        
        return delivery
    
    def create_invoice(self, sales_order_id: str, delivery_id: str) -> SalesInvoice:
        """Create invoice from delivered order."""
        sales_order = self.sales_orders.get(sales_order_id)
        if not sales_order:
            raise ValueError(f"Sales Order {sales_order_id} not found")
        
        if sales_order.status != "DELIVERED":
            raise ValueError(f"Sales Order {sales_order_id} not delivered yet")
        
        self._invoice_counter += 1
        invoice_id = f"INV-{self._invoice_counter:04d}"
        
        invoice = SalesInvoice(
            id=invoice_id,
            sales_order_id=sales_order_id,
            delivery_id=delivery_id,
            customer_id=sales_order.customer_id,
            lines=sales_order.lines,
            total=sales_order.total,
            status="POSTED"
        )
        self.invoices[invoice_id] = invoice
        
        # Update sales order status
        sales_order.status = "INVOICED"
        
        # Update customer balance
        customer = self.customers.get(invoice.customer_id)
        if customer:
            customer.balance += invoice.total
        
        return invoice
    
    def record_payment(self, invoice_id: str, amount: Decimal, method: str = "CASH") -> Payment:
        """Record payment against invoice."""
        invoice = self.invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        if invoice.status == "PAID":
            raise ValueError(f"Invoice {invoice_id} already paid")
        
        # Calculate total paid so far
        total_paid = sum(
            p.amount for p in self.payments.values() 
            if p.invoice_id == invoice_id
        )
        
        self._payment_counter += 1
        payment_id = f"PMT-{self._payment_counter:04d}"
        
        payment = Payment(
            id=payment_id,
            invoice_id=invoice_id,
            customer_id=invoice.customer_id,
            amount=amount,
            method=method,
            status="COMPLETED",
            paid_at=datetime.now()
        )
        self.payments[payment_id] = payment
        
        # Update total paid including new payment
        total_paid += amount
        
        # Update invoice status if fully paid
        if total_paid >= invoice.total:
            invoice.status = "PAID"
        
        # Update customer balance
        customer = self.customers.get(invoice.customer_id)
        if customer:
            customer.balance -= amount
        
        # Update sales order status
        if invoice.sales_order_id:
            sales_order = self.sales_orders.get(invoice.sales_order_id)
            if sales_order and invoice.status == "PAID":
                sales_order.status = "COMPLETED"
        
        return payment


# ========== FIXTURES ==========

@pytest.fixture
def sales_service():
    """Create sales cycle service."""
    return SalesCycleService()


@pytest.fixture
def sample_customer(sales_service):
    """Create a sample customer."""
    return sales_service.create_customer(
        customer_id="CUST-001",
        name="Test Customer LLC",
        email="customer@test.com"
    )


@pytest.fixture
def sample_products(sales_service):
    """Create sample products."""
    product1 = sales_service.create_product(
        product_id="PROD-001",
        sku="SKU-001",
        name="Widget A",
        price=Decimal("100.00"),
        cost=Decimal("60.00"),
        stock=Decimal("100")
    )
    
    product2 = sales_service.create_product(
        product_id="PROD-002",
        sku="SKU-002",
        name="Widget B",
        price=Decimal("150.00"),
        cost=Decimal("90.00"),
        stock=Decimal("50")
    )
    
    return [product1, product2]


# ========== TESTS ==========

class TestCompleteSalesCycle:
    """Tests for complete sales cycle from quote to payment."""
    
    def test_full_sales_cycle(self, sales_service, sample_customer, sample_products):
        """
        Test complete flow:
        Quote → Order → Delivery → Invoice → Payment
        """
        # Step 1: Create Quotation
        quotation_lines = [
            {"product_id": "PROD-001", "quantity": Decimal("10")},
            {"product_id": "PROD-002", "quantity": Decimal("5")}
        ]
        quotation = sales_service.create_quotation(
            customer_id="CUST-001",
            lines=quotation_lines
        )
        
        # Assert quotation created
        assert quotation.id.startswith("QUO-")
        assert quotation.status == "DRAFT"
        expected_total = Decimal("1750.00")  # 10 * 100 + 5 * 150 = 1000 + 750 = 1750
        assert quotation.total == expected_total
        
        # Step 2: Accept Quotation → Create Sales Order
        sales_order = sales_service.accept_quotation(quotation.id)
        
        # Assert order created
        assert sales_order.id.startswith("SO-")
        assert sales_order.quotation_id == quotation.id
        assert sales_order.status == "PENDING"
        assert sales_order.total == Decimal("1750.00")
        
        # Assert stock reserved
        prod1 = sales_service.products["PROD-001"]
        prod2 = sales_service.products["PROD-002"]
        assert prod1.stock_quantity == Decimal("90")  # 100 - 10
        assert prod2.stock_quantity == Decimal("45")  # 50 - 5
        
        # Step 3: Create Delivery
        delivery = sales_service.create_delivery(sales_order.id)
        
        # Assert delivery created
        assert delivery.id.startswith("DEL-")
        assert delivery.status == "COMPLETED"
        assert sales_order.status == "DELIVERED"
        
        # Step 4: Create Invoice
        invoice = sales_service.create_invoice(
            sales_order_id=sales_order.id,
            delivery_id=delivery.id
        )
        
        # Assert invoice created
        assert invoice.id.startswith("INV-")
        assert invoice.status == "POSTED"
        assert invoice.total == Decimal("1750.00")
        assert sales_order.status == "INVOICED"
        
        # Assert customer balance updated
        customer = sales_service.customers["CUST-001"]
        assert customer.balance == Decimal("1750.00")
        
        # Step 5: Record Payment
        payment = sales_service.record_payment(
            invoice_id=invoice.id,
            amount=Decimal("1750.00"),
            method="BANK_TRANSFER"
        )
        
        # Assert payment recorded
        assert payment.id.startswith("PMT-")
        assert payment.status == "COMPLETED"
        assert invoice.status == "PAID"
        assert sales_order.status == "COMPLETED"
        
        # Assert customer balance cleared
        customer = sales_service.customers["CUST-001"]
        assert customer.balance == Decimal("0.00")
    
    def test_partial_payment(self, sales_service, sample_customer, sample_products):
        """Test partial payment scenario."""
        # Create and accept quotation
        quotation = sales_service.create_quotation(
            customer_id="CUST-001",
            lines=[{"product_id": "PROD-001", "quantity": Decimal("10")}]
        )
        sales_order = sales_service.accept_quotation(quotation.id)
        delivery = sales_service.create_delivery(sales_order.id)
        invoice = sales_service.create_invoice(sales_order.id, delivery.id)
        
        # First partial payment
        payment1 = sales_service.record_payment(
            invoice_id=invoice.id,
            amount=Decimal("500.00")
        )
        
        # Assert
        assert invoice.status == "POSTED"  # Not fully paid yet
        customer = sales_service.customers["CUST-001"]
        assert customer.balance == Decimal("500.00")  # 1000 - 500
        
        # Second partial payment (full remaining amount)
        payment2 = sales_service.record_payment(
            invoice_id=invoice.id,
            amount=Decimal("500.00")
        )
        
        # Assert
        assert invoice.status == "PAID"
        customer = sales_service.customers["CUST-001"]
        assert customer.balance == Decimal("0.00")
    
    def test_stock_reserved_on_order(self, sales_service, sample_customer, sample_products):
        """Test that stock is reserved when order is created."""
        # Initial stock
        prod1 = sales_service.products["PROD-001"]
        assert prod1.stock_quantity == Decimal("100")
        
        # Create and accept order
        quotation = sales_service.create_quotation(
            customer_id="CUST-001",
            lines=[{"product_id": "PROD-001", "quantity": Decimal("25")}]
        )
        sales_order = sales_service.accept_quotation(quotation.id)
        
        # Stock should be reserved
        prod1 = sales_service.products["PROD-001"]
        assert prod1.stock_quantity == Decimal("75")  # 100 - 25
    
    def test_quotation_rejection(self, sales_service, sample_customer, sample_products):
        """Test quotation rejection scenario."""
        # Create quotation
        quotation = sales_service.create_quotation(
            customer_id="CUST-001",
            lines=[{"product_id": "PROD-001", "quantity": Decimal("10")}]
        )
        
        # Reject (in real system, would update status)
        quotation.status = "REJECTED"
        
        # Assert no order created
        assert len(sales_service.sales_orders) == 0
        
        # Assert stock not reserved
        prod1 = sales_service.products["PROD-001"]
        assert prod1.stock_quantity == Decimal("100")  # Unchanged


class TestSalesCycleEdgeCases:
    """Tests for edge cases in sales cycle."""
    
    def test_cannot_invoice_undelivered_order(self, sales_service, sample_customer, sample_products):
        """Cannot create invoice for undelivered order."""
        # Create order but don't deliver
        quotation = sales_service.create_quotation(
            customer_id="CUST-001",
            lines=[{"product_id": "PROD-001", "quantity": Decimal("10")}]
        )
        sales_order = sales_service.accept_quotation(quotation.id)
        
        # Attempt to invoice without delivery
        with pytest.raises(ValueError) as exc_info:
            sales_service.create_invoice(sales_order.id, None)
        
        assert "not delivered" in str(exc_info.value).lower()
    
    def test_cannot_accept_already_accepted_quote(self, sales_service, sample_customer, sample_products):
        """Cannot accept quotation twice."""
        # Create and accept quotation
        quotation = sales_service.create_quotation(
            customer_id="CUST-001",
            lines=[{"product_id": "PROD-001", "quantity": Decimal("10")}]
        )
        sales_service.accept_quotation(quotation.id)
        
        # Attempt to accept again
        with pytest.raises(ValueError) as exc_info:
            sales_service.accept_quotation(quotation.id)
        
        assert "cannot be accepted" in str(exc_info.value).lower()
    
    def test_multiple_products_in_single_order(self, sales_service, sample_customer, sample_products):
        """Test order with multiple products."""
        # Create quotation with multiple products
        quotation = sales_service.create_quotation(
            customer_id="CUST-001",
            lines=[
                {"product_id": "PROD-001", "quantity": Decimal("5")},
                {"product_id": "PROD-002", "quantity": Decimal("3")},
                {"product_id": "PROD-001", "quantity": Decimal("2")}
            ]
        )
        
        # Accept quotation
        sales_order = sales_service.accept_quotation(quotation.id)
        
        # Verify totals
        # PROD-001: 7 units × 100 = 700
        # PROD-002: 3 units × 150 = 450
        # Total: 1150
        assert sales_order.total == Decimal("1150.00")
        
        # Verify stock
        assert sales_service.products["PROD-001"].stock_quantity == Decimal("93")  # 100 - 7
        assert sales_service.products["PROD-002"].stock_quantity == Decimal("47")  # 50 - 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
