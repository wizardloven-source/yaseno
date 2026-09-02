# core/themes/light_theme.py
"""
Light Theme - الثيم الفاتح
"""

from .base_theme import BaseTheme
from .theme_constants import Colors


class LightTheme(BaseTheme):
    """الثيم الفاتح للتطبيق"""
    
    name: str = "light"
    display_name: str = "فاتح"
    
    def __init__(self):
        # ألوان الخلفية
        self.background = Colors.LIGHT_BACKGROUND
        self.background_alt = Colors.LIGHT_BACKGROUND_ALT
        self.surface = Colors.LIGHT_SURFACE
        self.surface_alt = Colors.LIGHT_SURFACE_ALT
        
        # ألوان النصوص
        self.text_primary = Colors.LIGHT_TEXT_PRIMARY
        self.text_secondary = Colors.LIGHT_TEXT_SECONDARY
        self.text_disabled = Colors.LIGHT_TEXT_DISABLED
        self.text_hint = Colors.LIGHT_TEXT_HINT
        
        # ألوان الحدود
        self.border = Colors.LIGHT_BORDER
        self.border_light = Colors.LIGHT_BORDER_LIGHT
        self.border_dark = Colors.LIGHT_BORDER_DARK
        
        # ألوان التفاعل
        self.hover = Colors.LIGHT_HOVER
        self.active = Colors.LIGHT_ACTIVE
        self.selected = Colors.LIGHT_SELECTED
        self.focus = Colors.LIGHT_FOCUS
        
        # الألوان الأساسية
        self.primary = Colors.PRIMARY
        self.primary_dark = Colors.PRIMARY_DARK
        self.primary_light = Colors.PRIMARY_LIGHT
        self.secondary = Colors.SECONDARY
        self.secondary_dark = Colors.SECONDARY_DARK
        self.secondary_light = Colors.SECONDARY_LIGHT
        self.success = Colors.SUCCESS
        self.error = Colors.ERROR
        self.warning = Colors.WARNING
        self.info = Colors.INFO
        
        super().__init__()
    
    def get_stylesheet(self) -> str:
        """الحصول على الـ Stylesheet (بدون transition)"""
        return f"""
            QMainWindow, QDialog {{
                background-color: {self.background};
            }}
            
            QFrame#sidebar {{
                background-color: {self.secondary};
                border-right: 1px solid {self.secondary_dark};
            }}
            
            QLabel#logo {{
                color: {self.primary};
                padding: 10px;
            }}
            
            QPushButton#sidebar_btn {{
                background-color: transparent;
                color: #e0e0e0;
                border: none;
                text-align: left;
                padding: 8px 15px;
                font-size: 14px;
                border-radius: 8px;
            }}
            
            QPushButton#sidebar_btn:hover {{
                background-color: {self.secondary_light};
                color: white;
            }}
            
            QPushButton#sidebar_btn[active="true"] {{
                background-color: {self.primary};
                color: white;
            }}
            
            QFrame#card {{
                background-color: {self.surface};
                border-radius: 12px;
                padding: 15px;
            }}
            
            QLabel#card_value {{
                color: {self.primary};
                font-size: 24px;
                font-weight: bold;
            }}
            
            QTableWidget {{
                background-color: {self.surface};
                alternate-background-color: {self.surface_alt};
                border-radius: 10px;
                gridline-color: {self.border_light};
                selection-background-color: {self.primary};
                selection-color: white;
            }}
            
            QTableWidget::item {{
                padding: 8px;
            }}
            
            QHeaderView::section {{
                background-color: {self.secondary};
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }}
            
            QPushButton {{
                background-color: {self.surface};
                border: 1px solid {self.border};
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 13px;
            }}
            
            QPushButton:hover {{
                background-color: {self.hover};
            }}
            
            QPushButton:pressed {{
                background-color: {self.active};
            }}
            
            QPushButton#primary_button {{
                background-color: {self.primary};
                color: white;
                border: none;
            }}
            
            QPushButton#primary_button:hover {{
                background-color: {self.primary_dark};
            }}
            
            QPushButton#success_button {{
                background-color: {self.success};
                color: white;
                border: none;
            }}
            
            QPushButton#danger_button {{
                background-color: {self.error};
                color: white;
                border: none;
            }}
            
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
                background-color: {self.surface};
                border: 1px solid {self.border};
                padding: 6px;
                border-radius: 6px;
            }}
            
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
                border-color: {self.primary};
            }}
            
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {self.border};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }}
            
            QGroupBox::title {{
                left: 10px;
                padding: 0 5px;
            }}
            
            QMenu {{
                background-color: {self.surface};
                border: 1px solid {self.border};
                border-radius: 6px;
                padding: 5px;
            }}
            
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            
            QMenu::item:selected {{
                background-color: {self.primary};
                color: white;
            }}
            
            QStatusBar {{
                background-color: {self.surface_alt};
                color: {self.text_secondary};
                padding: 3px;
            }}
        """