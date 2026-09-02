# core/themes/__init__.py
"""
Themes System - نظام الثيمات الموحد للتطبيق
"""

from .theme_manager import ThemeManager
from .base_theme import BaseTheme
from .light_theme import LightTheme
from .dark_theme import DarkTheme
from .theme_constants import Colors, Spacing, Typography, BorderRadius

# ✅ إزالة استيراد 'Theme' غير الموجود
# فقط نحاول استيراد ModernTheme إذا كان موجوداً
try:
    from .modern_theme import ModernTheme
except ImportError:
    ModernTheme = None

__all__ = [
    "ThemeManager",
    "BaseTheme", 
    "LightTheme",
    "DarkTheme",
    "Colors",
    "Spacing", 
    "Typography",
    "BorderRadius",
]

if ModernTheme:
    __all__.append("ModernTheme")