# core/application/settings/converters.py
"""
Converters for Settings - تحويل بين Domain Entities و DTOs
"""

from typing import Dict, Any, Optional
from datetime import datetime

from core.domain.settings.entities import Settings
from core.domain.settings.value_objects import (
    UiSettings, InvoicingSettings, PurchasingSettings, ProductSettings,
    CustomerSettings, SupplierSettings, UserSettings, NotificationSettings,
    PrinterSettings, BackupSettings, Theme, Language, Currency, PaperSize, NotificationSound
)

from .dtos import (
    SettingsDTO, UiSettingsDTO, InvoicingSettingsDTO, PurchasingSettingsDTO,
    ProductSettingsDTO, CustomerSettingsDTO, SupplierSettingsDTO, UserSettingsDTO,
    NotificationSettingsDTO, PrinterSettingsDTO, BackupSettingsDTO
)


# ========== DTO to Domain Converters ==========

def ui_dto_to_domain(dto: UiSettingsDTO) -> UiSettings:
    """تحويل UiSettingsDTO إلى UiSettings Domain"""
    return UiSettings(
        theme=Theme(dto.theme),
        language=Language(dto.language),
        font_size=dto.font_size,
        font_family=dto.font_family,
        animations_enabled=dto.animations_enabled,
        animation_speed=dto.animation_speed,
        sidebar_collapsed=dto.sidebar_collapsed,
        recent_items_count=dto.recent_items_count,
        confirm_before_close=dto.confirm_before_close,
        show_tooltips=dto.show_tooltips,
        show_status_bar=dto.show_status_bar,
        auto_save_interval=dto.auto_save_interval,
    )


def invoicing_dto_to_domain(dto: InvoicingSettingsDTO) -> InvoicingSettings:
    """تحويل InvoicingSettingsDTO إلى InvoicingSettings Domain"""
    return InvoicingSettings(
        default_currency=Currency(dto.default_currency),
        default_payment_terms=dto.default_payment_terms,
        invoice_prefix=dto.invoice_prefix,
        invoice_number_length=dto.invoice_number_length,
        auto_generate_number=dto.auto_generate_number,
        require_customer=dto.require_customer,
        require_site=dto.require_site,
        show_tax=dto.show_tax,
        default_tax_rate=dto.default_tax_rate,
        allow_draft_edit=dto.allow_draft_edit,
        days_before_due=dto.days_before_due,
        invoice_notes_template=dto.invoice_notes_template,
    )


def purchasing_dto_to_domain(dto: PurchasingSettingsDTO) -> PurchasingSettings:
    """تحويل PurchasingSettingsDTO إلى PurchasingSettings Domain"""
    return PurchasingSettings(
        default_currency=Currency(dto.default_currency),
        default_payment_terms=dto.default_payment_terms,
        purchase_prefix=dto.purchase_prefix,
        purchase_number_length=dto.purchase_number_length,
        auto_generate_number=dto.auto_generate_number,
        require_supplier=dto.require_supplier,
        require_expected_delivery=dto.require_expected_delivery,
        auto_receive_on_post=dto.auto_receive_on_post,
    )


def product_dto_to_domain(dto: ProductSettingsDTO) -> ProductSettings:
    """تحويل ProductSettingsDTO إلى ProductSettings Domain"""
    return ProductSettings(
        default_currency=Currency(dto.default_currency),
        default_tax_rate=dto.default_tax_rate,
        default_unit=dto.default_unit,
        low_stock_threshold=dto.low_stock_threshold,
        enable_batch_tracking=dto.enable_batch_tracking,
        enable_serial_tracking=dto.enable_serial_tracking,
        auto_generate_code=dto.auto_generate_code,
        code_prefix=dto.code_prefix,
        code_length=dto.code_length,
    )


def customer_dto_to_domain(dto: CustomerSettingsDTO) -> CustomerSettings:
    """تحويل CustomerSettingsDTO إلى CustomerSettings Domain"""
    return CustomerSettings(
        default_currency=Currency(dto.default_currency),
        default_payment_terms=dto.default_payment_terms,
        auto_generate_code=dto.auto_generate_code,
        code_prefix=dto.code_prefix,
        code_length=dto.code_length,
        require_tax_number=dto.require_tax_number,
        default_credit_limit=dto.default_credit_limit,
        enable_credit_check=dto.enable_credit_check,
    )


