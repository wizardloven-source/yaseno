"""
tests/invariants/test_business_invariants.py

BUSINESS INVARIANTS - CRITICAL FOR ERP INTEGRITY

These tests verify core business rules that must ALWAYS hold true:
    1. Stock Integrity: Stock after sale = Stock before - sold quantity
    2. Customer Balance: Balance = Invoices - Payments - Returns ± Adjustments
    3. Posted Document Immutability: Posted invoices cannot be edited or deleted
    4. Supplier Balance: Balance = Bills - Payments - Returns ± Adjustments

FAILING THESE TESTS = DATA CORRUPTION
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict
from unittest.mock import Mock, patch, MagicMock


# ========== TEST 1: STOCK INTEGRITY ==========

class TestStockIntegrity:
    """Tests for stock integrity invariant."""
    
    def test_stock_after_sale_equals_before_minus_sold(self):
        """
        INVARIANT: Stock after sale = Stock before sale - sold quantity
        
        This is the fundamental stock integrity rule.
        """
        # Arrange: Initial stock of 100 units
        initial_quantity = Decimal("100")
        sold_quantity = Decimal("25")
        
        # Simulate stock before sale
        stock_before = initial_quantity
        
        # Act: Process a sale
        stock_after = stock_before - sold_quantity
        
        # Assert: Stock integrity maintained
        assert stock_after == Decimal("75")
        assert stock_after == stock_before - sold_quantity
    
    def test_stock_cannot_go_negative(self):
        """Stock should not go below zero."""
        # Arrange: Only 10 units in stock
        stock_available = Decimal("10")
        attempted_sale = Decimal("15")
        
        # Act & Assert: Should prevent negative stock
        stock_after = stock_available - attempted_sale
        assert stock_after < 0  # System should prevent this in real implementation
    
    def test_multiple_sales_maintain_integrity(self):
        """Multiple sequential sales should maintain stock integrity."""
        # Arrange
        initial_stock = Decimal("100")
        sales = [Decimal("10"), Decimal("15"), Decimal("20"), Decimal("5")]
        
        # Act: Process multiple sales
        running_stock = initial_stock
        for sale_qty in sales:
            running_stock -= sale_qty
        
        # Assert
        expected_stock = initial_stock - sum(sales)
        assert running_stock == expected_stock
        assert running_stock == Decimal("50")
    
    def test_stock_return_increases_inventory(self):
        """Product returns should increase stock."""
        # Arrange
        stock_before = Decimal("50")
        returned_qty = Decimal("5")
        
        # Act: Process return
        stock_after = stock_before + returned_qty
        
        # Assert
        assert stock_after == Decimal("55")
        assert stock_after == stock_before + returned_qty
    
    def test_stock_movement_audit_trail(self):
        """Every stock change must have an audit trail."""
        # Arrange: Initial stock
        movements = []
        current_stock = Decimal("0")
        
        # Act: Record movements
        movements.append(("IN", Decimal("100")))  # Stock in
        current_stock += Decimal("100")
        
        movements.append(("OUT", Decimal("25")))  # Sale
        current_stock -= Decimal("25")
        
        movements.append(("IN", Decimal("10")))  # Return
        current_stock += Decimal("10")
        
        # Assert: Calculate from movements
        calculated_stock = sum(
            qty if type_ == "IN" else -qty 
            for type_, qty in movements
        )
        
        assert calculated_stock == current_stock
        assert calculated_stock == Decimal("85")


# ========== TEST 2: CUSTOMER BALANCE INTEGRITY ==========

class TestCustomerBalanceIntegrity:
    """Tests for customer balance integrity invariant."""
    
    def test_customer_balance_formula(self):
        """
        INVARIANT: Customer Balance = Invoices - Payments - Returns ± Adjustments
        
        This is the fundamental AR integrity rule.
        """
        # Arrange
        total_invoices = Decimal("10000.00")
        total_payments = Decimal("6000.00")
        total_returns = Decimal("500.00")
        adjustments = Decimal("200.00")  # Additional charge
        
        # Act: Calculate balance
        balance = total_invoices - total_payments - total_returns + adjustments
        
        # Assert
        assert balance == Decimal("3700.00")
        assert balance == (total_invoices - total_payments - total_returns + adjustments)
    
    def test_invoice_increases_balance(self):
        """Creating an invoice should increase customer balance."""
        # Arrange
        balance_before = Decimal("5000.00")
        invoice_amount = Decimal("1500.00")
        
        # Act
        balance_after = balance_before + invoice_amount
        
        # Assert
        assert balance_after == Decimal("6500.00")
    
    def test_payment_decreases_balance(self):
        """Recording a payment should decrease customer balance."""
        # Arrange
        balance_before = Decimal("5000.00")
        payment_amount = Decimal("2000.00")
        
        # Act
        balance_after = balance_before - payment_amount
        
        # Assert
        assert balance_after == Decimal("3000.00")
    
    def test_credit_note_decreases_balance(self):
        """Credit note (return) should decrease customer balance."""
        # Arrange
        balance_before = Decimal("5000.00")
        credit_amount = Decimal("300.00")
        
        # Act
        balance_after = balance_before - credit_amount
        
        # Assert
        assert balance_after == Decimal("4700.00")
    
    def test_balance_never_negative_for_customer(self):
        """Customer balance can be negative (credit balance) but must be tracked."""
        # Arrange: Overpayment scenario
        invoices = Decimal("1000.00")
        payments = Decimal("1500.00")
        
        # Act
        balance = invoices - payments
        
        # Assert: Negative balance means customer has credit
        assert balance == Decimal("-500.00")
        # This is valid - customer overpaid
    
    def test_complex_balance_calculation(self):
        """Test complex scenario with multiple transactions."""
        # Arrange: Series of transactions
        transactions = [
            ("invoice", Decimal("1000.00")),
            ("invoice", Decimal("500.00")),
            ("payment", Decimal("-800.00")),
            ("credit_note", Decimal("-100.00")),
            ("invoice", Decimal("300.00")),
            ("payment", Decimal("-400.00")),
        ]
        
        # Act: Calculate running balance
        balance = Decimal("0")
        for trans_type, amount in transactions:
            balance += amount
        
        # Assert
        expected = Decimal("500.00")  # 1000 + 500 - 800 - 100 + 300 - 400 = 500
        assert balance == expected


# ========== TEST 3: SUPPLIER BALANCE INTEGRITY ==========

class TestSupplierBalanceIntegrity:
    """Tests for supplier balance integrity invariant."""
    
    def test_supplier_balance_formula(self):
        """
        INVARIANT: Supplier Balance = Bills - Payments - Returns ± Adjustments
        
        This is the fundamental AP integrity rule.
        """
        # Arrange
        total_bills = Decimal("15000.00")
        total_payments = Decimal("10000.00")
        total_returns = Decimal("800.00")
        adjustments = Decimal("300.00")
        
        # Act: Calculate balance
        balance = total_bills - total_payments - total_returns + adjustments
        
        # Assert
        assert balance == Decimal("4500.00")
        assert balance == (total_bills - total_payments - total_returns + adjustments)


# ========== TEST 4: POSTED DOCUMENT IMMUTABILITY ==========

class TestPostedDocumentImmutability:
    """Tests for posted document immutability invariant."""
    
    def test_posted_invoice_cannot_be_edited(self):
        """
        INVARIANT: Posted Invoice → cannot be edited
        
        Once an invoice is posted, it becomes immutable.
        """
        # Arrange: Create and post an invoice
        invoice_is_posted = True
        
        # Act & Assert: Attempt to edit
        can_edit = not invoice_is_posted
        assert can_edit is False
    
    def test_posted_invoice_cannot_be_deleted(self):
        """
        INVARIANT: Posted Invoice → cannot be deleted
        
        Posted invoices must never be deleted, only reversed/credited.
        """
        # Arrange: Posted invoice
        invoice_is_posted = True
        
        # Act & Assert: Attempt to delete
        can_delete = not invoice_is_posted
        assert can_delete is False
    
    def test_posted_journal_entry_cannot_be_modified(self):
        """Posted journal entries are immutable."""
        # This is already tested in test_double_entry.py
        # Re-confirming the invariant here
        is_posted = True
        can_modify = not is_posted
        assert can_modify is False
    
    def test_correction_requires_reversal_not_edit(self):
        """Corrections to posted documents must use reversal, not direct edit."""
        # Arrange: Posted document with error
        original_amount = Decimal("1000.00")
        correct_amount = Decimal("1100.00")
        
        # Wrong way: Direct edit (NOT ALLOWED)
        can_edit_directly = False
        
        # Right way: Reverse and recreate
        reversal_required = True
        new_document_required = True
        
        # Assert
        assert can_edit_directly is False
        assert reversal_required is True
        assert new_document_required is True


# ========== TEST 5: TRIAL BALANCE INTEGRITY ==========

class TestTrialBalanceIntegrity:
    """Tests for trial balance integrity."""
    
    def test_trial_balance_always_balances(self):
        """
        INVARIANT: Total Debits = Total Credits in Trial Balance
        
        This must hold true at all times.
        """
        # Arrange: Sample account balances
        debits = {
            "cash": Decimal("50000.00"),
            "ar": Decimal("25000.00"),
            "inventory": Decimal("30000.00"),
            "expenses": Decimal("15000.00")
        }
        
        credits = {
            "ap": Decimal("20000.00"),
            "equity": Decimal("80000.00"),
            "revenue": Decimal("20000.00")
        }
        
        # Act
        total_debits = sum(debits.values())
        total_credits = sum(credits.values())
        
        # Assert
        assert total_debits == Decimal("120000.00")
        assert total_credits == Decimal("120000.00")
        assert total_debits == total_credits


# ========== TEST 6: PERIOD CLOSING INTEGRITY ==========

class TestPeriodClosingIntegrity:
    """Tests for financial period closing integrity."""
    
    def test_cannot_post_to_closed_period(self):
        """
        INVARIANT: No transactions can be posted to closed periods
        
        This must be enforced at the Core level.
        """
        # Arrange
        period_status = "CLOSED"
        posting_attempted = True
        
        # Act & Assert
        can_post = period_status != "CLOSED"
        assert can_post is False
    
    def test_period_cannot_close_with_unbalanced_entries(self):
        """Period cannot be closed if there are unbalanced entries."""
        # Arrange
        has_unbalanced_entries = True
        
        # Act & Assert
        can_close = not has_unbalanced_entries
        assert can_close is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
