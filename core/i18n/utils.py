# core/i18n/utils.py

"""
Utilities for Internationalization (i18n) System
دوال مساعدة لنظام الترجمة والتعريب
الإصدار: 2.0.0 - PySide6
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

# ✅ استيراد PySide6 بدلاً من PyQt6
from PySide6.QtCore import QLocale, QDate, QDateTime, QTime, Qt
from PySide6.QtWidgets import QWidget, QApplication


# =============================================================================
# دوال تحويل التاريخ والوقت
# =============================================================================

class DateFormat(Enum):
    """تنسيقات التاريخ المدعومة"""
    YYYY_MM_DD = "yyyy-MM-dd"
    DD_MM_YYYY = "dd/MM/yyyy"
    MM_DD_YYYY = "MM/dd/yyyy"
    YYYY_MM_DD_AR = "yyyy/MM/dd"
    DD_MM_YYYY_AR = "dd/MM/yyyy"
    

def format_date(date: Any, lang_code: str = "ar", format_type: str = "default") -> str:
    """
    تنسيق التاريخ حسب اللغة
    
    Args:
        date: التاريخ (QDate, datetime, أو string)
        lang_code: رمز اللغة (ar, en, fr)
        format_type: نوع التنسيق (default, short, long, full)
    
    Returns:
        التاريخ المنسق كنص
    """
    if date is None:
        return ""
    
    # تحويل إلى QDate إذا لزم الأمر
    if isinstance(date, str):
        try:
            date = QDate.fromString(date, "yyyy-MM-dd")
        except:
            return date
    elif hasattr(date, 'strftime'):
        # datetime object
        date = QDate(date.year, date.month, date.day)
    
    if not isinstance(date, QDate):
        return str(date)
    
    # تنسيق حسب اللغة
    if lang_code == "ar":
        # العربية: استخدام الأرقام العربية
        if format_type == "short":
            formatted = date.toString("dd/MM/yyyy")
        elif format_type == "long":
            formatted = date.toString("dd MMMM yyyy")
        elif format_type == "full":
            formatted = date.toString("dd MMMM yyyy")
        else:
            formatted = date.toString("yyyy-MM-dd")
        
        # تحويل الأرقام إلى عربية
        formatted = convert_to_arabic_numbers(formatted)
        
    elif lang_code == "fr":
        if format_type == "short":
            formatted = date.toString("dd/MM/yyyy")
        elif format_type == "long":
            formatted = date.toString("dd MMMM yyyy")
        else:
            formatted = date.toString("dd/MM/yyyy")
    else:
        # الإنجليزية
        if format_type == "short":
            formatted = date.toString("MM/dd/yyyy")
        elif format_type == "long":
            formatted = date.toString("MMMM dd, yyyy")
        else:
            formatted = date.toString("yyyy-MM-dd")
    
    return formatted


def format_datetime(dt: Any, lang_code: str = "ar", include_time: bool = True) -> str:
    """
    تنسيق التاريخ والوقت حسب اللغة
    
    Args:
        dt: التاريخ والوقت (QDateTime, datetime, أو string)
        lang_code: رمز اللغة
        include_time: هل نعرض الوقت؟
    
    Returns:
        التاريخ والوقت المنسق
    """
    if dt is None:
        return ""
    
    # تحويل إلى QDateTime إذا لزم الأمر
    if isinstance(dt, str):
        try:
            dt = QDateTime.fromString(dt, "yyyy-MM-dd HH:mm:ss")
        except:
            return dt
    elif hasattr(dt, 'strftime'):
        # datetime object
        dt = QDateTime(dt)
    
    if not isinstance(dt, QDateTime):
        return str(dt)
    
    if lang_code == "ar":
        date_str = dt.toString("dd/MM/yyyy")
        date_str = convert_to_arabic_numbers(date_str)
        
        if include_time:
            time_str = dt.toString("hh:mm:ss")
            time_str = convert_to_arabic_numbers(time_str)
            return f"{date_str} {time_str}"
        return date_str
    
    elif lang_code == "fr":
        date_str = dt.toString("dd/MM/yyyy")
        if include_time:
            return f"{date_str} {dt.toString('HH:mm:ss')}"
        return date_str
    else:
        # الإنجليزية
        date_str = dt.toString("MM/dd/yyyy")
        if include_time:
            return f"{date_str} {dt.toString('hh:mm:ss AP')}"
        return date_str


def format_time(time: Any, lang_code: str = "ar") -> str:
    """
    تنسيق الوقت حسب اللغة
    
    Args:
        time: الوقت (QTime, datetime, أو string)
        lang_code: رمز اللغة
    
    Returns:
        الوقت المنسق
    """
    if time is None:
        return ""
    
    if isinstance(time, str):
        try:
            time = QTime.fromString(time, "hh:mm:ss")
        except:
            return time
    elif hasattr(time, 'strftime'):
        time = QTime(time.hour, time.minute, time.second)
    
    if not isinstance(time, QTime):
        return str(time)
    
    if lang_code == "ar":
        formatted = time.toString("hh:mm:ss")
        return convert_to_arabic_numbers(formatted)
    else:
        return time.toString("hh:mm:ss")


# =============================================================================
# دوال تحويل الأرقام
# =============================================================================

def convert_to_arabic_numbers(text: str) -> str:
    """
    تحويل الأرقام الإنجليزية إلى أرقام عربية
    
    Args:
        text: النص المراد تحويله
    
    Returns:
        النص مع أرقام عربية
    """
    arabic_numbers = {
        '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
        '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
    }
    
    for eng, arb in arabic_numbers.items():
        text = text.replace(eng, arb)
    
    return text


def convert_to_english_numbers(text: str) -> str:
    """
    تحويل الأرقام العربية إلى أرقام إنجليزية
    
    Args:
        text: النص المراد تحويله
    
    Returns:
        النص مع أرقام إنجليزية
    """
    arabic_numbers = {
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
    }
    
    for arb, eng in arabic_numbers.items():
        text = text.replace(arb, eng)
    
    return text


def format_number(number: Any, lang_code: str = "ar", decimals: int = 2) -> str:
    """
    تنسيق الأرقام حسب اللغة
    
    Args:
        number: الرقم المراد تنسيقه
        lang_code: رمز اللغة
        decimals: عدد الخانات العشرية
    
    Returns:
        الرقم المنسق كنص
    """
    if number is None:
        return ""
    
    try:
        num = float(number)
    except (ValueError, TypeError):
        return str(number)
    
    # تنسيق الرقم مع فواصل الآلاف
    if lang_code == "ar":
        # العربية: استخدام الأرقام العربية وفاصل الآلاف
        formatted = f"{num:,.{decimals}f}"
        formatted = formatted.replace(',', '٬')  # فاصل الآلاف عربي
        formatted = convert_to_arabic_numbers(formatted)
    else:
        # الإنجليزية/الفرنسية
        if lang_code == "fr":
            # الفرنسية: فاصل الآلاف مسافة، فاصل عشري فاصلة
            formatted = f"{num:,.{decimals}f}".replace(',', ' ')
            formatted = formatted.replace('.', ',')
        else:
            # الإنجليزية: فاصل الآلاف فاصلة، فاصل عشري نقطة
            formatted = f"{num:,.{decimals}f}"
    
    return formatted


def format_currency(amount: float, currency: str = "USD", lang_code: str = "ar") -> str:
    """
    تنسيق المبالغ المالية حسب اللغة والعملة
    
    Args:
        amount: المبلغ
        currency: رمز العملة (USD, EUR, LBP, GBP)
        lang_code: رمز اللغة
    
    Returns:
        المبلغ المنسق مع العملة
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "LBP": "ل.ل",
        "GBP": "£",
    }
    
    symbol = currency_symbols.get(currency, currency)
    formatted_amount = format_number(amount, lang_code, decimals=2)
    
    if lang_code == "ar":
        # العربية: العملة بعد المبلغ
        return f"{formatted_amount} {symbol}"
    else:
        # الإنجليزية: العملة قبل المبلغ
        return f"{symbol} {formatted_amount}"


