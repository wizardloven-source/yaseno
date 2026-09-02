# tests/__init__.py (جديد - هيكل الاختبارات الموحد)

"""
YAseen ERP Test Suite

Directory structure:
    tests/
    ├── unit/
    │   ├── domain/
    │   │   ├── test_accounting_entities.py
    │   │   ├── test_accounting_services.py
    │   │   ├── test_invoicing_entities.py
    │   │   └── test_products_entities.py
    │   └── application/
    │       ├── test_invoicing_handlers.py
    │       ├── test_accounting_handlers.py
    │       └── test_products_handlers.py
    ├── integration/
    │   ├── test_repositories.py
    │   ├── test_unit_of_work.py
    │   └── test_event_bus.py
    ├── accounting/
    │   ├── test_double_entry.py
    │   ├── test_posting_engine.py
    │   ├── test_closing_service.py
    │   └── test_trial_balance.py
    └── api/
        ├── test_invoices_api.py
        └── test_accounting_api.py
"""

import pytest

# Configure pytest
# NOTE: The legacy plugin path references a top-level `tests` package that is
# not present in this workspace. Collection already works through
# `core/tests/conftest.py`, so keep plugin registration empty to avoid
# importing non-existent fixtures modules.
pytest_plugins = []

# Test configuration
def pytest_configure(config):
    """Configure pytest for YAseen ERP"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires database)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "accounting: mark test as accounting critical test"
    )