"""
tests/accounting/test_double_entry.py

ACCOUNTING TESTS - THE MOST IMPORTANT TESTS IN THE SYSTEM

These tests verify:
    1. Double-entry accounting principle: SUM(debit) = SUM(credit)
    2. Immutability of posted entries
    3. Reversal pattern works correctly
    4. Trial balance always balances
    5. Period closing works properly

FAILING THESE TESTS = SYSTEM IS BROKEN
These tests must pass 100% of the time.
"""

import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict
from unittest.mock import Mock, patch

from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.value_objects import (
    AccountCode, Money, JournalEntryId, TransactionType
)
from core.domain.accounting.exceptions import (
    UnbalancedEntryError,
    AlreadyPostedError,
    PostedEntryModificationError,
    ClosedPeriodError,
    CannotReverseUnpostedError
)
from core.domain.accounting.services import (
    PostingEngine, LedgerEngine, ReversalService, ClosingService
)


# ========== FIXTURES ==========

@pytest.fixture
def sample_account_codes():
    """Sample account codes for testing."""
    return {
        "cash": AccountCode("1010"),
        "accounts_receivable": AccountCode("1020"),
        "inventory": AccountCode("1030"),
        "accounts_payable": AccountCode("2010"),
        "retained_earnings": AccountCode("3010"),
        "revenue": AccountCode("4010"),
        "cogs": AccountCode("5100"),
        "expense": AccountCode("5200")
    }


@pytest.fixture
def balanced_entry(sample_account_codes):
    """Create a balanced journal entry."""
    money = Money(Decimal("1000.00"), "USD")
    
    entry = JournalEntry(
        description="Test sale transaction",
        lines=[
            JournalLine(
                account_code=sample_account_codes["cash"],
                debit=money,
                credit=Money(Decimal("0"), "USD")
            ),
            JournalLine(
                account_code=sample_account_codes["revenue"],
                debit=Money(Decimal("0"), "USD"),
                credit=money
            )
        ]
    )
    return entry


@pytest.fixture
def unbalanced_entry(sample_account_codes):
    """Create an unbalanced journal entry."""
    money = Money(Decimal("1000.00"), "USD")
    
    entry = JournalEntry(
        description="Unbalanced transaction",
        lines=[
            JournalLine(
                account_code=sample_account_codes["cash"],
                debit=money,
                credit=Money(Decimal("0"), "USD")
            ),
            JournalLine(
                account_code=sample_account_codes["revenue"],
                debit=Money(Decimal("0"), "USD"),
                credit=Money(Decimal("900.00"), "USD")  # Only 900, not 1000
            )
        ]
    )
    return entry


@pytest.fixture
def three_line_balanced_entry(sample_account_codes):
    """Create a balanced entry with three lines."""
    total = Money(Decimal("5000.00"), "USD")
    
    entry = JournalEntry(
        description="Three-line transaction",
        lines=[
            JournalLine(
                account_code=sample_account_codes["cash"],
                debit=total,
                credit=Money(Decimal("0"), "USD")
            ),
            JournalLine(
                account_code=sample_account_codes["accounts_receivable"],
                debit=total,
                credit=Money(Decimal("0"), "USD")
            ),
            JournalLine(
                account_code=sample_account_codes["revenue"],
                debit=Money(Decimal("0"), "USD"),
                credit=Money(Decimal("10000.00"), "USD")  # Sum of both debits
            )
        ]
    )
    return entry


@pytest.fixture
def mock_ledger_repo():
    """Mock ledger repository for testing."""
    repo = Mock()
    repo.add_entry = Mock()
    repo.get_balance = Mock(return_value=Money(Decimal("0"), "USD"))
    repo.get_trial_balance = Mock(return_value={})
    return repo


@pytest.fixture
def mock_journal_repo():
    """Mock journal repository for testing."""
    repo = Mock()
    repo.save = Mock()
    repo.get_by_id = Mock(return_value=None)
    repo.exists_reversal = Mock(return_value=False)
    return repo


@pytest.fixture
def mock_period_repo():
    """Mock fiscal period repository for testing."""
    repo = Mock()
    repo.is_period_closed = Mock(return_value=False)
    repo.get_period_by_date = Mock(return_value=None)
    return repo


# ========== TEST 1: BALANCED ENTRY POSTS SUCCESSFULLY ==========

