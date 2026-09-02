# core/i18n/build_locale.py
"""
أداة لبناء وتحديث ملفات الترجمة
يمكن تشغيلها لإنشاء ملفات JSON جديدة من القوالب
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


TEMPLATE = {
    "meta": {
        "language": "",
        "name": "",
        "direction": "ltr",
        "version": "1.0.0",
        "updated_at": ""
    },
    "app": {
        "name": "YAseen ERP",
        "title": "",
        "version": "2.0.0"
    },
    "common": {},
    "navigation": {},
    "invoices": {},
    "products": {},
    "customers": {},
    "suppliers": {},
    "accounting": {},
    "settings": {},
    "currency": {},
    "messages": {}
}


LANGUAGES = {
    "ar": {
        "name": "العربية",
        "direction": "rtl",
        "title": "نظام المؤسسات المتكامل"
    },
    "en": {
        "name": "English",
        "direction": "ltr",
        "title": "Enterprise Resource Planning System"
    },
    "fr": {
        "name": "Français",
        "direction": "ltr",
        "title": "Système de Planification des Ressources"
    }
}


def create_language_file(lang_code: str, output_path: Path):
    """إنشاء ملف لغة جديد"""
    if lang_code not in LANGUAGES:
        print(f"❌ Language {lang_code} not defined")
        return False
    
    # نسخ القالب
    data = json.loads(json.dumps(TEMPLATE))
    
    # تعيين البيانات
    data["meta"]["language"] = lang_code
    data["meta"]["name"] = LANGUAGES[lang_code]["name"]
    data["meta"]["direction"] = LANGUAGES[lang_code]["direction"]
    data["meta"]["updated_at"] = datetime.now().isoformat()
    data["app"]["title"] = LANGUAGES[lang_code]["title"]
    
    # إضافة الترجمات الأساسية للعربية
    if lang_code == "ar":
        data = add_arabic_translations(data)
    elif lang_code == "en":
        data = add_english_translations(data)
    
    # حفظ الملف
    output_file = output_path / f"{lang_code}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Created {output_file}")
    return True


def add_arabic_translations(data: Dict) -> Dict:
    """إضافة الترجمات العربية"""
    # Common
    data["common"] = {
        "save": "حفظ",
        "cancel": "إلغاء",
        "delete": "حذف",
        "edit": "تعديل",
        "view": "عرض",
        "add": "إضافة",
        "remove": "إزالة",
        "clear": "مسح",
        "refresh": "تحديث",
        "search": "بحث",
        "filter": "تصفية",
        "export": "تصدير",
        "import": "استيراد",
        "print": "طباعة",
        "preview": "معاينة",
        "close": "إغلاق",
        "back": "رجوع",
        "next": "التالي",
        "previous": "السابق",
        "first": "الأول",
        "last": "الأخير",
        "yes": "نعم",
        "no": "لا",
        "ok": "موافق",
        "confirm": "تأكيد",
        "submit": "إرسال",
        "reset": "إعادة تعيين",
        "loading": "جاري التحميل...",
        "processing": "جاري المعالجة...",
        "no_data": "لا توجد بيانات",
        "error": "خطأ",
        "warning": "تحذير",
        "info": "معلومة",
        "success": "نجاح"
    }
    
    # Navigation
    data["navigation"] = {
        "dashboard": "لوحة التحكم",
        "invoices": "الفواتير",
        "purchasing": "المشتريات",
        "products": "المنتجات",
        "customers": "العملاء",
        "suppliers": "الموردين",
        "accounts": "شجرة الحسابات",
        "funds": "الصناديق النقدية",
        "journal": "قيود اليومية",
        "ledger": "دفتر الأستاذ",
        "reports": "التقارير",
        "settings": "الإعدادات",
        "help": "مساعدة",
        "about": "عن البرنامج",
        "logout": "تسجيل خروج"
    }
    
    return data


def add_english_translations(data: Dict) -> Dict:
    """إضافة الترجمات الإنجليزية"""
    data["common"] = {
        "save": "Save",
        "cancel": "Cancel",
        "delete": "Delete",
        "edit": "Edit",
        "view": "View",
        "add": "Add",
        "remove": "Remove",
        "clear": "Clear",
        "refresh": "Refresh",
        "search": "Search",
        "filter": "Filter",
        "export": "Export",
        "import": "Import",
        "print": "Print",
        "preview": "Preview",
        "close": "Close",
        "back": "Back",
        "next": "Next",
        "previous": "Previous",
        "first": "First",
        "last": "Last",
        "yes": "Yes",
        "no": "No",
        "ok": "OK",
        "confirm": "Confirm",
        "submit": "Submit",
        "reset": "Reset",
        "loading": "Loading...",
        "processing": "Processing...",
        "no_data": "No data available",
        "error": "Error",
        "warning": "Warning",
        "info": "Information",
        "success": "Success"
    }
    
    data["navigation"] = {
        "dashboard": "Dashboard",
        "invoices": "Invoices",
        "purchasing": "Purchasing",
        "products": "Products",
        "customers": "Customers",
        "suppliers": "Suppliers",
        "accounts": "Chart of Accounts",
        "funds": "Cash Funds",
        "journal": "Journal Entries",
        "ledger": "General Ledger",
        "reports": "Reports",
        "settings": "Settings",
        "help": "Help",
        "about": "About",
        "logout": "Logout"
    }
    
    return data


def update_all_locales():
    """تحديث جميع ملفات اللغة"""
    locale_path = Path(__file__).parent / "locale"
    locale_path.mkdir(parents=True, exist_ok=True)
    
    for lang_code in LANGUAGES.keys():
        create_language_file(lang_code, locale_path)
    
    print("\n✅ All locale files updated!")


def validate_locale_files():
    """التحقق من صحة ملفات اللغة"""
    locale_path = Path(__file__).parent / "locale"
    errors = []
    
    for lang_code in LANGUAGES.keys():
        lang_file = locale_path / f"{lang_code}.json"
        
        if not lang_file.exists():
            errors.append(f"Missing: {lang_code}.json")
            continue
        
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # التحقق من البنية الأساسية
            required_keys = ["meta", "app", "common", "navigation"]
            for key in required_keys:
                if key not in data:
                    errors.append(f"{lang_code}.json: missing '{key}' section")
        
        except json.JSONDecodeError as e:
            errors.append(f"{lang_code}.json: invalid JSON - {e}")
        except Exception as e:
            errors.append(f"{lang_code}.json: {e}")
    
    if errors:
        print("❌ Validation errors:")
        for error in errors:
            print(f"   {error}")
        return False
    
    print("✅ All locale files are valid!")
    return True


def main():
    """الدالة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Build and manage translation files")
    parser.add_argument("command", choices=["build", "validate", "update"], 
                        help="Command to execute")
    
    args = parser.parse_args()
    
    if args.command == "build":
        update_all_locales()
    elif args.command == "validate":
        validate_locale_files()
    elif args.command == "update":
        update_all_locales()
        validate_locale_files()


if __name__ == "__main__":
    main()