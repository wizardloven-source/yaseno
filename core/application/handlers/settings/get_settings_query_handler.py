# core/application/handlers/settings/get_settings_query_handler.py
"""
Get Settings Query Handler - استعلام جلب جميع الإعدادات
"""

from typing import Optional, Dict, Any

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.settings.commands import GetSettingsQuery


def _safe_get_value(obj):
    """الحصول على القيمة بأمان - سواء كانت نصاً أو كائن Enum"""
    if obj is None:
        return None
    if hasattr(obj, 'value'):
        return obj.value
    return obj


class GetSettingsQueryHandler(BaseQueryHandler[GetSettingsQuery, Optional[Dict[str, Any]]]):
    """
    معالج استعلام جلب جميع الإعدادات
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def handle(self, query: GetSettingsQuery) -> Optional[Dict[str, Any]]:
        """
        تنفيذ جلب جميع الإعدادات
        
        Args:
            query: استعلام جلب جميع الإعدادات
        
        Returns:
            Optional[Dict[str, Any]]: بيانات الإعدادات أو None
        """
        with self._uow:
            settings = self._uow.settings.get()

            if not settings:
                return None

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
                # ... باقي الفئات
                'version': settings.version,
                'updated_at': settings.updated_at.isoformat() if settings.updated_at else None,
                'updated_by': settings.updated_by,
            }