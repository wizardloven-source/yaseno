# core/currency_fetcher.py
"""
جلب سعر الدولار (شراء وبيع) من موقع sp-today.com
"""
import os
import re
import json
import requests
from datetime import datetime

# مجلد حفظ البيانات
DATA_FOLDER = "currency_data"
RATES_FILE = os.path.join(DATA_FOLDER, "rates.txt")


def ensure_folder():
    """التأكد من وجود المجلد"""
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
        print(f"✅ تم إنشاء مجلد: {DATA_FOLDER}")


def save_rates_to_file(buy_rate, sell_rate):
    """
    حفظ السعرين في ملف txt مع التاريخ
    """
    ensure_folder()
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    # قراءة الملف الحالي إذا وجد
    existing_rates = []
    if os.path.exists(RATES_FILE):
        with open(RATES_FILE, 'r', encoding='utf-8') as f:
            existing_rates = f.readlines()
    
    # إضافة السعر الجديد في الأعلى
    new_line = f"{date_str} | {time_str} | شراء: {buy_rate} | بيع: {sell_rate}\n"
    existing_rates.insert(0, new_line)
    
    # الاحتفاظ بآخر 30 سعر فقط
    existing_rates = existing_rates[:30]
    
    # كتابة الملف
    with open(RATES_FILE, 'w', encoding='utf-8') as f:
        f.writelines(existing_rates)
    
    print(f"✅ تم حفظ السعرين في الملف: شراء={buy_rate}, بيع={sell_rate}")
    return True


