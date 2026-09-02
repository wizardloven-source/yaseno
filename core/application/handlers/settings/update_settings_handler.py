# core/application/handlers/settings/update_settings_handler.py
"""
Update Settings Handler - معالج تحديث الإعدادات مع بث الأحداث
"""

from typing import Dict, Any
from datetime import datetime, timezone

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.settings.value_objects import UiSettings, Theme, Language
from core.domain.settings.aggregates import Settings
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.settings.commands import UpdateUiSettingsCommand, UpdateAllSettingsCommand


# =============================================================================
# UpdateUiSettingsHandler - معالج تحديث إعدادات واجهة المستخدم
# =============================================================================

class UpdateUiSettingsHandler:
    """
    معالج تحديث إعدادات واجهة المستخدم
    ✅ محدث: يبث أحداثاً فورية لتحديث جميع النوافذ
    """
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: UpdateUiSettingsCommand, user_context: UserContext) -> Dict[str, Any]:
        with self._uow:
            # الحصول على الإعدادات الحالية
            settings = self._uow.settings.get()
            
            if not settings:
                settings = Settings()
            
            # تتبع التغييرات
            changes = {}
            
            # إنشاء إعدادات UI جديدة
            new_ui = UiSettings(
                theme=Theme(command.theme) if command.theme else settings.ui.theme,
                language=Language(command.language) if command.language else settings.ui.language,
                font_size=command.font_size if command.font_size is not None else settings.ui.font_size,
                font_family=command.font_family if command.font_family is not None else settings.ui.font_family,
                animations_enabled=command.animations_enabled if command.animations_enabled is not None else settings.ui.animations_enabled,
                animation_speed=command.animation_speed if command.animation_speed is not None else settings.ui.animation_speed,
                sidebar_collapsed=command.sidebar_collapsed if command.sidebar_collapsed is not None else settings.ui.sidebar_collapsed,
                recent_items_count=command.recent_items_count if command.recent_items_count is not None else settings.ui.recent_items_count,
                confirm_before_close=command.confirm_before_close if command.confirm_before_close is not None else settings.ui.confirm_before_close,
                show_tooltips=command.show_tooltips if command.show_tooltips is not None else settings.ui.show_tooltips,
                show_status_bar=command.show_status_bar if command.show_status_bar is not None else settings.ui.show_status_bar,
                auto_save_interval=command.auto_save_interval if command.auto_save_interval is not None else settings.ui.auto_save_interval,
            )
            
            # التحقق مما إذا تغير شيء
            if new_ui != settings.ui:
                # تسجيل التغييرات قبل التحديث
                if new_ui.theme != settings.ui.theme:
                    changes['theme'] = {'old': settings.ui.theme.value, 'new': new_ui.theme.value}
                
                if new_ui.language != settings.ui.language:
                    changes['language'] = {'old': settings.ui.language.value, 'new': new_ui.language.value}
                
                if new_ui.font_size != settings.ui.font_size:
                    changes['font_size'] = {'old': settings.ui.font_size, 'new': new_ui.font_size}
                
                # تحديث الإعدادات
                settings.update_ui(new_ui, user_context.user_id)
                
                # حفظ في قاعدة البيانات
                self._uow.settings.save(settings)
                
                # جمع الأحداث لصرفها (سيتم صرفها تلقائياً عند commit)
                events = settings.pull_events()
                self._uow.collect_events(events)
                
                self._uow.commit()
                
                return {
                    'success': True,
                    'changed': True,
                    'changes': changes,
                    'version': settings.version,
                }
            
            return {
                'success': True,
                'changed': False,
                'message': 'No changes detected',
                'version': settings.version,
            }


# =============================================================================
# UpdateSettingsHandler - معالج تحديث جميع الإعدادات
# =============================================================================

class UpdateSettingsHandler:
    """
    معالج تحديث جميع الإعدادات
    """

    def __init__(self, uow: IUnitOfWork):
        self._uow = uow

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: UpdateAllSettingsCommand, user_context: UserContext) -> Dict[str, Any]:
        """
        تنفيذ تحديث جميع الإعدادات

        Args:
            command: أمر تحديث جميع الإعدادات
            user_context: سياق المستخدم

        Returns:
            Dict[str, Any]: نتيجة العملية
        """
        import dataclasses
        from enum import Enum

        with self._uow:
            settings = self._uow.settings.get()

            if not settings:
                settings = Settings()
                settings.created_by = user_context.user_id

            changes = {}

            def _coerce(field_type, value):
                if isinstance(value, field_type):
                    return value
                if isinstance(field_type, type) and issubclass(field_type, Enum):
                    return field_type(value)
                return value

            def _apply(current, data: Dict[str, Any]):
                fields = {f.name: f.type for f in dataclasses.fields(current)}
                kwargs = {}
                for k, v in data.items():
                    if k not in fields:
                        continue
                    ftype = fields[k]
                    args = getattr(ftype, '__args__', None)
                    if getattr(ftype, '__origin__', None) is not None and args:
                        ftype = args[0]
                    if not isinstance(ftype, type):
                        ftype = None
                    kwargs[k] = _coerce(ftype, v) if ftype else v
                return dataclasses.replace(current, **kwargs)

            # تحديث كل فئة
            if command.ui:
                new_ui = _apply(settings.ui, command.ui)
                if settings.update_ui(new_ui, user_context.user_id):
                    changes['ui'] = True
            if command.invoicing:
                new_inv = _apply(settings.invoicing, command.invoicing)
                if settings.update_invoicing(new_inv, user_context.user_id):
                    changes['invoicing'] = True
            for attr, key in [
                ('purchasing', 'purchasing'),
                ('products', 'products'),
                ('customers', 'customers'),
                ('suppliers', 'suppliers'),
                ('users', 'users'),
                ('notifications', 'notifications'),
                ('printer', 'printer'),
                ('backup', 'backup'),
            ]:
                data = getattr(command, key, None)
                if data:
                    new = _apply(getattr(settings, attr), data)
                    if new != getattr(settings, attr):
                        setattr(settings, attr, new)
                        changes[key] = True

            settings.updated_by = user_context.user_id
            settings.updated_at = datetime.now(timezone.utc)
            settings.version += 1

            self._uow.settings.save(settings)
            self._uow.commit()

            return {
                "success": True,
                "changed": len(changes) > 0,
                "changes": changes,
                "version": settings.version
            }