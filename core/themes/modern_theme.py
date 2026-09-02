# core/themes/modern_theme.py
"""
Modern Theme - ثيم عصري احترافي لـ YAseen ERP
ملاحظة: تم إزالة خاصية transition لأنها غير مدعومة في Qt
"""

from .base_theme import BaseTheme
from .theme_constants import Colors, Spacing, Typography, BorderRadius


class ModernTheme(BaseTheme):
    """الثيم العصري الاحترافي - يدعم الوضع الفاتح والداكن تلقائياً"""
    
    name: str = "modern"
    display_name: str = "عصري"
    
    def __init__(self, dark_mode: bool = False):
        self._dark_mode = dark_mode
        
        if dark_mode:
            self._init_dark_theme()
        else:
            self._init_light_theme()
        
        self.spacing = Spacing()
        self.typography = Typography()
        self.radius = BorderRadius()
        
        super().__init__()
    
    def _init_light_theme(self):
        """تهيئة النسخة الفاتحة"""
        self.primary = "#2563EB"
        self.primary_dark = "#1D4ED8"
        self.primary_light = "#DBEAFE"
        self.secondary = "#1F2937"
        self.secondary_dark = "#111827"
        self.secondary_light = "#374151"
        self.success = "#10B981"
        self.error = "#EF4444"
        self.warning = "#F59E0B"
        self.info = "#8B5CF6"
        self.background = "#F9FAFB"
        self.background_alt = "#F3F4F6"
        self.surface = "#FFFFFF"
        self.surface_alt = "#F9FAFB"
        self.text_primary = "#111827"
        self.text_secondary = "#6B7280"
        self.text_disabled = "#9CA3AF"
        self.text_hint = "#9CA3AF"
        self.border = "#E5E7EB"
        self.border_light = "#F3F4F6"
        self.border_dark = "#D1D5DB"
        self.hover = "#F3F4F6"
        self.active = "#E5E7EB"
        self.selected = "#DBEAFE"
        self.focus = "#2563EB"
    
    def _init_dark_theme(self):
        """تهيئة النسخة الداكنة"""
        self.primary = "#3B82F6"
        self.primary_dark = "#2563EB"
        self.primary_light = "#1E3A8A"
        self.secondary = "#1F2937"
        self.secondary_dark = "#111827"
        self.secondary_light = "#374151"
        self.success = "#10B981"
        self.error = "#EF4444"
        self.warning = "#F59E0B"
        self.info = "#8B5CF6"
        self.background = "#0F172A"
        self.background_alt = "#1E293B"
        self.surface = "#1E293B"
        self.surface_alt = "#334155"
        self.text_primary = "#F8FAFC"
        self.text_secondary = "#94A3B8"
        self.text_disabled = "#64748B"
        self.text_hint = "#64748B"
        self.border = "#334155"
        self.border_light = "#475569"
        self.border_dark = "#1E293B"
        self.hover = "#334155"
        self.active = "#475569"
        self.selected = "#1E3A8A"
        self.focus = "#3B82F6"
    
    def set_dark_mode(self, enabled: bool):
        self._dark_mode = enabled
        if enabled:
            self._init_dark_theme()
        else:
            self._init_light_theme()
    
    def is_dark_mode(self) -> bool:
        return self._dark_mode
    
    def get_stylesheet(self) -> str:
        """الحصول على الـ Stylesheet الكامل (بدون transition)"""
        return f"""
            /* ====================================================================
               YAseen ERP - MODERN THEME
               الإصدار: 2.0
            ==================================================================== */
            
            /* ========== النافذة الرئيسية ========== */
            QMainWindow, QDialog {{
                background-color: {self.background};
            }}
            
            /* ========== شريط علوي ========== */
            QFrame#app_header {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary}, stop:1 {self.primary_dark});
                color: white;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }}
            
            QFrame#app_header QLabel {{
                color: white;
            }}
            
            /* ========== الشريط الجانبي ========== */
            QFrame#sidebar {{
                background-color: {self.secondary};
                border-right: 1px solid {self.secondary_dark};
            }}
            
            QLabel#logo {{
                color: {self.primary_light};
                padding: {self.spacing.MD}px;
                font-size: {self.typography.SIZE_XXL};
                font-weight: {self.typography.WEIGHT_BOLD};
            }}
            
            /* ========== أزرار الشريط الجانبي ========== */
            QPushButton#sidebar_btn {{
                background-color: transparent;
                color: {self.text_secondary};
                border: none;
                text-align: left;
                padding: {self.spacing.SM}px {self.spacing.LG}px;
                font-size: {self.typography.SIZE_LG};
                border-radius: {self.radius.MD};
                margin: 2px {self.spacing.SM}px;
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
            
            /* ========== بطاقات المعلومات ========== */
            QFrame#card {{
                background-color: {self.surface};
                border-radius: {self.radius.LG};
                padding: {self.spacing.LG}px;
                border: 1px solid {self.border};
            }}
            
            QFrame#card:hover {{
                border-color: {self.primary_light};
            }}
            
            QLabel#card_value {{
                color: {self.primary};
                font-size: {self.typography.SIZE_XXXL};
                font-weight: {self.typography.WEIGHT_BOLD};
            }}
            
            /* ========== الجداول ========== */
            QTableWidget {{
                background-color: {self.surface};
                alternate-background-color: {self.surface_alt};
                border-radius: {self.radius.LG};
                gridline-color: {self.border};
                selection-background-color: {self.primary};
                selection-color: white;
                outline: none;
            }}
            
            QTableWidget::item {{
                padding: {self.spacing.SM}px;
                border-bottom: 1px solid {self.border_light};
            }}
            
            QTableWidget::item:selected {{
                background-color: {self.primary};
                color: white;
            }}
            
            QHeaderView::section {{
                background-color: {self.secondary};
                color: white;
                padding: {self.spacing.SM}px;
                border: none;
                font-weight: {self.typography.WEIGHT_BOLD};
            }}
            
            /* ========== أزرار ========== */
            QPushButton {{
                background-color: {self.surface};
                border: 1px solid {self.border};
                color: {self.text_primary};
                padding: {self.spacing.SM}px {self.spacing.LG}px;
                border-radius: {self.radius.MD};
                font-size: {self.typography.SIZE_LG};
                font-weight: {self.typography.WEIGHT_MEDIUM};
            }}
            
            QPushButton:hover {{
                background-color: {self.hover};
                border-color: {self.primary_light};
            }}
            
            QPushButton:pressed {{
                background-color: {self.active};
            }}
            
            QPushButton:disabled {{
                background-color: {self.border_light};
                color: {self.text_disabled};
            }}
            
            QPushButton#primary_button {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary}, stop:1 {self.primary_dark});
                color: white;
                border: none;
                font-weight: {self.typography.WEIGHT_BOLD};
            }}
            
            QPushButton#primary_button:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary_dark}, stop:1 {self.primary});
            }}
            
            QPushButton#success_button {{
                background-color: {self.success};
                color: white;
                border: none;
            }}
            
            QPushButton#success_button:hover {{
                background-color: #059669;
            }}
            
            QPushButton#danger_button {{
                background-color: {self.error};
                color: white;
                border: none;
            }}
            
            QPushButton#danger_button:hover {{
                background-color: #DC2626;
            }}
            
            /* ========== حقول الإدخال ========== */
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
                background-color: {self.surface};
                border: 2px solid {self.border};
                color: {self.text_primary};
                padding: {self.spacing.SM}px;
                border-radius: {self.radius.MD};
                font-size: {self.typography.SIZE_LG};
                min-height: 20px;
            }}
            
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, 
            QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {{
                border-color: {self.primary};
                outline: none;
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {self.surface};
                color: {self.text_primary};
                selection-background-color: {self.primary};
                selection-color: white;
                border-radius: {self.radius.MD};
                outline: none;
            }}
            
            /* ========== علامات التبويب ========== */
            QTabWidget::pane {{
                border: 1px solid {self.border};
                border-radius: {self.radius.MD};
                background-color: {self.surface};
            }}
            
            QTabBar::tab {{
                padding: {self.spacing.SM}px {self.spacing.LG}px;
                margin: {self.spacing.XS}px;
                border-radius: {self.radius.MD};
                color: {self.text_secondary};
            }}
            
            QTabBar::tab:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary}, stop:1 {self.primary_dark});
                color: white;
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {self.hover};
                color: {self.text_primary};
            }}
            
            /* ========== المجموعات ========== */
            QGroupBox {{
                font-weight: {self.typography.WEIGHT_BOLD};
                border: 2px solid {self.border};
                border-radius: {self.radius.LG};
                margin-top: {self.spacing.LG}px;
                padding-top: {self.spacing.SM}px;
                color: {self.text_primary};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {self.spacing.LG}px;
                padding: 0 {self.spacing.SM}px;
                color: {self.text_primary};
                background-color: {self.surface};
            }}
            
            /* ========== أشرطة التمرير ========== */
            QScrollBar:vertical {{
                background-color: {self.surface_alt};
                width: {self.spacing.LG}px;
                border-radius: {self.radius.SM};
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {self.border_dark};
                border-radius: {self.radius.SM};
                min-height: {self.spacing.XXXL}px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {self.primary};
            }}
            
            /* ========== أشرطة التقدم ========== */
            QProgressBar {{
                border: none;
                background-color: {self.border};
                border-radius: {self.radius.SM};
                text-align: center;
                color: {self.text_primary};
                height: 8px;
            }}
            
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary}, stop:1 {self.primary_dark});
                border-radius: {self.radius.SM};
            }}
            
            /* ========== القوائم ========== */
            QMenu {{
                background-color: {self.surface};
                border: 1px solid {self.border};
                border-radius: {self.radius.MD};
                padding: {self.spacing.XS}px;
                color: {self.text_primary};
            }}
            
            QMenu::item {{
                padding: {self.spacing.SM}px {self.spacing.XL}px;
                border-radius: {self.radius.SM};
                margin: {self.spacing.XS}px;
            }}
            
            QMenu::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary}, stop:1 {self.primary_dark});
                color: white;
            }}
            
            QMenu::separator {{
                height: 1px;
                background-color: {self.border};
                margin: {self.spacing.XS}px;
            }}
            
            /* ========== رسائل الخطأ ========== */
            QLabel[class="error"] {{
                color: {self.error};
                font-size: {self.typography.SIZE_SM};
                padding: {self.spacing.XS}px;
            }}
            
            QLabel[class="success"] {{
                color: {self.success};
                font-size: {self.typography.SIZE_SM};
                padding: {self.spacing.XS}px;
            }}
            
            QLabel[class="warning"] {{
                color: {self.warning};
                font-size: {self.typography.SIZE_SM};
                padding: {self.spacing.XS}px;
            }}
            
            /* ========== شريط الحالة ========== */
            QStatusBar {{
                background-color: {self.surface};
                color: {self.text_secondary};
                padding: {self.spacing.XS}px;
            }}
            
            /* ========== شريط أسعار الصرف ========== */
            QFrame#currency_frame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary}, stop:1 {self.primary_dark});
                border-radius: {self.radius.LG};
                padding: {self.spacing.SM}px;
                margin: {self.spacing.XS}px;
            }}
            
            QFrame#currency_frame QLabel {{
                color: white;
            }}
            
            QLabel#currency_buy {{
                color: {self.success};
                font-weight: bold;
            }}
            
            QLabel#currency_sell {{
                color: {self.warning};
                font-weight: bold;
            }}
            
            /* ========== أدوات إضافية ========== */
            QToolTip {{
                background-color: {self.secondary};
                color: white;
                border: none;
                border-radius: {self.radius.SM};
                padding: {self.spacing.SM}px;
            }}
            
            QCheckBox {{
                color: {self.text_primary};
                spacing: {self.spacing.SM}px;
            }}
            
            QCheckBox::indicator {{
                width: {self.spacing.LG}px;
                height: {self.spacing.LG}px;
                border-radius: {self.radius.SM};
                border: 2px solid {self.border};
                background-color: {self.surface};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {self.primary};
                border-color: {self.primary};
            }}
            
            QRadioButton {{
                color: {self.text_primary};
                spacing: {self.spacing.SM}px;
            }}
            
            QRadioButton::indicator {{
                width: {self.spacing.LG}px;
                height: {self.spacing.LG}px;
                border-radius: {self.radius.CIRCLE};
                border: 2px solid {self.border};
                background-color: {self.surface};
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {self.primary};
                border-color: {self.primary};
            }}
            
            /* ========== Splitter ========== */
            QSplitter::handle {{
                background-color: {self.border};
            }}
            
            QSplitter::handle:hover {{
                background-color: {self.primary};
            }}
        """