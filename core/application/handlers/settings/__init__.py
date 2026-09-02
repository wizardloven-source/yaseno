# core/application/handlers/settings/__init__.py
"""Settings Handlers Module"""

from core.application.settings.commands import (
    UpdateUiSettingsCommand,
    GetSettingsQuery,
    GetUiSettingsQuery,
)

from .get_settings_handler import GetSettingsHandler, GetUiSettingsHandler
from .update_settings_handler import UpdateUiSettingsHandler, UpdateSettingsHandler

# ✅ إضافة المعالجات المفقودة
from .export_import_handler import ExportSettingsHandler, ImportSettingsHandler
from .get_settings_query_handler import GetSettingsQueryHandler
from .get_ui_settings_query_handler import GetUiSettingsQueryHandler

__all__ = [
    # Commands
    "UpdateUiSettingsCommand",
    "GetSettingsQuery",
    "GetUiSettingsQuery",
    # Handlers
    "GetSettingsHandler",
    "GetUiSettingsHandler",
    "UpdateUiSettingsHandler",
    "UpdateSettingsHandler",
    # ✅ إضافة المعالجات الجديدة
    "ExportSettingsHandler",
    "ImportSettingsHandler",
    "GetSettingsQueryHandler",
    "GetUiSettingsQueryHandler",
]