class TestDoubleEntryPrinciple:
    """Tests for the fundamental double-entry accounting principle."""
    
    def test_balanced_entry_posts_successfully(self, balanced_entry):
        """A balanced entry should post without errors."""
        # Act
        balanced_entry.post(posted_by="test_user")
        
        # Assert
        assert balanced_entry.is_posted is True
        assert balanced_entry.posted_by == "test_user"
        assert balanced_entry.posted_at is not None
    
    def test_balanced_entry_calculates_totals_correctly(self, balanced_entry):
        """Verify debit and credit totals are calculated correctly."""
        # Act
        debit, credit = balanced_entry._calculate_totals()
        
        # Assert
        assert debit == Decimal("1000.00")
        assert credit == Decimal("1000.00")
    
    def test_is_balanced_returns_true_for_balanced_entry(self, balanced_entry):
        """is_balanced() should return True for balanced entries."""
        assert balanced_entry.is_balanced() is True
    
    def test_balanced_entry_with_three_lines_posts_successfully(self, three_line_balanced_entry):
        """Entries with multiple lines should still balance."""
        # Act
        three_line_balanced_entry.post(posted_by="test_user")
        
        # Assert
        assert three_line_balanced_entry.is_posted is True
        debit, credit = three_line_balanced_entry._calculate_totals()
        assert debit == credit


class TestUnbalancedEntries:
    """Tests for unbalanced entries - must be rejected."""
    
    def test_unbalanced_entry_raises_error(self, unbalanced_entry):
        """Unbalanced entries MUST raise UnbalancedEntryError."""
        # Act & Assert
        with pytest.raises(UnbalancedEntryError) as exc_info:
            unbalanced_entry.post(posted_by="test_user")
        
        assert exc_info.value.debit_total == Decimal("1000.00")
        assert exc_info.value.credit_total == Decimal("900.00")
        assert exc_info.value.difference == Decimal("100.00")
    
    def test_unbalanced_entry_is_not_posted(self, unbalanced_entry):
        """Unbalanced entries should never be marked as posted."""
        try:
            unbalanced_entry.post(posted_by="test_user")
        except UnbalancedEntryError:
            pass
        
        assert unbalanced_entry.is_posted is False
        assert unbalanced_entry.posted_at is None
    
    def test_is_balanced_returns_false_for_unbalanced_entry(self, unbalanced_entry):
        """is_balanced() should return False for unbalanced entries."""
        assert unbalanced_entry.is_balanced() is False
    
    def test_cannot_add_line_with_both_debit_and_credit(self, sample_account_codes):
        """A journal line cannot have both debit and credit."""
        money = Money(Decimal("100"), "USD")
        
        with pytest.raises(ValueError) as exc_info:
            JournalLine(
                account_code=sample_account_codes["cash"],
                debit=money,
                credit=money
            )
        
        assert "cannot have both" in str(exc_info.value).lower()
    
    def test_cannot_add_line_with_neither_debit_nor_credit(self, sample_account_codes):
        """A journal line must have either debit or credit."""
        zero = Money(Decimal("0"), "USD")
        
        with pytest.raises(ValueError) as exc_info:
            JournalLine(
                account_code=sample_account_codes["cash"],
                debit=zero,
                credit=zero
            )
        
        assert "either debit or credit" in str(exc_info.value).lower()
    
    def test_cannot_add_negative_amounts(self, sample_account_codes):
        """Negative amounts are not allowed."""
        negative_money = Money(Decimal("-100"), "USD")
        
        with pytest.raises(ValueError) as exc_info:
            JournalLine(
                account_code=sample_account_codes["cash"],
                debit=negative_money,
                credit=Money(Decimal("0"), "USD")
            )
        
        assert "negative" in str(exc_info.value).lower()