def supplier_dto_to_domain(dto: SupplierSettingsDTO) -> SupplierSettings:
    """تحويل SupplierSettingsDTO إلى SupplierSettings Domain"""
    return SupplierSettings(
        default_currency=Currency(dto.default_currency),
        default_payment_terms=dto.default_payment_terms,
        auto_generate_code=dto.auto_generate_code,
        code_prefix=dto.code_prefix,
        code_length=dto.code_length,
        require_tax_number=dto.require_tax_number,
        default_credit_limit=dto.default_credit_limit,
    )


def user_dto_to_domain(dto: UserSettingsDTO) -> UserSettings:
    """تحويل UserSettingsDTO إلى UserSettings Domain"""
    return UserSettings(
        session_timeout_minutes=dto.session_timeout_minutes,
        max_login_attempts=dto.max_login_attempts,
        lockout_minutes=dto.lockout_minutes,
        require_strong_password=dto.require_strong_password,
        password_min_length=dto.password_min_length,
        enable_2fa=dto.enable_2fa,
        audit_log_enabled=dto.audit_log_enabled,
        max_sessions_per_user=dto.max_sessions_per_user,
    )


def notification_dto_to_domain(dto: NotificationSettingsDTO) -> NotificationSettings:
    """تحويل NotificationSettingsDTO إلى NotificationSettings Domain"""
    return NotificationSettings(
        enable_system_notifications=dto.enable_system_notifications,
        enable_email_notifications=dto.enable_email_notifications,
        enable_sound_notifications=dto.enable_sound_notifications,
        notification_sound=NotificationSound(dto.notification_sound),
        email_smtp_server=dto.email_smtp_server,
        email_smtp_port=dto.email_smtp_port,
        email_username=dto.email_username,
        email_password=dto.email_password,
        email_from=dto.email_from,
        low_stock_alert=dto.low_stock_alert,
        overdue_invoice_alert=dto.overdue_invoice_alert,
        new_user_alert=dto.new_user_alert,
        system_update_alert=dto.system_update_alert,
    )


def printer_dto_to_domain(dto: PrinterSettingsDTO) -> PrinterSettings:
    """تحويل PrinterSettingsDTO إلى PrinterSettings Domain"""
    return PrinterSettings(
        default_printer=dto.default_printer,
        paper_size=PaperSize(dto.paper_size),
        copies=dto.copies,
        print_duplex=dto.print_duplex,
        header_margin=dto.header_margin,
        footer_margin=dto.footer_margin,
        left_margin=dto.left_margin,
        right_margin=dto.right_margin,
        show_company_logo=dto.show_company_logo,
        show_company_info=dto.show_company_info,
        show_footer=dto.show_footer,
        footer_text=dto.footer_text,
    )


def backup_dto_to_domain(dto: BackupSettingsDTO) -> BackupSettings:
    """تحويل BackupSettingsDTO إلى BackupSettings Domain"""
    return BackupSettings(
        auto_backup_enabled=dto.auto_backup_enabled,
        backup_interval_hours=dto.backup_interval_hours,
        backup_retention_days=dto.backup_retention_days,
        backup_path=dto.backup_path,
        backup_on_exit=dto.backup_on_exit,
        include_attachments=dto.include_attachments,
        compress_backup=dto.compress_backup,
        encrypt_backup=dto.encrypt_backup,
    )


# ========== Domain to DTO Converters ==========

def ui_domain_to_dto(ui: UiSettings) -> UiSettingsDTO:
    """تحويل UiSettings Domain إلى UiSettingsDTO"""
    return UiSettingsDTO(
        theme=ui.theme.value,
        language=ui.language.value,
        font_size=ui.font_size,
        font_family=ui.font_family,
        animations_enabled=ui.animations_enabled,
        animation_speed=ui.animation_speed,
        sidebar_collapsed=ui.sidebar_collapsed,
        recent_items_count=ui.recent_items_count,
        confirm_before_close=ui.confirm_before_close,
        show_tooltips=ui.show_tooltips,
        show_status_bar=ui.show_status_bar,
        auto_save_interval=ui.auto_save_interval,
    )