# =============================================================================
# دوال تحويل النصوص
# =============================================================================

def pluralize(word: str, count: int, lang_code: str = "ar") -> str:
    """
    صيغة الجمع حسب اللغة
    
    Args:
        word: الكلمة المفردة
        count: العدد
        lang_code: رمز اللغة
    
    Returns:
        الكلمة بصيغة مناسبة للعدد
    """
    if lang_code == "ar":
        # العربية: قواعد معقدة، مبسطة هنا
        if count == 1:
            return word
        elif count == 2:
            return word + "ان"
        elif 3 <= count <= 10:
            return word + "ات"
        else:
            return word + "ات"
    else:
        # الإنجليزية: إضافة s للجمع
        if count == 1:
            return word
        else:
            if word.endswith('y'):
                return word[:-1] + 'ies'
            elif word.endswith('s') or word.endswith('x') or word.endswith('ch'):
                return word + 'es'
            else:
                return word + 's'


def capitalize(text: str, lang_code: str = "ar") -> str:
    """
    تحويل أول حرف إلى كبير حسب اللغة
    
    Args:
        text: النص المراد تحويله
        lang_code: رمز اللغة
    
    Returns:
        النص مع أول حرف كبير
    """
    if not text:
        return text
    
    if lang_code == "ar":
        # العربية: لا يوجد concept للحروف الكبيرة
        return text
    else:
        return text[0].upper() + text[1:]


