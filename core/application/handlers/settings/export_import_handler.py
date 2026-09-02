# core/application/handlers/settings/export_import_handler.py
"""
Export/Import Settings Handlers - معالجات تصدير واستيراد الإعدادات
"""

import json
from typing import Dict, Any
from datetime import datetime, timezone

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.security.authorization import UserContext, require_permission, Permission


class ExportSettingsHandler:
    """
    معالج تصدير الإعدادات
    """

    def __init__(self, uow: IUnitOfWork):
        self._uow = uow

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext) -> Dict[str, Any]:
        """
        تنفيذ تصدير الإعدادات
        
        Args:
            command: أمر تصدير الإعدادات
            user_context: سياق المستخدم
        
        Returns:
            Dict[str, Any]: بيانات الإعدادات المصدرة
        """
        with self._uow:
            settings = self._uow.settings.get()

            if not settings:
                return {
                    "success": False,
                    "message": "No settings found to export"
                }

            export_data = {
                "version": settings.version,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "exported_by": user_context.user_id,
                "settings": settings.to_dict()
            }

            return {
                "success": True,
                "data": export_data,
                "message": "Settings exported successfully"
            }


class ImportSettingsHandler:
    """
    معالج استيراد الإعدادات
    """

    def __init__(self, uow: IUnitOfWork):
        self._uow = uow

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command, user_context: UserContext) -> Dict[str, Any]:
        """
        تنفيذ استيراد الإعدادات
        
        Args:
            command: أمر استيراد الإعدادات
            user_context: سياق المستخدم
        
        Returns:
            Dict[str, Any]: نتيجة العملية
        """
        with self._uow:
            settings = self._uow.settings.get()

            if not settings:
                settings = Settings()
                settings.created_by = user_context.user_id

            # استيراد البيانات
            import_data = command.data
            settings_data = import_data.get('settings', {})

            # تحديث الإعدادات من البيانات المستوردة
            settings = self._import_settings(settings, settings_data)

            settings.updated_by = user_context.user_id
            settings.updated_at = datetime.now(timezone.utc)
            settings.version += 1

            self._uow.settings.save(settings)
            self._uow.commit()

            return {
                "success": True,
                "message": "Settings imported successfully",
                "version": settings.version
            }

    def _import_settings(self, settings, data: Dict) -> Any:
        """استيراد البيانات إلى كائن الإعدادات"""
        # تنفيذ استيراد كل فئة
        # ...
        return settings