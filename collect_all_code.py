import os
import sys
from pathlib import Path
from datetime import datetime
import json
import traceback

# ============================================================
# الإعدادات المحدثة - تحسين البحث باستخدام المجموعات (Sets)
# ============================================================

# مجلدات يتم تخطيها لعدم أهميتها البرمجية أو حجمها الكبير
IGNORE_DIRS = {
    '__pycache__', 'venv', '.venv', 'env', '.git', 'backups', 'logs', 
    'migrations', 'node_modules', 'dist', 'build', '.idea', 
    '.vscode', 'temp', 'temp_backup', '.mypy_cache', 
    '.pytest_cache', 'htmlcov', '.dart_tool', 'ios', 'macos', 
    'windows', 'linux', 'web', 'Runner', 'Assets.xcassets',
    'ephemeral', 'hooks_runner', 'objective_c'
}

# امتدادات الملفات غير النصية التي يجب تجاهلها
IGNORE_FILES = {
    '.pyc', '.db', '.sqlite', '.log', '.bak', '.pyo', '.pyd', 
    '.so', '.dll', '.exe', '.zip', '.rar', '.7z', '.tar', 
    '.gz', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', 
    '.svg', '.mp3', '.mp4', '.wav', '.pdf', '.doc', '.docx', 
    '.xls', '.xlsx', '.dill', '.json', '.cmake', '.txt'
}

# الامتدادات المسموح بجمع محتواها النصي
EXTENSIONS = {
    '.py', '.dart', '.yaml', '.yml', '.ini', '.cfg', 
    '.md', '.rst', '.html', '.css', '.js', '.ts', '.jsx', '.tsx',
    '.xml', '.sh', '.bat', '.ps1', '.dockerfile', '.cmake'
}

# ============================================================
# الدوال المصلحة
# ============================================================

def should_ignore_path(path):
    """
    التحقق مما إذا كان المسار يجب تجاهله بناءً على المجلدات أو الامتداد.
    """
    path_obj = Path(path)
    
    # التحقق من المجلدات المستثناة
    for part in path_obj.parts:
        if part in IGNORE_DIRS:
            return True
    
    # التحقق من امتداد الملف
    if path_obj.suffix.lower() in IGNORE_FILES:
        return True
        
    return False

def read_file_safely(file_path):
    """
    قراءة الملف بشكل آمن مع دعم الترميز العربي ومعالجة أخطاء الوصول.
    """
    # ترتيب التشفيرات لضمان دعم النصوص العربية وملفات UTF-8
    encodings = ['utf-8', 'utf-8-sig', 'cp1256', 'iso-8859-6', 'windows-1256', 'latin-1']
    
    try:
        # حماية من الملفات الضخمة (رفع الحد إلى 10 ميجابايت)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # حد 10 ميجابايت
            return f"⚠️ ملف كبير جداً ({file_size / 1024 / 1024:.1f} MB)، تم تخطي المحتوى.", 'skipped'
            
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # إزالة الأحرف غير القابلة للطباعة
                    content = ''.join(char for char in content if char.isprintable() or char in '\n\r\t')
                    return content, encoding
            except (UnicodeDecodeError, UnicodeError):
                continue
            except Exception as e:
                print(f"   ⚠️ خطأ في قراءة {file_path} بـ {encoding}: {e}")
                continue
                
    except PermissionError:
        return "⚠️ خطأ: لا توجد صلاحية للوصول (Permission Denied).", 'permission_denied'
    except Exception as e:
        return f"⚠️ خطأ غير متوقع: {str(e)}", 'error'
    
    return "⚠️ تعذر القراءة: ترميز غير معروف.", 'unknown'