class TestPostedEntryImmutability:
    """Tests for immutability of posted entries."""
    
    def test_cannot_modify_posted_entry(self, balanced_entry):
        """Posted entries cannot be modified."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act & Assert
        with pytest.raises(PostedEntryModificationError) as exc_info:
            balanced_entry.add_line(
                JournalLine(
                    account_code=AccountCode("1020"),
                    debit=Money(Decimal("100"), "USD"),
                    credit=Money(Decimal("0"), "USD")
                )
            )
        
        assert str(balanced_entry.id) in str(exc_info.value)
    
    def test_cannot_post_entry_twice(self, balanced_entry):
        """Posting an entry twice should raise an error."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act & Assert
        with pytest.raises(AlreadyPostedError) as exc_info:
            balanced_entry.post(posted_by="test_user2")
        
        assert str(balanced_entry.id) in str(exc_info.value)
    
    def test_validate_for_posting_returns_errors_for_posted_entry(self, balanced_entry):
        """validate_for_posting() should return errors for posted entries."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act
        errors = balanced_entry.validate_for_posting()
        
        # Assert
        assert any("already posted" in e.lower() for e in errors)
    
    def test_cannot_add_line_after_post(self, balanced_entry):
        """Cannot add lines after posting."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act & Assert
        with pytest.raises(PostedEntryModificationError):
            balanced_entry.add_line(
                JournalLine(
                    account_code=AccountCode("1020"),
                    debit=Money(Decimal("100"), "USD"),
                    credit=Money(Decimal("0"), "USD")
                )
            )