def save_rates_to_settings(buy_rate: float, sell_rate: float) -> bool:
    """
    حفظ أسعار الصرف مباشرة في الإعدادات
    
    Args:
        buy_rate: سعر الشراء
        sell_rate: سعر البيع
    
    Returns:
        bool: نجاح العملية
    """
    try:
        from core.infrastructure.db.postgres.settings_repository import SettingsRepository
        settings_repo = SettingsRepository()
        
        settings_repo.set("usd_buy_rate", str(buy_rate))
        settings_repo.set("usd_sell_rate", str(sell_rate))
        settings_repo.set("last_rate_update", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # أيضاً تحديث usd_rate للتوافق مع الإصدارات السابقة
        settings_repo.set("usd_rate", str(sell_rate))
        
        print(f"✅ تم حفظ الأسعار في قاعدة البيانات: شراء {buy_rate} | بيع {sell_rate}")
        return True
    except Exception as e:
        print(f"خطأ في حفظ الأسعار في قاعدة البيانات: {e}")
        return False


def get_latest_rates():
    """
    قراءة آخر سعرين (شراء وبيع) من ملف txt
    """
    ensure_folder()
    
    if not os.path.exists(RATES_FILE):
        return None, None, None
    
    try:
        with open(RATES_FILE, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            if first_line:
                parts = first_line.split(' | ')
                if len(parts) >= 3:
                    date = parts[0]
                    time = parts[1]
                    rates_part = parts[2]
                    
                    buy_match = re.search(r'شراء:\s*([\d\.]+)', rates_part)
                    sell_match = re.search(r'بيع:\s*([\d\.]+)', rates_part)
                    
                    buy_rate = float(buy_match.group(1)) if buy_match else None
                    sell_rate = float(sell_match.group(1)) if sell_match else None
                    
                    return buy_rate, sell_rate, f"{date} {time}"
    except Exception as e:
        print(f"خطأ في قراءة الملف: {e}")
    
    return None, None, None


def get_rates_history():
    """
    قراءة تاريخ الأسعار بالكامل
    """
    ensure_folder()
    
    if not os.path.exists(RATES_FILE):
        return []
    
    rates = []
    try:
        with open(RATES_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split(' | ')
                    if len(parts) >= 3:
                        date = parts[0]
                        time = parts[1]
                        rates_part = parts[2]
                        
                        buy_match = re.search(r'شراء:\s*([\d\.]+)', rates_part)
                        sell_match = re.search(r'بيع:\s*([\d\.]+)', rates_part)
                        
                        buy_rate = float(buy_match.group(1)) if buy_match else None
                        sell_rate = float(sell_match.group(1)) if sell_match else None
                        
                        if buy_rate and sell_rate:
                            rates.append({
                                'date': date,
                                'time': time,
                                'buy_rate': buy_rate,
                                'sell_rate': sell_rate
                            })
    except Exception as e:
        print(f"خطأ في قراءة التاريخ: {e}")
    
    return rates


def fetch_rates_from_website():
    """
    جلب سعر الشراء وسعر البيع من موقع sp-today.com
    """
    try:
        print("🔄 جاري الاتصال بموقع sp-today.com...")
        
        url = "https://sp-today.com"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ar,en;q=0.9',
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        html = response.text
        
        # البحث عن سعر الدولار في الصفحة
        buy_rate = None
        sell_rate = None
        
        # أنماط البحث المختلفة
        patterns = [
            r'USD[^>]*>[^<]*<\/[^>]*>[^<]*<\/[^>]*>[^<]*<\/[^>]*>\s*([\d,]+)\s*([\d,]+)',
            r'دولار أمريكي[^>]*>[^<]*<\/[^>]*>[^<]*<\/[^>]*>\s*([\d,]+)\s*([\d,]+)',
            r'شراء[\s\S]*?([\d,]+)[\s\S]*?بيع[\s\S]*?([\d,]+)',
            r'USD.*?(\d{1,3}(?:,\d{3})*).*?(\d{1,3}(?:,\d{3})*)',
            r'(\d{1,3}(?:,\d{3})*)\s*-\s*(\d{1,3}(?:,\d{3})*)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                if len(match) >= 2:
                    try:
                        buy = float(match[0].replace(',', ''))
                        sell = float(match[1].replace(',', ''))
                        if 1000 < buy < 50000 and 1000 < sell < 50000 and buy < sell:
                            buy_rate = buy
                            sell_rate = sell
                            break
                    except:
                        pass
            if buy_rate and sell_rate:
                break
        
        # إذا لم نجد، نبحث عن جميع الأرقام
        if not buy_rate or not sell_rate:
            numbers = re.findall(r'(\d{1,3}(?:,\d{3})*)', html)
            valid_rates = []
            for num in numbers:
                try:
                    rate = float(num.replace(',', ''))
                    if 10000 < rate < 50000:
                        valid_rates.append(rate)
                except:
                    pass
            
            valid_rates = list(set(valid_rates))
            valid_rates.sort()
            
            if len(valid_rates) >= 2:
                buy_rate = valid_rates[0]
                sell_rate = valid_rates[-1]
            elif len(valid_rates) == 1:
                buy_rate = valid_rates[0]
                sell_rate = valid_rates[0] + 70
        
        if buy_rate and sell_rate:
            print(f"✅ تم جلب السعرين: شراء {buy_rate} | بيع {sell_rate}")
            return buy_rate, sell_rate
        else:
            print("❌ لم يتم العثور على الأسعار")
            return None, None
        
    except requests.RequestException as e:
        print(f"❌ خطأ في الاتصال: {e}")
        return None, None
    except Exception as e:
        print(f"❌ خطأ في جلب السعر: {e}")
        return None, None


def update_rates_auto():
    """
    تحديث السعرين تلقائياً (جلب + حفظ في الملفات وقاعدة البيانات)
    """
    print("=" * 50)
    print("🔄 جاري جلب سعر الدولار (شراء وبيع) من sp-today.com...")
    print("=" * 50)
    
    buy_rate, sell_rate = fetch_rates_from_website()
    
    if buy_rate and sell_rate:
        # حفظ في الملف القديم للتوافق
        save_rates_to_file(buy_rate, sell_rate)
        # حفظ في قاعدة البيانات
        save_rates_to_settings(buy_rate, sell_rate)
        print(f"✅ تم تحديث الأسعار بنجاح!")
        return buy_rate, sell_rate, True
    else:
        print("❌ تعذر جلب السعرين - سيتم الاحتفاظ بالأسعار القديمة")
        return None, None, False


def get_current_rates_from_db():
    """
    الحصول على السعرين الحاليين من قاعدة البيانات
    """
    try:
        from core.infrastructure.db.postgres.settings_repository import SettingsRepository
        settings_repo = SettingsRepository()
        
        buy_rate = settings_repo.get("usd_buy_rate")
        sell_rate = settings_repo.get("usd_sell_rate")
        
        if buy_rate and sell_rate:
            return float(buy_rate), float(sell_rate)
    except Exception as e:
        print(f"خطأ في قراءة قاعدة البيانات: {e}")
    
    # قيم افتراضية
    return 12730, 12800


def get_current_rates():
    """
    الحصول على السعرين الحاليين (من الملف أولاً، ثم قاعدة البيانات)
    """
    buy_rate, sell_rate, last_date = get_latest_rates()
    
    if buy_rate and sell_rate:
        return buy_rate, sell_rate
    else:
        return get_current_rates_from_db()


def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
    """
    تحويل العملات
    
    Args:
        amount: المبلغ المراد تحويله
        from_currency: العملة المصدر (USD, LBP, EUR)
        to_currency: العملة الهدف
    
    Returns:
        المبلغ المحول
    """
    if from_currency == to_currency:
        return amount
    
    buy_rate, sell_rate = get_current_rates()
    
    # تحويل من USD إلى LBP
    if from_currency == "USD" and to_currency == "LBP":
        return amount * buy_rate
    
    # تحويل من LBP إلى USD
    if from_currency == "LBP" and to_currency == "USD":
        return amount / sell_rate
    
    # تحويل عبر USD كعملة وسيطة
    if from_currency != "USD":
        amount_in_usd = convert_currency(amount, from_currency, "USD")
        return convert_currency(amount_in_usd, "USD", to_currency)
    
    return amount


def update_rates_button():
    """
    دالة لتحديث الأسعار عند الضغط على زر (مع واجهة المستخدم)
    """
    buy_rate, sell_rate, success = update_rates_auto()
    
    if success:
        print(f"""
╔══════════════════════════════════════════════════════════════╗
║                      ✅ تم تحديث الأسعار                      ║
╠══════════════════════════════════════════════════════════════╣
║  🟢 سعر الشراء (USD → LBP):  {buy_rate:>10.2f} LBP           ║
║  🔴 سعر البيع   (LBP → USD):  {sell_rate:>10.2f} LBP          ║
║  💹 الفرق:                     {(sell_rate - buy_rate):>10.2f} LBP           ║
╚══════════════════════════════════════════════════════════════╝
        """)
    else:
        print("❌ فشل تحديث الأسعار. يرجى التحقق من اتصال الإنترنت.")
    
    return success


# إذا تم تشغيل الملف مباشرة
if __name__ == "__main__":
    update_rates_auto()