def invoicing_domain_to_dto(invoicing: InvoicingSettings) -> InvoicingSettingsDTO:
    """تحويل InvoicingSettings Domain إلى InvoicingSettingsDTO"""
    return InvoicingSettingsDTO(
        default_currency=invoicing.default_currency.value,
        default_payment_terms=invoicing.default_payment_terms,
        invoice_prefix=invoicing.invoice_prefix,
        invoice_number_length=invoicing.invoice_number_length,
        auto_generate_number=invoicing.auto_generate_number,
        require_customer=invoicing.require_customer,
        require_site=invoicing.require_site,
        show_tax=invoicing.show_tax,
        default_tax_rate=invoicing.default_tax_rate,
        allow_draft_edit=invoicing.allow_draft_edit,
        days_before_due=invoicing.days_before_due,
        invoice_notes_template=invoicing.invoice_notes_template,
    )


def purchasing_domain_to_dto(purchasing: PurchasingSettings) -> PurchasingSettingsDTO:
    """تحويل PurchasingSettings Domain إلى PurchasingSettingsDTO"""
    return PurchasingSettingsDTO(
        default_currency=purchasing.default_currency.value,
        default_payment_terms=purchasing.default_payment_terms,
        purchase_prefix=purchasing.purchase_prefix,
        purchase_number_length=purchasing.purchase_number_length,
        auto_generate_number=purchasing.auto_generate_number,
        require_supplier=purchasing.require_supplier,
        require_expected_delivery=purchasing.require_expected_delivery,
        auto_receive_on_post=purchasing.auto_receive_on_post,
    )


def product_domain_to_dto(products: ProductSettings) -> ProductSettingsDTO:
    """تحويل ProductSettings Domain إلى ProductSettingsDTO"""
    return ProductSettingsDTO(
        default_currency=products.default_currency.value,
        default_tax_rate=products.default_tax_rate,
        default_unit=products.default_unit,
        low_stock_threshold=products.low_stock_threshold,
        enable_batch_tracking=products.enable_batch_tracking,
        enable_serial_tracking=products.enable_serial_tracking,
        auto_generate_code=products.auto_generate_code,
        code_prefix=products.code_prefix,
        code_length=products.code_length,
    )


def customer_domain_to_dto(customers: CustomerSettings) -> CustomerSettingsDTO:
    """تحويل CustomerSettings Domain إلى CustomerSettingsDTO"""
    return CustomerSettingsDTO(
        default_currency=customers.default_currency.value,
        default_payment_terms=customers.default_payment_terms,
        auto_generate_code=customers.auto_generate_code,
        code_prefix=customers.code_prefix,
        code_length=customers.code_length,
        require_tax_number=customers.require_tax_number,
        default_credit_limit=customers.default_credit_limit,
        enable_credit_check=customers.enable_credit_check,
    )


def supplier_domain_to_dto(suppliers: SupplierSettings) -> SupplierSettingsDTO:
    """تحويل SupplierSettings Domain إلى SupplierSettingsDTO"""
    return SupplierSettingsDTO(
        default_currency=suppliers.default_currency.value,
        default_payment_terms=suppliers.default_payment_terms,
        auto_generate_code=suppliers.auto_generate_code,
        code_prefix=suppliers.code_prefix,
        code_length=suppliers.code_length,
        require_tax_number=suppliers.require_tax_number,
        default_credit_limit=suppliers.default_credit_limit,
    )


def user_domain_to_dto(users: UserSettings) -> UserSettingsDTO:
    """تحويل UserSettings Domain إلى UserSettingsDTO"""
    return UserSettingsDTO(
        session_timeout_minutes=users.session_timeout_minutes,
        max_login_attempts=users.max_login_attempts,
        lockout_minutes=users.lockout_minutes,
        require_strong_password=users.require_strong_password,
        password_min_length=users.password_min_length,
        enable_2fa=users.enable_2fa,
        audit_log_enabled=users.audit_log_enabled,
        max_sessions_per_user=users.max_sessions_per_user,
    )