def create_summary(all_files, start_path):
    """إنشاء ملخص إحصائي للملفات التي تم العثور عليها."""
    summary = [
        "=" * 80,
        "📊 ملخص المشروع (YAseen ERP)",
        "=" * 80,
        f"📁 مسار المشروع: {start_path}",
        f"📅 تاريخ الإنشاء: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"📄 إجمالي الملفات المكتشفة: {len(all_files)}",
        ""
    ]
    
    # إحصائيات المجلدات
    folders = {}
    extensions_count = {}
    for rel_path, _ in all_files:
        folder = os.path.dirname(rel_path) or "Root"
        folders[folder] = folders.get(folder, 0) + 1
        
        # إحصائيات الامتدادات
        ext = os.path.splitext(rel_path)[1] or 'no_extension'
        extensions_count[ext] = extensions_count.get(ext, 0) + 1
    
    summary.append("📁 توزيع الملفات:")
    for folder, count in sorted(folders.items()):
        summary.append(f"   📂 {folder}: {count} ملف")
    
    summary.append("\n📊 توزيع الامتدادات:")
    for ext, count in sorted(extensions_count.items(), key=lambda x: x[1], reverse=True):
        summary.append(f"   📄 {ext}: {count} ملف")
    
    summary.append("\n" + "=" * 80 + "\n")
    return "\n".join(summary)

def collect_code():
    """الدالة الأساسية لجمع الأكواد."""
    project_path = os.getcwd()
    print(f"\n🚀 بدء معالجة المشروع من: {project_path}")
    print(f"📋 سيتم تجاهل المجلدات: {', '.join(sorted(IGNORE_DIRS)[:10])}...")
    print(f"📋 سيتم جمع الامتدادات: {', '.join(sorted(EXTENSIONS))}")
    
    # جمع الملفات باستخدام rglob لضمان الدقة والسرعة
    all_files = []
    total_scanned = 0
    
    for ext in EXTENSIONS:
        for file_path in Path(project_path).rglob(f"*{ext}"):
            total_scanned += 1
            if not should_ignore_path(file_path):
                try:
                    rel_path = file_path.relative_to(project_path)
                    all_files.append((str(rel_path), str(file_path)))
                except ValueError:
                    # في حالة عدم القدرة على جعل المسار نسبياً
                    all_files.append((str(file_path), str(file_path)))

    all_files.sort()

    print(f"\n📊 تم فحص {total_scanned} ملف، تم اختيار {len(all_files)} ملفاً للتجميع.")

    if not all_files:
        print("❌ لم يتم العثور على ملفات برمجية!")
        return

    # إنشاء ملف المخرجات
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(project_path, f"Project_Backup_Code_{timestamp}.txt")
    
    try:
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write(create_summary(all_files, project_path))
            
            success_count = 0
            failed_count = 0
            
            for idx, (rel_path, full_path) in enumerate(all_files, 1):
                print(f"   [{idx}/{len(all_files)}] قراءة: {rel_path}")
                
                content, encoding = read_file_safely(full_path)
                
                out.write(f"\n{'='*80}\n")
                out.write(f"📄 PATH: {rel_path}\n")
                out.write(f"🔢 ENCODING: {encoding}\n")
                out.write(f"{'='*80}\n\n")
                out.write(content)
                out.write("\n\n")
                
                if encoding not in ['unknown', 'error', 'permission_denied', 'skipped']:
                    success_count += 1
                else:
                    failed_count += 1
            
        print(f"\n✅ نجحت العملية!")
        print(f"   📄 تم حفظ كود {success_count} ملف في:")
        print(f"   👉 {output_file}")
        if failed_count > 0:
            print(f"   ⚠️ فشل قراءة {failed_count} ملف")
            
    except Exception as e:
        print(f"❌ خطأ فادح أثناء كتابة ملف الإخراج: {e}")
        traceback.print_exc()

def main():
    print("\n" + "╔" + "═"*48 + "╗")
    print("║" + " "*10 + "YAseen ERP - Code Collector" + " "*11 + "║")
    print("╚" + "═"*48 + "╝")
    
    print("\nخيارات العمل:")
    print("1. جمع كافة الأكواد (للفحص الشامل)")
    print("2. جمع الملفات الأساسية فقط (Python, Dart, YAML)")
    print("3. خروج")
    
    choice = input("\nاختر (1-3): ").strip()
    
    if choice == "1":
        collect_code()
    elif choice == "2":
        # تغيير الامتدادات للملفات الأساسية فقط
        global EXTENSIONS
        EXTENSIONS = {'.py', '.dart', '.yaml', '.yml', '.md', '.json'}
        collect_code()
    else:
        print("👋 مع السلامة!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ تم إيقاف العملية بواسطة المستخدم.")
    except Exception as e:
        print(f"\n❌ خطأ غير متوقع: {e}")
        traceback.print_exc()