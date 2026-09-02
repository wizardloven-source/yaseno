# core/i18n/translator.py - PySide6

"""
نظام الترجمة المتكامل - يدعم JSON و Qt .qm files
الإصدار: 2.0.0 - PySide6
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from functools import lru_cache
from datetime import datetime
import logging

# ✅ استيراد PySide6 بدلاً من PyQt6
from PySide6.QtCore import QTranslator, QCoreApplication, QLocale, QObject, Signal, Qt
from PySide6.QtWidgets import QApplication, QWidget, QMainWindow

# إعداد تسجيل الأخطاء
logger = logging.getLogger(__name__)

# ✅ ثابت يمثل النص الذي سيظهر بدلاً من المفتاح المفقود
MISSING_TRANSLATION_MARKER = "🔴 MISSING: {key} 🔴"


@dataclass
class LanguageInfo:
    """معلومات اللغة"""
    code: str
    name: str
    native_name: str
    flag: str
    direction: str = "ltr"
    
    def __str__(self):
        return f"{self.flag} {self.native_name}"


# اللغات المدعومة
SUPPORTED_LANGUAGES = {
    "ar": LanguageInfo("ar", "Arabic", "العربية", "🇸🇦", "rtl"),
    "en": LanguageInfo("en", "English", "English", "🇺🇸", "ltr"),
    "fr": LanguageInfo("fr", "French", "Français", "🇫🇷", "ltr"),
}


class TranslationManager(QObject):
    """
    مدير الترجمة المركزي - النسخة الاحترافية
    
    Signals:
        language_changed: عند تغيير اللغة (رمز اللغة الجديد)
        translation_updated: عند تحديث الترجمة
        missing_key_detected: عند اكتشاف مفتاح مفقود (لأغراض التطوير)
    """
    
    # ✅ PySide6 Signal
    language_changed = Signal(str)
    translation_updated = Signal()
    missing_key_detected = Signal(str, str)
    
    _instance: Optional['TranslationManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        
        self._current_language: str = "ar"
        self._translations: Dict[str, Dict[str, str]] = {}
        self._qt_translator: Optional[QTranslator] = None
        self._listeners: List[Callable[[str], None]] = []
        self._tr_cache: Dict[str, str] = {}
        
        # إعدادات التطوير
        self._enable_missing_key_logging: bool = False
        self._missing_keys_log: Dict[str, List[str]] = {}
        
        # تحميل ملفات الترجمة
        self._load_all_translations()
        
        # تحميل اللغة المحفوظة
        self._load_saved_language()
        
        print(f"✅ TranslationManager initialized with language: {self._current_language}")
    
    def _get_locale_path(self) -> Path:
        """الحصول على مسار ملفات الترجمة"""
        base_path = Path(__file__).parent
        return base_path / "locale"
    
    def _load_all_translations(self):
        """تحميل جميع ملفات الترجمة"""
        locale_path = self._get_locale_path()
        
        for lang_code in SUPPORTED_LANGUAGES.keys():
            lang_file = locale_path / f"{lang_code}.json"
            
            if lang_file.exists():
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._translations[lang_code] = self._flatten_dict(data)
                    print(f"✅ Loaded translations: {lang_code}")
                except Exception as e:
                    print(f"❌ Failed to load {lang_code}.json: {e}")
                    self._translations[lang_code] = {}
            else:
                print(f"⚠️ Translation file not found: {lang_file}")
                self._translations[lang_code] = self._get_default_translations(lang_code)
        
        # مسح الكاش
        self._tr_cache.clear()
    
    def _flatten_dict(self, d: Dict, parent_key: str = '') -> Dict[str, str]:
        """تحويل قاموس متداخل إلى قاموس مسطح"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def _get_default_translations(self, lang_code: str) -> Dict[str, str]:
        """الحصول على الترجمات الافتراضية (fallback)"""
        if lang_code == "ar":
            return self._get_default_arabic()
        elif lang_code == "en":
            return self._get_default_english()
        else:
            return self._get_default_english()
    
    def _get_default_arabic(self) -> Dict[str, str]:
        """الترجمات العربية الافتراضية"""
        return {
            "common.save": "حفظ",
            "common.cancel": "إلغاء",
            "common.delete": "حذف",
            "common.edit": "تعديل",
            "common.view": "عرض",
            "common.add": "إضافة",
            "common.search": "بحث",
            "common.loading": "جاري التحميل...",
            "common.error": "خطأ",
            "common.success": "نجاح",
            "common.ready": "جاهز",
            "common.processing": "جاري المعالجة...",
            "navigation.dashboard": "لوحة التحكم",
            "navigation.invoices": "الفواتير",
            "navigation.products": "المنتجات",
            "navigation.customers": "العملاء",
            "navigation.suppliers": "الموردين",
            "navigation.settings": "الإعدادات",
        }
    
    def _get_default_english(self) -> Dict[str, str]:
        """الترجمات الإنجليزية الافتراضية"""
        return {
            "common.save": "Save",
            "common.cancel": "Cancel",
            "common.delete": "Delete",
            "common.edit": "Edit",
            "common.view": "View",
            "common.add": "Add",
            "common.search": "Search",
            "common.loading": "Loading...",
            "common.error": "Error",
            "common.success": "Success",
            "common.ready": "Ready",
            "common.processing": "Processing...",
            "navigation.dashboard": "Dashboard",
            "navigation.invoices": "Invoices",
            "navigation.products": "Products",
            "navigation.customers": "Customers",
            "navigation.suppliers": "Suppliers",
            "navigation.settings": "Settings",
        }
    
    def _load_saved_language(self):
        """تحميل اللغة المحفوظة"""
        try:
            from core.infrastructure.db.postgres.settings_repository import SettingsRepository
            repo = SettingsRepository()
            saved_lang = repo.get("app_language", "ar")
            if saved_lang in SUPPORTED_LANGUAGES:
                self._current_language = saved_lang
        except Exception as e:
            print(f"⚠️ Could not load saved language: {e}")
    
    def _save_language(self, lang_code: str):
        """حفظ اللغة المختارة"""
        try:
            from core.infrastructure.db.postgres.settings_repository import SettingsRepository
            repo = SettingsRepository()
            repo.set("app_language", lang_code)
        except Exception as e:
            print(f"⚠️ Could not save language: {e}")
    
    def tr(self, key: str, **kwargs) -> str:
        """ترجمة مفتاح إلى النص الحالي"""
        cache_key = f"{self._current_language}:{key}"
        if cache_key in self._tr_cache:
            text = self._tr_cache[cache_key]
        else:
            lang_dict = self._translations.get(self._current_language, {})
            
            if key in lang_dict:
                text = lang_dict[key]
            elif key in self._translations.get("en", {}):
                text = self._translations["en"][key]
                self._log_missing_key(key)
            elif key in self._translations.get("ar", {}):
                text = self._translations["ar"][key]
                self._log_missing_key(key)
            else:
                text = MISSING_TRANSLATION_MARKER.format(key=key)
                self._log_missing_key(key)
                self.missing_key_detected.emit(self._current_language, key)
            
            self._tr_cache[cache_key] = text
        
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError:
                pass
        
        return text
    
    def _log_missing_key(self, key: str):
        """تسجيل المفتاح المفقود"""
        if not self._enable_missing_key_logging:
            return
        
        if self._current_language not in self._missing_keys_log:
            self._missing_keys_log[self._current_language] = []
        
        if key not in self._missing_keys_log[self._current_language]:
            self._missing_keys_log[self._current_language].append(key)
            logger.warning(f"Missing translation key: '{key}' for language '{self._current_language}'")
    
    def get_missing_keys_report(self) -> Dict[str, List[str]]:
        return self._missing_keys_log.copy()
    
    def enable_missing_key_logging(self, enabled: bool = True):
        self._enable_missing_key_logging = enabled
        if not enabled:
            self._missing_keys_log.clear()
    
    def get_language(self) -> str:
        return self._current_language
    
    def get_language_info(self) -> LanguageInfo:
        return SUPPORTED_LANGUAGES.get(self._current_language, SUPPORTED_LANGUAGES["ar"])
    
    def get_all_languages(self) -> List[LanguageInfo]:
        return list(SUPPORTED_LANGUAGES.values())
    
    def set_language(self, lang_code: str, apply_to_ui: bool = True) -> bool:
        if lang_code not in SUPPORTED_LANGUAGES:
            print(f"❌ Language {lang_code} not supported")
            return False
        
        if self._current_language == lang_code:
            return True
        
        old_lang = self._current_language
        self._current_language = lang_code
        
        self._tr_cache.clear()
        self._save_language(lang_code)
        
        print(f"✅ Language changed: {old_lang} -> {lang_code}")
        
        self.language_changed.emit(lang_code)
        self.translation_updated.emit()
        
        for listener in self._listeners:
            try:
                listener(lang_code)
            except Exception as e:
                print(f"Error in language listener: {e}")
        
        if apply_to_ui:
            self._apply_to_ui()
        
        return True
    
    def _apply_to_ui(self):
        """تطبيق اللغة على جميع عناصر الواجهة"""
        app = QApplication.instance()
        if not app:
            return
        
        for widget in app.topLevelWidgets():
            self._update_widget_language(widget)
        
        self._update_layout_direction()
        print("✅ Applied language to UI")
    
    def _update_widget_language(self, widget: QWidget):
        if hasattr(widget, 'retranslate_ui'):
            try:
                widget.retranslate_ui()
            except Exception as e:
                print(f"Error retranslating {widget}: {e}")
        
        for child in widget.findChildren(QWidget):
            if hasattr(child, 'retranslate_ui'):
                try:
                    child.retranslate_ui()
                except Exception:
                    pass
    
    def _update_layout_direction(self):
        app = QApplication.instance()
        if not app:
            return
        
        lang_info = self.get_language_info()
        is_rtl = lang_info.direction == "rtl"
        
        if is_rtl:
            app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        else:
            app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        
        for widget in app.topLevelWidgets():
            if is_rtl:
                widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            else:
                widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    
    def add_listener(self, callback: Callable[[str], None]):
        if callback not in self._listeners:
            self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[str], None]):
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def reload_translations(self):
        self._load_all_translations()
        self.translation_updated.emit()
    
    def clear_cache(self):
        self._tr_cache.clear()
    
    @staticmethod
    def instance() -> 'TranslationManager':
        return TranslationManager()


# دالة مساعدة للوصول السريع
_translator: Optional[TranslationManager] = None


def tr(key: str, **kwargs) -> str:
    """دالة مساعدة للترجمة السريعة"""
    global _translator
    if _translator is None:
        _translator = TranslationManager.instance()
    return _translator.tr(key, **kwargs)


def get_translator() -> TranslationManager:
    """الحصول على مدير الترجمة"""
    global _translator
    if _translator is None:
        _translator = TranslationManager.instance()
    return _translator