def notification_domain_to_dto(notifications: NotificationSettings) -> NotificationSettingsDTO:
    """تحويل NotificationSettings Domain إلى NotificationSettingsDTO"""
    return NotificationSettingsDTO(
        enable_system_notifications=notifications.enable_system_notifications,
        enable_email_notifications=notifications.enable_email_notifications,
        enable_sound_notifications=notifications.enable_sound_notifications,
        notification_sound=notifications.notification_sound.value,
        email_smtp_server=notifications.email_smtp_server,
        email_smtp_port=notifications.email_smtp_port,
        email_username=notifications.email_username,
        email_password=notifications.email_password,
        email_from=notifications.email_from,
        low_stock_alert=notifications.low_stock_alert,
        overdue_invoice_alert=notifications.overdue_invoice_alert,
        new_user_alert=notifications.new_user_alert,
        system_update_alert=notifications.system_update_alert,
    )


def printer_domain_to_dto(printer: PrinterSettings) -> PrinterSettingsDTO:
    """تحويل PrinterSettings Domain إلى PrinterSettingsDTO"""
    return PrinterSettingsDTO(
        default_printer=printer.default_printer,
        paper_size=printer.paper_size.value,
        copies=printer.copies,
        print_duplex=printer.print_duplex,
        header_margin=printer.header_margin,
        footer_margin=printer.footer_margin,
        left_margin=printer.left_margin,
        right_margin=printer.right_margin,
        show_company_logo=printer.show_company_logo,
        show_company_info=printer.show_company_info,
        show_footer=printer.show_footer,
        footer_text=printer.footer_text,
    )


def backup_domain_to_dto(backup: BackupSettings) -> BackupSettingsDTO:
    """تحويل BackupSettings Domain إلى BackupSettingsDTO"""
    return BackupSettingsDTO(
        auto_backup_enabled=backup.auto_backup_enabled,
        backup_interval_hours=backup.backup_interval_hours,
        backup_retention_days=backup.backup_retention_days,
        backup_path=backup.backup_path,
        backup_on_exit=backup.backup_on_exit,
        include_attachments=backup.include_attachments,
        compress_backup=backup.compress_backup,
        encrypt_backup=backup.encrypt_backup,
    )


# ========== Settings Main Converters ==========

def settings_to_dto(settings: Settings) -> SettingsDTO:
    """
    تحويل كيان Settings Domain إلى SettingsDTO
    
    Args:
        settings: كيان الإعدادات من Domain Layer
    
    Returns:
        SettingsDTO: كائن نقل البيانات للإعدادات
    """
    if not settings:
        return None
    
    return SettingsDTO(
        ui=ui_domain_to_dto(settings.ui),
        invoicing=invoicing_domain_to_dto(settings.invoicing),
        purchasing=purchasing_domain_to_dto(settings.purchasing),
        products=product_domain_to_dto(settings.products),
        customers=customer_domain_to_dto(settings.customers),
        suppliers=supplier_domain_to_dto(settings.suppliers),
        users=user_domain_to_dto(settings.users),
        notifications=notification_domain_to_dto(settings.notifications),
        printer=printer_domain_to_dto(settings.printer),
        backup=backup_domain_to_dto(settings.backup),
        version=settings.version,
        updated_at=settings.updated_at,
        updated_by=settings.updated_by,
    )


def dto_to_settings(dto: SettingsDTO) -> Settings:
    """
    تحويل SettingsDTO إلى كيان Settings Domain
    
    Args:
        dto: كائن نقل البيانات للإعدادات
    
    Returns:
        Settings: كيان الإعدادات من Domain Layer
    """
    if not dto:
        return None
    
    return Settings(
        ui=ui_dto_to_domain(dto.ui),
        invoicing=invoicing_dto_to_domain(dto.invoicing),
        purchasing=purchasing_dto_to_domain(dto.purchasing),
        products=product_dto_to_domain(dto.products),
        customers=customer_dto_to_domain(dto.customers),
        suppliers=supplier_dto_to_domain(dto.suppliers),
        users=user_dto_to_domain(dto.users),
        notifications=notification_dto_to_domain(dto.notifications),
        printer=printer_dto_to_domain(dto.printer),
        backup=backup_dto_to_domain(dto.backup),
        version=dto.version,
        updated_at=dto.updated_at,
        updated_by=dto.updated_by,
    )


