# core/application/handlers/settings/get_ui_settings_query_handler.py
"""
Get UI Settings Query Handler - استعلام جلب إعدادات واجهة المستخدم
"""

from typing import Optional, Dict, Any

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseQueryHandler
from core.application.settings.commands import GetUiSettingsQuery


def _safe_get_value(obj):
    """الحصول على القيمة بأمان"""
    if obj is None:
        return None
    if hasattr(obj, 'value'):
        return obj.value
    return obj


class GetUiSettingsQueryHandler(BaseQueryHandler[GetUiSettingsQuery, Optional[Dict[str, Any]]]):
    """
    معالج استعلام جلب إعدادات واجهة المستخدم
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def handle(self, query: GetUiSettingsQuery) -> Optional[Dict[str, Any]]:
        """
        تنفيذ جلب إعدادات واجهة المستخدم
        
        Args:
            query: استعلام جلب إعدادات واجهة المستخدم
        
        Returns:
            Optional[Dict[str, Any]]: بيانات إعدادات واجهة المستخدم أو None
        """
        with self._uow:
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