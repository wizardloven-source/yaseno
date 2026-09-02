# core/themes/theme_constants.py
"""
Theme Constants - الثوابت المستخدمة في جميع الثيمات
✅ محدث: إضافة الألوان الداكنة والفاتحة للحالات
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Tuple, List, Optional


class ColorRole(Enum):
    """
    أدوار الألوان في التطبيق
    Color roles in the application
    """
    # الألوان الأساسية - Primary colors
    PRIMARY = "primary"
    PRIMARY_DARK = "primary_dark"
    PRIMARY_LIGHT = "primary_light"
    
    # الألوان الثانوية - Secondary colors
    SECONDARY = "secondary"
    SECONDARY_DARK = "secondary_dark"
    SECONDARY_LIGHT = "secondary_light"
    
    # ألوان الحالة - Status colors
    SUCCESS = "success"
    SUCCESS_DARK = "success_dark"
    SUCCESS_LIGHT = "success_light"
    ERROR = "error"
    ERROR_DARK = "error_dark"
    ERROR_LIGHT = "error_light"
    WARNING = "warning"
    WARNING_DARK = "warning_dark"
    WARNING_LIGHT = "warning_light"
    INFO = "info"
    INFO_DARK = "info_dark"
    INFO_LIGHT = "info_light"
    
    # ألوان الخلفية - Background colors
    BACKGROUND = "background"
    BACKGROUND_ALT = "background_alt"
    SURFACE = "surface"
    SURFACE_ALT = "surface_alt"
    SURFACE_ELEVATED = "surface_elevated"
    
    # ألوان النصوص - Text colors
    TEXT_PRIMARY = "text_primary"
    TEXT_SECONDARY = "text_secondary"
    TEXT_DISABLED = "text_disabled"
    TEXT_HINT = "text_hint"
    TEXT_INVERSE = "text_inverse"
    
    # ألوان الحدود - Border colors
    BORDER = "border"
    BORDER_LIGHT = "border_light"
    BORDER_DARK = "border_dark"
    BORDER_FOCUS = "border_focus"
    
    # ألوان التفاعل - Interaction colors
    HOVER = "hover"
    ACTIVE = "active"
    SELECTED = "selected"
    FOCUS = "focus"
    PRESSED = "pressed"
    
    @classmethod
    def get_all_roles(cls) -> List[str]:
        """
        الحصول على جميع أدوار الألوان
        Get all color roles
        
        العائد:
            قائمة بجميع أسماء أدوار الألوان
        """
        return [role.value for role in cls]
    
    @classmethod
    def get_status_roles(cls) -> List[str]:
        """
        الحصول على أدوار ألوان الحالة فقط
        Get only status color roles
        
        العائد:
            قائمة بأدوار ألوان الحالة
        """
        return ["success", "error", "warning", "info"]


@dataclass(frozen=True)
class Colors:
    """
    الألوان الأساسية (قيم RGB hex)
    Base colors (RGB hex values)
    """
    
    # ========== الألوان الأساسية ==========
    PRIMARY: str = "#e94560"      # اللون الأساسي (أحمر)
    PRIMARY_DARK: str = "#c73550"  # اللون الأساسي غامق
    PRIMARY_LIGHT: str = "#f05d78" # اللون الأساسي فاتح
    
    SECONDARY: str = "#1a1a2e"    # اللون الثانوي (أزرق داكن)
    SECONDARY_DARK: str = "#0f0f1a"
    SECONDARY_LIGHT: str = "#252540"
    
    # ========== ألوان الحالة (مع dark/light) ==========
    SUCCESS: str = "#4CAF50"      # أخضر - نجاح
    SUCCESS_DARK: str = "#388E3C"  # أخضر غامق
    SUCCESS_LIGHT: str = "#A5D6A7" # أخضر فاتح
    
    ERROR: str = "#f44336"        # أحمر - خطأ
    ERROR_DARK: str = "#d32f2f"   # أحمر غامق
    ERROR_LIGHT: str = "#ef9a9a"  # أحمر فاتح
    
    WARNING: str = "#ff9800"      # برتقالي - تحذير
    WARNING_DARK: str = "#f57c00" # برتقالي غامق
    WARNING_LIGHT: str = "#ffe0b2" # برتقالي فاتح
    
    INFO: str = "#2196F3"         # أزرق - معلومات
    INFO_DARK: str = "#1976D2"    # أزرق غامق
    INFO_LIGHT: str = "#90CAF9"   # أزرق فاتح
    
    # ========== الألوان المحايدة - Neutral colors ==========
    WHITE: str = "#FFFFFF"
    BLACK: str = "#000000"
    
    GRAY_50: str = "#fafafa"
    GRAY_100: str = "#f5f5f5"
    GRAY_200: str = "#eeeeee"
    GRAY_300: str = "#e0e0e0"
    GRAY_400: str = "#bdbdbd"
    GRAY_500: str = "#9e9e9e"
    GRAY_600: str = "#757575"
    GRAY_700: str = "#616161"
    GRAY_800: str = "#424242"
    GRAY_900: str = "#212121"
    
    # ========== ألوان الثيم الفاتح - Light theme colors ==========
    LIGHT_BACKGROUND: str = "#f5f5f5"
    LIGHT_BACKGROUND_ALT: str = "#ffffff"
    LIGHT_SURFACE: str = "#ffffff"
    LIGHT_SURFACE_ALT: str = "#f8f9fa"
    LIGHT_SURFACE_ELEVATED: str = "#ffffff"
    
    LIGHT_TEXT_PRIMARY: str = "#212529"
    LIGHT_TEXT_SECONDARY: str = "#6c757d"
    LIGHT_TEXT_DISABLED: str = "#adb5bd"
    LIGHT_TEXT_HINT: str = "#999999"
    LIGHT_TEXT_INVERSE: str = "#ffffff"
    
    LIGHT_BORDER: str = "#dee2e6"
    LIGHT_BORDER_LIGHT: str = "#e9ecef"
    LIGHT_BORDER_DARK: str = "#ced4da"
    LIGHT_BORDER_FOCUS: str = "#e94560"
    
    LIGHT_HOVER: str = "#f8f9fa"
    LIGHT_ACTIVE: str = "#e9ecef"
    LIGHT_SELECTED: str = "#e94560"
    LIGHT_FOCUS: str = "#e94560"
    LIGHT_PRESSED: str = "#dee2e6"
    
    # ========== ألوان الثيم الداكن - Dark theme colors ==========
    DARK_BACKGROUND: str = "#121212"
    DARK_BACKGROUND_ALT: str = "#1e1e1e"
    DARK_SURFACE: str = "#2d2d2d"
    DARK_SURFACE_ALT: str = "#383838"
    DARK_SURFACE_ELEVATED: str = "#3d3d3d"
    
    DARK_TEXT_PRIMARY: str = "#ffffff"
    DARK_TEXT_SECONDARY: str = "#b0b0b0"
    DARK_TEXT_DISABLED: str = "#6c757d"
    DARK_TEXT_HINT: str = "#808080"
    DARK_TEXT_INVERSE: str = "#212529"
    
    DARK_BORDER: str = "#404040"
    DARK_BORDER_LIGHT: str = "#353535"
    DARK_BORDER_DARK: str = "#4a4a4a"
    DARK_BORDER_FOCUS: str = "#e94560"
    
    DARK_HOVER: str = "#2d2d2d"
    DARK_ACTIVE: str = "#383838"
    DARK_SELECTED: str = "#e94560"
    DARK_FOCUS: str = "#e94560"
    DARK_PRESSED: str = "#404040"
    
    # ========== دوال مساعدة ==========
    
    @classmethod
    def get_light_theme_colors(cls) -> Dict[str, str]:
        """
        الحصول على جميع ألوان الثيم الفاتح
        Get all light theme colors
        
        العائد:
            قاموس يحتوي على ألوان الثيم الفاتح
        """
        return {
            "background": cls.LIGHT_BACKGROUND,
            "background_alt": cls.LIGHT_BACKGROUND_ALT,
            "surface": cls.LIGHT_SURFACE,
            "surface_alt": cls.LIGHT_SURFACE_ALT,
            "surface_elevated": cls.LIGHT_SURFACE_ELEVATED,
            "text_primary": cls.LIGHT_TEXT_PRIMARY,
            "text_secondary": cls.LIGHT_TEXT_SECONDARY,
            "text_disabled": cls.LIGHT_TEXT_DISABLED,
            "text_hint": cls.LIGHT_TEXT_HINT,
            "text_inverse": cls.LIGHT_TEXT_INVERSE,
            "border": cls.LIGHT_BORDER,
            "border_light": cls.LIGHT_BORDER_LIGHT,
            "border_dark": cls.LIGHT_BORDER_DARK,
            "border_focus": cls.LIGHT_BORDER_FOCUS,
            "hover": cls.LIGHT_HOVER,
            "active": cls.LIGHT_ACTIVE,
            "selected": cls.LIGHT_SELECTED,
            "focus": cls.LIGHT_FOCUS,
            "pressed": cls.LIGHT_PRESSED,
        }
    
    @classmethod
    def get_dark_theme_colors(cls) -> Dict[str, str]:
        """
        الحصول على جميع ألوان الثيم الداكن
        Get all dark theme colors
        
        العائد:
            قاموس يحتوي على ألوان الثيم الداكن
        """
        return {
            "background": cls.DARK_BACKGROUND,
            "background_alt": cls.DARK_BACKGROUND_ALT,
            "surface": cls.DARK_SURFACE,
            "surface_alt": cls.DARK_SURFACE_ALT,
            "surface_elevated": cls.DARK_SURFACE_ELEVATED,
            "text_primary": cls.DARK_TEXT_PRIMARY,
            "text_secondary": cls.DARK_TEXT_SECONDARY,
            "text_disabled": cls.DARK_TEXT_DISABLED,
            "text_hint": cls.DARK_TEXT_HINT,
            "text_inverse": cls.DARK_TEXT_INVERSE,
            "border": cls.DARK_BORDER,
            "border_light": cls.DARK_BORDER_LIGHT,
            "border_dark": cls.DARK_BORDER_DARK,
            "border_focus": cls.DARK_BORDER_FOCUS,
            "hover": cls.DARK_HOVER,
            "active": cls.DARK_ACTIVE,
            "selected": cls.DARK_SELECTED,
            "focus": cls.DARK_FOCUS,
            "pressed": cls.DARK_PRESSED,
        }
    
    @classmethod
    def get_status_color(cls, status: str, variant: str = "") -> str:
        """
        الحصول على لون الحالة (نجاح، خطأ، تحذير، معلومات)
        Get status color (success, error, warning, info)
        
        المعاملات:
            status: الحالة (success, error, warning, info)
            variant: النوع (dark, light, أو فارغ للون الأساسي)
        
        العائد:
            قيمة اللون hex
        """
        status_map = {
            "success": {"": cls.SUCCESS, "dark": cls.SUCCESS_DARK, "light": cls.SUCCESS_LIGHT},
            "error": {"": cls.ERROR, "dark": cls.ERROR_DARK, "light": cls.ERROR_LIGHT},
            "warning": {"": cls.WARNING, "dark": cls.WARNING_DARK, "light": cls.WARNING_LIGHT},
            "info": {"": cls.INFO, "dark": cls.INFO_DARK, "light": cls.INFO_LIGHT},
        }
        
        color_map = status_map.get(status.lower(), status_map["info"])
        return color_map.get(variant, color_map[""])
    
    @classmethod
    def get_gray_shades(cls) -> Dict[str, str]:
        """
        الحصول على جميع درجات الرمادي
        Get all gray shades
        
        العائد:
            قاموس بدرجات الرمادي
        """
        return {
            "50": cls.GRAY_50,
            "100": cls.GRAY_100,
            "200": cls.GRAY_200,
            "300": cls.GRAY_300,
            "400": cls.GRAY_400,
            "500": cls.GRAY_500,
            "600": cls.GRAY_600,
            "700": cls.GRAY_700,
            "800": cls.GRAY_800,
            "900": cls.GRAY_900,
        }
    
    @classmethod
    def is_dark_color(cls, hex_color: str) -> bool:
        """
        التحقق مما إذا كان اللون داكنًا
        Check if a color is dark
        
        المعاملات:
            hex_color: لون بصيغة hex (مثال: #RRGGBB)
        
        العائد:
            True إذا كان داكن، False إذا كان فاتح
        """
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness < 128
        except (ValueError, IndexError):
            return False
    
    @classmethod
    def get_contrast_color(cls, hex_color: str) -> str:
        """
        الحصول على لون متباين (أبيض أو أسود) مناسب للخلفية
        Get contrasting color (white or black) suitable for background
        
        المعاملات:
            hex_color: لون الخلفية بصيغة hex
        
        العائد:
            "#FFFFFF" للخلفيات الداكنة، "#000000" للخلفيات الفاتحة
        """
        if cls.is_dark_color(hex_color):
            return cls.WHITE
        return cls.BLACK
    
    @classmethod
    def to_rgb(cls, hex_color: str) -> Tuple[int, int, int]:
        """
        تحويل لون hex إلى قيم RGB
        Convert hex color to RGB values
        
        المعاملات:
            hex_color: لون بصيغة hex (مثال: #RRGGBB)
        
        العائد:
            tuple (r, g, b) بقيم من 0 إلى 255
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @classmethod
    def to_rgba(cls, hex_color: str, alpha: float = 1.0) -> str:
        """
        تحويل لون hex إلى صيغة rgba
        Convert hex color to rgba format
        
        المعاملات:
            hex_color: لون بصيغة hex
            alpha: قيمة الشفافية (0.0 إلى 1.0)
        
        العائد:
            لون بصيغة rgba(r, g, b, a)
        """
        r, g, b = cls.to_rgb(hex_color)
        return f"rgba({r}, {g}, {b}, {alpha})"


@dataclass(frozen=True)
class Spacing:
    """
    مسافات موحدة - نظام 8px
    Unified spacing - 8px system
    """
    XS: int = 4
    SM: int = 8
    MD: int = 12
    LG: int = 16
    XL: int = 24
    XXL: int = 32
    XXXL: int = 48
    
    @property
    def all(self) -> Dict[str, int]:
        """
        الحصول على جميع المسافات
        Get all spacing values
        
        العائد:
            قاموس بجميع المسافات
        """
        return {
            "xs": self.XS,
            "sm": self.SM,
            "md": self.MD,
            "lg": self.LG,
            "xl": self.XL,
            "xxl": self.XXL,
            "xxxl": self.XXXL,
        }
    
    def get(self, size: str) -> int:
        """
        الحصول على مسافة محددة
        Get specific spacing value
        
        المعاملات:
            size: xs, sm, md, lg, xl, xxl, xxxl
        
        العائد:
            قيمة المسافة بالبكسل
        """
        return self.all.get(size.lower(), self.MD)
    
    def scale(self, size: str, factor: float) -> int:
        """
        تغيير حجم المسافة بعامل معين
        Scale spacing by a factor
        
        المعاملات:
            size: اسم الحجم
            factor: عامل التكبير/التصغير
        
        العائد:
            المسافة الجديدة بعد القياس
        """
        return int(self.get(size) * factor)


@dataclass(frozen=True)
class Typography:
    """
    أنماط الخطوط الموحدة
    Unified typography styles
    """
    # أحجام الخطوط (بالبكسل) - Font sizes (in pixels)
    SIZE_XS: int = 10
    SIZE_SM: int = 11
    SIZE_MD: int = 12
    SIZE_LG: int = 14
    SIZE_XL: int = 16
    SIZE_XXL: int = 18
    SIZE_XXXL: int = 24
    SIZE_HUGE: int = 32
    
    # أوزان الخطوط - Font weights
    WEIGHT_NORMAL: int = 400
    WEIGHT_MEDIUM: int = 500
    WEIGHT_SEMI_BOLD: int = 600
    WEIGHT_BOLD: int = 700
    
    # عائلات الخطوط - Font families
    FAMILY_PRIMARY: str = "Segoe UI, Arial, sans-serif"
    FAMILY_ARABIC: str = "Segoe UI, Tahoma, 'Arabic Transparent', Arial, sans-serif"
    FAMILY_MONO: str = "Consolas, 'Courier New', monospace"
    
    @property
    def all_sizes(self) -> Dict[str, int]:
        """
        الحصول على جميع أحجام الخطوط
        Get all font sizes
        """
        return {
            "xs": self.SIZE_XS,
            "sm": self.SIZE_SM,
            "md": self.SIZE_MD,
            "lg": self.SIZE_LG,
            "xl": self.SIZE_XL,
            "xxl": self.SIZE_XXL,
            "xxxl": self.SIZE_XXXL,
            "huge": self.SIZE_HUGE,
        }
    
    @property
    def all_weights(self) -> Dict[str, int]:
        """
        الحصول على جميع أوزان الخطوط
        Get all font weights
        """
        return {
            "normal": self.WEIGHT_NORMAL,
            "medium": self.WEIGHT_MEDIUM,
            "semibold": self.WEIGHT_SEMI_BOLD,
            "bold": self.WEIGHT_BOLD,
        }
    
    def get_size(self, size: str) -> int:
        """
        الحصول على حجم خط محدد
        Get specific font size
        
        المعاملات:
            size: xs, sm, md, lg, xl, xxl, xxxl, huge
        
        العائد:
            حجم الخط بالبكسل
        """
        return self.all_sizes.get(size.lower(), self.SIZE_MD)
    
    def get_weight(self, weight: str) -> int:
        """
        الحصول على وزن خط محدد
        Get specific font weight
        
        المعاملات:
            weight: normal, medium, semibold, bold
        
        العائد:
            وزن الخط
        """
        return self.all_weights.get(weight.lower(), self.WEIGHT_NORMAL)
    
    def get_size_css(self, size: str) -> str:
        """
        الحصول على حجم الخط بصيغة CSS
        Get font size in CSS format
        
        المعاملات:
            size: xs, sm, md, lg, xl, xxl, xxxl, huge
        
        العائد:
            حجم الخط مع وحدة px
        """
        return f"{self.get_size(size)}px"


@dataclass(frozen=True)
class BorderRadius:
    """
    أنصاف أقطار الزوايا الموحدة
    Unified border radii
    """
    NONE: int = 0
    SM: int = 4
    MD: int = 8
    LG: int = 12
    XL: int = 16
    XXL: int = 24
    CIRCLE: int = 9999  # يستخدم للدوائر الكاملة
    PILL: int = 9999    # يستخدم للزوايا المستديرة بالكامل
    
    @property
    def all(self) -> Dict[str, int]:
        """
        الحصول على جميع أنصاف الأقطار
        Get all border radii
        """
        return {
            "none": self.NONE,
            "sm": self.SM,
            "md": self.MD,
            "lg": self.LG,
            "xl": self.XL,
            "xxl": self.XXL,
            "circle": self.CIRCLE,
            "pill": self.PILL,
        }
    
    def get(self, size: str) -> int:
        """
        الحصول على نصف قطر محدد
        Get specific border radius
        
        المعاملات:
            size: none, sm, md, lg, xl, xxl, circle, pill
        
        العائد:
            قيمة نصف القطر بالبكسل
        """
        return self.all.get(size.lower(), self.MD)
    
    def get_css(self, size: str) -> str:
        """
        الحصول على نصف القطر بصيغة CSS
        Get border radius in CSS format
        
        المعاملات:
            size: none, sm, md, lg, xl, xxl, circle, pill
        
        العائد:
            نصف القطر مع وحدة px (أو % للدوائر)
        """
        value = self.get(size)
        if size == "circle":
            return "50%"
        return f"{value}px"


# مثال للاستخدام
if __name__ == "__main__":
    print("=" * 60)
    print("Theme Constants Test / اختبار ثوابت الثيم")
    print("=" * 60)
    
    # اختبار الألوان
    print("\n1. Colors / الألوان:")
    print(f"   Primary: {Colors.PRIMARY}")
    print(f"   Success: {Colors.SUCCESS}")
    print(f"   Error: {Colors.ERROR}")
    
    # اختبار ألوان الثيم الفاتح
    light_colors = Colors.get_light_theme_colors()
    print(f"\n2. Light Theme Colors (sample):")
    print(f"   Background: {light_colors['background']}")
    print(f"   Surface: {light_colors['surface']}")
    print(f"   Text Primary: {light_colors['text_primary']}")
    
    # اختبار ألوان الثيم الداكن
    dark_colors = Colors.get_dark_theme_colors()
    print(f"\n3. Dark Theme Colors (sample):")
    print(f"   Background: {dark_colors['background']}")
    print(f"   Surface: {dark_colors['surface']}")
    print(f"   Text Primary: {dark_colors['text_primary']}")
    
    # اختبار ألوان الحالة
    print(f"\n4. Status Colors:")
    print(f"   Success: {Colors.get_status_color('success')}")
    print(f"   Success Dark: {Colors.get_status_color('success', 'dark')}")
    print(f"   Error: {Colors.get_status_color('error')}")
    print(f"   Warning: {Colors.get_status_color('warning')}")
    print(f"   Info: {Colors.get_status_color('info')}")
    
    # اختبار درجات الرمادي
    gray_shades = Colors.get_gray_shades()
    print(f"\n5. Gray Shades (sample):")
    print(f"   Gray 100: {gray_shades['100']}")
    print(f"   Gray 500: {gray_shades['500']}")
    print(f"   Gray 900: {gray_shades['900']}")
    
    # اختبار التباين
    print(f"\n6. Contrast Test:")
    print(f"   Dark color #121212 → contrast: {Colors.get_contrast_color('#121212')}")
    print(f"   Light color #ffffff → contrast: {Colors.get_contrast_color('#ffffff')}")
    
    # اختبار RGBA
    rgba = Colors.to_rgba(Colors.PRIMARY, 0.5)
    print(f"\n7. RGBA Conversion:")
    print(f"   Primary with 50% opacity: {rgba}")
    
    # اختبار المسافات
    spacing = Spacing()
    print(f"\n8. Spacing System:")
    print(f"   XS: {spacing.XS}px")
    print(f"   SM: {spacing.SM}px")
    print(f"   MD: {spacing.MD}px")
    print(f"   LG: {spacing.LG}px")
    print(f"   XL: {spacing.XL}px")
    print(f"   Scaled MD (x1.5): {spacing.scale('md', 1.5)}px")
    
    # اختبار الخطوط
    typography = Typography()
    print(f"\n9. Typography:")
    print(f"   Size MD: {typography.get_size_css('md')}")
    print(f"   Weight Bold: {typography.get_weight('bold')}")
    print(f"   Arabic Font: {typography.FAMILY_ARABIC}")
    
    # اختبار الزوايا
    radius = BorderRadius()
    print(f"\n10. Border Radius:")
    print(f"   SM: {radius.get_css('sm')}")
    print(f"   MD: {radius.get_css('md')}")
    print(f"   Circle: {radius.get_css('circle')}")
    
    # اختبار أدوار الألوان
    print(f"\n11. Color Roles:")
    print(f"   All roles: {ColorRole.get_all_roles()[:5]}...")
    print(f"   Status roles: {ColorRole.get_status_roles()}")
    
    print("\n" + "=" * 60)
    print("✅ All constants loaded successfully!")
    print("تم تحميل جميع الثوابت بنجاح!")