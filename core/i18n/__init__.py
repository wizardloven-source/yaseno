# core/i18n/__init__.py
"""
Internationalization Module - YAseen ERP
"""

from .translator import TranslationManager, tr, get_translator
from .utils import (
    format_date,
    format_datetime,
    format_time,
    format_number,
    format_currency,
    convert_to_arabic_numbers,
    convert_to_english_numbers,
    is_rtl_language,
    get_translation_stats,
)

__all__ = [
    "TranslationManager",
    "tr",
    "get_translator",
    "format_date",
    "format_datetime",
    "format_time",
    "format_number",
    "format_currency",
    "convert_to_arabic_numbers",
    "convert_to_english_numbers",
    "is_rtl_language",
    "get_translation_stats",
]