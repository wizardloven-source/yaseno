# core/application/handlers/settings/get_settings_handler.py
"""Get Settings Handler - استعلام جلب الإعدادات"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

from core.domain.accounting.interfaces import IUnitOfWork
from core.infrastructure.db.postgres.settings_repository import PostgresSettingsRepository


@dataclass(frozen=True)
class GetSettingsQuery:
    """استعلام لجلب جميع الإعدادات"""
    pass


@dataclass(frozen=True)
class GetUiSettingsQuery:
    """استعلام لجلب إعدادات واجهة المستخدم"""
    pass


def _safe_get_value(obj):
    """الحصول على القيمة بأمان - سواء كانت نصاً أو كائن Enum"""
    if obj is None:
        return None
    if hasattr(obj, 'value'):
        return obj.value
    return obj


class GetSettingsHandler:
    """معالج جلب جميع الإعدادات"""
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    def handle(self, query: GetSettingsQuery) -> Optional[Dict[str, Any]]:
        """جلب جميع الإعدادات"""
        settings = self._uow.settings.get()
        if not settings:
            return None
        
        # ✅ استخدام _safe_get_value لجميع القيم التي قد تكون Enum
        return {
            'ui': {
                'theme': _safe_get_value(settings.ui.theme),
                'language': _safe_get_value(settings.ui.language),
                'font_size': settings.ui.font_size,
                'font_family': settings.ui.font_family,
                'animations_enabled': settings.ui.animations_enabled,
                'animation_speed': settings.ui.animation_speed,
                'sidebar_collapsed': settings.ui.sidebar_collapsed,
                'recent_items_count': settings.ui.recent_items_count,
                'confirm_before_close': settings.ui.confirm_before_close,
                'show_tooltips': settings.ui.show_tooltips,
                'show_status_bar': settings.ui.show_status_bar,
                'auto_save_interval': settings.ui.auto_save_interval,
            },
            'invoicing': {
                'default_currency': _safe_get_value(settings.invoicing.default_currency),
                'default_payment_terms': settings.invoicing.default_payment_terms,
                'invoice_prefix': settings.invoicing.invoice_prefix,
                'invoice_number_length': settings.invoicing.invoice_number_length,
                'auto_generate_number': settings.invoicing.auto_generate_number,
                'require_customer': settings.invoicing.require_customer,
                'require_site': settings.invoicing.require_site,
                'show_tax': settings.invoicing.show_tax,
                'default_tax_rate': settings.invoicing.default_tax_rate,
                'allow_draft_edit': settings.invoicing.allow_draft_edit,
                'days_before_due': settings.invoicing.days_before_due,
                'invoice_notes_template': settings.invoicing.invoice_notes_template,
            },
            'purchasing': {
                'default_currency': _safe_get_value(settings.purchasing.default_currency),
                'default_payment_terms': settings.purchasing.default_payment_terms,
                'purchase_prefix': settings.purchasing.purchase_prefix,
                'purchase_number_length': settings.purchasing.purchase_number_length,
                'auto_generate_number': settings.purchasing.auto_generate_number,
                'require_supplier': settings.purchasing.require_supplier,
                'require_expected_delivery': settings.purchasing.require_expected_delivery,
                'auto_receive_on_post': settings.purchasing.auto_receive_on_post,
            },
            'products': {
                'default_currency': _safe_get_value(settings.products.default_currency),
                'default_tax_rate': settings.products.default_tax_rate,
                'default_unit': settings.products.default_unit,
                'low_stock_threshold': settings.products.low_stock_threshold,
                'enable_batch_tracking': settings.products.enable_batch_tracking,
                'enable_serial_tracking': settings.products.enable_serial_tracking,
                'auto_generate_code': settings.products.auto_generate_code,
                'code_prefix': settings.products.code_prefix,
                'code_length': settings.products.code_length,
            },
            'customers': {
                'default_currency': _safe_get_value(settings.customers.default_currency),
                'default_payment_terms': settings.customers.default_payment_terms,
                'auto_generate_code': settings.customers.auto_generate_code,
                'code_prefix': settings.customers.code_prefix,
                'code_length': settings.customers.code_length,
                'require_tax_number': settings.customers.require_tax_number,
                'default_credit_limit': settings.customers.default_credit_limit,
                'enable_credit_check': settings.customers.enable_credit_check,
            },
            'suppliers': {
                'default_currency': _safe_get_value(settings.suppliers.default_currency),
                'default_payment_terms': settings.suppliers.default_payment_terms,
                'auto_generate_code': settings.suppliers.auto_generate_code,
                'code_prefix': settings.suppliers.code_prefix,
                'code_length': settings.suppliers.code_length,
                'require_tax_number': settings.suppliers.require_tax_number,
                'default_credit_limit': settings.suppliers.default_credit_limit,
            },
            'users': {
                'session_timeout_minutes': settings.users.session_timeout_minutes,
                'max_login_attempts': settings.users.max_login_attempts,
                'lockout_minutes': settings.users.lockout_minutes,
                'require_strong_password': settings.users.require_strong_password,
                'password_min_length': settings.users.password_min_length,
                'enable_2fa': settings.users.enable_2fa,
                'audit_log_enabled': settings.users.audit_log_enabled,
                'max_sessions_per_user': settings.users.max_sessions_per_user,
            },
            'notifications': {
                'enable_system_notifications': settings.notifications.enable_system_notifications,
                'enable_email_notifications': settings.notifications.enable_email_notifications,
                'enable_sound_notifications': settings.notifications.enable_sound_notifications,
                'notification_sound': _safe_get_value(settings.notifications.notification_sound),  # ✅ إصلاح
                'email_smtp_server': settings.notifications.email_smtp_server,
                'email_smtp_port': settings.notifications.email_smtp_port,
                'email_username': settings.notifications.email_username,
                'email_password': settings.notifications.email_password,
                'email_from': settings.notifications.email_from,
                'low_stock_alert': settings.notifications.low_stock_alert,
                'overdue_invoice_alert': settings.notifications.overdue_invoice_alert,
                'new_user_alert': settings.notifications.new_user_alert,
                'system_update_alert': settings.notifications.system_update_alert,
            },
            'printer': {
                'default_printer': settings.printer.default_printer,
                'paper_size': _safe_get_value(settings.printer.paper_size),
                'copies': settings.printer.copies,
                'print_duplex': settings.printer.print_duplex,
                'header_margin': settings.printer.header_margin,
                'footer_margin': settings.printer.footer_margin,
                'left_margin': settings.printer.left_margin,
                'right_margin': settings.printer.right_margin,
                'show_company_logo': settings.printer.show_company_logo,
                'show_company_info': settings.printer.show_company_info,
                'show_footer': settings.printer.show_footer,
                'footer_text': settings.printer.footer_text,
            },
            'backup': {
                'auto_backup_enabled': settings.backup.auto_backup_enabled,
                'backup_interval_hours': settings.backup.backup_interval_hours,
                'backup_retention_days': settings.backup.backup_retention_days,
                'backup_path': settings.backup.backup_path,
                'backup_on_exit': settings.backup.backup_on_exit,
                'include_attachments': settings.backup.include_attachments,
                'compress_backup': settings.backup.compress_backup,
                'encrypt_backup': settings.backup.encrypt_backup,
            },
            'version': settings.version,
            'updated_at': settings.updated_at.isoformat() if settings.updated_at else None,
            'updated_by': settings.updated_by,
        }


class GetUiSettingsHandler:
    """معالج جلب إعدادات واجهة المستخدم"""
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    def handle(self, query: GetUiSettingsQuery) -> Optional[Dict[str, Any]]:
        """جلب إعدادات واجهة المستخدم"""
        settings = self._uow.settings.get()
        if not settings:
            return None
        
        return {
            'theme': _safe_get_value(settings.ui.theme),
            'language': _safe_get_value(settings.ui.language),
            'font_size': settings.ui.font_size,
            'font_family': settings.ui.font_family,
            'animations_enabled': settings.ui.animations_enabled,
            'animation_speed': settings.ui.animation_speed,
            'sidebar_collapsed': settings.ui.sidebar_collapsed,
            'recent_items_count': settings.ui.recent_items_count,
            'confirm_before_close': settings.ui.confirm_before_close,
            'show_tooltips': settings.ui.show_tooltips,
            'show_status_bar': settings.ui.show_status_bar,
            'auto_save_interval': settings.ui.auto_save_interval,
        }