def truncate(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    قص النص إذا تجاوز طولاً معيناً
    
    Args:
        text: النص المراد قصه
        max_length: الحد الأقصى للطول
        suffix: النص المضاف في النهاية
    
    Returns:
        النص المقصوص
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


# =============================================================================
# دوال مساعدة للحصول على إعدادات اللغة
# =============================================================================

def get_rtl_languages() -> List[str]:
    """الحصول على قائمة اللغات التي تكتب من اليمين إلى اليسار"""
    return ["ar", "fa", "he", "ur"]


def is_rtl_language(lang_code: str) -> bool:
    """التحقق مما إذا كانت اللغة تكتب من اليمين إلى اليسار"""
    return lang_code in get_rtl_languages()


def get_locale_for_language(lang_code: str) -> QLocale:
    """
    الحصول على كائن QLocale للغة معينة
    
    Args:
        lang_code: رمز اللغة (ar, en, fr)
    
    Returns:
        كائن QLocale
    """
    locale_map = {
        "ar": QLocale(QLocale.Language.Arabic, QLocale.Country.SaudiArabia),
        "en": QLocale(QLocale.Language.English, QLocale.Country.UnitedStates),
        "fr": QLocale(QLocale.Language.French, QLocale.Country.France),
    }
    return locale_map.get(lang_code, QLocale())


# =============================================================================
# دوال تحميل ودمج ملفات الترجمة
# =============================================================================

def load_translation_file(file_path: Path) -> Dict[str, Any]:
    """
    تحميل ملف ترجمة JSON
    
    Args:
        file_path: مسار ملف JSON
    
    Returns:
        قاموس الترجمة
    """
    if not file_path.exists():
        return {}
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}


def merge_translations(base: Dict, override: Dict) -> Dict:
    """
    دمج ترجمتين (الترجمة الأساسية + ترجمة مخصصة)
    
    Args:
        base: القاموس الأساسي
        override: القاموس المعدل
    
    Returns:
        القاموس المدمج
    """
    result = base.copy()
    
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = merge_translations(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_translations(translations: Dict, parent_key: str = '') -> Dict[str, str]:
    """
    تحويل قاموس ترجمة متداخل إلى قاموس مسطح
    
    Args:
        translations: القاموس المتداخل
        parent_key: المفتاح الأب الحالي
    
    Returns:
        قاموس مسطح بالمفاتيح المسقطة
    """
    items = []
    
    for key, value in translations.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_translations(value, new_key).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def unflatten_translations(flat_dict: Dict[str, str]) -> Dict[str, Any]:
    """
    تحويل قاموس ترجمة مسطح إلى قاموس متداخل
    
    Args:
        flat_dict: القاموس المسطح (مفاتيح مثل "common.save")
    
    Returns:
        القاموس المتداخل
    """
    result = {}
    
    for key, value in flat_dict.items():
        parts = key.split('.')
        current = result
        
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                current[part] = value
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]
    
    return result


# =============================================================================
# دوال التحقق من صحة ملفات الترجمة
# =============================================================================

