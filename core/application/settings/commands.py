# core/application/settings/commands.py
"""Commands and Queries for Settings"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


# ========== UPDATE COMMANDS ==========

@dataclass(frozen=True)
class UpdateUiSettingsCommand:
    """أمر تحديث إعدادات واجهة المستخدم"""
    theme: Optional[str] = None
    language: Optional[str] = None
    font_size: Optional[int] = None
    font_family: Optional[str] = None
    animations_enabled: Optional[bool] = None
    animation_speed: Optional[int] = None
    sidebar_collapsed: Optional[bool] = None
    recent_items_count: Optional[int] = None
    confirm_before_close: Optional[bool] = None
    show_tooltips: Optional[bool] = None
    show_status_bar: Optional[bool] = None
    auto_save_interval: Optional[int] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdateInvoicingSettingsCommand:
    """أمر تحديث إعدادات الفواتير"""
    default_currency: Optional[str] = None
    default_payment_terms: Optional[str] = None
    invoice_prefix: Optional[str] = None
    invoice_number_length: Optional[int] = None
    auto_generate_number: Optional[bool] = None
    require_customer: Optional[bool] = None
    require_site: Optional[bool] = None
    show_tax: Optional[bool] = None
    default_tax_rate: Optional[float] = None
    allow_draft_edit: Optional[bool] = None
    days_before_due: Optional[int] = None
    invoice_notes_template: Optional[str] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdatePurchasingSettingsCommand:
    """أمر تحديث إعدادات المشتريات"""
    default_currency: Optional[str] = None
    default_payment_terms: Optional[str] = None
    purchase_prefix: Optional[str] = None
    purchase_number_length: Optional[int] = None
    auto_generate_number: Optional[bool] = None
    require_supplier: Optional[bool] = None
    require_expected_delivery: Optional[bool] = None
    auto_receive_on_post: Optional[bool] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdateProductSettingsCommand:
    """أمر تحديث إعدادات المنتجات"""
    default_currency: Optional[str] = None
    default_tax_rate: Optional[float] = None
    default_unit: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    enable_batch_tracking: Optional[bool] = None
    enable_serial_tracking: Optional[bool] = None
    auto_generate_code: Optional[bool] = None
    code_prefix: Optional[str] = None
    code_length: Optional[int] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdateCustomerSettingsCommand:
    """أمر تحديث إعدادات العملاء"""
    default_currency: Optional[str] = None
    default_payment_terms: Optional[str] = None
    auto_generate_code: Optional[bool] = None
    code_prefix: Optional[str] = None
    code_length: Optional[int] = None
    require_tax_number: Optional[bool] = None
    default_credit_limit: Optional[float] = None
    enable_credit_check: Optional[bool] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdateSupplierSettingsCommand:
    """أمر تحديث إعدادات الموردين"""
    default_currency: Optional[str] = None
    default_payment_terms: Optional[str] = None
    auto_generate_code: Optional[bool] = None
    code_prefix: Optional[str] = None
    code_length: Optional[int] = None
    require_tax_number: Optional[bool] = None
    default_credit_limit: Optional[float] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdateUserSettingsCommand:
    """أمر تحديث إعدادات المستخدمين"""
    session_timeout_minutes: Optional[int] = None
    max_login_attempts: Optional[int] = None
    lockout_minutes: Optional[int] = None
    require_strong_password: Optional[bool] = None
    password_min_length: Optional[int] = None
    enable_2fa: Optional[bool] = None
    audit_log_enabled: Optional[bool] = None
    max_sessions_per_user: Optional[int] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdateNotificationSettingsCommand:
    """أمر تحديث إعدادات الإشعارات"""
    enable_system_notifications: Optional[bool] = None
    enable_email_notifications: Optional[bool] = None
    enable_sound_notifications: Optional[bool] = None
    notification_sound: Optional[str] = None
    email_smtp_server: Optional[str] = None
    email_smtp_port: Optional[int] = None
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None
    low_stock_alert: Optional[bool] = None
    overdue_invoice_alert: Optional[bool] = None
    new_user_alert: Optional[bool] = None
    system_update_alert: Optional[bool] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdatePrinterSettingsCommand:
    """أمر تحديث إعدادات الطباعة"""
    default_printer: Optional[str] = None
    paper_size: Optional[str] = None
    copies: Optional[int] = None
    print_duplex: Optional[bool] = None
    header_margin: Optional[int] = None
    footer_margin: Optional[int] = None
    left_margin: Optional[int] = None
    right_margin: Optional[int] = None
    show_company_logo: Optional[bool] = None
    show_company_info: Optional[bool] = None
    show_footer: Optional[bool] = None
    footer_text: Optional[str] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class UpdateBackupSettingsCommand:
    """أمر تحديث إعدادات النسخ الاحتياطي"""
    auto_backup_enabled: Optional[bool] = None
    backup_interval_hours: Optional[int] = None
    backup_retention_days: Optional[int] = None
    backup_path: Optional[str] = None
    backup_on_exit: Optional[bool] = None
    include_attachments: Optional[bool] = None
    compress_backup: Optional[bool] = None
    encrypt_backup: Optional[bool] = None
    updated_by: str = "system"


# ========== BULK UPDATE COMMANDS ==========

@dataclass(frozen=True)
class UpdateAllSettingsCommand:
    """تحديث جميع الإعدادات دفعة واحدة"""
    ui: Optional[dict] = None
    invoicing: Optional[dict] = None
    purchasing: Optional[dict] = None
    products: Optional[dict] = None
    customers: Optional[dict] = None
    suppliers: Optional[dict] = None
    users: Optional[dict] = None
    notifications: Optional[dict] = None
    printer: Optional[dict] = None
    backup: Optional[dict] = None
    updated_by: str = "system"


# ========== QUERIES ==========

@dataclass(frozen=True)
class GetSettingsQuery:
    """استعلام لجلب جميع الإعدادات"""
    pass


@dataclass(frozen=True)
class GetUiSettingsQuery:
    pass


@dataclass(frozen=True)
class GetInvoicingSettingsQuery:
    pass


@dataclass(frozen=True)
class GetPurchasingSettingsQuery:
    pass


@dataclass(frozen=True)
class GetProductSettingsQuery:
    pass


@dataclass(frozen=True)
class GetCustomerSettingsQuery:
    pass


@dataclass(frozen=True)
class GetSupplierSettingsQuery:
    pass


@dataclass(frozen=True)
class GetUserSettingsQuery:
    pass


@dataclass(frozen=True)
class GetNotificationSettingsQuery:
    pass


@dataclass(frozen=True)
class GetPrinterSettingsQuery:
    pass


@dataclass(frozen=True)
class GetBackupSettingsQuery:
    pass


__all__ = [
    # Update Commands
    "UpdateUiSettingsCommand",
    "UpdateInvoicingSettingsCommand",
    "UpdatePurchasingSettingsCommand",
    "UpdateProductSettingsCommand",
    "UpdateCustomerSettingsCommand",
    "UpdateSupplierSettingsCommand",
    "UpdateUserSettingsCommand",
    "UpdateNotificationSettingsCommand",
    "UpdatePrinterSettingsCommand",
    "UpdateBackupSettingsCommand",
    "UpdateAllSettingsCommand",
    # Queries
    "GetSettingsQuery",
    "GetUiSettingsQuery",
    "GetInvoicingSettingsQuery",
    "GetPurchasingSettingsQuery",
    "GetProductSettingsQuery",
    "GetCustomerSettingsQuery",
    "GetSupplierSettingsQuery",
    "GetUserSettingsQuery",
    "GetNotificationSettingsQuery",
    "GetPrinterSettingsQuery",
    "GetBackupSettingsQuery",
]