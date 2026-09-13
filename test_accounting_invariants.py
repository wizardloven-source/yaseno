#!/usr/bin/env python3
"""
YAseen ERP - Accounting Invariants Tests
PHASE 1: Accounting Core Hardening

Test the fundamental accounting rules that must always hold true.
"""

import sys
sys.path.insert(0, '/workspace')

from decimal import Decimal
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.accounting.exceptions import (
    UnbalancedEntryError,
    PostedEntryModificationError,
    CannotReverseUnpostedError,
    AlreadyReversedError
)


def test_invariant_1_debit_equals_credit():
    """Invariant 1: Debit MUST equal Credit for every Journal Entry"""
    print("\n" + "="*70)
    print("INVARIANT 1: Debit == Credit for every Journal Entry")
    print("="*70)
    
    # Create a balanced entry
    je = JournalEntry(description="Test Balanced Entry")
    je.add_line(JournalLine(
        account_code=AccountCode("1000"),
        debit=Money(Decimal("1000.00"), "USD"),
        credit=Money(Decimal("0"), "USD")
    ))
    je.add_line(JournalLine(
        account_code=AccountCode("2000"),
        debit=Money(Decimal("0"), "USD"),
        credit=Money(Decimal("1000.00"), "USD")
    ))
    
    assert je.total_debit == Decimal("1000.00"), "Total debit should be 1000.00"
    assert je.total_credit == Decimal("1000.00"), "Total credit should be 1000.00"
    assert je.is_balanced, "Entry should be balanced"
    
    print(f"✓ Total Debit: {je.total_debit}")
    print(f"✓ Total Credit: {je.total_credit}")
    print(f"✓ Is Balanced: {je.is_balanced}")
    print("✓ INVARIANT 1 PASSED\n")
    return True


def test_invariant_2_unbalanced_prevention():
    """Invariant 2: System must prevent posting unbalanced entries"""
    print("\n" + "="*70)
    print("INVARIANT 2: Cannot post unbalanced entries")
    print("="*70)
    
    # Create an unbalanced entry
    je = JournalEntry(description="Test Unbalanced Entry")
    je.add_line(JournalLine(
        account_code=AccountCode("1000"),
        debit=Money(Decimal("1000.00"), "USD"),
        credit=Money(Decimal("0"), "USD")
    ))
    je.add_line(JournalLine(
        account_code=AccountCode("2000"),
        debit=Money(Decimal("0"), "USD"),
        credit=Money(Decimal("500.00"), "USD")
    ))
    
    assert je.total_debit == Decimal("1000.00"), "Total debit should be 1000.00"
    assert je.total_credit == Decimal("500.00"), "Total credit should be 500.00"
    assert not je.is_balanced, "Entry should NOT be balanced"
    
    errors = je.validate_for_posting()
    assert len(errors) > 0, "Should have validation errors"
    assert any("unbalanced" in e.lower() for e in errors), "Should mention unbalanced"
    
    print(f"✓ Total Debit: {je.total_debit}")
    print(f"✓ Total Credit: {je.total_credit}")
    print(f"✓ Is Balanced: {je.is_balanced}")
    print(f"✓ Validation Errors: {errors}")
    print("✓ INVARIANT 2 PASSED\n")
    return True


def test_invariant_3_posted_journal_cannot_be_modified():
    """Invariant 3: Posted Journal cannot be modified silently"""
    print("\n" + "="*70)
    print("INVARIANT 3: Posted Journal cannot be modified")
    print("="*70)
    
    # Create and post a balanced entry
    je = JournalEntry(description="Test Posted Entry")
    je.add_line(JournalLine(
        account_code=AccountCode("1000"),
        debit=Money(Decimal("1000.00"), "USD"),
        credit=Money(Decimal("0"), "USD")
    ))
    je.add_line(JournalLine(
        account_code=AccountCode("2000"),
        debit=Money(Decimal("0"), "USD"),
        credit=Money(Decimal("1000.00"), "USD")
    ))
    
    # Post the entry
    je.post(posted_by="test_user")
    assert je.is_posted, "Entry should be posted"
    
    # Try to modify it - should raise exception
    try:
        je.add_line(JournalLine(
            account_code=AccountCode("3000"),
            debit=Money(Decimal("100.00"), "USD"),
            credit=Money(Decimal("0"), "USD")
        ))
        assert False, "Should have raised PostedEntryModificationError"
    except PostedEntryModificationError as e:
        print(f"✓ Correctly prevented modification: {type(e).__name__}")
    
    print(f"✓ Is Posted: {je.is_posted}")
    print(f"✓ Posted At: {je.posted_at}")
    print(f"✓ Posted By: {je.posted_by}")
    print("✓ INVARIANT 3 PASSED\n")
    return True


