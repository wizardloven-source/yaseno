# core/application/handlers/__init__.py

"""
Application Handlers - Organized by bounded context
"""

from .base_handler import BaseHandler, BaseQueryHandler

# Invoicing Handlers
from .invoicing import (
    CreateInvoiceHandler,
    AddInvoiceLineHandler,
    UpdateInvoiceLineHandler,
    RemoveInvoiceLineHandler,
    ClearInvoiceLinesHandler,
    PostInvoiceHandler,
    DeleteDraftInvoiceHandler,
    GetInvoiceQueryHandler,
    ListInvoicesQueryHandler,
)

# Products Handlers
from .products import (
    CreateProductHandler,
    UpdateProductHandler,
    DeleteProductHandler,
    UpdateStockHandler,
    GetProductQueryHandler,
    GetProductByCodeQueryHandler,
    ListProductsQueryHandler,
    SearchProductsQueryHandler,
    GetLowStockProductsQueryHandler,
)

# ✅ Accounting Handlers - استيراد كسول (Lazy) لتجنب الاستيراد الدائري
# (handlers/__init__ -> accounting.handlers -> handlers.base_handler -> handlers/__init__)
_ACCOUNTING_HANDLER_NAMES = {
    "CreateJournalEntryHandler",
    "PostJournalEntryHandler",
    "ReverseJournalEntryHandler",
    "ClosePeriodHandler",
    "GetJournalEntryQueryHandler",
    "GetTrialBalanceQueryHandler",
    "GetAccountBalanceQueryHandler",
    "ListJournalEntriesQueryHandler",
    "GetPeriodStatusQueryHandler",
}

# ✅ Customers Handlers - استيراد مباشر من الملفات لتجنب الاستيراد الدائري
from .customers.create_customer_handler import CreateCustomerHandler
from .customers.update_customer_handler import UpdateCustomerHandler
from .customers.change_customer_status_handler import ChangeCustomerStatusHandler
from .customers.delete_customer_handler import DeleteCustomerHandler
from .customers.get_customer_query_handler import GetCustomerQueryHandler
from .customers.list_customers_query_handler import ListCustomersQueryHandler
from .customers.search_customers_query_handler import SearchCustomersQueryHandler
from .customers.get_customer_statement_query_handler import GetCustomerStatementQueryHandler

# ✅ Suppliers Handlers - استيراد مباشر من الملفات
from .suppliers.create_supplier_handler import CreateSupplierHandler
from .suppliers.update_supplier_handler import UpdateSupplierHandler
from .suppliers.change_supplier_status_handler import ChangeSupplierStatusHandler
from .suppliers.delete_supplier_handler import DeleteSupplierHandler
from .suppliers.get_supplier_query_handler import GetSupplierQueryHandler
from .suppliers.list_suppliers_query_handler import ListSuppliersQueryHandler
from .suppliers.search_suppliers_query_handler import SearchSuppliersQueryHandler
from .suppliers.get_supplier_statement_query_handler import GetSupplierStatementQueryHandler

# ✅ Purchasing Handlers
from .purchasing import (
    CreatePurchaseOrderHandler,
    AddPurchaseLineHandler,
    UpdatePurchaseLineHandler,
    RemovePurchaseLineHandler,
    ClearPurchaseLinesHandler,
    PostPurchaseOrderHandler,
    DeleteDraftPurchaseOrderHandler,
    ReceivePurchaseLineHandler,
    GetPurchaseOrderQueryHandler,
    ListPurchaseOrdersQueryHandler,
)

# ✅ Settings Handlers
from .settings import (
    GetSettingsHandler,
    GetUiSettingsHandler,
    UpdateUiSettingsHandler,
)

# ✅ Currency Handlers
from .currency import (
    CreateCurrencyHandler,
    UpdateCurrencyHandler,
    DeleteCurrencyHandler,
    SetExchangeRateHandler,
    GetCurrencyQueryHandler,
    GetCurrencyByCodeQueryHandler,
    ListCurrenciesQueryHandler,
    GetBaseCurrencyQueryHandler,
)