def settings_dict_to_dto(data: Dict[str, Any]) -> SettingsDTO:
    """
    تحويل قاموس البيانات إلى SettingsDTO
    
    Args:
        data: قاموس يحتوي على بيانات الإعدادات
    
    Returns:
        SettingsDTO: كائن نقل البيانات للإعدادات
    """
    if not data:
        return None
    
    ui_data = data.get('ui', {})
    invoicing_data = data.get('invoicing', {})
    purchasing_data = data.get('purchasing', {})
    products_data = data.get('products', {})
    customers_data = data.get('customers', {})
    suppliers_data = data.get('suppliers', {})
    users_data = data.get('users', {})
    notifications_data = data.get('notifications', {})
    printer_data = data.get('printer', {})
    backup_data = data.get('backup', {})
    
    return SettingsDTO(
        ui=UiSettingsDTO(
            theme=ui_data.get('theme', 'light'),
            language=ui_data.get('language', 'ar'),
            font_size=ui_data.get('font_size', 12),
            font_family=ui_data.get('font_family', 'Segoe UI'),
            animations_enabled=ui_data.get('animations_enabled', True),
            animation_speed=ui_data.get('animation_speed', 250),
            sidebar_collapsed=ui_data.get('sidebar_collapsed', False),
            recent_items_count=ui_data.get('recent_items_count', 10),
            confirm_before_close=ui_data.get('confirm_before_close', True),
            show_tooltips=ui_data.get('show_tooltips', True),
            show_status_bar=ui_data.get('show_status_bar', True),
            auto_save_interval=ui_data.get('auto_save_interval', 60),
        ),
        invoicing=InvoicingSettingsDTO(
            default_currency=invoicing_data.get('default_currency', 'USD'),
            default_payment_terms=invoicing_data.get('default_payment_terms', 'net_30'),
            invoice_prefix=invoicing_data.get('invoice_prefix', 'INV'),
            invoice_number_length=invoicing_data.get('invoice_number_length', 5),
            auto_generate_number=invoicing_data.get('auto_generate_number', True),
            require_customer=invoicing_data.get('require_customer', True),
            require_site=invoicing_data.get('require_site', False),
            show_tax=invoicing_data.get('show_tax', True),
            default_tax_rate=invoicing_data.get('default_tax_rate', 0.0),
            allow_draft_edit=invoicing_data.get('allow_draft_edit', True),
            days_before_due=invoicing_data.get('days_before_due', 30),
            invoice_notes_template=invoicing_data.get('invoice_notes_template', 'شكراً لتسوقكم معنا'),
        ),
        purchasing=PurchasingSettingsDTO(
            default_currency=purchasing_data.get('default_currency', 'USD'),
            default_payment_terms=purchasing_data.get('default_payment_terms', 'net_30'),
            purchase_prefix=purchasing_data.get('purchase_prefix', 'PO'),
            purchase_number_length=purchasing_data.get('purchase_number_length', 5),
            auto_generate_number=purchasing_data.get('auto_generate_number', True),
            require_supplier=purchasing_data.get('require_supplier', True),
            require_expected_delivery=purchasing_data.get('require_expected_delivery', False),
            auto_receive_on_post=purchasing_data.get('auto_receive_on_post', False),
        ),
        products=ProductSettingsDTO(
            default_currency=products_data.get('default_currency', 'USD'),
            default_tax_rate=products_data.get('default_tax_rate', 0.0),
            default_unit=products_data.get('default_unit', 'قطعة (pc)'),
            low_stock_threshold=products_data.get('low_stock_threshold', 10),
            enable_batch_tracking=products_data.get('enable_batch_tracking', False),
            enable_serial_tracking=products_data.get('enable_serial_tracking', False),
            auto_generate_code=products_data.get('auto_generate_code', True),
            code_prefix=products_data.get('code_prefix', 'P'),
            code_length=products_data.get('code_length', 5),
        ),
        customers=CustomerSettingsDTO(
            default_currency=customers_data.get('default_currency', 'USD'),
            default_payment_terms=customers_data.get('default_payment_terms', 'net_30'),
            auto_generate_code=customers_data.get('auto_generate_code', True),
            code_prefix=customers_data.get('code_prefix', 'C'),
            code_length=customers_data.get('code_length', 5),
            require_tax_number=customers_data.get('require_tax_number', False),
            default_credit_limit=customers_data.get('default_credit_limit', 0.0),
            enable_credit_check=customers_data.get('enable_credit_check', False),
        ),
        suppliers=SupplierSettingsDTO(
            default_currency=suppliers_data.get('default_currency', 'USD'),
            default_payment_terms=suppliers_data.get('default_payment_terms', 'net_30'),
            auto_generate_code=suppliers_data.get('auto_generate_code', True),
            code_prefix=suppliers_data.get('code_prefix', 'S'),
            code_length=suppliers_data.get('code_length', 5),
            require_tax_number=suppliers_data.get('require_tax_number', False),
            default_credit_limit=suppliers_data.get('default_credit_limit', 0.0),
        ),
        users=UserSettingsDTO(
            session_timeout_minutes=users_data.get('session_timeout_minutes', 30),
            max_login_attempts=users_data.get('max_login_attempts', 5),
            lockout_minutes=users_data.get('lockout_minutes', 15),
            require_strong_password=users_data.get('require_strong_password', True),
            password_min_length=users_data.get('password_min_length', 8),
            enable_2fa=users_data.get('enable_2fa', False),
            audit_log_enabled=users_data.get('audit_log_enabled', True),
            max_sessions_per_user=users_data.get('max_sessions_per_user', 3),
        ),
        notifications=NotificationSettingsDTO(
            enable_system_notifications=notifications_data.get('enable_system_notifications', True),
            enable_email_notifications=notifications_data.get('enable_email_notifications', False),
            enable_sound_notifications=notifications_data.get('enable_sound_notifications', True),
            notification_sound=notifications_data.get('notification_sound', 'default'),
            email_smtp_server=notifications_data.get('email_smtp_server', ''),
            email_smtp_port=notifications_data.get('email_smtp_port', 587),
            email_username=notifications_data.get('email_username', ''),
            email_password=notifications_data.get('email_password', ''),
            email_from=notifications_data.get('email_from', ''),
            low_stock_alert=notifications_data.get('low_stock_alert', True),
            overdue_invoice_alert=notifications_data.get('overdue_invoice_alert', True),
            new_user_alert=notifications_data.get('new_user_alert', True),
            system_update_alert=notifications_data.get('system_update_alert', True),
        ),
        printer=PrinterSettingsDTO(
            default_printer=printer_data.get('default_printer', ''),
            paper_size=printer_data.get('paper_size', 'A4'),
            copies=printer_data.get('copies', 1),
            print_duplex=printer_data.get('print_duplex', False),
            header_margin=printer_data.get('header_margin', 20),
            footer_margin=printer_data.get('footer_margin', 20),
            left_margin=printer_data.get('left_margin', 15),
            right_margin=printer_data.get('right_margin', 15),
            show_company_logo=printer_data.get('show_company_logo', True),
            show_company_info=printer_data.get('show_company_info', True),
            show_footer=printer_data.get('show_footer', True),
            footer_text=printer_data.get('footer_text', 'شكراً لكم'),
        ),
        backup=BackupSettingsDTO(
            auto_backup_enabled=backup_data.get('auto_backup_enabled', False),
            backup_interval_hours=backup_data.get('backup_interval_hours', 24),
            backup_retention_days=backup_data.get('backup_retention_days', 30),
            backup_path=backup_data.get('backup_path', './backups'),
            backup_on_exit=backup_data.get('backup_on_exit', True),
            include_attachments=backup_data.get('include_attachments', True),
            compress_backup=backup_data.get('compress_backup', True),
            encrypt_backup=backup_data.get('encrypt_backup', False),
        ),
        version=data.get('version', 1),
        updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
        updated_by=data.get('updated_by', 'system'),
    )


__all__ = [
    # DTO to Domain
    "ui_dto_to_domain",
    "invoicing_dto_to_domain",
    "purchasing_dto_to_domain",
    "product_dto_to_domain",
    "customer_dto_to_domain",
    "supplier_dto_to_domain",
    "user_dto_to_domain",
    "notification_dto_to_domain",
    "printer_dto_to_domain",
    "backup_dto_to_domain",
    # Domain to DTO
    "ui_domain_to_dto",
    "invoicing_domain_to_dto",
    "purchasing_domain_to_dto",
    "product_domain_to_dto",
    "customer_domain_to_dto",
    "supplier_domain_to_dto",
    "user_domain_to_dto",
    "notification_domain_to_dto",
    "printer_domain_to_dto",
    "backup_domain_to_dto",
    # Main Converters
    "settings_to_dto",
    "dto_to_settings",
    "settings_dict_to_dto",
]