# core/application/settings/dtos.py
"""
Data Transfer Objects for Settings Module
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any


# ========== UI Settings DTOs ==========

@dataclass(frozen=True)
class UiSettingsDTO:
    """إعدادات واجهة المستخدم - DTO"""
    theme: str = "light"
    language: str = "ar"
    font_size: int = 12
    font_family: str = "Segoe UI"
    animations_enabled: bool = True
    animation_speed: int = 250
    sidebar_collapsed: bool = False
    recent_items_count: int = 10
    confirm_before_close: bool = True
    show_tooltips: bool = True
    show_status_bar: bool = True
    auto_save_interval: int = 60
    
    @property
    def is_dark_theme(self) -> bool:
        """هل الثيم داكن؟"""
        return self.theme in ["dark", "modern_dark"]
    
    @property
    def is_light_theme(self) -> bool:
        """هل الثيم فاتح؟"""
        return self.theme in ["light", "modern_light"]
    
    @property
    def theme_display_name(self) -> str:
        """الاسم المعروض للثيم"""
        themes = {
            "light": "فاتح",
            "dark": "داكن",
            "modern_light": "عصري فاتح",
            "modern_dark": "عصري داكن",
            "system": "نظام",
        }
        return themes.get(self.theme, self.theme)
    
    @property
    def language_display_name(self) -> str:
        """الاسم المعروض للغة"""
        languages = {
            "ar": "العربية",
            "en": "English",
            "fr": "Français",
        }
        return languages.get(self.language, self.language)


# ========== Invoicing Settings DTOs ==========

@dataclass(frozen=True)
class InvoicingSettingsDTO:
    """إعدادات الفواتير - DTO"""
    default_currency: str = "USD"
    default_payment_terms: str = "net_30"
    invoice_prefix: str = "INV"
    invoice_number_length: int = 5
    auto_generate_number: bool = True
    require_customer: bool = True
    require_site: bool = False
    show_tax: bool = True
    default_tax_rate: float = 0.0
    allow_draft_edit: bool = True
    days_before_due: int = 30
    invoice_notes_template: str = "شكراً لتسوقكم معنا"
    
    @property
    def payment_terms_display(self) -> str:
        """الاسم المعروض لشروط الدفع"""
        terms = {
            "cash": "نقدي",
            "net_15": "صافي 15 يوم",
            "net_30": "صافي 30 يوم",
            "net_45": "صافي 45 يوم",
            "net_60": "صافي 60 يوم",
        }
        return terms.get(self.default_payment_terms, self.default_payment_terms)
    
    @property
    def sample_invoice_number(self) -> str:
        """رقم فاتورة تجريبي"""
        return f"{self.invoice_prefix}-{'1'.zfill(self.invoice_number_length)}"


# ========== Purchasing Settings DTOs ==========

@dataclass(frozen=True)
class PurchasingSettingsDTO:
    """إعدادات المشتريات - DTO"""
    default_currency: str = "USD"
    default_payment_terms: str = "net_30"
    purchase_prefix: str = "PO"
    purchase_number_length: int = 5
    auto_generate_number: bool = True
    require_supplier: bool = True
    require_expected_delivery: bool = False
    auto_receive_on_post: bool = False
    
    @property
    def sample_order_number(self) -> str:
        """رقم أمر شراء تجريبي"""
        return f"{self.purchase_prefix}-{'1'.zfill(self.purchase_number_length)}"


# ========== Products Settings DTOs ==========

@dataclass(frozen=True)
class ProductSettingsDTO:
    """إعدادات المنتجات - DTO"""
    default_currency: str = "USD"
    default_tax_rate: float = 0.0
    default_unit: str = "قطعة (pc)"
    low_stock_threshold: int = 10
    enable_batch_tracking: bool = False
    enable_serial_tracking: bool = False
    auto_generate_code: bool = True
    code_prefix: str = "P"
    code_length: int = 5
    
    @property
    def sample_product_code(self) -> str:
        """كود منتج تجريبي"""
        return f"{self.code_prefix}-{'1'.zfill(self.code_length)}"


# ========== Customers Settings DTOs ==========

@dataclass(frozen=True)
class CustomerSettingsDTO:
    """إعدادات العملاء - DTO"""
    default_currency: str = "USD"
    default_payment_terms: str = "net_30"
    auto_generate_code: bool = True
    code_prefix: str = "C"
    code_length: int = 5
    require_tax_number: bool = False
    default_credit_limit: float = 0.0
    enable_credit_check: bool = False
    
    @property
    def sample_customer_code(self) -> str:
        """كود عميل تجريبي"""
        return f"{self.code_prefix}-{'1'.zfill(self.code_length)}"


# ========== Suppliers Settings DTOs ==========

@dataclass(frozen=True)
class SupplierSettingsDTO:
    """إعدادات الموردين - DTO"""
    default_currency: str = "USD"
    default_payment_terms: str = "net_30"
    auto_generate_code: bool = True
    code_prefix: str = "S"
    code_length: int = 5
    require_tax_number: bool = False
    default_credit_limit: float = 0.0
    
    @property
    def sample_supplier_code(self) -> str:
        """كود مورد تجريبي"""
        return f"{self.code_prefix}-{'1'.zfill(self.code_length)}"


# ========== Users Settings DTOs ==========

@dataclass(frozen=True)
class UserSettingsDTO:
    """إعدادات المستخدمين - DTO"""
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    require_strong_password: bool = True
    password_min_length: int = 8
    enable_2fa: bool = False
    audit_log_enabled: bool = True
    max_sessions_per_user: int = 3
    
    @property
    def password_requirements(self) -> List[str]:
        """متطلبات كلمة المرور"""
        requirements = []
        if self.require_strong_password:
            requirements.append(f"الحد الأدنى {self.password_min_length} أحرف")
            requirements.append("حرف كبير واحد على الأقل")
            requirements.append("حرف صغير واحد على الأقل")
            requirements.append("رقم واحد على الأقل")
        return requirements


# ========== Notifications Settings DTOs ==========

@dataclass(frozen=True)
class NotificationSettingsDTO:
    """إعدادات الإشعارات - DTO"""
    enable_system_notifications: bool = True
    enable_email_notifications: bool = False
    enable_sound_notifications: bool = True
    notification_sound: str = "default"
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    low_stock_alert: bool = True
    overdue_invoice_alert: bool = True
    new_user_alert: bool = True
    system_update_alert: bool = True
    
    @property
    def is_email_configured(self) -> bool:
        """هل تم تكوين البريد الإلكتروني؟"""
        return bool(self.email_smtp_server and self.email_username and self.email_from)
    
    @property
    def sound_display_name(self) -> str:
        """الاسم المعروض للصوت"""
        sounds = {
            "none": "بدون صوت",
            "default": "افتراضي",
            "soft": "هادئ",
            "urgent": "طارئ",
            "custom": "مخصص",
        }
        return sounds.get(self.notification_sound, self.notification_sound)


# ========== Printer Settings DTOs ==========

@dataclass(frozen=True)
class PrinterSettingsDTO:
    """إعدادات الطباعة - DTO"""
    default_printer: str = ""
    paper_size: str = "A4"
    copies: int = 1
    print_duplex: bool = False
    header_margin: int = 20
    footer_margin: int = 20
    left_margin: int = 15
    right_margin: int = 15
    show_company_logo: bool = True
    show_company_info: bool = True
    show_footer: bool = True
    footer_text: str = "شكراً لكم"
    
    @property
    def paper_size_display(self) -> str:
        """الاسم المعروض لحجم الورق"""
        sizes = {
            "A4": "A4",
            "A5": "A5",
            "Letter": "Letter",
            "80mm": "80mm (حراري)",
            "58mm": "58mm (حراري)",
        }
        return sizes.get(self.paper_size, self.paper_size)


# ========== Backup Settings DTOs ==========

@dataclass(frozen=True)
class BackupSettingsDTO:
    """إعدادات النسخ الاحتياطي - DTO"""
    auto_backup_enabled: bool = False
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    backup_path: str = "./backups"
    backup_on_exit: bool = True
    include_attachments: bool = True
    compress_backup: bool = True
    encrypt_backup: bool = False


# ========== Main Settings DTO ==========

@dataclass(frozen=True)
class SettingsDTO:
    """كائن نقل البيانات الرئيسي للإعدادات"""
    ui: UiSettingsDTO
    invoicing: InvoicingSettingsDTO
    purchasing: PurchasingSettingsDTO
    products: ProductSettingsDTO
    customers: CustomerSettingsDTO
    suppliers: SupplierSettingsDTO
    users: UserSettingsDTO
    notifications: NotificationSettingsDTO
    printer: PrinterSettingsDTO
    backup: BackupSettingsDTO
    version: int = 1
    updated_at: Optional[datetime] = None
    updated_by: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس للتسلسل"""
        return {
            'ui': {
                'theme': self.ui.theme,
                'language': self.ui.language,
                'font_size': self.ui.font_size,
                'font_family': self.ui.font_family,
                'animations_enabled': self.ui.animations_enabled,
                'animation_speed': self.ui.animation_speed,
                'sidebar_collapsed': self.ui.sidebar_collapsed,
                'recent_items_count': self.ui.recent_items_count,
                'confirm_before_close': self.ui.confirm_before_close,
                'show_tooltips': self.ui.show_tooltips,
                'show_status_bar': self.ui.show_status_bar,
                'auto_save_interval': self.ui.auto_save_interval,
            },
            'invoicing': {
                'default_currency': self.invoicing.default_currency,
                'default_payment_terms': self.invoicing.default_payment_terms,
                'invoice_prefix': self.invoicing.invoice_prefix,
                'invoice_number_length': self.invoicing.invoice_number_length,
                'auto_generate_number': self.invoicing.auto_generate_number,
                'require_customer': self.invoicing.require_customer,
                'require_site': self.invoicing.require_site,
                'show_tax': self.invoicing.show_tax,
                'default_tax_rate': self.invoicing.default_tax_rate,
                'allow_draft_edit': self.invoicing.allow_draft_edit,
                'days_before_due': self.invoicing.days_before_due,
                'invoice_notes_template': self.invoicing.invoice_notes_template,
            },
            'purchasing': {
                'default_currency': self.purchasing.default_currency,
                'default_payment_terms': self.purchasing.default_payment_terms,
                'purchase_prefix': self.purchasing.purchase_prefix,
                'purchase_number_length': self.purchasing.purchase_number_length,
                'auto_generate_number': self.purchasing.auto_generate_number,
                'require_supplier': self.purchasing.require_supplier,
                'require_expected_delivery': self.purchasing.require_expected_delivery,
                'auto_receive_on_post': self.purchasing.auto_receive_on_post,
            },
            'products': {
                'default_currency': self.products.default_currency,
                'default_tax_rate': self.products.default_tax_rate,
                'default_unit': self.products.default_unit,
                'low_stock_threshold': self.products.low_stock_threshold,
                'enable_batch_tracking': self.products.enable_batch_tracking,
                'enable_serial_tracking': self.products.enable_serial_tracking,
                'auto_generate_code': self.products.auto_generate_code,
                'code_prefix': self.products.code_prefix,
                'code_length': self.products.code_length,
            },
            'customers': {
                'default_currency': self.customers.default_currency,
                'default_payment_terms': self.customers.default_payment_terms,
                'auto_generate_code': self.customers.auto_generate_code,
                'code_prefix': self.customers.code_prefix,
                'code_length': self.customers.code_length,
                'require_tax_number': self.customers.require_tax_number,
                'default_credit_limit': self.customers.default_credit_limit,
                'enable_credit_check': self.customers.enable_credit_check,
            },
            'suppliers': {
                'default_currency': self.suppliers.default_currency,
                'default_payment_terms': self.suppliers.default_payment_terms,
                'auto_generate_code': self.suppliers.auto_generate_code,
                'code_prefix': self.suppliers.code_prefix,
                'code_length': self.suppliers.code_length,
                'require_tax_number': self.suppliers.require_tax_number,
                'default_credit_limit': self.suppliers.default_credit_limit,
            },
            'users': {
                'session_timeout_minutes': self.users.session_timeout_minutes,
                'max_login_attempts': self.users.max_login_attempts,
                'lockout_minutes': self.users.lockout_minutes,
                'require_strong_password': self.users.require_strong_password,
                'password_min_length': self.users.password_min_length,
                'enable_2fa': self.users.enable_2fa,
                'audit_log_enabled': self.users.audit_log_enabled,
                'max_sessions_per_user': self.users.max_sessions_per_user,
            },
            'notifications': {
                'enable_system_notifications': self.notifications.enable_system_notifications,
                'enable_email_notifications': self.notifications.enable_email_notifications,
                'enable_sound_notifications': self.notifications.enable_sound_notifications,
                'notification_sound': self.notifications.notification_sound,
                'email_smtp_server': self.notifications.email_smtp_server,
                'email_smtp_port': self.notifications.email_smtp_port,
                'email_username': self.notifications.email_username,
                'email_password': self.notifications.email_password,
                'email_from': self.notifications.email_from,
                'low_stock_alert': self.notifications.low_stock_alert,
                'overdue_invoice_alert': self.notifications.overdue_invoice_alert,
                'new_user_alert': self.notifications.new_user_alert,
                'system_update_alert': self.notifications.system_update_alert,
            },
            'printer': {
                'default_printer': self.printer.default_printer,
                'paper_size': self.printer.paper_size,
                'copies': self.printer.copies,
                'print_duplex': self.printer.print_duplex,
                'header_margin': self.printer.header_margin,
                'footer_margin': self.printer.footer_margin,
                'left_margin': self.printer.left_margin,
                'right_margin': self.printer.right_margin,
                'show_company_logo': self.printer.show_company_logo,
                'show_company_info': self.printer.show_company_info,
                'show_footer': self.printer.show_footer,
                'footer_text': self.printer.footer_text,
            },
            'backup': {
                'auto_backup_enabled': self.backup.auto_backup_enabled,
                'backup_interval_hours': self.backup.backup_interval_hours,
                'backup_retention_days': self.backup.backup_retention_days,
                'backup_path': self.backup.backup_path,
                'backup_on_exit': self.backup.backup_on_exit,
                'include_attachments': self.backup.include_attachments,
                'compress_backup': self.backup.compress_backup,
                'encrypt_backup': self.backup.encrypt_backup,
            },
            'version': self.version,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
        }


__all__ = [
    "UiSettingsDTO",
    "InvoicingSettingsDTO",
    "PurchasingSettingsDTO",
    "ProductSettingsDTO",
    "CustomerSettingsDTO",
    "SupplierSettingsDTO",
    "UserSettingsDTO",
    "NotificationSettingsDTO",
    "PrinterSettingsDTO",
    "BackupSettingsDTO",
    "SettingsDTO",
]