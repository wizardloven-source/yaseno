# core/bootstrap/modules/__init__.py

from typing import List, Dict, Any, TYPE_CHECKING

from .base import Module
from .database import DatabaseModule
from .accounting import AccountingModule
from .invoicing import InvoicingModule
from .purchasing import PurchasingModule
from .inventory import InventoryModule  # ✅ مفعل
from .products import ProductsModule
from .customers import CustomersModule
from .suppliers import SuppliersModule
from .funds import FundsModule  # ✅ مفعل
from .payments import PaymentsModule
from .sites import SitesModule
from .currency import CurrencyModule
from .tax import TaxModule
from .financial_statements import FinancialStatementsModule
from .fiscal import FiscalModule
from .settings import SettingsModule
from .security import SecurityModule
from .workflow import WorkflowModule
from .centers import CentersModule
from .reports import ReportsModule
from .notifications import NotificationsModule
from .fixed_assets import FixedAssetsModule

if TYPE_CHECKING:
    from ..container import DependencyContainer


def get_all_modules() -> List[Module]:
    """الحصول على قائمة بجميع الوحدات"""
    return [
        DatabaseModule(),
        SecurityModule(),
        FiscalModule(),
        AccountingModule(),
        InvoicingModule(),
        PurchasingModule(),
        InventoryModule(),  # ✅ مفعل
        ProductsModule(),
        CustomersModule(),
        SuppliersModule(),
        FundsModule(),  # ✅ مفعل
        PaymentsModule(),
        SitesModule(),
        CurrencyModule(),
        TaxModule(),
        FinancialStatementsModule(),
        SettingsModule(),
        WorkflowModule(),
        CentersModule(),
        ReportsModule(),
        NotificationsModule(),
        FixedAssetsModule(),
    ]


def register_all_modules(container: 'DependencyContainer', config: Dict[str, Any]) -> None:
    """
    تسجيل جميع الوحدات في الحاوية
    
    Args:
        container: حاوية حقن التبعيات
        config: إعدادات التطبيق
    """
    # 1. تسجيل الوحدات
    for module in get_all_modules():
        module.register(container)
    
    # 2. تكوين الوحدات
    for module in get_all_modules():
        module.configure(container, config)


__all__ = [
    "Module",
    "DatabaseModule",
    "AccountingModule",
    "InvoicingModule",
    "PurchasingModule",
    "InventoryModule",
    "ProductsModule",
    "CustomersModule",
    "SuppliersModule",
    "FundsModule",
    "PaymentsModule",
    "SitesModule",
    "CurrencyModule",
    "TaxModule",
    "FinancialStatementsModule",
    "FiscalModule",
    "SettingsModule",
    "SecurityModule",
    "WorkflowModule",
    "CentersModule",
    "ReportsModule",
    "NotificationsModule",
    "FixedAssetsModule",
    "get_all_modules",
    "register_all_modules",
]