class TestReversalPattern:
    """Tests for the reversal pattern - the ONLY way to modify posted entries."""
    
    def test_reverse_creates_new_entry(self, balanced_entry):
        """Reversing creates a new entry, doesn't modify original."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act
        reversal = balanced_entry.reverse(reason="Test reversal")
        
        # Assert
        assert reversal is not balanced_entry
        assert reversal.reverses_entry_id == balanced_entry.id
        assert reversal.is_posted is False
    
    def test_reversal_swaps_debit_and_credit(self, balanced_entry):
        """Reversal should swap all debits with credits."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act
        reversal = balanced_entry.reverse(reason="Test reversal")
        
        # Assert
        original_line = balanced_entry.lines[0]
        reversal_line = reversal.lines[0]
        
        # Original: debit 1000, credit 0
        # Reversal: debit 0, credit 1000
        assert original_line.debit.amount == Decimal("1000")
        assert reversal_line.debit.amount == Decimal("0")
        assert reversal_line.credit.amount == Decimal("1000")
    
    def test_reversal_is_balanced(self, balanced_entry):
        """Reversal entries must also be balanced."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act
        reversal = balanced_entry.reverse(reason="Test reversal")
        
        # Assert
        assert reversal.is_balanced() is True
        debit, credit = reversal._calculate_totals()
        assert debit == credit
    
    def test_cannot_reverse_unposted_entry(self, balanced_entry):
        """Cannot reverse an entry that hasn't been posted."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            balanced_entry.reverse(reason="Test")
        
        assert "only reverse posted" in str(exc_info.value).lower()
    
    def test_reversal_description_includes_original(self, balanced_entry):
        """Reversal description should reference the original entry."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act
        reversal = balanced_entry.reverse(reason="Error correction")
        
        # Assert
        assert str(balanced_entry.id) in reversal.description
        assert "Error correction" in reversal.description


class TestPostingEngine:
    """Tests for the PostingEngine domain service."""
    
    def test_posting_engine_posts_valid_entry(
        self, balanced_entry, mock_ledger_repo, mock_journal_repo, mock_period_repo
    ):
        """PostingEngine should successfully post valid entries."""
        # Arrange
        engine = PostingEngine(
            journal_repo=mock_journal_repo,
            ledger_repo=mock_ledger_repo,
            period_repo=mock_period_repo
        )
        
        # Act
        engine.post(balanced_entry, posted_by="test_user")
        
        # Assert
        assert balanced_entry.is_posted is True
        # Ledger entries should be created
        assert mock_ledger_repo.add_entry.call_count == len(balanced_entry.lines)
        # Journal entry should be saved
        mock_journal_repo.save.assert_called_once_with(balanced_entry)
    
    def test_posting_engine_rejects_unbalanced_entry(
        self, unbalanced_entry, mock_ledger_repo, mock_journal_repo, mock_period_repo
    ):
        """PostingEngine must reject unbalanced entries."""
        # Arrange
        engine = PostingEngine(
            journal_repo=mock_journal_repo,
            ledger_repo=mock_ledger_repo,
            period_repo=mock_period_repo
        )
        
        # Act & Assert
        with pytest.raises(UnbalancedEntryError):
            engine.post(unbalanced_entry, posted_by="test_user")
        
        # No ledger entries should be created
        mock_ledger_repo.add_entry.assert_not_called()
        # Entry should not be saved as posted
        assert unbalanced_entry.is_posted is False
    
    def test_posting_engine_rejects_duplicate_post(
        self, balanced_entry, mock_ledger_repo, mock_journal_repo, mock_period_repo
    ):
        """Cannot post the same entry twice."""
        # Arrange
        engine = PostingEngine(
            journal_repo=mock_journal_repo,
            ledger_repo=mock_ledger_repo,
            period_repo=mock_period_repo
        )
        
        engine.post(balanced_entry, posted_by="user1")
        
        # Act & Assert
        with pytest.raises(AlreadyPostedError):
            engine.post(balanced_entry, posted_by="user2")
    
    def test_posting_engine_rejects_closed_period(
        self, balanced_entry, mock_ledger_repo, mock_journal_repo, mock_period_repo
    ):
        """Cannot post to a closed fiscal period."""
        # Arrange
        mock_period_repo.is_period_closed.return_value = True
        
        engine = PostingEngine(
            journal_repo=mock_journal_repo,
            ledger_repo=mock_ledger_repo,
            period_repo=mock_period_repo
        )
        
        # Act & Assert
        with pytest.raises(ClosedPeriodError):
            engine.post(balanced_entry, posted_by="test_user")
    
    def test_validate_before_posting_returns_errors(self, unbalanced_entry, mock_period_repo):
        """validate_before_posting() should return validation errors."""
        # Arrange
        engine = PostingEngine(
            journal_repo=Mock(),
            ledger_repo=Mock(),
            period_repo=mock_period_repo
        )
        
        # Act
        errors = engine.validate_before_posting(unbalanced_entry)
        
        # Assert
        assert len(errors) > 0
        assert any("unbalanced" in e.lower() for e in errors)


class TestLedgerEngine:
    """Tests for the LedgerEngine domain service."""
    
    def test_get_balance_calculates_correctly(self, mock_ledger_repo):
        """LedgerEngine should calculate balances correctly."""
        # Arrange
        mock_ledger_repo.get_balance.return_value = Money(Decimal("5000.00"), "USD")
        engine = LedgerEngine(ledger_repo=mock_ledger_repo)
        account = AccountCode("1010")
        as_of = date.today()
        
        # Act
        balance = engine.get_balance(account, as_of)
        
        # Assert
        assert balance.amount == Decimal("5000.00")
        mock_ledger_repo.get_balance.assert_called_once_with(account, as_of)
    
    def test_verify_trial_balance_returns_balanced_flag(self, mock_ledger_repo):
        """verify_trial_balance() should return whether balances match."""
        # Arrange
        mock_ledger_repo.get_trial_balance.return_value = {
            AccountCode("1010"): Money(Decimal("1000"), "USD"),
            AccountCode("2010"): Money(Decimal("-1000"), "USD")
        }
        engine = LedgerEngine(ledger_repo=mock_ledger_repo)
        
        # Act
        is_balanced, difference = engine.verify_trial_balance(date.today())
        
        # Assert
        assert is_balanced is True
        assert difference < 0.01


class TestReversalService:
    """Tests for the ReversalService domain service."""
    
    def test_reverse_service_creates_reversal(
        self, balanced_entry, mock_journal_repo, mock_ledger_repo, mock_period_repo
    ):
        """ReversalService should create reversal entries."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        mock_journal_repo.get_by_id.return_value = balanced_entry
        
        posting_engine = PostingEngine(
            journal_repo=mock_journal_repo,
            ledger_repo=mock_ledger_repo,
            period_repo=mock_period_repo
        )
        reversal_service = ReversalService(
            journal_repo=mock_journal_repo,
            posting_engine=posting_engine
        )
        
        # Act
        reversal = reversal_service.reverse_entry(
            original_entry_id=balanced_entry.id,
            reason="Test reversal",
            posted_by="test_user",
            auto_post=True
        )
        
        # Assert
        assert reversal is not None
        assert reversal.reverses_entry_id == balanced_entry.id
        mock_journal_repo.save.assert_called()
    
    def test_can_reverse_returns_true_for_posted_entry(
        self, balanced_entry, mock_journal_repo
    ):
        """can_reverse() should return True for posted entries without reversals."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        mock_journal_repo.get_by_id.return_value = balanced_entry
        mock_journal_repo.exists_reversal.return_value = False
        
        posting_engine = Mock()
        reversal_service = ReversalService(
            journal_repo=mock_journal_repo,
            posting_engine=posting_engine
        )
        
        # Act
        can_reverse, reason = reversal_service.can_reverse(balanced_entry.id)
        
        # Assert
        assert can_reverse is True
        assert reason is None


class TestDomainEvents:
    """Tests for domain events."""
    
    def test_entry_posted_event_is_raised(self, balanced_entry):
        """EntryPostedEvent should be raised when entry is posted."""
        # Act
        balanced_entry.post(posted_by="test_user")
        events = balanced_entry.pull_events()
        
        # Assert
        assert len(events) == 1
        from core.domain.accounting.events import EntryPostedEvent
        assert isinstance(events[0], EntryPostedEvent)
        assert events[0].entry_id == balanced_entry.id
        assert events[0].posted_by == "test_user"
    
    def test_events_are_cleared_after_pull(self, balanced_entry):
        """Events should be cleared after pull_events() is called."""
        # Arrange
        balanced_entry.post(posted_by="test_user")
        
        # Act
        first_pull = balanced_entry.pull_events()
        second_pull = balanced_entry.pull_events()
        
        # Assert
        assert len(first_pull) == 1
        assert len(second_pull) == 0


class TestEdgeCases:
    """Edge case tests."""
    
    def test_zero_amount_entry(self, sample_account_codes):
        """Entries with zero amount should be rejected."""
        zero = Money(Decimal("0"), "USD")
        
        entry = JournalEntry(
            description="Zero amount transaction",
            lines=[
                JournalLine(
                    account_code=sample_account_codes["cash"],
                    debit=zero,
                    credit=Money(Decimal("0"), "USD")
                ),
                JournalLine(
                    account_code=sample_account_codes["revenue"],
                    debit=Money(Decimal("0"), "USD"),
                    credit=zero
                )
            ]
        )
        
        with pytest.raises(ValueError) as exc_info:
            entry.post(posted_by="test_user")
        
        assert "either debit or credit" in str(exc_info.value).lower()
    
    def test_very_large_amounts(self, sample_account_codes):
        """System should handle very large amounts."""
        large_amount = Decimal("999999999.99")
        money = Money(large_amount, "USD")
        
        entry = JournalEntry(
            description="Large transaction",
            lines=[
                JournalLine(
                    account_code=sample_account_codes["cash"],
                    debit=money,
                    credit=Money(Decimal("0"), "USD")
                ),
                JournalLine(
                    account_code=sample_account_codes["revenue"],
                    debit=Money(Decimal("0"), "USD"),
                    credit=money
                )
            ]
        )
        
        # Should not raise any errors
        entry.post(posted_by="test_user")
        assert entry.is_posted is True
        
        debit, credit = entry._calculate_totals()
        assert debit == large_amount
        assert credit == large_amount
    
    def test_multiple_currencies(self, sample_account_codes):
        """Different currencies should not be mixed without conversion."""
        usd = Money(Decimal("1000"), "USD")
        eur = Money(Decimal("1000"), "EUR")
        
        entry = JournalEntry(
            description="Multi-currency transaction",
            lines=[
                JournalLine(
                    account_code=sample_account_codes["cash"],
                    debit=usd,
                    credit=Money(Decimal("0"), "USD")
                ),
                JournalLine(
                    account_code=sample_account_codes["revenue"],
                    debit=Money(Decimal("0"), "EUR"),
                    credit=eur
                )
            ]
        )
        
        # This should fail because currencies don't match for balancing
        with pytest.raises(ValueError):
            entry.post(posted_by="test_user")
    
    def test_high_precision_decimals(self, sample_account_codes):
        """System should handle high precision decimals correctly."""
        precise_amount = Decimal("1000.12345678")
        money = Money(precise_amount, "USD")
        
        entry = JournalEntry(
            description="Precise transaction",
            lines=[
                JournalLine(
                    account_code=sample_account_codes["cash"],
                    debit=money,
                    credit=Money(Decimal("0"), "USD")
                ),
                JournalLine(
                    account_code=sample_account_codes["revenue"],
                    debit=Money(Decimal("0"), "USD"),
                    credit=money
                )
            ]
        )
        
        # Money rounds to 2 decimal places
        assert money.amount == Decimal("1000.12")
        entry.post(posted_by="test_user")
        assert entry.is_posted is True


# ========== INTEGRATION-STYLE TESTS ==========

class TestIntegrationScenarios:
    """End-to-end scenario tests."""
    
    def test_complete_sales_cycle(self, sample_account_codes):
        """Test a complete sales cycle: sale → reversal → correction."""
        
        # Step 1: Create sales entry
        sale_amount = Money(Decimal("5000.00"), "USD")
        sale_entry = JournalEntry(
            description="Sale to customer",
            lines=[
                JournalLine(
                    account_code=sample_account_codes["cash"],
                    debit=sale_amount,
                    credit=Money(Decimal("0"), "USD")
                ),
                JournalLine(
                    account_code=sample_account_codes["revenue"],
                    debit=Money(Decimal("0"), "USD"),
                    credit=sale_amount
                )
            ]
        )
        
        # Step 2: Post the sale
        sale_entry.post(posted_by="sales_user")
        assert sale_entry.is_posted is True
        
        # Step 3: Discover error (should have been $500, not $5000)
        # Step 4: Reverse the incorrect entry
        reversal = sale_entry.reverse(reason="Wrong amount: should be 500 not 5000")
        assert reversal.is_balanced() is True
        
        # Step 5: Post the reversal
        reversal.post(posted_by="admin_user")
        assert reversal.is_posted is True
        
        # Step 6: Create correct entry
        correct_amount = Money(Decimal("500.00"), "USD")
        correct_entry = JournalEntry(
            description="Correct sale to customer",
            lines=[
                JournalLine(
                    account_code=sample_account_codes["cash"],
                    debit=correct_amount,
                    credit=Money(Decimal("0"), "USD")
                ),
                JournalLine(
                    account_code=sample_account_codes["revenue"],
                    debit=Money(Decimal("0"), "USD"),
                    credit=correct_amount
                )
            ]
        )
        
        correct_entry.post(posted_by="sales_user")
        assert correct_entry.is_posted is True
        
        # Verification: All entries are balanced
        assert sale_entry.is_balanced() is True
        assert reversal.is_balanced() is True
        assert correct_entry.is_balanced() is True
    
    def test_transfer_between_accounts(self, sample_account_codes):
        """Test transferring money between two accounts."""
        transfer_amount = Money(Decimal("10000.00"), "USD")
        
        # Transfer from Cash to Accounts Receivable
        transfer_entry = JournalEntry(
            description="Transfer to AR",
            lines=[
                JournalLine(
                    account_code=sample_account_codes["accounts_receivable"],
                    debit=transfer_amount,
                    credit=Money(Decimal("0"), "USD")
                ),
                JournalLine(
                    account_code=sample_account_codes["cash"],
                    debit=Money(Decimal("0"), "USD"),
                    credit=transfer_amount
                )
            ]
        )
        
        transfer_entry.post(posted_by="accountant")
        
        assert transfer_entry.is_balanced() is True
        assert transfer_entry.get_total_debit() == Decimal("10000.00")
        assert transfer_entry.get_total_credit() == Decimal("10000.00")
    
    def test_multi_line_complex_entry(self, sample_account_codes):
        """Test a complex entry with multiple debits and credits."""
        
        # A complex transaction: Purchase inventory partially with cash, partially on credit
        total_cost = Money(Decimal("15000.00"), "USD")
        cash_paid = Money(Decimal("5000.00"), "USD")
        credit_amount = Money(Decimal("10000.00"), "USD")
        
        entry = JournalEntry(
            description="Purchase inventory - mixed payment",
            lines=[
                # Debit inventory for full amount
                JournalLine(
                    account_code=sample_account_codes["inventory"],
                    debit=total_cost,
                    credit=Money(Decimal("0"), "USD")
                ),
                # Credit cash for amount paid
                JournalLine(
                    account_code=sample_account_codes["cash"],
                    debit=Money(Decimal("0"), "USD"),
                    credit=cash_paid
                ),
                # Credit AP for remainder
                JournalLine(
                    account_code=sample_account_codes["accounts_payable"],
                    debit=Money(Decimal("0"), "USD"),
                    credit=credit_amount
                )
            ]
        )
        
        # Verify balance
        debit, credit = entry._calculate_totals()
        assert debit == total_cost.amount  # 15000
        assert credit == cash_paid.amount + credit_amount.amount  # 5000 + 10000 = 15000
        
        entry.post(posted_by="purchasing")
        assert entry.is_posted is True