# core/infrastructure/__init__.py
"""
Infrastructure Layer - Databases, Message Buses, External Services
✅ محدث: إضافة دعم الإعدادات والموردين وأوامر الشراء
✅ محدث: إضافة NotificationModel
✅ محدث: إضافة PaymentModel
✅ محدث: إضافة FundModel
✅ محدث: إضافة SiteModel
✅ محدث: إضافة CurrencyModel
✅ محدث: إضافة جميع النماذج الحديثة
"""

from .bus.in_memory_event_bus import InMemoryEventBus
from .db.postgres.unit_of_work import PostgresUnitOfWork, SessionFactory

# ========== Accounting Repositories ==========
from .db.postgres.repositories import (
    PostgresJournalEntryRepository,
    PostgresLedgerRepository,
    PostgresAccountRepository,
    PostgresFiscalPeriodRepository as PostgresAccountingPeriodRepo,
    PostgresAuditRepository,
)

# ========== Invoice Repository ==========
from .db.postgres.repositories_invoice import PostgresInvoiceRepository

# ========== Product Repository ==========
from .db.postgres.repositories_product import PostgresProductRepository

# ========== Purchase Order Repository ==========
from .db.postgres.repositories_purchase_order import PostgresPurchaseOrderRepository

# ========== Customers Repository ==========
from .db.postgres.customers_repository import PostgresCustomerRepository

# ========== Suppliers Repository ==========
from .db.postgres.supplier_repository import PostgresSupplierRepository

# ========== Settings Repositories ==========
from .db.postgres.settings_repository import PostgresSettingsRepository, SettingsRepository, get_settings_repo

# ========== Currency Repository ==========
from .db.postgres.currency_repository import PostgresCurrencyRepository

# ========== Funds Repositories ==========
from .db.postgres.funds_repository import PostgresFundRepository, PostgresFundMovementRepository

# ========== Site Repository ==========
from .db.postgres.site_repository import PostgresSiteRepository

# ========== Payment Repository ==========
from .db.postgres.repositories_payment import PostgresPaymentRepository

# ========== Inventory Repositories ==========
from .db.postgres.repositories_inventory import (
    PostgresStockMovementRepository,
    PostgresStockBatchRepository,
    PostgresStockTransferRepository
)

# ========== Workflow Repositories ==========
from .db.postgres.workflow_repository import (
    PostgresWorkflowRepository,
    PostgresApprovalRequestRepository
)

# ========== Auth Repositories ==========
from .db.postgres.auth_repository import (
    PostgresUserRepository,
    PostgresRoleRepository,
    PostgresPermissionRepository
)

# ========== Fiscal Repositories ==========
from .db.postgres.fiscal_repository import (
    PostgresFiscalYearRepository,
    PostgresFiscalPeriodRepository
)

# ========== Tax Repositories ==========
from .db.postgres.tax_repository import (
    PostgresTaxRepository,
    PostgresTaxGroupRepository,
    PostgresTaxExemptionRepository,
    PostgresTaxPeriodRepository
)

# ========== Center Repositories ==========
from .db.postgres.center_repository import (
    PostgresCenterRepository,
    PostgresAllocationRepository,
    PostgresAllocationRuleRepository
)

# ========== Models - Accounting ==========
from .db.models.account_model import (
    Base,
    AccountModel,
    JournalEntryModel,
    JournalLineModel,
    LedgerEntryModel,
    FiscalYearModel,
    FiscalPeriodModel,
    AuditLogModel,
)

# ========== Models - Invoice ==========
from .db.models.invoice_model import (
    InvoiceModel,
    InvoiceLineModel,
)

# ========== Models - Product ==========
from .db.models.product_model import ProductModel

# ========== Models - Customer ==========
from .db.models.customer_model import CustomerModel

# ========== Models - Supplier ==========
from .db.models.supplier_model import SupplierModel

# ========== Models - Purchase Order ==========
from .db.models.purchase_order_model import PurchaseOrderModel, PurchaseOrderLineModel

# ========== Models - Settings ==========
from .db.models.settings_model import SettingsModel, AccountingSettingsModel

# ========== Models - Currency ==========
from .db.models.currency_model import CurrencyModel, ExchangeRateModel

# ========== Models - Fund ==========
from .db.models.fund_model import FundModel, FundMovementModel, FundTransferModel
from .db.models.fund_advanced_models import (
    FundAdvancedModel,
    ProjectModel,
    ExchangeRateHistoryModel,
    CurrencyGainLossModel,
    ProductPriceMultiCurrencyModel,
    SavedFilterModel,
    # RealTimeNotificationModel,  # ✅ تم نقله إلى notification_model.py
    CacheEntryModel,
    FundAuditLogModel,
)

# ========== Models - Site ==========
from .db.models.site_model import SiteModel

# ========== Models - Payment ==========
from .db.models.payment_model import PaymentModel, PaymentLineModel
from .db.models.payment_allocation_model import PaymentAllocationModel

# ========== Models - Notification ==========
from .db.models.notification_model import (
    NotificationModel,
    NotificationPreferenceModel,
    NotificationTemplateModel,
    FundsNotificationModel,  # ✅ إضافة هذا
)

# ========== Models - Center ==========
from .db.models.center_model import (
    CenterModel,
    CenterAllocationModel,
    CenterAllocationRuleModel,
)

# ========== Models - Tax ==========
from .db.models.tax_model import (
    TaxRuleModel,
    TaxGroupModel,
    TaxGroupRulesModel,
    TaxExemptionModel,
    TaxPeriodModel,
    TaxCalculationLogModel,
)