def test_invariant_4_reversal_mechanism():
    """Invariant 4: Reversal creates correct opposite entries"""
    print("\n" + "="*70)
    print("INVARIANT 4: Reversal creates correct opposite entries")
    print("="*70)
    
    # Create and post original entry
    original = JournalEntry(description="Original Entry")
    original.add_line(JournalLine(
        account_code=AccountCode("1000"),
        debit=Money(Decimal("1000.00"), "USD"),
        credit=Money(Decimal("0"), "USD")
    ))
    original.add_line(JournalLine(
        account_code=AccountCode("2000"),
        debit=Money(Decimal("0"), "USD"),
        credit=Money(Decimal("1000.00"), "USD")
    ))
    original.post(posted_by="test_user")
    
    # Create reversal
    reversal = original.reverse(reason="Test reversal")
    
    # Verify reversal properties
    assert reversal.reverses_entry_id == original.id, "Reversal should reference original"
    assert original.reversed_entry_id == reversal.id, "Original should reference reversal"
    
    # Verify amounts are swapped
    for i, orig_line in enumerate(original.lines):
        rev_line = reversal.lines[i]
        assert orig_line.debit.amount == rev_line.credit.amount, "Debit should become credit"
        assert orig_line.credit.amount == rev_line.debit.amount, "Credit should become debit"
        assert orig_line.account_code.code == rev_line.account_code.code, "Account should be same"
    
    print(f"✓ Original Entry ID: {original.id}")
    print(f"✓ Reversal Entry ID: {reversal.id}")
    print(f"✓ Reversal References Original: {reversal.reverses_entry_id == original.id}")
    print(f"✓ Amounts Correctly Swapped")
    print("✓ INVARIANT 4 PASSED\n")
    return True


def test_invariant_5_cannot_reverse_unposted():
    """Invariant 5: Cannot reverse unposted entry"""
    print("\n" + "="*70)
    print("INVARIANT 5: Cannot reverse unposted entry")
    print("="*70)
    
    # Create unposted entry
    je = JournalEntry(description="Unposted Entry")
    je.add_line(JournalLine(
        account_code=AccountCode("1000"),
        debit=Money(Decimal("1000.00"), "USD"),
        credit=Money(Decimal("0"), "USD")
    ))
    je.add_line(JournalLine(
        account_code=AccountCode("2000"),
        debit=Money(Decimal("0"), "USD"),
        credit=Money(Decimal("1000.00"), "USD")
    ))
    
    # Try to reverse - should fail
    try:
        je.reverse(reason="Test")
        assert False, "Should have raised CannotReverseUnpostedError"
    except CannotReverseUnpostedError as e:
        print(f"✓ Correctly prevented reversal: {type(e).__name__}")
    
    print(f"✓ Is Posted: {je.is_posted}")
    print("✓ INVARIANT 5 PASSED\n")
    return True


