# core/domain/settings/entities.py
"""Settings Aggregate Root"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Any, List

from .value_objects import (
    UiSettings, InvoicingSettings, PurchasingSettings, ProductSettings,
    CustomerSettings, SupplierSettings, UserSettings, NotificationSettings,
    PrinterSettings, BackupSettings, Theme, Language, Currency
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Settings:
    """
    AGGREGATE ROOT - إعدادات النظام الرئيسية
    
    ملاحظة: الـ version للتحكم في التزامن (Optimistic Locking)
    يتم إدارته فقط بواسطة الـ Repository
    """
    
    # الفئات الرئيسية
    ui: UiSettings = field(default_factory=UiSettings)
    invoicing: InvoicingSettings = field(default_factory=InvoicingSettings)
    purchasing: PurchasingSettings = field(default_factory=PurchasingSettings)
    products: ProductSettings = field(default_factory=ProductSettings)
    customers: CustomerSettings = field(default_factory=CustomerSettings)
    suppliers: SupplierSettings = field(default_factory=SupplierSettings)
    users: UserSettings = field(default_factory=UserSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    printer: PrinterSettings = field(default_factory=PrinterSettings)
    backup: BackupSettings = field(default_factory=BackupSettings)
    
    # بيانات التدقيق
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    
    # التحكم في التزامن
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # ========== دوال التحديث ==========
    
    def update_ui(self, new_ui: UiSettings, updated_by: str) -> None:
        """تحديث إعدادات واجهة المستخدم"""
        self.ui = new_ui
        self._update_metadata(updated_by)
    
    def update_invoicing(self, new_invoicing: InvoicingSettings, updated_by: str) -> None:
        """تحديث إعدادات الفواتير"""
        self.invoicing = new_invoicing
        self._update_metadata(updated_by)
    
    def update_purchasing(self, new_purchasing: PurchasingSettings, updated_by: str) -> None:
        """تحديث إعدادات المشتريات"""
        self.purchasing = new_purchasing
        self._update_metadata(updated_by)
    
    def update_products(self, new_products: ProductSettings, updated_by: str) -> None:
        """تحديث إعدادات المنتجات"""
        self.products = new_products
        self._update_metadata(updated_by)
    
    def update_customers(self, new_customers: CustomerSettings, updated_by: str) -> None:
        """تحديث إعدادات العملاء"""
        self.customers = new_customers
        self._update_metadata(updated_by)
    
    def update_suppliers(self, new_suppliers: SupplierSettings, updated_by: str) -> None:
        """تحديث إعدادات الموردين"""
        self.suppliers = new_suppliers
        self._update_metadata(updated_by)
    
    def update_users(self, new_users: UserSettings, updated_by: str) -> None:
        """تحديث إعدادات المستخدمين"""
        self.users = new_users
        self._update_metadata(updated_by)
    
    def update_notifications(self, new_notifications: NotificationSettings, updated_by: str) -> None:
        """تحديث إعدادات الإشعارات"""
        self.notifications = new_notifications
        self._update_metadata(updated_by)
    
    def update_printer(self, new_printer: PrinterSettings, updated_by: str) -> None:
        """تحديث إعدادات الطباعة"""
        self.printer = new_printer
        self._update_metadata(updated_by)
    
    def update_backup(self, new_backup: BackupSettings, updated_by: str) -> None:
        """تحديث إعدادات النسخ الاحتياطي"""
        self.backup = new_backup
        self._update_metadata(updated_by)
    
    def _update_metadata(self, updated_by: str) -> None:
        """تحديث بيانات التدقيق"""
        self.updated_at = utc_now()
        self.updated_by = updated_by
    
    # ========== Domain Events ==========
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events