# ========== Models - Workflow ==========
from .db.models.workflow_model import WorkflowModel, ApprovalRequestModel

# ========== Models - Auth ==========
from .db.models.auth_models import UserModel, RoleModel, PermissionModel

# ========== Models - Rules ==========
from .db.models.rule_model import PostingRuleModel, RuleGroupModel, RuleExecutionLogModel

# ========== Models - Financial Statements ==========
from .db.models.financial_statement_model import FinancialStatementModel, FinancialStatementLineModel


__all__ = [
    # ===== Event Bus =====
    "InMemoryEventBus",
    
    # ===== Unit of Work =====
    "PostgresUnitOfWork",
    "SessionFactory",
    
    # ===== Accounting Repositories =====
    "PostgresJournalEntryRepository",
    "PostgresLedgerRepository",
    "PostgresAccountRepository",
    "PostgresFiscalPeriodRepository",
    "PostgresAuditRepository",
    
    # ===== Invoice Repository =====
    "PostgresInvoiceRepository",
    
    # ===== Product Repository =====
    "PostgresProductRepository",
    
    # ===== Purchase Order Repository =====
    "PostgresPurchaseOrderRepository",
    
    # ===== Customers Repository =====
    "PostgresCustomerRepository",
    
    # ===== Suppliers Repository =====
    "PostgresSupplierRepository",
    
    # ===== Settings Repositories =====
    "PostgresSettingsRepository",
    "SettingsRepository",
    "get_settings_repo",
    
    # ===== Currency Repository =====
    "PostgresCurrencyRepository",
    
    # ===== Funds Repositories =====
    "PostgresFundRepository",
    "PostgresFundMovementRepository",
    
    # ===== Site Repository =====
    "PostgresSiteRepository",
    
    # ===== Payment Repository =====
    "PostgresPaymentRepository",
    
    # ===== Inventory Repositories =====
    "PostgresStockMovementRepository",
    "PostgresStockBatchRepository",
    "PostgresStockTransferRepository",
    
    # ===== Workflow Repositories =====
    "PostgresWorkflowRepository",
    "PostgresApprovalRequestRepository",
    
    # ===== Auth Repositories =====
    "PostgresUserRepository",
    "PostgresRoleRepository",
    "PostgresPermissionRepository",
    
    # ===== Fiscal Repositories =====
    "PostgresFiscalYearRepository",
    "PostgresFiscalPeriodRepository",
    
    # ===== Tax Repositories =====
    "PostgresTaxRepository",
    "PostgresTaxGroupRepository",
    "PostgresTaxExemptionRepository",
    "PostgresTaxPeriodRepository",
    
    # ===== Center Repositories =====
    "PostgresCenterRepository",
    "PostgresAllocationRepository",
    "PostgresAllocationRuleRepository",
    
    # ===== Base Model =====
    "Base",
    
    # ===== Accounting Models =====
    "AccountModel",
    "JournalEntryModel",
    "JournalLineModel",
    "LedgerEntryModel",
    "FiscalYearModel",
    "FiscalPeriodModel",
    "AuditLogModel",
    
    # ===== Invoice Models =====
    "InvoiceModel",
    "InvoiceLineModel",
    
    # ===== Product Model =====
    "ProductModel",
    
    # ===== Customer Model =====
    "CustomerModel",
    
    # ===== Supplier Model =====
    "SupplierModel",
    
    # ===== Purchase Order Models =====
    "PurchaseOrderModel",
    "PurchaseOrderLineModel",
    
    # ===== Settings Models =====
    "SettingsModel",
    "AccountingSettingsModel",
    
    # ===== Currency Models =====
    "CurrencyModel",
    "ExchangeRateModel",
    
    # ===== Fund Models =====
    "FundModel",
    "FundMovementModel",
    "FundTransferModel",
    "FundAdvancedModel",
    "ProjectModel",
    "ExchangeRateHistoryModel",
    "CurrencyGainLossModel",
    "ProductPriceMultiCurrencyModel",
    "SavedFilterModel",
    # "RealTimeNotificationModel",  # ✅ تم نقله إلى notification_model.py
    "CacheEntryModel",
    "FundAuditLogModel",
    
    # ===== Site Model =====
    "SiteModel",
    
    # ===== Payment Models =====
    "PaymentModel",
    "PaymentLineModel",
    "PaymentAllocationModel",
    
    # ===== Notification Models =====
    "NotificationModel",
    "NotificationPreferenceModel",
    "NotificationTemplateModel",
    "FundsNotificationModel",  # ✅ إضافة هذا
    
    # ===== Center Models =====
    "CenterModel",
    "CenterAllocationModel",
    "CenterAllocationRuleModel",
    
    # ===== Tax Models =====
    "TaxRuleModel",
    "TaxGroupModel",
    "TaxGroupRulesModel",
    "TaxExemptionModel",
    "TaxPeriodModel",
    "TaxCalculationLogModel",
    
    # ===== Workflow Models =====
    "WorkflowModel",
    "ApprovalRequestModel",
    
    # ===== Auth Models =====
    "UserModel",
    "RoleModel",
    "PermissionModel",
    
    # ===== Rules Models =====
    "PostingRuleModel",
    "RuleGroupModel",
    "RuleExecutionLogModel",
    
    # ===== Financial Statement Models =====
    "FinancialStatementModel",
    "FinancialStatementLineModel",
]