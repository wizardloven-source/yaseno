# core/domain/settings/aggregates.py (إضافة الأحداث داخل الكيان)
"""
Unified Settings Aggregate - المصدر الوحيد للحقيقة للإعدادات
✅ محدث: إضافة دعم الأحداث
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum

from .value_objects import (
    Theme, Language, Currency,
    UiSettings, InvoicingSettings, PurchasingSettings,
    ProductSettings, CustomerSettings, SupplierSettings,
    UserSettings, NotificationSettings, PrinterSettings,
    BackupSettings
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SettingsCategory(Enum):
    SYSTEM = "system"
    UI = "ui"
    ACCOUNTING = "accounting"
    INVOICING = "invoicing"
    PURCHASING = "purchasing"
    PRODUCTS = "products"
    CUSTOMERS = "customers"
    SUPPLIERS = "suppliers"
    USERS = "users"
    NOTIFICATIONS = "notifications"
    PRINTING = "printing"
    BACKUP = "backup"


@dataclass
class AuditEntry:
    setting_path: str
    old_value: Any
    new_value: Any
    changed_by: str
    changed_at: datetime
    category: SettingsCategory


@dataclass
class Settings:
    """
    AGGREGATE ROOT - نظام الإعدادات الموحد
    
    هذا هو المصدر الوحيد للحقيقة للإعدادات.
    """
    
    # الإصدار
    version: int = 1
    
    # فئات الإعدادات
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
    
    # سجل التغييرات والأحداث
    _audit_log: List[AuditEntry] = field(default_factory=list, repr=False)
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # ========== دوال التحديث ==========
    
    def update_ui(
        self,
        new_ui: UiSettings,
        changed_by: str
    ) -> bool:
        """تحديث إعدادات واجهة المستخدم بالكامل"""
        if self.ui == new_ui:
            return False
        
        old_ui = self.ui
        self.ui = new_ui
        self.updated_at = utc_now()
        self.updated_by = changed_by
        self.version += 1
        
        # تسجيل التغييرات في سجل التدقيق
        self._audit_log.append(AuditEntry(
            setting_path="ui",
            old_value=old_ui.to_dict(),
            new_value=new_ui.to_dict(),
            changed_by=changed_by,
            changed_at=utc_now(),
            category=SettingsCategory.UI
        ))
        
        # ✅ بث حدث تغيير الثيم إذا تغير
        if old_ui.theme != new_ui.theme:
            from .events import ThemeChangedEvent
            self._events.append(ThemeChangedEvent(
                old_theme=old_ui.theme,
                new_theme=new_ui.theme,
                changed_by=changed_by
            ))
        
        # ✅ بث حدث تغيير اللغة إذا تغيرت
        if old_ui.language != new_ui.language:
            from .events import LanguageChangedEvent
            self._events.append(LanguageChangedEvent(
                old_language=old_ui.language,
                new_language=new_ui.language,
                changed_by=changed_by
            ))
        
        return True
    
    def update_ui_setting(
        self,
        setting_name: str,
        value: Any,
        changed_by: str
    ) -> bool:
        """تحديث إعداد UI واحد"""
        old_value = getattr(self.ui, setting_name, None)
        
        if old_value == value:
            return False
        
        setattr(self.ui, setting_name, value)
        self.updated_at = utc_now()
        self.updated_by = changed_by
        self.version += 1
        
        # تسجيل في سجل التدقيق
        self._audit_log.append(AuditEntry(
            setting_path=f"ui.{setting_name}",
            old_value=old_value,
            new_value=value,
            changed_by=changed_by,
            changed_at=utc_now(),
            category=SettingsCategory.UI
        ))
        
        # ✅ بث حدث مناسب
        from .events import SettingChangedEvent
        
        if setting_name == "theme":
            self._events.append(SettingChangedEvent(
                setting_path="ui.theme",
                old_value=old_value,
                new_value=value,
                changed_by=changed_by,
                category="ui"
            ))
        
        return True
    
    def update_invoicing(
        self,
        new_invoicing: InvoicingSettings,
        changed_by: str
    ) -> bool:
        """تحديث إعدادات الفواتير"""
        if self.invoicing == new_invoicing:
            return False
        
        old_invoicing = self.invoicing
        self.invoicing = new_invoicing
        self.updated_at = utc_now()
        self.updated_by = changed_by
        self.version += 1
        
        self._audit_log.append(AuditEntry(
            setting_path="invoicing",
            old_value=old_invoicing.to_dict(),
            new_value=new_invoicing.to_dict(),
            changed_by=changed_by,
            changed_at=utc_now(),
            category=SettingsCategory.INVOICING
        ))
        
        # ✅ بث حدث تغيير العملة إذا تغيرت
        if old_invoicing.default_currency != new_invoicing.default_currency:
            from .events import CurrencyChangedEvent
            self._events.append(CurrencyChangedEvent(
                old_currency=old_invoicing.default_currency,
                new_currency=new_invoicing.default_currency,
                changed_by=changed_by
            ))
        
        return True
    
    # ========== استيراد/تصدير ==========
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتصدير"""
        return {
            'version': self.version,
            'exported_at': utc_now().isoformat(),
            'exported_by': self.updated_by,
            'settings': {
                'ui': self.ui.to_dict(),
                'invoicing': self.invoicing.to_dict(),
                'purchasing': self.purchasing.to_dict(),
                'products': self.products.to_dict(),
                'customers': self.customers.to_dict(),
                'suppliers': self.suppliers.to_dict(),
                'users': self.users.to_dict(),
                'notifications': self.notifications.to_dict(),
                'printer': self.printer.to_dict(),
                'backup': self.backup.to_dict(),
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        """إنشاء من قاموس"""
        settings_data = data.get('settings', {})
        
        return cls(
            version=data.get('version', 1),
            updated_by=data.get('exported_by', 'system'),
            ui=UiSettings.from_dict(settings_data.get('ui', {})),
            invoicing=InvoicingSettings.from_dict(settings_data.get('invoicing', {})),
            purchasing=PurchasingSettings.from_dict(settings_data.get('purchasing', {})),
            products=ProductSettings.from_dict(settings_data.get('products', {})),
            customers=CustomerSettings.from_dict(settings_data.get('customers', {})),
            suppliers=SupplierSettings.from_dict(settings_data.get('suppliers', {})),
            users=UserSettings.from_dict(settings_data.get('users', {})),
            notifications=NotificationSettings.from_dict(settings_data.get('notifications', {})),
            printer=PrinterSettings.from_dict(settings_data.get('printer', {})),
            backup=BackupSettings.from_dict(settings_data.get('backup', {})),
        )
    
    def get_audit_log(self, limit: int = 100) -> List[AuditEntry]:
        return self._audit_log[-limit:]
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events