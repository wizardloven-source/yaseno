# C:\Users\MTC\Desktop\core\tests\conftest.py
"""
تهيئة pytest لمشروع YAseen ERP
"""

import sys
import os
from pathlib import Path

# ============================================================================
# ✅ إضافة مسار المشروع إلى sys.path (الحل الأساسي)
# ============================================================================

# إضافة مجلد core إلى sys.path
project_root = Path(__file__).parent.parent  # C:\Users\MTC\Desktop\core
project_root_str = str(project_root)

if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

print(f"✅ Project root added to path: {project_root_str}")
print(f"✅ sys.path: {sys.path[:3]}...")

# ============================================================================
# ✅ التحقق من أن core قابل للاستيراد
# ============================================================================

try:
    import core
    print(f"✅ core imported successfully from: {core.__file__}")
except ImportError as e:
    print(f"❌ Failed to import core: {e}")
    print(f"   Current working directory: {os.getcwd()}")
    print(f"   Project root: {project_root_str}")

# ============================================================================
# ✅ استيراد pytest
# ============================================================================

import pytest

# ============================================================================
# ✅ تعريف BaseDomainEvent إذا لم يكن موجوداً
# ============================================================================

try:
    from core.domain.shared.value_objects import BaseDomainEvent
    print("✅ BaseDomainEvent imported from core")
except ImportError:
    print("⚠️ BaseDomainEvent not found, using fallback")
    
    from datetime import datetime, timezone
    
    class BaseDomainEvent:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
            self._occurred_at = datetime.now(timezone.utc)
        
        @property
        def occurred_at(self):
            return self._occurred_at
        
        def get_event_name(self):
            return self.__class__.__name__
        
        def to_dict(self):
            return {
                "event_type": self.get_event_name(),
                "occurred_at": self.occurred_at.isoformat()
            }

# ============================================================================
# ✅ Fixtures مشتركة
# ============================================================================

@pytest.fixture
def sample_date():
    from datetime import date
    return date(2024, 1, 15)


@pytest.fixture
def sample_datetime():
    from datetime import datetime, timezone
    return datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_account_codes():
    try:
        from core.domain.shared.value_objects import AccountCode
    except ImportError:
        from dataclasses import dataclass
        
        @dataclass(frozen=True)
        class AccountCode:
            code: str
            
            def __str__(self):
                return self.code
    
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
def mock_repositories():
    from unittest.mock import Mock
    
    mock_journal = Mock()
    mock_journal.save = Mock()
    mock_journal.get_by_id = Mock(return_value=None)
    mock_journal.exists_reversal = Mock(return_value=False)
    mock_journal.get_reversal_for = Mock(return_value=None)
    
    mock_ledger = Mock()
    mock_ledger.add_entry = Mock()
    mock_ledger.get_balance = Mock(return_value=None)
    mock_ledger.get_trial_balance = Mock(return_value={})
    
    mock_period = Mock()
    mock_period.is_period_closed = Mock(return_value=False)
    mock_period.get_period_by_date = Mock(return_value=None)
    
    mock_account = Mock()
    mock_account.exists = Mock(return_value=True)
    
    return {
        "journal": mock_journal,
        "ledger": mock_ledger,
        "period": mock_period,
        "account": mock_account
    }


@pytest.fixture
def posting_engine(mock_repositories):
    try:
        from core.domain.accounting.posting_engine import PostingEngine
    except ImportError:
        from core.domain.accounting.services import PostingEngine
    
    return PostingEngine(
        journal_repo=mock_repositories["journal"],
        ledger_repo=mock_repositories["ledger"],
        period_repo=mock_repositories["period"],
        account_repo=mock_repositories["account"]
    )


print("✅ conftest.py loaded successfully!")