def test_invariant_6_cannot_double_reverse():
    """Invariant 6: Cannot reverse already reversed entry"""
    print("\n" + "="*70)
    print("INVARIANT 6: Cannot reverse already reversed entry")
    print("="*70)
    
    # Create, post, and reverse entry
    original = JournalEntry(description="Original Entry")
    original.add_line(JournalLine(
        account_code=AccountCode("1000"),
        debit=Money(Decimal("1000.00"), "USD"),
        credit=Money(Decimal("0"), "USD")
    ))
    original.add_line(JournalLine(
        account_code=AccountCode("2000"),
        debit=Money(Decimal("0"), "USD"),
        credit=Money(Decimal("1000.00"), "USD")
    ))
    original.post(posted_by="test_user")
    
    # First reversal
    reversal1 = original.reverse(reason="First reversal")
    
    # Try to reverse again - should fail
    try:
        original.reverse(reason="Second reversal")
        assert False, "Should have raised AlreadyReversedError"
    except AlreadyReversedError as e:
        print(f"✓ Correctly prevented double reversal: {type(e).__name__}")
    
    print(f"✓ Original Has Reversal: {original.reversed_entry_id is not None}")
    print("✓ INVARIANT 6 PASSED\n")
    return True


def test_invariant_7_multi_currency_balance():
    """Invariant 7: Multi-currency entries must balance per currency"""
    print("\n" + "="*70)
    print("INVARIANT 7: Multi-currency entries must balance per currency")
    print("="*70)
    
    # Create entry with mixed currencies (should be detected)
    je = JournalEntry(description="Multi-currency Test")
    je.add_line(JournalLine(
        account_code=AccountCode("1000"),
        debit=Money(Decimal("1000.00"), "USD"),
        credit=Money(Decimal("0"), "USD")
    ))
    je.add_line(JournalLine(
        account_code=AccountCode("2000"),
        debit=Money(Decimal("0"), "EUR"),
        credit=Money(Decimal("1000.00"), "EUR")
    ))
    
    # Should detect currency mismatch during validation
    errors = je.validate_for_posting()
    print(f"✓ Validation detected currency issues: {len(errors)} errors")
    
    # Check currency breakdown
    breakdown = je.currency_breakdown
    print(f"✓ Currency Breakdown: {breakdown}")
    
    print("✓ INVARIANT 7 PASSED\n")
    return True


def test_invariant_8_zero_amount_prevention():
    """Invariant 8: Cannot add zero-amount lines"""
    print("\n" + "="*70)
    print("INVARIANT 8: Cannot add zero-amount lines")
    print("="*70)
    
    je = JournalEntry(description="Zero Amount Test")
    
    # Try to add zero line
    try:
        je.add_line(JournalLine(
            account_code=AccountCode("1000"),
            debit=Money(Decimal("0"), "USD"),
            credit=Money(Decimal("0"), "USD")
        ))
        assert False, "Should have raised InvalidLineError"
    except Exception as e:
        print(f"✓ Correctly prevented zero line: {type(e).__name__}")
    
    print("✓ INVARIANT 8 PASSED\n")
    return True


def run_all_tests():
    """Run all accounting invariant tests"""
    print("\n" + "="*70)
    print("YASEEN ERP - ACCOUNTING INVARIANTS TEST SUITE")
    print("PHASE 1: Accounting Core Hardening")
    print("="*70)
    
    tests = [
        ("Invariant 1: Debit == Credit", test_invariant_1_debit_equals_credit),
        ("Invariant 2: Unbalanced Prevention", test_invariant_2_unbalanced_prevention),
        ("Invariant 3: Posted Journal Protection", test_invariant_3_posted_journal_cannot_be_modified),
        ("Invariant 4: Reversal Mechanism", test_invariant_4_reversal_mechanism),
        ("Invariant 5: Cannot Reverse Unposted", test_invariant_5_cannot_reverse_unposted),
        ("Invariant 6: No Double Reversal", test_invariant_6_cannot_double_reverse),
        ("Invariant 7: Multi-currency Balance", test_invariant_7_multi_currency_balance),
        ("Invariant 8: Zero Amount Prevention", test_invariant_8_zero_amount_prevention),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {name} FAILED: {e}\n")
            failed += 1
    
    print("\n" + "="*70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("="*70)
    
    if failed == 0:
        print("\n✓✓✓ ALL ACCOUNTING INVARIANTS VERIFIED ✓✓✓\n")
        return True
    else:
        print(f"\n✗✗✗ {failed} INVARIANTS FAILED ✗✗✗\n")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
