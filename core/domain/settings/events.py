# core/domain/settings/events.py
"""
Domain Events for Settings
أحداث الإعدادات - تمكن من تحديث واجهات المستخدم تلقائياً
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import Theme, Language, Currency


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SettingChangedEvent(BaseDomainEvent):
    """حدث تغيير إعداد واحد - تبث فوراً لتحديث الواجهات"""
    setting_path: str
    old_value: Any
    new_value: Any
    changed_by: str
    category: str  # ui, accounting, invoicing, etc.
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "settings.setting.changed"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "setting_path": self.setting_path,
            "old_value": str(self.old_value),
            "new_value": str(self.new_value),
            "changed_by": self.changed_by,
            "category": self.category,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class SettingGroupChangedEvent(BaseDomainEvent):
    """حدث تغيير مجموعة إعدادات كاملة"""
    group: str
    settings: Dict[str, Any]
    changed_by: str
    changed_count: int
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "settings.group.changed"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "group": self.group,
            "changed_count": self.changed_count,
            "changed_by": self.changed_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class ThemeChangedEvent(BaseDomainEvent):
    """حدث تغيير الثيم - لتحديث جميع النوافذ فوراً"""
    old_theme: Theme
    new_theme: Theme
    changed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "settings.theme.changed"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "old_theme": self.old_theme.value,
            "new_theme": self.new_theme.value,
            "changed_by": self.changed_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class LanguageChangedEvent(BaseDomainEvent):
    """حدث تغيير اللغة - لإعادة الترجمة"""
    old_language: Language
    new_language: Language
    changed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "settings.language.changed"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "old_language": self.old_language.value,
            "new_language": self.new_language.value,
            "changed_by": self.changed_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class CurrencyChangedEvent(BaseDomainEvent):
    """حدث تغيير العملة الافتراضية"""
    old_currency: Currency
    new_currency: Currency
    changed_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "settings.currency.changed"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "old_currency": self.old_currency.value,
            "new_currency": self.new_currency.value,
            "changed_by": self.changed_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class SettingsImportedEvent(BaseDomainEvent):
    """حدث استيراد الإعدادات"""
    imported_by: str
    settings_count: int
    overwrite: bool
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "settings.imported"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "imported_by": self.imported_by,
            "settings_count": self.settings_count,
            "overwrite": self.overwrite,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class SettingsExportedEvent(BaseDomainEvent):
    """حدث تصدير الإعدادات"""
    exported_by: str
    settings_count: int
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "settings.exported"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "exported_by": self.exported_by,
            "settings_count": self.settings_count,
            "occurred_at": self.occurred_at.isoformat()
        }