# core/themes/dark_theme.py
"""
Dark Theme - الثيم الداكن
"""

from typing import Dict, Any
from .base_theme import BaseTheme
from .theme_constants import Colors


class DarkTheme(BaseTheme):
    """
    الثيم الداكن للتطبيق
    Dark theme for the application
    """
    
    name: str = "dark"
    display_name: str = "داكن"
    
    def __init__(self):
        """تهيئة الثيم الداكن - Initialize dark theme"""
        super().__init__()
        
        # ألوان الخلفية - Background colors
        self.background = Colors.DARK_BACKGROUND
        self.background_alt = Colors.DARK_BACKGROUND_ALT
        self.surface = Colors.DARK_SURFACE
        self.surface_alt = Colors.DARK_SURFACE_ALT
        self.surface_elevated = Colors.DARK_SURFACE_ELEVATED if hasattr(Colors, 'DARK_SURFACE_ELEVATED') else Colors.DARK_SURFACE
        
        # ألوان النصوص - Text colors
        self.text_primary = Colors.DARK_TEXT_PRIMARY
        self.text_secondary = Colors.DARK_TEXT_SECONDARY
        self.text_disabled = Colors.DARK_TEXT_DISABLED
        self.text_hint = Colors.DARK_TEXT_HINT
        self.text_inverse = "#FFFFFF"  # نص فاتح على خلفية داكنة
        
        # ألوان الحدود - Border colors
        self.border = Colors.DARK_BORDER
        self.border_light = Colors.DARK_BORDER_LIGHT
        self.border_dark = Colors.DARK_BORDER_DARK
        self.border_focus = Colors.PRIMARY
        
        # ألوان التفاعل - Interaction colors
        self.hover = Colors.DARK_HOVER
        self.active = Colors.PRIMARY
        self.selected = Colors.DARK_SELECTED
        self.focus = Colors.DARK_FOCUS
        self.pressed = Colors.DARK_PRESSED if hasattr(Colors, 'DARK_PRESSED') else "#1a1a1a"
        
        # الألوان الأساسية - Primary colors
        self.primary = Colors.PRIMARY
        self.primary_dark = Colors.PRIMARY_DARK
        self.primary_light = Colors.PRIMARY_LIGHT
        
        self.secondary = Colors.SECONDARY
        self.secondary_dark = Colors.SECONDARY_DARK
        self.secondary_light = Colors.SECONDARY_LIGHT
        
        # ألوان الحالة - Status colors
        self.success = Colors.SUCCESS
        self.success_dark = Colors.SUCCESS_DARK
        self.success_light = Colors.SUCCESS_LIGHT
        
        self.error = Colors.ERROR
        self.error_dark = Colors.ERROR_DARK
        self.error_light = Colors.ERROR_LIGHT
        
        self.warning = Colors.WARNING
        self.warning_dark = Colors.WARNING_DARK
        self.warning_light = Colors.WARNING_LIGHT
        
        self.info = Colors.INFO
        self.info_dark = Colors.INFO_DARK
        self.info_light = Colors.INFO_LIGHT
        
        # تحديث الظلال للثيم الداكن - Update shadows for dark theme
        self._update_shadows_for_dark_mode()
    
    def _update_shadows_for_dark_mode(self):
        """تحديث الظلال لتناسب الثيم الداكن"""
        self.shadow_small = "0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.24)"
        self.shadow_medium = "0 3px 6px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.12)"
        self.shadow_large = "0 10px 20px rgba(0,0,0,0.4), 0 6px 6px rgba(0,0,0,0.23)"
        self.shadow_hover = "0 14px 28px rgba(0,0,0,0.5), 0 10px 10px rgba(0,0,0,0.22)"
    
    def get_stylesheet(self) -> str:
        """
        الحصول على الـ Stylesheet الكامل للثيم الداكن
        Get complete stylesheet for dark theme
        """
        return f"""
            /* ========== النافذة الرئيسية ========== */
            QMainWindow, QDialog, QWidget {{
                background-color: {self.background};
                color: {self.text_primary};
            }}
            
            /* ========== الشريط الجانبي ========== */
            QFrame#sidebar {{
                background-color: {self.secondary};
                border-right: 1px solid {self.secondary_dark};
            }}
            
            QLabel#logo {{
                color: {self.primary_light};
                padding: {self.get_spacing('md')}px;
                font-size: {self.get_font_size('xxl')};
                font-weight: {self.get_font_weight('bold')};
            }}
            
            QPushButton#sidebar_btn {{
                background-color: transparent;
                color: {self.text_secondary};
                border: none;
                text-align: left;
                padding: {self.get_spacing('sm')}px {self.get_spacing('lg')}px;
                font-size: {self.get_font_size('lg')};
                border-radius: {self.get_border_radius('md')};
                margin: {self.get_spacing('xs')}px {self.get_spacing('sm')}px;
            }}
            
            QPushButton#sidebar_btn:hover {{
                background-color: {self.secondary_light};
                color: white;
            }}
            
            QPushButton#sidebar_btn[active="true"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary}, stop:1 {self.primary_dark});
                color: white;
            }}
            
            QPushButton#sidebar_btn[active="true"]:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary_dark}, stop:1 {self.primary});
            }}
            
            /* ========== البطاقات ========== */
            QFrame#card {{
                background-color: {self.surface};
                border-radius: {self.get_border_radius('lg')};
                padding: {self.get_spacing('lg')}px;
                border: 1px solid {self.border};
            }}
            
            QFrame#card:hover {{
                border-color: {self.primary_light};
            }}
            
            QLabel#card_title {{
                color: {self.text_primary};
                font-size: {self.get_font_size('xl')};
                font-weight: {self.get_font_weight('bold')};
                margin-bottom: {self.get_spacing('md')}px;
            }}
            
            QLabel#card_value {{
                color: {self.primary};
                font-size: {self.get_font_size('xxxl')};
                font-weight: {self.get_font_weight('bold')};
            }}
            
            QLabel#card_description {{
                color: {self.text_secondary};
                font-size: {self.get_font_size('md')};
                margin-top: {self.get_spacing('sm')}px;
            }}
            
            /* ========== الجداول ========== */
            QTableWidget {{
                background-color: {self.surface};
                alternate-background-color: {self.surface_alt};
                border-radius: {self.get_border_radius('lg')};
                gridline-color: {self.border};
                selection-background-color: {self.primary};
                selection-color: white;
                outline: none;
            }}
            
            QTableWidget::item {{
                padding: {self.get_spacing('sm')}px;
                border-bottom: 1px solid {self.border};
            }}
            
            QTableWidget::item:selected {{
                background-color: {self.primary};
                color: white;
            }}
            
            QHeaderView::section {{
                background-color: {self.secondary};
                color: white;
                padding: {self.get_spacing('sm')}px;
                border: none;
                font-weight: {self.get_font_weight('bold')};
            }}
            
            QTableCornerButton::section {{
                background-color: {self.secondary};
                border: none;
            }}
            
            /* ========== الأزرار ========== */
            QPushButton {{
                background-color: {self.surface};
                border: 1px solid {self.border};
                color: {self.text_primary};
                padding: {self.get_spacing('sm')}px {self.get_spacing('lg')}px;
                border-radius: {self.get_border_radius('md')};
                font-size: {self.get_font_size('lg')};
                font-weight: {self.get_font_weight('medium')};
                min-height: {self.min_height_button}px;
            }}
            
            QPushButton:hover {{
                background-color: {self.hover};
                border-color: {self.primary_light};
            }}
            
            QPushButton:pressed {{
                background-color: {self.pressed};
            }}
            
            QPushButton:disabled {{
                background-color: {self.surface_alt};
                color: {self.text_disabled};
                border-color: {self.border_light};
            }}
            
            QPushButton#primary_button {{
                background-color: {self.primary};
                color: white;
                border: none;
            }}
            
            QPushButton#primary_button:hover {{
                background-color: {self.primary_dark};
            }}
            
            QPushButton#primary_button:pressed {{
                background-color: {self.primary_dark};
            }}
            
            QPushButton#success_button {{
                background-color: {self.success};
                color: white;
                border: none;
            }}
            
            QPushButton#success_button:hover {{
                background-color: {self.success_dark};
            }}
            
            QPushButton#danger_button {{
                background-color: {self.error};
                color: white;
                border: none;
            }}
            
            QPushButton#danger_button:hover {{
                background-color: {self.error_dark};
            }}
            
            QPushButton#icon_button {{
                background-color: transparent;
                border: none;
                padding: {self.get_spacing('sm')}px;
            }}
            
            QPushButton#icon_button:hover {{
                background-color: {self.hover};
                border-radius: {self.get_border_radius('md')}px;
            }}
            
            /* ========== حقول الإدخال ========== */
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
                background-color: {self.surface};
                border: 2px solid {self.border};
                color: {self.text_primary};
                padding: {self.get_spacing('sm')}px;
                border-radius: {self.get_border_radius('md')};
                font-size: {self.get_font_size('lg')};
                min-height: {self.min_height_input - 12}px;
            }}
            
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus,
            QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                border-color: {self.border_focus};
                outline: none;
            }}
            
            QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled {{
                background-color: {self.surface_alt};
                color: {self.text_disabled};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: {self.get_spacing('xl')}px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {self.text_secondary};
                margin-right: {self.get_spacing('sm')}px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {self.surface};
                color: {self.text_primary};
                selection-background-color: {self.primary};
                selection-color: white;
                border-radius: {self.get_border_radius('md')}px;
                outline: none;
                padding: {self.get_spacing('sm')}px;
            }}
            
            /* ========== مجموعة الصناديق ========== */
            QGroupBox {{
                font-weight: {self.get_font_weight('bold')};
                border: 1px solid {self.border};
                border-radius: {self.get_border_radius('md')}px;
                margin-top: {self.get_spacing('md')}px;
                padding-top: {self.get_spacing('sm')}px;
                color: {self.text_primary};
            }}
            
            QGroupBox::title {{
                left: {self.get_spacing('md')}px;
                padding: 0 {self.get_spacing('sm')}px;
                color: {self.text_primary};
            }}
            
            /* ========== القوائم ========== */
            QMenuBar {{
                background-color: {self.surface};
                color: {self.text_primary};
                border-bottom: 1px solid {self.border};
            }}
            
            QMenuBar::item {{
                padding: {self.get_spacing('sm')}px {self.get_spacing('md')}px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {self.primary};
                color: white;
            }}
            
            QMenu {{
                background-color: {self.surface};
                color: {self.text_primary};
                border: 1px solid {self.border};
                border-radius: {self.get_border_radius('md')}px;
                padding: {self.get_spacing('sm')}px;
            }}
            
            QMenu::item {{
                padding: {self.get_spacing('sm')}px {self.get_spacing('xl')}px;
                border-radius: {self.get_border_radius('sm')}px;
            }}
            
            QMenu::item:selected {{
                background-color: {self.primary};
                color: white;
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {self.border};
                margin: {self.get_spacing('sm')}px;
            }}
            
            /* ========== شريط الحالة ========== */
            QStatusBar {{
                background-color: {self.surface};
                color: {self.text_secondary};
                padding: {self.get_spacing('sm')}px;
            }}
            
            QStatusBar::item {{
                border: none;
            }}
            
            /* ========== تلميحات الأدوات ========== */
            QToolTip {{
                background-color: {self.surface_elevated};
                color: {self.text_primary};
                border: 1px solid {self.border};
                border-radius: {self.get_border_radius('sm')}px;
                padding: {self.get_spacing('sm')}px;
            }}
            
            /* ========== أشرطة التمرير ========== */
            QScrollBar:vertical {{
                background-color: {self.surface};
                width: {self.get_spacing('sm')}px;
                border-radius: {self.get_border_radius('xs')}px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {self.border};
                border-radius: {self.get_border_radius('xs')}px;
                min-height: {self.get_spacing('lg')}px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {self.border_dark};
            }}
            
            QScrollBar:horizontal {{
                background-color: {self.surface};
                height: {self.get_spacing('sm')}px;
                border-radius: {self.get_border_radius('xs')}px;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {self.border};
                border-radius: {self.get_border_radius('xs')}px;
                min-width: {self.get_spacing('lg')}px;
            }}
            
            /* ========== أشرطة التقدم ========== */
            QProgressBar {{
                background-color: {self.surface};
                border: 1px solid {self.border};
                border-radius: {self.get_border_radius('md')}px;
                text-align: center;
                color: {self.text_primary};
                font-weight: {self.get_font_weight('bold')};
            }}
            
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary}, stop:1 {self.primary_light});
                border-radius: {self.get_border_radius('md')}px;
            }}
            
            /* ========== علامات التبويب ========== */
            QTabWidget::pane {{
                background-color: {self.surface};
                border: 1px solid {self.border};
                border-radius: {self.get_border_radius('md')}px;
                padding: {self.get_spacing('md')}px;
            }}
            
            QTabBar::tab {{
                background-color: {self.background};
                color: {self.text_secondary};
                padding: {self.get_spacing('sm')}px {self.get_spacing('lg')}px;
                margin-right: {self.get_spacing('xs')}px;
                border-top-left-radius: {self.get_border_radius('md')}px;
                border-top-right-radius: {self.get_border_radius('md')}px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {self.surface};
                color: {self.primary};
                border-bottom: 2px solid {self.primary};
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {self.hover};
            }}
            
            /* ========== خانات الاختيار وأزرار الراديو ========== */
            QCheckBox, QRadioButton {{
                spacing: {self.get_spacing('sm')}px;
                color: {self.text_primary};
                font-size: {self.get_font_size('lg')};
            }}
            
            QCheckBox::indicator, QRadioButton::indicator {{
                width: {self.get_spacing('lg')}px;
                height: {self.get_spacing('lg')}px;
            }}
            
            QCheckBox::indicator:unchecked {{
                border: 2px solid {self.border};
                background-color: {self.surface};
                border-radius: {self.get_border_radius('xs')}px;
            }}
            
            QCheckBox::indicator:checked {{
                border: 2px solid {self.primary};
                background-color: {self.primary};
                border-radius: {self.get_border_radius('xs')}px;
            }}
            
            QRadioButton::indicator:unchecked {{
                border: 2px solid {self.border};
                background-color: {self.surface};
                border-radius: {self.get_border_radius('lg')}px;
            }}
            
            QRadioButton::indicator:checked {{
                border: 2px solid {self.primary};
                background-color: {self.primary};
                border-radius: {self.get_border_radius('lg')}px;
            }}
        """
    
    def is_dark_mode(self) -> bool:
        """
        التحقق مما إذا كان الثيم داكن (دائماً True)
        Check if theme is dark (always True)
        """
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        تحويل الثيم إلى قاموس للتسلسل
        Convert theme to dictionary for serialization
        """
        base_dict = super().to_dict()
        base_dict["name"] = self.name
        base_dict["display_name"] = self.display_name
        base_dict["is_dark"] = True
        return base_dict


# مثال للاستخدام
if __name__ == "__main__":
    # إنشاء ثيم داكن
    dark_theme = DarkTheme()
    
    print("=" * 60)
    print("Dark Theme Information / معلومات الثيم الداكن")
    print("=" * 60)
    print(f"Name: {dark_theme.name}")
    print(f"Display Name: {dark_theme.display_name}")
    print(f"Is Dark Mode: {dark_theme.is_dark_mode()}")
    print(f"Background: {dark_theme.background}")
    print(f"Surface: {dark_theme.surface}")
    print(f"Text Primary: {dark_theme.text_primary}")
    print(f"Text Secondary: {dark_theme.text_secondary}")
    
    print("\n" + "=" * 60)
    print("Testing Spacing / اختبار المسافات")
    print("=" * 60)
    for size in ["xs", "sm", "md", "lg", "xl"]:
        print(f"Spacing {size}: {dark_theme.get_spacing(size)}px")
    
    print("\n" + "=" * 60)
    print("Testing Border Radius / اختبار الزوايا")
    print("=" * 60)
    for size in ["sm", "md", "lg", "xl", "circle", "pill"]:
        print(f"Radius {size}: {dark_theme.get_border_radius(size)}")
    
    print("\n" + "=" * 60)
    print("Stylesheet Preview / معاينة الستايل شيت")
    print("=" * 60)
    stylesheet = dark_theme.get_stylesheet()
    print(f"Stylesheet length: {len(stylesheet)} characters")
    print(f"First 500 chars: {stylesheet[:500]}...")
    
    print("\n" + "=" * 60)
    print("Dictionary Export / تصدير القاموس")
    print("=" * 60)
    theme_dict = dark_theme.to_dict()
    print(f"Keys: {list(theme_dict.keys())}")
    print(f"Is Dark: {theme_dict['is_dark']}")