def validate_translation_keys(base_keys: set, target_keys: set, lang_name: str) -> List[str]:
    """
    التحقق من صحة مفاتيح الترجمة
    
    Args:
        base_keys: المفاتيح الأساسية (العربية عادة)
        target_keys: المفاتيح المستهدفة
        lang_name: اسم اللغة للتقارير
    
    Returns:
        قائمة بالمفاتيح المفقودة
    """
    missing = base_keys - target_keys
    extra = target_keys - base_keys
    
    errors = []
    
    if missing:
        errors.append(f"[{lang_name}] Missing keys ({len(missing)}): {list(missing)[:10]}...")
    
    if extra:
        errors.append(f"[{lang_name}] Extra keys ({len(extra)}): {list(extra)[:10]}...")
    
    return errors


def validate_translation_file(file_path: Path, reference_keys: set) -> Tuple[bool, List[str]]:
    """
    التحقق من صحة ملف ترجمة مقابل مفاتيح مرجعية
    
    Args:
        file_path: مسار ملف الترجمة
        reference_keys: المفاتيح المرجعية
    
    Returns:
        (صحة, قائمة الأخطاء)
    """
    translations = load_translation_file(file_path)
    flat = flatten_translations(translations)
    
    current_keys = set(flat.keys())
    errors = validate_translation_keys(reference_keys, current_keys, file_path.stem)
    
    return len(errors) == 0, errors


# =============================================================================
# دوال مساعدة لتحديث واجهة المستخدم
# =============================================================================

def retranslate_children(widget, recursive: bool = True):
    """
    إعادة ترجمة جميع أبناء widget
    
    Args:
        widget: الـ widget الأب
        recursive: هل نطبق على جميع الأبناء بشكل متكرر؟
    """
    # تطبيق على الـ widget نفسه إذا كان يدعم
    if hasattr(widget, 'retranslate_ui'):
        try:
            widget.retranslate_ui()
        except Exception as e:
            print(f"Error retranslating {widget}: {e}")
    
    # تطبيق على جميع الأطفال
    for child in widget.findChildren(QWidget):
        if hasattr(child, 'retranslate_ui'):
            try:
                child.retranslate_ui()
            except Exception:
                pass
        
        if recursive:
            retranslate_children(child, recursive=False)


def update_layout_direction(widget, is_rtl: bool):
    """
    تحديث اتجاه تخطيط widget
    
    Args:
        widget: الـ widget المراد تحديثه
        is_rtl: هل الاتجاه من اليمين إلى اليسار؟
    """
    if is_rtl:
        widget.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    else:
        widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    
    # تحديث جميع الأطفال
    for child in widget.findChildren(QWidget):
        update_layout_direction(child, is_rtl)


# =============================================================================
# دوال مساعدة لتوليد معرفات الترجمة
# =============================================================================

def generate_key_id(*parts: str) -> str:
    """
    توليد معرف ترجمة من أجزاء
    
    Args:
        *parts: أجزاء المفتاح
    
    Returns:
        المفتاح الكامل (مثل "invoices.new_invoice")
    """
    return '.'.join(parts)


def extract_key_parts(key: str) -> List[str]:
    """
    استخراج أجزاء المفتاح
    
    Args:
        key: المفتاح الكامل
    
    Returns:
        قائمة الأجزاء
    """
    return key.split('.')


def get_key_category(key: str) -> str:
    """
    الحصول على فئة المفتاح (الجزء الأول)
    
    Args:
        key: المفتاح الكامل
    
    Returns:
        الفئة (مثل "invoices")
    """
    parts = extract_key_parts(key)
    return parts[0] if parts else ""


# =============================================================================
# دوال مساعدة للتطوير
# =============================================================================

