# core/i18n/translation_coverage.py
"""
أداة تحليل تغطية الترجمة والبحث عن النصوص الثابتة.
"""

import os
import re
import json
from pathlib import Path
from typing import List, Set, Tuple, Dict

PROJECT_ROOT = Path(__file__).parent.parent.parent  # يصل إلى جذر المشروع
LOCALE_PATH = Path(__file__).parent / "locale"

# الأنماط التي سنبحث عنها
PATTERNS = {
    "direct_arabic": re.compile(r'["\']([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\u0600-\u06FF]{2,})["\']'),
    "tr_function": re.compile(r'tr\(["\']([\w\.]+)["\']'),
    "qstring_tr": re.compile(r'QObject\.tr\(["\']([\w\.]+)["\']'),
}

# الامتدادات المسموح بها
EXTENSIONS = {'.py', '.ui'}


class TranslationCoverageAnalyzer:
    def __init__(self):
        self.direct_texts: List[Tuple[str, str, int]] = []  # (file, text, line)
        self.used_keys: Set[str] = set()
        self.all_keys: Set[str] = set()
        self.missing_keys: Set[str] = set()
        self.widgets_without_retranslate: List[str] = []

    def scan_files(self):
        """فحص جميع الملفات في المشروع."""
        print("🔍 بدء فشمشروع...")
        for root, _, files in os.walk(PROJECT_ROOT):
            for file in files:
                if Path(file).suffix in EXTENSIONS:
                    self._scan_file(Path(root) / file)

    def _scan_file(self, file_path: Path):
        """فحص ملف واحد."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"⚠️ لا يمكن قراءة الملف {file_path}: {e}")
            return

        rel_path = file_path.relative_to(PROJECT_ROOT)

        for i, line in enumerate(lines, 1):
            # البحث عن النصوص العربية المباشرة
            if match := PATTERNS["direct_arabic"].search(line):
                text = match.group(1)
                if len(text) > 2 and not any(keyword in text for keyword in ["import", "class", "def"]):
                    self.direct_texts.append((str(rel_path), text, i))

            # البحث عن مفاتيح الترجمة المستخدمة
            for match in PATTERNS["tr_function"].finditer(line):
                key = match.group(1)
                self.used_keys.add(key)

    def load_translation_keys(self):
        """تحميل جميع مفاتيح الترجمة من ملفات اللغة."""
        if not LOCALE_PATH.exists():
            print(f"❌ مجلد الترجمة غير موجود: {LOCALE_PATH}")
            return

        for lang_file in LOCALE_PATH.glob("*.json"):
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # تسطيح القاموس للحصول على جميع المفاتيح
                    self._flatten_keys(data, lang_file.stem)
            except Exception as e:
                print(f"⚠️ خطأ في قراءة {lang_file}: {e}")

    def _flatten_keys(self, data: dict, lang: str, parent_key: str = ''):
        """تسطيح القاموس للحصول على جميع المفاتيح."""
        for key, value in data.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                self._flatten_keys(value, lang, new_key)
            else:
                self.all_keys.add(new_key)

    def analyze(self):
        """تحليل وتجميع النتائج."""
        self.load_translation_keys()
        self.missing_keys = self.used_keys - self.all_keys

        print("\n" + "=" * 80)
        print("📊 تقرير تغطية الترجمة - YAseen ERP")
        print("=" * 80)
        
        print(f"\n📈 المفاتيح المستخدمة في الكود: {len(self.used_keys)}")
        print(f"📋 المفاتيح المتاحة في ملفات الترجمة: {len(self.all_keys)}")
        print(f"❌ المفاتيح المفقودة: {len(self.missing_keys)}")
        
        if self.missing_keys:
            print("\n🔑 المفاتيح المفقودة:")
            for key in sorted(self.missing_keys):
                print(f"   - {key}")

        print(f"\n🚫 النصوص العربية المباشرة (Hardcoded): {len(self.direct_texts)}")
        if self.direct_texts:
            print("\n📝 أمثلة على نصوص مباشرة تحتاج إلى `tr(...)`:")
            for file, text, line in self.direct_texts[:15]:
                print(f"   - {file}:{line} -> '{text}'")
            if len(self.direct_texts) > 15:
                print(f"   ... و {len(self.direct_texts)-15} نصاً آخر")

        print("\n" + "=" * 80)

    def save_report(self, output_path: Path):
        """حفظ التقرير في ملف JSON."""
        report = {
            "total_keys_used": len(self.used_keys),
            "total_keys_available": len(self.all_keys),
            "missing_keys_count": len(self.missing_keys),
            "missing_keys": sorted(list(self.missing_keys)),
            "hardcoded_texts_count": len(self.direct_texts),
            "hardcoded_texts": self.direct_texts[:50],  # حد أقصى 50 نصاً للتقرير
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n💾 تم حفظ التقرير في: {output_path}")


def run_coverage_analysis():
    """تشغيل تحليل التغطية."""
    analyzer = TranslationCoverageAnalyzer()
    analyzer.scan_files()
    analyzer.analyze()
    report_path = PROJECT_ROOT / "translation_coverage_report.json"
    analyzer.save_report(report_path)
    
    # إرجاع رمز خطأ إذا كان هناك مشاكل كبيرة
    if analyzer.missing_keys or analyzer.direct_texts:
        print("\n⚠️ هناك نصوص مباشرة أو مفاتيح مفقودة. يرجى مراجعة التقرير.")
        # في CI/CD، يمكن إرجاع 1 للفشل
        # sys.exit(1) 
    else:
        print("\n✅ نظام الترجمة يعمل بشكل ممتاز. لا توجد مشاكل.")


if __name__ == "__main__":
    run_coverage_analysis()