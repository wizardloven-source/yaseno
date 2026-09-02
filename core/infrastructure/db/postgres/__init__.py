# C:\Users\MTC\Desktop\erpya\core\infrastructure\db\postgres\__init__.py
"""PostgreSQL Database Implementation"""

from .unit_of_work import PostgresUnitOfWork, SessionFactory

# ========== Accounting Repositories ==========
from .repositories import (
    PostgresJournalEntryRepository,
    PostgresLedgerRepository,
    PostgresAccountRepository,
    PostgresFiscalPeriodRepository,
    PostgresAuditRepository,
)

# ========== Invoice Repository ==========
from .repositories_invoice import PostgresInvoiceRepository

# ========== Product Repository ==========
from .repositories_product import PostgresProductRepository

# ========== Purchase Order Repository ==========
from .repositories_purchase_order import PostgresPurchaseOrderRepository

# ========== Customers Repository ==========
from .customers_repository import PostgresCustomerRepository

# ========== Suppliers Repository ==========
from .supplier_repository import PostgresSupplierRepository

# ========== Settings Repository ==========
from .settings_repository import PostgresSettingsRepository, SettingsRepository

# ========== Currency Repository ==========
from .currency_repository import PostgresCurrencyRepository

# ========== Funds Repositories ==========
from .funds_repository import PostgresFundRepository, PostgresFundMovementRepository
from .customer_branch_repository import PostgresCustomerBranchRepository


__all__ = [
    # Unit of Work
    "PostgresUnitOfWork",
    "SessionFactory",
    
    # Accounting Repositories
    "PostgresJournalEntryRepository",
    "PostgresLedgerRepository",
    "PostgresAccountRepository",
    "PostgresFiscalPeriodRepository",
    "PostgresAuditRepository",
    
    # Invoice Repository
    "PostgresInvoiceRepository",
    
    # Product Repository
    "PostgresProductRepository",
    
    # Purchase Order Repository
    "PostgresPurchaseOrderRepository",
    
    # Customers Repository
    "PostgresCustomerRepository",
    
    # Suppliers Repository
    "PostgresSupplierRepository",
    
    # Settings Repositories
    "PostgresSettingsRepository",
    "SettingsRepository",
    
    # Currency Repository
    "PostgresCurrencyRepository",
    
    # Funds Repositories
    "PostgresFundRepository",
    "PostgresFundMovementRepository",
    "PostgresCustomerBranchRepository",
]