def generate_translation_report(translations_dir: Path) -> Dict[str, Any]:
    """
    إنشاء تقرير عن حالة الترجمة
    
    Args:
        translations_dir: المسار الذي يحتوي على ملفات JSON
    
    Returns:
        قاموس يحتوي على التقرير
    """
    report = {
        "total_languages": 0,
        "languages": {},
        "missing_keys": {},
        "completion_percentage": {}
    }
    
    if not translations_dir.exists():
        return report
    
    # تحميل الملفات
    files = {}
    for file_path in translations_dir.glob("*.json"):
        files[file_path.stem] = load_translation_file(file_path)
    
    if not files:
        return report
    
    # استخدام العربية كمرجع
    reference = files.get("ar", {})
    reference_flat = flatten_translations(reference)
    reference_keys = set(reference_flat.keys())
    
    report["total_languages"] = len(files)
    
    for lang_code, data in files.items():
        flat = flatten_translations(data)
        current_keys = set(flat.keys())
        
        missing = reference_keys - current_keys
        extra = current_keys - reference_keys
        
        completion = len(current_keys & reference_keys) / len(reference_keys) * 100 if reference_keys else 0
        
        report["languages"][lang_code] = {
            "total_keys": len(flat),
            "completion": round(completion, 2),
            "missing_count": len(missing),
            "extra_count": len(extra)
        }
        
        if missing:
            report["missing_keys"][lang_code] = list(missing)[:20]  # أول 20 مفتاح فقط
        
        report["completion_percentage"][lang_code] = round(completion, 2)
    
    return report


def print_translation_report(translations_dir: Path):
    """طباعة تقرير الترجمة في وحدة التحكم"""
    report = generate_translation_report(translations_dir)
    
    print("\n" + "=" * 60)
    print("📊 TRANSLATION STATUS REPORT")
    print("=" * 60)
    
    print(f"\n📁 Directory: {translations_dir}")
    print(f"🌐 Languages: {report['total_languages']}")
    
    print("\n📈 Completion percentages:")
    for lang, percentage in report.get("completion_percentage", {}).items():
        bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        print(f"   {lang}: {bar} {percentage}%")
    
    if report.get("missing_keys"):
        print("\n⚠️ Missing keys:")
        for lang, missing in report["missing_keys"].items():
            if missing:
                print(f"   {lang}: {len(missing)} keys missing")
                for key in missing[:5]:
                    print(f"      - {key}")
                if len(missing) > 5:
                    print(f"      ... and {len(missing) - 5} more")
    
    print("\n" + "=" * 60)


# =============================================================================
# دوال مساعدة للحصول على نصوص الترجمة
# =============================================================================

def get_translation_stats(translations_dir: Path) -> Dict[str, int]:
    """
    الحصول على إحصائيات الترجمة
    
    Args:
        translations_dir: مسار مجلد الترجمة
    
    Returns:
        قاموس بالإحصائيات
    """
    stats = {
        "total_keys": 0,
        "total_translations": 0,
        "languages": {},
        "largest_file": "",
        "largest_size": 0
    }
    
    for file_path in translations_dir.glob("*.json"):
        data = load_translation_file(file_path)
        flat = flatten_translations(data)
        size = len(json.dumps(data, ensure_ascii=False))
        
        stats["languages"][file_path.stem] = {
            "keys": len(flat),
            "size": size
        }
        
        if size > stats["largest_size"]:
            stats["largest_size"] = size
            stats["largest_file"] = file_path.stem
    
    if stats["languages"]:
        stats["total_keys"] = max(l["keys"] for l in stats["languages"].values())
        stats["total_translations"] = sum(l["keys"] for l in stats["languages"].values())
    
    return stats


# =============================================================================
# مثال الاستخدام
# =============================================================================

if __name__ == "__main__":
    # اختبار الدوال
    print("Testing i18n utilities...")
    
    # اختبار تنسيق الأرقام
    print(f"\nFormat number (1234567.89):")
    print(f"  English: {format_number(1234567.89, 'en')}")
    print(f"  Arabic: {format_number(1234567.89, 'ar')}")
    print(f"  French: {format_number(1234567.89, 'fr')}")
    
    # اختبار تنسيق العملات
    print(f"\nFormat currency (1234.56 USD):")
    print(f"  English: {format_currency(1234.56, 'USD', 'en')}")
    print(f"  Arabic: {format_currency(1234.56, 'USD', 'ar')}")
    
    # اختبار تنسيق التاريخ
    from PySide6.QtCore import QDate
    today = QDate.currentDate()
    print(f"\nFormat date ({today.toString()}):")
    print(f"  English: {format_date(today, 'en')}")
    print(f"  Arabic: {format_date(today, 'ar')}")
    
    # اختبار الجمع
    print(f"\nPluralize:")
    print(f"  {pluralize('product', 1)}")
    print(f"  {pluralize('product', 5)}")
    print(f"  {pluralize('product', 2)}")
    
    print("\n✅ All tests completed!")