# core/infrastructure/db/models/all_models.py
"""
📦 جميع نماذج قاعدة البيانات - المصدر الوحيد للحقيقة
✅ هذا الملف يضمن عدم وجود تعارض بين النماذج
✅ يساعد في تجنب مشاكل DuplicateTable
✅ يشمل جميع النماذج بما في ذلك فروع العملاء والتسوية البنكية
"""

# استيراد Base من account_model
from .account_model import Base

# ✅ استيراد جميع النماذج هنا (مرة واحدة فقط)
from .account_model import (
    AccountModel,
    JournalEntryModel,
    JournalLineModel,
    LedgerEntryModel,
    FiscalYearModel,
    FiscalPeriodModel,
    AuditLogModel,
)

from .customer_model import CustomerModel
from .customer_branch_model import CustomerBranchModel
from .supplier_model import SupplierModel
from .product_model import ProductModel
from .invoice_model import InvoiceModel, InvoiceLineModel
from .purchase_order_model import PurchaseOrderModel, PurchaseOrderLineModel
from .fund_model import FundModel, FundMovementModel, FundTransferModel
from .payment_model import PaymentModel, PaymentLineModel
from .payment_allocation_model import PaymentAllocationModel
from .site_model import SiteModel
from .currency_model import CurrencyModel
from .settings_model import SettingsModel, AccountingSettingsModel

# ✅ استيراد نماذج الإشعارات (بما فيها FundsNotificationModel)
from .notification_model import (
    NotificationModel,
    NotificationPreferenceModel,
    NotificationTemplateModel,
    FundsNotificationModel,  # ✅ إضافة هذا
)

from .center_model import CenterModel, CenterAllocationModel, CenterAllocationRuleModel
from .tax_model import TaxRuleModel, TaxGroupModel, TaxGroupRulesModel, TaxExemptionModel, TaxPeriodModel, TaxCalculationLogModel
from .workflow_model import WorkflowModel, ApprovalRequestModel
from .auth_models import UserModel, RoleModel, PermissionModel
from .financial_statement_model import FinancialStatementModel, FinancialStatementLineModel

# ✅ إضافة النماذج المتقدمة للصناديق
from .fund_advanced_models import (
    ExchangeRateHistoryModel,
    CurrencyGainLossModel,
    ProjectModel,
    FundAdvancedModel,
    ProductPriceMultiCurrencyModel,
    SavedFilterModel,
    RealTimeNotificationModel,
    CacheEntryModel,
    FundAuditLogModel,
)

# ✅ ✅ ✅ إضافة نماذج التسوية البنكية (جديد)
from .reconciliation_model import (
    BankStatementModel,
    ReconciliationModel,
    ReconciliationMatchModel,
)

# ✅ تصدير كل شيء
__all__ = [
    # Base
    "Base",
    
    # Accounting Models
    "AccountModel",
    "JournalEntryModel",
    "JournalLineModel",
    "LedgerEntryModel",
    "FiscalYearModel",
    "FiscalPeriodModel",
    "AuditLogModel",
    
    # Customer & Branch
    "CustomerModel",
    "CustomerBranchModel",
    
    # Supplier
    "SupplierModel",
    
    # Product
    "ProductModel",
    
    # Invoice
    "InvoiceModel",
    "InvoiceLineModel",
    
    # Purchase Order
    "PurchaseOrderModel",
    "PurchaseOrderLineModel",
    
    # Fund
    "FundModel",
    "FundMovementModel",
    "FundTransferModel",
    
    # Payment
    "PaymentModel",
    "PaymentLineModel",
    "PaymentAllocationModel",
    
    # Site
    "SiteModel",
    
    # Currency
    "CurrencyModel",
    
    # Settings
    "SettingsModel",
    "AccountingSettingsModel",
    
    # Notification
    "NotificationModel",
    "NotificationPreferenceModel",
    "NotificationTemplateModel",
    "FundsNotificationModel",  # ✅ إضافة هذا
    
    # Center
    "CenterModel",
    "CenterAllocationModel",
    "CenterAllocationRuleModel",
    
    # Tax
    "TaxRuleModel",
    "TaxGroupModel",
    "TaxGroupRulesModel",
    "TaxExemptionModel",
    "TaxPeriodModel",
    "TaxCalculationLogModel",
    
    # Workflow
    "WorkflowModel",
    "ApprovalRequestModel",
    
    # Auth
    "UserModel",
    "RoleModel",
    "PermissionModel",
    
    # Financial Statement
    "FinancialStatementModel",
    "FinancialStatementLineModel",
    
    # Fund Advanced
    "ExchangeRateHistoryModel",
    "CurrencyGainLossModel",
    "ProjectModel",
    "FundAdvancedModel",
    "ProductPriceMultiCurrencyModel",
    "SavedFilterModel",
    "RealTimeNotificationModel",
    "CacheEntryModel",
    "FundAuditLogModel",
    
    # ✅ ✅ ✅ إضافة نماذج التسوية البنكية (جديد)
    "BankStatementModel",
    "ReconciliationModel",
    "ReconciliationMatchModel",
]