# core/infrastructure/db/models/__init__.py
"""Database Models - جميع نماذج قاعدة البيانات"""

from .account_model import (
    Base,
    AccountModel,
    JournalEntryModel,
    JournalLineModel,
    LedgerEntryModel,
    FiscalPeriodModel,
    AuditLogModel,
)
from .invoice_model import InvoiceModel, InvoiceLineModel
from .product_model import ProductModel
from .customer_model import CustomerModel

# ✅ نموذج الإشعارات
from .notification_model import (
    NotificationModel,
    NotificationPreferenceModel,
    NotificationTemplateModel,
    FundsNotificationModel,  # ✅ إضافة هذا
)

# ✅ نماذج أخرى
from .supplier_model import SupplierModel
from .purchase_order_model import PurchaseOrderModel, PurchaseOrderLineModel
from .fund_model import FundModel, FundMovementModel, FundTransferModel
from .payment_model import PaymentModel, PaymentLineModel
from .payment_allocation_model import PaymentAllocationModel
from .site_model import SiteModel
from .currency_model import CurrencyModel
from .settings_model import SettingsModel, AccountingSettingsModel
from .center_model import CenterModel, CenterAllocationModel, CenterAllocationRuleModel
from .tax_model import TaxRuleModel, TaxGroupModel, TaxExemptionModel, TaxPeriodModel
from .workflow_model import WorkflowModel, ApprovalRequestModel
from .auth_models import UserModel, RoleModel, PermissionModel
from .financial_statement_model import FinancialStatementModel, FinancialStatementLineModel

# ✅ نماذج التسوية البنكية
from .reconciliation_model import (
    BankStatementModel,
    ReconciliationModel,
    ReconciliationMatchModel,
)

# ✅ ✅ ✅ إضافة النماذج المتقدمة للصناديق (مهم جداً)
from .fund_advanced_models import (
    ExchangeRateHistoryModel,
    CurrencyGainLossModel,
    ProjectModel,
    FundAdvancedModel,
    ProductPriceMultiCurrencyModel,
    SavedFilterModel,
    RealTimeNotificationModel,  # ✅ هذا النموذج مهم لجدول funds_notifications
    CacheEntryModel,
    FundAuditLogModel,
)

# ✅ نموذج فروع العملاء
from .customer_branch_model import CustomerBranchModel

# ✅ نموذج السنة المالية (إذا لم يكن موجوداً)
try:
    from .fiscal_year_model import FiscalYearModel
except ImportError:
    FiscalYearModel = None

# ✅ نموذج حركات المخزون (إذا لم يكن موجوداً)
try:
    from .stock_movement_model import StockMovementModel, StockBatchModel, StockTransferModel
except ImportError:
    StockMovementModel = None
    StockBatchModel = None
    StockTransferModel = None


__all__ = [
    # Base
    "Base",
    
    # Accounting
    "AccountModel",
    "JournalEntryModel",
    "JournalLineModel",
    "LedgerEntryModel",
    "FiscalPeriodModel",
    "AuditLogModel",
    
    # Invoicing
    "InvoiceModel",
    "InvoiceLineModel",
    
    # Products
    "ProductModel",
    
    # Customers & Suppliers
    "CustomerModel",
    "CustomerBranchModel",
    "SupplierModel",
    
    # Purchasing
    "PurchaseOrderModel",
    "PurchaseOrderLineModel",
    
    # Funds
    "FundModel",
    "FundMovementModel",
    "FundTransferModel",
    
    # Payments
    "PaymentModel",
    "PaymentLineModel",
    "PaymentAllocationModel",
    
    # Sites
    "SiteModel",
    
    # Currency
    "CurrencyModel",
    
    # Settings
    "SettingsModel",
    "AccountingSettingsModel",
    
    # Notifications
    "NotificationModel",
    "NotificationPreferenceModel",
    "NotificationTemplateModel",
    "FundsNotificationModel",  # ✅ إضافة هذا
    
    # Centers
    "CenterModel",
    "CenterAllocationModel",
    "CenterAllocationRuleModel",
    
    # Tax
    "TaxRuleModel",
    "TaxGroupModel",
    "TaxExemptionModel",
    "TaxPeriodModel",
    
    # Workflow
    "WorkflowModel",
    "ApprovalRequestModel",
    
    # Auth
    "UserModel",
    "RoleModel",
    "PermissionModel",
    
    # Financial Statements
    "FinancialStatementModel",
    "FinancialStatementLineModel",
    
    # Reconciliation
    "BankStatementModel",
    "ReconciliationModel",
    "ReconciliationMatchModel",
    
    # ✅ Fund Advanced Models (مهم)
    "ExchangeRateHistoryModel",
    "CurrencyGainLossModel",
    "ProjectModel",
    "FundAdvancedModel",
    "ProductPriceMultiCurrencyModel",
    "SavedFilterModel",
    "RealTimeNotificationModel",  # ✅ هذا النموذج
    "CacheEntryModel",
    "FundAuditLogModel",
    
    # Fiscal Year
    "FiscalYearModel",
    
    # Stock Movement
    "StockMovementModel",
    "StockBatchModel",
    "StockTransferModel",
]