# ✅ Users Handlers - استيراد مباشر من الملفات
from .users.create_user_handler import CreateUserHandler
from .users.update_user_handler import UpdateUserHandler
from .users.delete_user_handler import DeleteUserHandler
from .users.change_password_handler import ChangePasswordHandler
from .users.reset_password_handler import ResetPasswordHandler
from .users.get_user_query_handler import GetUserQueryHandler
from .users.list_users_query_handler import ListUsersQueryHandler
from .users.get_user_permissions_query_handler import GetUserPermissionsQueryHandler

__all__ = [
    "BaseHandler",
    "BaseQueryHandler",
    # Invoicing
    "CreateInvoiceHandler",
    "AddInvoiceLineHandler",
    "UpdateInvoiceLineHandler",
    "RemoveInvoiceLineHandler",
    "ClearInvoiceLinesHandler",
    "PostInvoiceHandler",
    "DeleteDraftInvoiceHandler",
    "GetInvoiceQueryHandler",
    "ListInvoicesQueryHandler",
    # Products
    "CreateProductHandler",
    "UpdateProductHandler",
    "DeleteProductHandler",
    "UpdateStockHandler",
    "GetProductQueryHandler",
    "GetProductByCodeQueryHandler",
    "ListProductsQueryHandler",
    "SearchProductsQueryHandler",
    "GetLowStockProductsQueryHandler",
    # Accounting
    "CreateJournalEntryHandler",
    "PostJournalEntryHandler",
    "ReverseJournalEntryHandler",
    "ClosePeriodHandler",
    "GetJournalEntryQueryHandler",
    "GetTrialBalanceQueryHandler",
    "GetAccountBalanceQueryHandler",
    "ListJournalEntriesQueryHandler",
    "GetPeriodStatusQueryHandler",
    # Customers
    "CreateCustomerHandler",
    "UpdateCustomerHandler",
    "ChangeCustomerStatusHandler",
    "DeleteCustomerHandler",
    "GetCustomerQueryHandler",
    "ListCustomersQueryHandler",
    "SearchCustomersQueryHandler",
    "GetCustomerStatementQueryHandler",
    # Suppliers
    "CreateSupplierHandler",
    "UpdateSupplierHandler",
    "ChangeSupplierStatusHandler",
    "DeleteSupplierHandler",
    "GetSupplierQueryHandler",
    "ListSuppliersQueryHandler",
    "SearchSuppliersQueryHandler",
    "GetSupplierStatementQueryHandler",
    # Purchasing
    "CreatePurchaseOrderHandler",
    "AddPurchaseLineHandler",
    "UpdatePurchaseLineHandler",
    "RemovePurchaseLineHandler",
    "ClearPurchaseLinesHandler",
    "PostPurchaseOrderHandler",
    "DeleteDraftPurchaseOrderHandler",
    "ReceivePurchaseLineHandler",
    "GetPurchaseOrderQueryHandler",
    "ListPurchaseOrdersQueryHandler",
    # Settings
    "GetSettingsHandler",
    "GetUiSettingsHandler",
    "UpdateUiSettingsHandler",
    # Currency
    "CreateCurrencyHandler",
    "UpdateCurrencyHandler",
    "DeleteCurrencyHandler",
    "SetExchangeRateHandler",
    "GetCurrencyQueryHandler",
    "GetCurrencyByCodeQueryHandler",
    "ListCurrenciesQueryHandler",
    "GetBaseCurrencyQueryHandler",
    # Users
    "CreateUserHandler",
    "UpdateUserHandler",
    "DeleteUserHandler",
    "ChangePasswordHandler",
    "ResetPasswordHandler",
    "GetUserQueryHandler",
    "ListUsersQueryHandler",
    "GetUserPermissionsQueryHandler",
]


def __getattr__(name):
    """استيراد كسول لمعالجات المحاسبة عبر الحزمة (لتجنب الدورة)."""
    if name in _ACCOUNTING_HANDLER_NAMES:
        from core.application.accounting import handlers
        return getattr(handlers, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")