# core/themes/theme_manager.py
"""
Theme Manager - مدير الثيمات الرئيسي
✅ نسخة مصححة - تدعم استقبال النصوص أو الكائنات
"""

from typing import Dict, Optional, List, Union, Any
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QSettings, pyqtSignal, QObject

from .base_theme import BaseTheme
from .light_theme import LightTheme
from .dark_theme import DarkTheme


class ThemeManager(QObject):
    """
    مدير الثيمات - يدير الثيمات ويطبقها على التطبيق
    Theme Manager - Manages themes and applies them to the application
    """
    
    theme_changed = pyqtSignal(str)  # تم تغيير الثيم
    theme_applied = pyqtSignal()     # تم تطبيق الثيم
    
    _instance: Optional['ThemeManager'] = None
    
    def __new__(cls):
        """Singleton pattern - نمط المفرد"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """تهيئة مدير الثيمات - Initialize theme manager"""
        if self._initialized:
            return
        self._initialized = True
        super().__init__()
        
        self._themes: Dict[str, BaseTheme] = {}
        self._current_theme: Optional[BaseTheme] = None
        self._settings = QSettings("YAseenERP", "Themes")
        
        # تسجيل الثيمات الافتراضية
        self._register_default_themes()
        
        # تحميل الثيم المحفوظ
        self.load_saved_theme()
    
    def _normalize_theme_name(self, theme_input: Any) -> str:
        """
        تحويل اسم الثيم إلى نص آمن
        Normalize theme name to safe string
        
        ✅ يدعم: نص، كائن له خاصية value (Enum)، كائن له خاصية name
        
        المعاملات:
            theme_input: يمكن أن يكون نصاً أو كائناً
        
        العائد:
            str: اسم الثيم كنص
        """
        if theme_input is None:
            return "light"
        
        # إذا كان كائن له خاصية value (مثل Enum من Role أو Theme)
        if hasattr(theme_input, 'value'):
            return str(theme_input.value)
        
        # إذا كان كائن BaseTheme له خاصية name
        if hasattr(theme_input, 'name'):
            return str(theme_input.name)
        
        # إذا كان نصاً عادياً
        return str(theme_input)
    
    def _register_default_themes(self):
        """تسجيل الثيمات الافتراضية - Register default themes"""
        try:
            light_theme = LightTheme()
            dark_theme = DarkTheme()
            
            self.register_theme(light_theme, "light")
            self.register_theme(dark_theme, "dark")
            
            # تسجيل الثيم الحديث إذا كان موجوداً
            try:
                from .modern_theme import ModernTheme
                self.register_theme(ModernTheme(dark_mode=False), "modern_light")
                self.register_theme(ModernTheme(dark_mode=True), "modern_dark")
                self.register_theme(ModernTheme(dark_mode=False), "modern")
                print("✅ تم تسجيل الثيمات الحديثة - Modern themes registered")
            except ImportError as e:
                print(f"⚠️ ModernTheme غير متوفر - Not available: {e}")
            
            print(f"📋 الثيمات المسجلة - Registered themes: {list(self._themes.keys())}")
        except Exception as e:
            print(f"❌ خطأ في تسجيل الثيمات - Error registering themes: {e}")
    
    def register_theme(self, theme: BaseTheme, name: Optional[str] = None):
        """
        تسجيل ثيم جديد
        Register a new theme
        
        المعاملات:
            theme: كائن الثيم
            name: اسم الثيم (اختياري)
        """
        theme_name = name or theme.name
        self._themes[theme_name] = theme
        print(f"✅ تم تسجيل الثيم - Theme registered: {theme_name}")
    
    def unregister_theme(self, name: str) -> bool:
        """
        إلغاء تسجيل ثيم
        Unregister a theme
        
        المعاملات:
            name: اسم الثيم
        
        العائد:
            True إذا تم الإلغاء بنجاح
        """
        theme_name = self._normalize_theme_name(name)
        if theme_name in self._themes and theme_name not in ["light", "dark"]:
            del self._themes[theme_name]
            print(f"🗑️ تم إلغاء تسجيل الثيم - Theme unregistered: {theme_name}")
            return True
        return False
    
    def get_theme(self, name: Union[str, Any]) -> Optional[BaseTheme]:
        """
        الحصول على ثيم بواسطة اسمه
        Get theme by name
        
        ✅ يقبل نص أو كائن
        
        المعاملات:
            name: اسم الثيم (نص) أو كائن له خاصية value/name
        
        العائد:
            BaseTheme أو None
        """
        theme_name = self._normalize_theme_name(name)
        return self._themes.get(theme_name)
    
    def get_available_themes(self) -> List[BaseTheme]:
        """
        الحصول على قائمة الثيمات المتاحة
        Get list of available themes
        
        العائد:
            قائمة بكائنات الثيمات
        """
        return list(self._themes.values())
    
    def get_theme_names(self) -> List[str]:
        """
        الحصول على أسماء الثيمات المتاحة
        Get list of available theme names
        
        العائد:
            قائمة بأسماء الثيمات
        """
        return list(self._themes.keys())
    
    def get_current_theme(self) -> Optional[BaseTheme]:
        """
        الحصول على الثيم الحالي
        Get current theme
        
        العائد:
            كائن الثيم الحالي أو None
        """
        return self._current_theme
    
    def get_current_theme_name(self) -> str:
        """
        الحصول على اسم الثيم الحالي
        Get current theme name
        
        العائد:
            اسم الثيم الحالي
        """
        if self._current_theme:
            return self._current_theme.name
        return "light"
    
    def apply_theme(self, theme_input: Union[str, Any], widget: Optional[QWidget] = None) -> bool:
        """
        تطبيق ثيم على التطبيق
        Apply theme to application
        
        ✅ يقبل نص أو كائن (Enum, BaseTheme, إلخ)
        
        المعاملات:
            theme_input: اسم الثيم (نص) أو كائن له خاصية value/name
            widget: Widget محدد لتطبيق الثيم عليه (اختياري)
        
        العائد:
            bool: نجاح العملية
        """
        # تطبيع اسم الثيم
        theme_name = self._normalize_theme_name(theme_input)
        
        theme = self.get_theme(theme_name)
        if not theme:
            print(f"⚠️ الثيم {theme_name} غير موجود، استخدام الثيم الافتراضي 'light'")
            theme = self.get_theme("light")
            if not theme:
                print(f"❌ لا يوجد ثيم افتراضي - No default theme!")
                return False
        
        self._current_theme = theme
        stylesheet = theme.get_stylesheet()
        
        try:
            if widget:
                widget.setStyleSheet(stylesheet)
            else:
                app = QApplication.instance()
                if app:
                    app.setStyleSheet(stylesheet)
                else:
                    print("⚠️ لا يوجد تطبيق QApplication - No QApplication instance")
                    return False
            
            self._settings.setValue("current_theme", theme_name)
            self.theme_changed.emit(theme_name)
            self.theme_applied.emit()
            
            print(f"🎨 تم تطبيق الثيم - Theme applied: {theme_name}")
            return True
        except Exception as e:
            print(f"❌ خطأ في تطبيق الثيم - Error applying theme: {e}")
            return False
    
    def apply_theme_to_widget(self, widget: QWidget, theme_input: Optional[Union[str, Any]] = None) -> bool:
        """
        تطبيق ثيم على Widget معين
        Apply theme to specific widget
        
        المعاملات:
            widget: العنصر المراد تطبيق الثيم عليه
            theme_input: اسم الثيم (اختياري، يستخدم الثيم الحالي إذا لم يحدد)
        
        العائد:
            bool: نجاح العملية
        """
        theme_name = theme_input or self.get_current_theme_name()
        theme = self.get_theme(theme_name)
        if theme:
            widget.setStyleSheet(theme.get_stylesheet())
            return True
        return False
    
    def load_saved_theme(self):
        """تحميل الثيم المحفوظ - Load saved theme"""
        saved_theme = self._settings.value("current_theme", "light")
        # ✅ التحقق من وجود الثيم المحفوظ
        if saved_theme not in self._themes:
            print(f"⚠️ الثيم المحفوظ '{saved_theme}' غير موجود، استخدام 'light'")
            saved_theme = "light"
        
        self.apply_theme(saved_theme)
    
    def save_current_theme(self):
        """حفظ الثيم الحالي - Save current theme"""
        if self._current_theme:
            self._settings.setValue("current_theme", self._current_theme.name)
            print(f"💾 تم حفظ الثيم - Theme saved: {self._current_theme.name}")
    
    def toggle_theme(self):
        """تبديل بين الثيم الفاتح والداكن - Toggle between light and dark themes"""
        current_name = self.get_current_theme_name()
        
        # خريطة التبديل
        toggle_map = {
            "light": "dark",
            "dark": "light",
            "modern_light": "modern_dark",
            "modern_dark": "modern_light",
        }
        
        new_theme = toggle_map.get(current_name, "light")
        self.apply_theme(new_theme)
    
    def toggle_modern_theme(self):
        """تبديل بين الثيم الحديث الفاتح والداكن - Toggle between modern light and dark"""
        current_name = self.get_current_theme_name()
        
        if current_name == "modern_light":
            self.apply_theme("modern_dark")
        elif current_name == "modern_dark":
            self.apply_theme("modern_light")
        else:
            self.apply_theme("modern_light")
    
    def is_dark_mode(self) -> bool:
        """
        هل الثيم الحالي داكن؟
        Is current theme dark mode?
        
        العائد:
            True إذا كان داكن، False إذا كان فاتح
        """
        if self._current_theme:
            if hasattr(self._current_theme, 'is_dark_mode'):
                return self._current_theme.is_dark_mode()
            # الثيمات القديمة التي لا تحتوي على is_dark_mode
            return self._current_theme.name in ["dark", "modern_dark"]
        return False
    
    def is_light_mode(self) -> bool:
        """
        هل الثيم الحالي فاتح؟
        Is current theme light mode?
        
        العائد:
            True إذا كان فاتح، False إذا كان داكن
        """
        return not self.is_dark_mode()
    
    def get_color(self, color_name: str, fallback: Optional[str] = None) -> str:
        """
        الحصول على لون من الثيم الحالي
        Get color from current theme
        
        المعاملات:
            color_name: اسم اللون
            fallback: لون بديل
        
        العائد:
            قيمة اللون
        """
        if self._current_theme and hasattr(self._current_theme, color_name):
            return getattr(self._current_theme, color_name)
        return fallback or "#2563EB"
    
    def get_spacing(self, size: str) -> int:
        """
        الحصول على مسافة من الثيم الحالي
        Get spacing from current theme
        
        المعاملات:
            size: xs, sm, md, lg, xl, xxl, xxxl
        
        العائد:
            قيمة المسافة بالبكسل
        """
        if self._current_theme and hasattr(self._current_theme, 'spacing'):
            spacing_map = {
                "xs": self._current_theme.spacing.XS,
                "sm": self._current_theme.spacing.SM,
                "md": self._current_theme.spacing.MD,
                "lg": self._current_theme.spacing.LG,
                "xl": self._current_theme.spacing.XL,
                "xxl": self._current_theme.spacing.XXL,
                "xxxl": self._current_theme.spacing.XXXL,
            }
            return spacing_map.get(size.lower(), 8)
        return 8
    
    def get_padding(self, size: str) -> int:
        """
        الحصول على حشوة من الثيم الحالي
        Get padding from current theme
        
        المعاملات:
            size: xs, sm, md, lg, xl
        
        العائد:
            قيمة الحشوة بالبكسل
        """
        if self._current_theme:
            padding_map = {
                "xs": getattr(self._current_theme, 'padding_xs', 4),
                "sm": getattr(self._current_theme, 'padding_sm', 8),
                "md": getattr(self._current_theme, 'padding_md', 12),
                "lg": getattr(self._current_theme, 'padding_lg', 16),
                "xl": getattr(self._current_theme, 'padding_xl', 24),
            }
            return padding_map.get(size.lower(), 12)
        return 12
    
    def get_font_size(self, size: str) -> str:
        """
        الحصول على حجم خط من الثيم الحالي
        Get font size from current theme
        
        المعاملات:
            size: xs, sm, md, lg, xl, xxl, xxxl, huge
        
        العائد:
            حجم الخط كـ string مع px
        """
        if self._current_theme and hasattr(self._current_theme, 'typography'):
            font_sizes = {
                "xs": self._current_theme.typography.SIZE_XS,
                "sm": self._current_theme.typography.SIZE_SM,
                "md": self._current_theme.typography.SIZE_MD,
                "lg": self._current_theme.typography.SIZE_LG,
                "xl": self._current_theme.typography.SIZE_XL,
                "xxl": self._current_theme.typography.SIZE_XXL,
                "xxxl": self._current_theme.typography.SIZE_XXXL,
                "huge": self._current_theme.typography.SIZE_HUGE,
            }
            size_value = font_sizes.get(size.lower(), 12)
            return f"{size_value}px" if isinstance(size_value, int) else size_value
        return "12px"
    
    def get_border_radius(self, size: str) -> str:
        """
        الحصول على نصف قطر الزوايا من الثيم الحالي
        Get border radius from current theme
        
        المعاملات:
            size: none, sm, md, lg, xl, xxl, circle, pill
        
        العائد:
            نصف القطر كـ string مع px أو %
        """
        if self._current_theme and hasattr(self._current_theme, 'radius'):
            radii = {
                "none": self._current_theme.radius.NONE,
                "sm": self._current_theme.radius.SM,
                "md": self._current_theme.radius.MD,
                "lg": self._current_theme.radius.LG,
                "xl": self._current_theme.radius.XL,
                "xxl": self._current_theme.radius.XXL,
                "circle": self._current_theme.radius.CIRCLE,
                "pill": self._current_theme.radius.PILL,
            }
            value = radii.get(size.lower(), 8)
            if size == "circle":
                return "50%"
            return f"{value}px"
        return "8px"
    
    def reset_to_default(self):
        """إعادة تعيين الثيم إلى الافتراضي - Reset theme to default"""
        self.apply_theme("light")
    
    def refresh_current_theme(self):
        """تحديث الثيم الحالي - Refresh current theme"""
        if self._current_theme:
            self.apply_theme(self._current_theme.name)
    
    @staticmethod
    def instance() -> 'ThemeManager':
        """
        الحصول على النسخة الوحيدة من مدير الثيمات
        Get the singleton instance of theme manager
        
        العائد:
            نسخة ThemeManager
        """
        return ThemeManager()


# دالة مساعدة سريعة لتطبيق الثيم
def apply_theme(theme_name: str, widget: Optional[QWidget] = None) -> bool:
    """
    دالة مساعدة سريعة لتطبيق ثيم
    Quick helper function to apply theme
    
    المعاملات:
        theme_name: اسم الثيم
        widget: العنصر المراد تطبيق الثيم عليه
    
    العائد:
        bool: نجاح العملية
    """
    return ThemeManager.instance().apply_theme(theme_name, widget)


def get_current_theme() -> Optional[BaseTheme]:
    """
    الحصول على الثيم الحالي
    Get current theme
    
    العائد:
        كائن الثيم الحالي
    """
    return ThemeManager.instance().get_current_theme()


def is_dark_mode() -> bool:
    """
    التحقق من الوضع الداكن
    Check if dark mode is active
    
    العائد:
        True إذا كان الوضع الداكن نشطاً
    """
    return ThemeManager.instance().is_dark_mode()


# مثال للاستخدام
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Theme Manager Test - اختبار مدير الثيمات")
            self.setGeometry(100, 100, 500, 400)
            
            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            
            # معلومات الثيم الحالي
            self.info_label = QLabel()
            layout.addWidget(self.info_label)
            
            # أزرار التحكم
            btn_light = QPushButton("🌞 Light Theme - ثيم فاتح")
            btn_light.clicked.connect(lambda: ThemeManager.instance().apply_theme("light"))
            layout.addWidget(btn_light)
            
            btn_dark = QPushButton("🌙 Dark Theme - ثيم داكن")
            btn_dark.clicked.connect(lambda: ThemeManager.instance().apply_theme("dark"))
            layout.addWidget(btn_dark)
            
            btn_toggle = QPushButton("🔄 Toggle Theme - تبديل الثيم")
            btn_toggle.clicked.connect(lambda: ThemeManager.instance().toggle_theme())
            layout.addWidget(btn_toggle)
            
            btn_info = QPushButton("ℹ️ Show Info - عرض معلومات")
            btn_info.clicked.connect(self.show_info)
            layout.addWidget(btn_info)
            
            layout.addStretch()
            
            # تحديث المعلومات
            self.show_info()
            
            # الاتصال بإشارة تغيير الثيم
            ThemeManager.instance().theme_changed.connect(self.on_theme_changed)
        
        def show_info(self):
            manager = ThemeManager.instance()
            info = f"""
            <div style='text-align: center; padding: 10px;'>
                <h3>Theme Manager Info - معلومات مدير الثيمات</h3>
                <p>Current Theme - الثيم الحالي: <b>{manager.get_current_theme_name()}</b></p>
                <p>Dark Mode - الوضع الداكن: <b>{manager.is_dark_mode()}</b></p>
                <p>Available Themes - الثيمات المتاحة: <b>{', '.join(manager.get_theme_names())}</b></p>
                <p>Primary Color - اللون الأساسي: <b>{manager.get_color('primary')}</b></p>
                <p>Spacing MD - المسافة المتوسطة: <b>{manager.get_spacing('md')}px</b></p>
            </div>
            """
            self.info_label.setText(info)
        
        def on_theme_changed(self, theme_name):
            print(f"Theme changed to: {theme_name}")
            self.show_info()
    
    # إنشاء التطبيق
    app = QApplication(sys.argv)
    
    # تسجيل الثيمات (تتم تلقائياً)
    manager = ThemeManager.instance()
    
    # إنشاء وإظهار النافذة
    window = TestWindow()
    window.show()
    
    # تطبيق الثيم الافتراضي
    manager.apply_theme("light")
    
    sys.exit(app.exec())