# core/themes/base_theme.py
"""
Base Theme - الثيم الأساسي (فئة مجردة)
✅ نسخة محسنة: أبعاد منسقة، حقول ذكية، دعم RTL
✅ مصحح: إزالة استيراد BorderRadius غير المستخدم
✅ مصحح: تحسين دالة is_dark_mode
✅ مصحح: إضافة دالة get_contrast_text_color مع fallback آمن
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from .theme_constants import Colors, Spacing, Typography, BorderRadius


@dataclass
class BaseTheme(ABC):
    """الثيم الأساسي - كل الثيمات ترث منه - تصميم احترافي عصري"""
    
    # ========== معلومات الثيم ==========
    name: str = "base"
    display_name: str = "Base"
    version: str = "2.0.0"
    
    # ========== الألوان الأساسية ==========
    primary: str = Colors.PRIMARY
    primary_dark: str = Colors.PRIMARY_DARK
    primary_light: str = Colors.PRIMARY_LIGHT
    
    secondary: str = Colors.SECONDARY
    secondary_dark: str = Colors.SECONDARY_DARK
    secondary_light: str = Colors.SECONDARY_LIGHT
    
    # ========== ألوان الحالة ==========
    success: str = Colors.SUCCESS
    success_dark: str = Colors.SUCCESS_DARK
    success_light: str = Colors.SUCCESS_LIGHT
    
    error: str = Colors.ERROR
    error_dark: str = Colors.ERROR_DARK
    error_light: str = Colors.ERROR_LIGHT
    
    warning: str = Colors.WARNING
    warning_dark: str = Colors.WARNING_DARK
    warning_light: str = Colors.WARNING_LIGHT
    
    info: str = Colors.INFO
    info_dark: str = Colors.INFO_DARK
    info_light: str = Colors.INFO_LIGHT
    
    # ========== ألوان الخلفية ==========
    background: str = Colors.GRAY_50
    background_alt: str = Colors.GRAY_100
    surface: str = Colors.WHITE
    surface_alt: str = Colors.GRAY_50
    surface_elevated: str = Colors.WHITE  # للسطح المرتفع (كروت مع ظل)
    
    # ========== ألوان النصوص ==========
    text_primary: str = Colors.GRAY_900
    text_secondary: str = Colors.GRAY_600
    text_disabled: str = Colors.GRAY_400
    text_hint: str = Colors.GRAY_500
    text_inverse: str = Colors.WHITE  # نص على خلفية داكنة
    
    # ========== ألوان الحدود ==========
    border: str = Colors.GRAY_300
    border_light: str = Colors.GRAY_200
    border_dark: str = Colors.GRAY_400
    border_focus: str = Colors.PRIMARY  # لون الحدود عند التركيز
    
    # ========== ألوان التفاعل ==========
    hover: str = Colors.GRAY_100
    active: str = Colors.PRIMARY
    selected: str = Colors.PRIMARY_LIGHT
    focus: str = Colors.PRIMARY
    pressed: str = Colors.GRAY_200  # لون عند الضغط
    
    # ========== الظلال ==========
    shadow_small: str = "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)"
    shadow_medium: str = "0 3px 6px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12)"
    shadow_large: str = "0 10px 20px rgba(0,0,0,0.15), 0 6px 6px rgba(0,0,0,0.10)"
    shadow_hover: str = "0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22)"
    
    # ========== المسافات (نظام 8px) ==========
    spacing: Spacing = field(default_factory=Spacing)
    
    # ========== هوامش مخصصة ==========
    margin_xs: int = 4
    margin_sm: int = 8
    margin_md: int = 12
    margin_lg: int = 16
    margin_xl: int = 24
    margin_xxl: int = 32
    
    # ========== حشوات داخلية ==========
    padding_xs: int = 4
    padding_sm: int = 8
    padding_md: int = 12
    padding_lg: int = 16
    padding_xl: int = 24
    
    # ========== الخطوط ==========
    typography: Typography = field(default_factory=Typography)
    
    # ========== الزوايا ==========
    radius: BorderRadius = field(default_factory=BorderRadius)
    
    # ========== أحجام العناصر ==========
    min_height_button: int = 36
    min_height_input: int = 40
    min_height_table_row: int = 48
    sidebar_width_expanded: int = 260
    sidebar_width_collapsed: int = 68
    header_height: int = 60
    footer_height: int = 40
    
    # ========== الشفافية ==========
    opacity_disabled: float = 0.5
    opacity_hover: float = 0.8
    opacity_pressed: float = 0.9
    
    # ========== مدة الحركات ==========
    transition_duration_fast: int = 150
    transition_duration_normal: int = 250
    transition_duration_slow: int = 350
    
    # ========== دوال مساعدة ==========
    
    @abstractmethod
    def get_stylesheet(self) -> str:
        """
        الحصول على الـ Stylesheet الكامل للثيم
        Get complete stylesheet for the theme
        """
        pass
    
    def get_color(self, color_name: str, fallback: Optional[str] = None) -> str:
        """
        الحصول على لون معين من الثيم
        Get a specific color from the theme
        
        المعاملات:
            color_name: اسم اللون
            fallback: لون بديل إذا لم يوجد
        
        العائد:
            قيمة اللون
        """
        if hasattr(self, color_name):
            return getattr(self, color_name)
        return fallback or self.primary
    
    def get_spacing(self, size: str) -> int:
        """
        الحصول على مسافة معينة
        Get specific spacing value
        
        المعاملات:
            size: xs, sm, md, lg, xl, xxl, xxxl
        
        العائد:
            قيمة المسافة بالبكسل
        """
        spacing_map = {
            "xs": self.spacing.XS,
            "sm": self.spacing.SM,
            "md": self.spacing.MD,
            "lg": self.spacing.LG,
            "xl": self.spacing.XL,
            "xxl": self.spacing.XXL,
            "xxxl": self.spacing.XXXL,
        }
        return spacing_map.get(size.lower(), self.spacing.MD)
    
    def get_padding(self, size: str) -> int:
        """
        الحصول على حشوة داخلية
        Get padding value
        
        المعاملات:
            size: xs, sm, md, lg, xl
        
        العائد:
            قيمة الحشوة بالبكسل
        """
        padding_map = {
            "xs": self.padding_xs,
            "sm": self.padding_sm,
            "md": self.padding_md,
            "lg": self.padding_lg,
            "xl": self.padding_xl,
        }
        return padding_map.get(size.lower(), self.padding_md)
    
    def get_margin(self, size: str) -> int:
        """
        الحصول على هامش خارجي
        Get margin value
        
        المعاملات:
            size: xs, sm, md, lg, xl, xxl
        
        العائد:
            قيمة الهامش بالبكسل
        """
        margin_map = {
            "xs": self.margin_xs,
            "sm": self.margin_sm,
            "md": self.margin_md,
            "lg": self.margin_lg,
            "xl": self.margin_xl,
            "xxl": self.margin_xxl,
        }
        return margin_map.get(size.lower(), self.margin_md)
    
    def get_font_size(self, size: str) -> str:
        """
        الحصول على حجم خط معين
        Get specific font size
        
        المعاملات:
            size: xs, sm, md, lg, xl, xxl, xxxl, huge
        
        العائد:
            حجم الخط كـ string مع px
        """
        font_sizes = {
            "xs": self.typography.SIZE_XS,
            "sm": self.typography.SIZE_SM,
            "md": self.typography.SIZE_MD,
            "lg": self.typography.SIZE_LG,
            "xl": self.typography.SIZE_XL,
            "xxl": self.typography.SIZE_XXL,
            "xxxl": self.typography.SIZE_XXXL,
            "huge": self.typography.SIZE_HUGE,
        }
        return f"{font_sizes.get(size.lower(), self.typography.SIZE_MD)}px"
    
    def get_font_weight(self, weight: str) -> int:
        """
        الحصول على وزن الخط
        Get font weight
        
        المعاملات:
            weight: normal, medium, semibold, bold
        
        العائد:
            قيمة الوزن
        """
        weights = {
            "normal": self.typography.WEIGHT_NORMAL,
            "medium": self.typography.WEIGHT_MEDIUM,
            "semibold": self.typography.WEIGHT_SEMI_BOLD,
            "bold": self.typography.WEIGHT_BOLD,
        }
        return weights.get(weight.lower(), self.typography.WEIGHT_NORMAL)
    
    def get_border_radius(self, size: str) -> str:
        """
        الحصول على نصف قطر الزوايا
        Get border radius value
        
        المعاملات:
            size: none, sm, md, lg, xl, xxl, circle, pill
        
        العائد:
            قيمة نصف القطر مع px
        """
        radii = {
            "none": self.radius.NONE,
            "sm": self.radius.SM,
            "md": self.radius.MD,
            "lg": self.radius.LG,
            "xl": self.radius.XL,
            "xxl": self.radius.XXL,
            "circle": self.radius.CIRCLE,
            "pill": self.radius.PILL,
        }
        return f"{radii.get(size.lower(), self.radius.MD)}px"
    
    def get_shadow(self, size: str) -> str:
        """
        الحصول على ظل معين
        Get specific shadow
        
        المعاملات:
            size: small, medium, large, hover
        
        العائد:
            قيمة الظل
        """
        shadows = {
            "small": self.shadow_small,
            "medium": self.shadow_medium,
            "large": self.shadow_large,
            "hover": self.shadow_hover,
        }
        return shadows.get(size.lower(), self.shadow_small)
    
    def get_transition(self, property_name: str = "all", duration: str = "normal") -> str:
        """
        الحصول على قيمة transition
        Get transition value
        
        المعاملات:
            property_name: الخاصية (all, background, color, etc.)
            duration: fast, normal, slow
        
        العائد:
            قيمة transition
        """
        durations = {
            "fast": self.transition_duration_fast,
            "normal": self.transition_duration_normal,
            "slow": self.transition_duration_slow,
        }
        dur = durations.get(duration, self.transition_duration_normal)
        return f"{property_name} {dur}ms ease-in-out"
    
    def is_dark_mode(self) -> bool:
        """
        التحقق مما إذا كان الثيم داكن
        Check if theme is dark mode
        
        ✅ مصحح: إضافة fallback آمن للقيم غير الصالحة
        
        العائد:
            True إذا كان داكن، False إذا كان فاتح
        """
        # التحقق من لون الخلفية
        if self.background and isinstance(self.background, str) and self.background.startswith('#'):
            try:
                # إزالة # وتحويل إلى RGB
                hex_color = self.background.lstrip('#')
                
                # دعم الألوان المختصرة (مثل #FFF)
                if len(hex_color) == 3:
                    r = int(hex_color[0] * 2, 16)
                    g = int(hex_color[1] * 2, 16)
                    b = int(hex_color[2] * 2, 16)
                elif len(hex_color) == 6:
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                else:
                    return False
                
                # حساب السطوع (معادلة السطوع المدركة)
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                return brightness < 128
            except (ValueError, IndexError, TypeError):
                return False
        return False
    
    def get_contrast_text_color(self) -> str:
        """
        الحصول على لون نص متباين مع الخلفية
        Get contrasting text color based on background
        
        ✅ مصحح: Fallback آمن للقيم غير الصالحة
        
        العائد:
            أبيض أو أسود حسب الخلفية
        """
        try:
            if self.is_dark_mode():
                return "#FFFFFF"
            return "#111827"
        except Exception:
            # Fallback آمن في حالة حدوث أي خطأ
            return "#111827"
    
    def to_css_variables(self) -> str:
        """
        تحويل الثيم إلى متغيرات CSS
        Convert theme to CSS variables
        
        العائد:
            نص CSS يحتوي على متغيرات الثيم
        """
        return f"""
            :root {{
                --primary: {self.primary};
                --primary-dark: {self.primary_dark};
                --primary-light: {self.primary_light};
                --secondary: {self.secondary};
                --secondary-dark: {self.secondary_dark};
                --secondary-light: {self.secondary_light};
                --success: {self.success};
                --error: {self.error};
                --warning: {self.warning};
                --info: {self.info};
                --background: {self.background};
                --surface: {self.surface};
                --text-primary: {self.text_primary};
                --text-secondary: {self.text_secondary};
                --border: {self.border};
                --border-radius: {self.radius.MD}px;
                --transition: {self.get_transition()};
                --shadow-small: {self.shadow_small};
                --shadow-medium: {self.shadow_medium};
                --shadow-large: {self.shadow_large};
            }}
        """
    
    def to_dict(self) -> Dict[str, Any]:
        """
        تحويل الثيم إلى قاموس للتسلسل
        Convert theme to dictionary for serialization
        
        العائد:
            قاموس يحتوي على جميع قيم الثيم
        """
        return {
            "name": self.name,
            "display_name": self.display_name,
            "version": self.version,
            "colors": {
                "primary": self.primary,
                "primary_dark": self.primary_dark,
                "primary_light": self.primary_light,
                "secondary": self.secondary,
                "secondary_dark": self.secondary_dark,
                "secondary_light": self.secondary_light,
                "success": self.success,
                "success_dark": self.success_dark,
                "success_light": self.success_light,
                "error": self.error,
                "error_dark": self.error_dark,
                "error_light": self.error_light,
                "warning": self.warning,
                "warning_dark": self.warning_dark,
                "warning_light": self.warning_light,
                "info": self.info,
                "info_dark": self.info_dark,
                "info_light": self.info_light,
                "background": self.background,
                "background_alt": self.background_alt,
                "surface": self.surface,
                "surface_alt": self.surface_alt,
                "surface_elevated": self.surface_elevated,
                "text_primary": self.text_primary,
                "text_secondary": self.text_secondary,
                "text_disabled": self.text_disabled,
                "text_hint": self.text_hint,
                "text_inverse": self.text_inverse,
                "border": self.border,
                "border_light": self.border_light,
                "border_dark": self.border_dark,
                "border_focus": self.border_focus,
                "hover": self.hover,
                "active": self.active,
                "selected": self.selected,
                "focus": self.focus,
                "pressed": self.pressed,
            },
            "spacing": {
                "xs": self.spacing.XS,
                "sm": self.spacing.SM,
                "md": self.spacing.MD,
                "lg": self.spacing.LG,
                "xl": self.spacing.XL,
                "xxl": self.spacing.XXL,
                "xxxl": self.spacing.XXXL,
            },
            "padding": {
                "xs": self.padding_xs,
                "sm": self.padding_sm,
                "md": self.padding_md,
                "lg": self.padding_lg,
                "xl": self.padding_xl,
            },
            "margin": {
                "xs": self.margin_xs,
                "sm": self.margin_sm,
                "md": self.margin_md,
                "lg": self.margin_lg,
                "xl": self.margin_xl,
                "xxl": self.margin_xxl,
            },
            "typography": {
                "family_primary": self.typography.FAMILY_PRIMARY,
                "family_arabic": self.typography.FAMILY_ARABIC,
                "sizes": {
                    "xs": self.typography.SIZE_XS,
                    "sm": self.typography.SIZE_SM,
                    "md": self.typography.SIZE_MD,
                    "lg": self.typography.SIZE_LG,
                    "xl": self.typography.SIZE_XL,
                    "xxl": self.typography.SIZE_XXL,
                    "xxxl": self.typography.SIZE_XXXL,
                    "huge": self.typography.SIZE_HUGE,
                },
                "weights": {
                    "normal": self.typography.WEIGHT_NORMAL,
                    "medium": self.typography.WEIGHT_MEDIUM,
                    "semibold": self.typography.WEIGHT_SEMI_BOLD,
                    "bold": self.typography.WEIGHT_BOLD,
                }
            },
            "radius": {
                "none": self.radius.NONE,
                "sm": self.radius.SM,
                "md": self.radius.MD,
                "lg": self.radius.LG,
                "xl": self.radius.XL,
                "xxl": self.radius.XXL,
                "circle": self.radius.CIRCLE,
                "pill": self.radius.PILL,
            },
            "shadows": {
                "small": self.shadow_small,
                "medium": self.shadow_medium,
                "large": self.shadow_large,
                "hover": self.shadow_hover,
            },
            "sizes": {
                "min_height_button": self.min_height_button,
                "min_height_input": self.min_height_input,
                "min_height_table_row": self.min_height_table_row,
                "sidebar_width_expanded": self.sidebar_width_expanded,
                "sidebar_width_collapsed": self.sidebar_width_collapsed,
                "header_height": self.header_height,
                "footer_height": self.footer_height,
            },
            "opacity": {
                "disabled": self.opacity_disabled,
                "hover": self.opacity_hover,
                "pressed": self.opacity_pressed,
            },
            "transitions": {
                "fast": self.transition_duration_fast,
                "normal": self.transition_duration_normal,
                "slow": self.transition_duration_slow,
            },
            "is_dark": self.is_dark_mode(),
        }
    
    def update_colors(self, colors: Dict[str, str]) -> None:
        """
        تحديث ألوان الثيم
        Update theme colors
        
        المعاملات:
            colors: قاموس يحتوي على الألوان الجديدة
        """
        for key, value in colors.items():
            if hasattr(self, key) and value is not None:
                # التحقق من أن القيمة هي نص (لون صالح)
                if isinstance(value, str):
                    setattr(self, key, value)
    
    def reset_to_defaults(self) -> None:
        """
        إعادة تعيين الثيم إلى القيم الافتراضية
        Reset theme to default values
        """
        # إعادة تعيين الألوان
        self.primary = Colors.PRIMARY
        self.primary_dark = Colors.PRIMARY_DARK
        self.primary_light = Colors.PRIMARY_LIGHT
        self.secondary = Colors.SECONDARY
        self.secondary_dark = Colors.SECONDARY_DARK
        self.secondary_light = Colors.SECONDARY_LIGHT
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
        self.background = Colors.GRAY_50
        self.background_alt = Colors.GRAY_100
        self.surface = Colors.WHITE
        self.surface_alt = Colors.GRAY_50
        self.surface_elevated = Colors.WHITE
        self.text_primary = Colors.GRAY_900
        self.text_secondary = Colors.GRAY_600
        self.text_disabled = Colors.GRAY_400
        self.text_hint = Colors.GRAY_500
        self.text_inverse = Colors.WHITE
        self.border = Colors.GRAY_300
        self.border_light = Colors.GRAY_200
        self.border_dark = Colors.GRAY_400
        self.border_focus = Colors.PRIMARY
        self.hover = Colors.GRAY_100
        self.active = Colors.PRIMARY
        self.selected = Colors.PRIMARY_LIGHT
        self.focus = Colors.PRIMARY
        self.pressed = Colors.GRAY_200
        
        # إعادة تعيين الظلال
        self.shadow_small = "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)"
        self.shadow_medium = "0 3px 6px rgba(0,0,0,0.15), 0 2px 4px rgba(0,0,0,0.12)"
        self.shadow_large = "0 10px 20px rgba(0,0,0,0.15), 0 6px 6px rgba(0,0,0,0.10)"
        self.shadow_hover = "0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22)"
        
        # إعادة تعيين المسافات
        self.margin_xs = 4
        self.margin_sm = 8
        self.margin_md = 12
        self.margin_lg = 16
        self.margin_xl = 24
        self.margin_xxl = 32
        self.padding_xs = 4
        self.padding_sm = 8
        self.padding_md = 12
        self.padding_lg = 16
        self.padding_xl = 24
        
        # إعادة تعيين أحجام العناصر
        self.min_height_button = 36
        self.min_height_input = 40
        self.min_height_table_row = 48
        self.sidebar_width_expanded = 260
        self.sidebar_width_collapsed = 68
        self.header_height = 60
        self.footer_height = 40
        
        # إعادة تعيين الشفافية
        self.opacity_disabled = 0.5
        self.opacity_hover = 0.8
        self.opacity_pressed = 0.9
        
        # إعادة تعيين مدة الحركات
        self.transition_duration_fast = 150
        self.transition_duration_normal = 250
        self.transition_duration_slow = 350


# مثال للاستخدام
if __name__ == "__main__":
    # إنشاء ثيم مخصص للتجربة
    @dataclass
    class CustomTheme(BaseTheme):
        name: str = "custom"
        display_name: str = "Custom Theme"
        version: str = "1.0.0"
        
        def get_stylesheet(self) -> str:
            return f"""
                QWidget {{
                    background-color: {self.background};
                    color: {self.text_primary};
                }}
                QPushButton {{
                    background-color: {self.primary};
                    color: white;
                    border-radius: {self.get_border_radius('md')};
                    padding: {self.get_padding('sm')}px;
                    min-height: {self.min_height_button}px;
                }}
                QPushButton:hover {{
                    background-color: {self.primary_dark};
                }}
            """
    
    # اختبار الثيم
    theme = CustomTheme()
    
    print("=" * 60)
    print("Theme Information / معلومات الثيم")
    print("=" * 60)
    print(f"Name: {theme.name}")
    print(f"Display Name: {theme.display_name}")
    print(f"Version: {theme.version}")
    print(f"Is Dark Mode: {theme.is_dark_mode()}")
    print(f"Contrast Text: {theme.get_contrast_text_color()}")
    
    print("\n" + "=" * 60)
    print("Spacing Test / اختبار المسافات")
    print("=" * 60)
    for size in ["xs", "sm", "md", "lg", "xl", "xxl", "xxxl"]:
        print(f"Spacing {size}: {theme.get_spacing(size)}px")
    
    print("\n" + "=" * 60)
    print("Padding Test / اختبار الحشوات")
    print("=" * 60)
    for size in ["xs", "sm", "md", "lg", "xl"]:
        print(f"Padding {size}: {theme.get_padding(size)}px")
    
    print("\n" + "=" * 60)
    print("CSS Variables / متغيرات CSS")
    print("=" * 60)
    print(theme.to_css_variables())
    
    print("\n" + "=" * 60)
    print("Dictionary Export / تصدير القاموس")
    print("=" * 60)
    theme_dict = theme.to_dict()
    print(f"Keys: {list(theme_dict.keys())}")
    print(f"Colors count: {len(theme_dict['colors'])}")
    print(f"Spacing values: {theme_dict['spacing']}")