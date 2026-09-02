# core/infrastructure/db/postgres/settings_repository.py
"""Settings Repository - تخزين الإعدادات في قاعدة البيانات"""

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import json
import logging

from core.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# ✅ الإصلاح 1: دالة utc_now متوافقة مع جميع الإصدارات
# =============================================================================

def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC - متوافق مع جميع إصدارات Python"""
    if hasattr(timezone, 'UTC'):
        return datetime.now(timezone.UTC)
    else:
        return datetime.now(timezone.utc)


# =============================================================================
# SettingsRepository - المستودع الأساسي
# =============================================================================

class SettingsRepository:
    """مستودع الإعدادات - يخزن في جدول settings في قاعدة البيانات"""
    
    def __init__(self):
        self._engine = create_engine(settings.database.connection_string)
    
    # =========================================================================
    # ✅ الإصلاح 2: _ensure_table مع دعم الأعمدة الجديدة
    # =========================================================================
    
    def _ensure_table(self):
        """التأكد من وجود جدول الإعدادات مع الأعمدة المطلوبة"""
        with self._engine.connect() as conn:
            # إنشاء الجدول إذا لم يكن موجوداً
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS settings (
                    key VARCHAR(255) PRIMARY KEY,
                    value TEXT,
                    category VARCHAR(100) DEFAULT 'general',
                    is_json BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # ✅ إضافة عمود category إذا لم يكن موجوداً
            try:
                conn.execute(text("""
                    ALTER TABLE settings ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'general'
                """))
            except Exception:
                pass
            
            # ✅ إضافة عمود is_json إذا لم يكن موجوداً
            try:
                conn.execute(text("""
                    ALTER TABLE settings ADD COLUMN IF NOT EXISTS is_json BOOLEAN DEFAULT FALSE
                """))
            except Exception:
                pass
            
            # ✅ إضافة عمود created_at إذا لم يكن موجوداً
            try:
                conn.execute(text("""
                    ALTER TABLE settings ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                """))
            except Exception:
                pass
            
            conn.commit()
    
    # =========================================================================
    # ✅ الإصلاح 3: set() مع دعم القيم غير النصية
    # =========================================================================
    
    def set(self, key: str, value: Any, category: str = "general") -> bool:
        """
        تخزين قيمة إعداد
        
        ✅ محدث: يدعم القيم غير النصية (تخزن كـ JSON)
        
        Args:
            key: مفتاح الإعداد
            value: القيمة (نص، رقم، قاموس، قائمة)
            category: فئة الإعداد (للتنظيم)
        """
        try:
            self._ensure_table()
            
            # تحديد ما إذا كانت القيمة JSON
            is_json = isinstance(value, (dict, list))
            value_str = json.dumps(value, ensure_ascii=False) if is_json else str(value)
            
            with Session(self._engine) as session:
                session.execute(
                    text("""
                        INSERT INTO settings (key, value, category, is_json, updated_at)
                        VALUES (:key, :value, :category, :is_json, NOW())
                        ON CONFLICT (key) DO UPDATE SET 
                            value = EXCLUDED.value,
                            category = EXCLUDED.category,
                            is_json = EXCLUDED.is_json,
                            updated_at = NOW()
                    """),
                    {
                        "key": key,
                        "value": value_str,
                        "category": category,
                        "is_json": is_json
                    }
                )
                session.commit()
            return True
        except Exception as e:
            logger.error(f"خطأ في حفظ الإعداد {key}: {e}")
            return False
    
    # =========================================================================
    # ✅ الإصلاح 4: get() مع دعم التحويل التلقائي
    # =========================================================================
    
    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        استرجاع قيمة إعداد
        
        ✅ محدث: يدعم التحويل التلقائي من JSON
        
        Args:
            key: مفتاح الإعداد
            default: القيمة الافتراضية إذا لم يوجد الإعداد
        
        Returns:
            القيمة (نص، رقم، قاموس، قائمة) حسب النوع
        """
        try:
            self._ensure_table()
            with Session(self._engine) as session:
                result = session.execute(
                    text("SELECT value, is_json FROM settings WHERE key = :key"),
                    {"key": key}
                ).first()
                
                if result:
                    value_str, is_json = result
                    if is_json:
                        try:
                            return json.loads(value_str)
                        except json.JSONDecodeError:
                            return value_str
                    return value_str
            return default
        except Exception as e:
            logger.error(f"خطأ في قراءة الإعداد {key}: {e}")
            return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """استرجاع قيمة إعداد كعدد صحيح"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """استرجاع قيمة إعداد كعدد عشري"""
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """استرجاع قيمة إعداد كقيمة منطقية"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def get_json(self, key: str, default: Optional[Dict] = None) -> Dict:
        """استرجاع قيمة إعداد كقاموس JSON"""
        value = self.get(key, default)
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return default or {}
    
    # =========================================================================
    # ✅ الإصلاح 5: get_all() مع ترتيب حسب الفئة
    # =========================================================================
    
    def get_all(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        استرجاع جميع الإعدادات
        
        ✅ محدث: يدعم التصفية حسب الفئة والتحويل التلقائي
        
        Args:
            category: فئة الإعدادات (اختياري)
        
        Returns:
            قاموس بالإعدادات
        """
        try:
            self._ensure_table()
            with Session(self._engine) as session:
                query = "SELECT key, value, is_json FROM settings"
                params = {}
                
                if category:
                    query += " WHERE category = :category"
                    params["category"] = category
                
                results = session.execute(text(query), params).fetchall()
                
                result = {}
                for key, value_str, is_json in results:
                    if is_json:
                        try:
                            result[key] = json.loads(value_str)
                        except json.JSONDecodeError:
                            result[key] = value_str
                    else:
                        result[key] = value_str
                
                return result
        except Exception as e:
            logger.error(f"خطأ في قراءة الإعدادات: {e}")
            return {}
    
    # =========================================================================
    # ✅ الإصلاح 6: get_by_category() - دالة جديدة
    # =========================================================================
    
    def get_by_category(self, category: str) -> Dict[str, Any]:
        """
        الحصول على إعدادات فئة محددة
        
        Args:
            category: اسم الفئة
        
        Returns:
            قاموس بإعدادات الفئة
        """
        return self.get_all(category=category)
    
    def get_categories(self) -> List[str]:
        """
        الحصول على قائمة بجميع الفئات المستخدمة
        
        Returns:
            قائمة بأسماء الفئات
        """
        try:
            self._ensure_table()
            with Session(self._engine) as session:
                results = session.execute(
                    text("SELECT DISTINCT category FROM settings ORDER BY category")
                ).fetchall()
                return [row[0] for row in results if row[0]]
        except Exception as e:
            logger.error(f"خطأ في قراءة الفئات: {e}")
            return []
    
    # =========================================================================
    # ✅ الإصلاح 7: set_bulk() - دالة جديدة للحفظ الجماعي
    # =========================================================================
    
    def set_bulk(self, settings_dict: Dict[str, Any], category: str = "general") -> int:
        """
        حفظ إعدادات متعددة دفعة واحدة
        
        Args:
            settings_dict: قاموس الإعدادات
            category: فئة الإعدادات
        
        Returns:
            عدد الإعدادات المحفوظة
        """
        saved_count = 0
        for key, value in settings_dict.items():
            if self.set(key, value, category):
                saved_count += 1
        return saved_count
    
    # =========================================================================
    # دوال إضافية
    # =========================================================================
    
    def delete(self, key: str) -> bool:
        """حذف إعداد"""
        try:
            self._ensure_table()
            with Session(self._engine) as session:
                session.execute(
                    text("DELETE FROM settings WHERE key = :key"),
                    {"key": key}
                )
                session.commit()
            return True
        except Exception as e:
            logger.error(f"خطأ في حذف الإعداد {key}: {e}")
            return False
    
    def delete_by_category(self, category: str) -> int:
        """
        حذف جميع الإعدادات في فئة محددة
        
        Args:
            category: اسم الفئة
        
        Returns:
            عدد الإعدادات المحذوفة
        """
        try:
            self._ensure_table()
            with Session(self._engine) as session:
                result = session.execute(
                    text("DELETE FROM settings WHERE category = :category"),
                    {"category": category}
                )
                session.commit()
                return result.rowcount
        except Exception as e:
            logger.error(f"خطأ في حذف إعدادات الفئة {category}: {e}")
            return 0


# =============================================================================
# ✅ الإصلاح 8: PostgresSettingsRepository المحسن
# =============================================================================

class PostgresSettingsRepository:
    """توافق مع Domain Layer - يستخدم نفس الجدول"""
    
    def __init__(self, session):
        self._session = session
        self._simple_repo = SettingsRepository()
    
    # =========================================================================
    # ✅ الإصلاح 8: get() مع معالجة أفضل للقيم الافتراضية
    # =========================================================================
    
    def get(self):
        """الحصول على إعدادات النظام ككائن Settings"""
        from core.domain.settings.entities import Settings
        from core.domain.settings.value_objects import (
            UiSettings, InvoicingSettings, PurchasingSettings, ProductSettings,
            CustomerSettings, SupplierSettings, UserSettings, NotificationSettings,
            PrinterSettings, BackupSettings, Theme, Language, Currency
        )
        
        all_settings = self._simple_repo.get_all()
        
        # دالة مساعدة للحصول على قيمة مع تحويل آمن
        def get_value(key: str, default: Any, converter: Optional[callable] = None) -> Any:
            value = all_settings.get(key, default)
            if converter and value is not None:
                try:
                    return converter(value)
                except (ValueError, TypeError):
                    return default
            return value
        
        # دالة مساعدة للقيم المنطقية
        def parse_bool(value: Any, default: bool = False) -> bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return default
        
        # إنشاء كائن Settings من القيم المخزنة
        ui = UiSettings(
            theme=Theme(get_value('theme', 'light')),
            language=Language(get_value('language', 'ar')),
            font_size=int(get_value('font_size', 12)),
            font_family=get_value('font_family', 'Segoe UI'),
            animations_enabled=parse_bool(get_value('animations_enabled', True)),
            animation_speed=int(get_value('animation_speed', 250)),
            sidebar_collapsed=parse_bool(get_value('sidebar_collapsed', False)),
            recent_items_count=int(get_value('recent_items_count', 10)),
            confirm_before_close=parse_bool(get_value('confirm_before_close', True)),
            show_tooltips=parse_bool(get_value('show_tooltips', True)),
            show_status_bar=parse_bool(get_value('show_status_bar', True)),
            auto_save_interval=int(get_value('auto_save_interval', 60)),
        )
        
        invoicing = InvoicingSettings(
            default_currency=Currency(get_value('default_currency', 'USD')),
            default_payment_terms=get_value('default_payment_terms', 'net_30'),
            invoice_prefix=get_value('invoice_prefix', 'INV'),
            invoice_number_length=int(get_value('invoice_number_length', 5)),
            auto_generate_number=parse_bool(get_value('auto_generate_number', True)),
            require_customer=parse_bool(get_value('require_customer', True)),
            require_site=parse_bool(get_value('require_site', False)),
            show_tax=parse_bool(get_value('show_tax', True)),
            default_tax_rate=float(get_value('default_tax_rate', 0)),
            allow_draft_edit=parse_bool(get_value('allow_draft_edit', True)),
            days_before_due=int(get_value('days_before_due', 30)),
            invoice_notes_template=get_value('invoice_notes_template', 'شكراً لتسوقكم معنا'),
        )
        
        purchasing = PurchasingSettings(
            default_currency=Currency(get_value('purchase_default_currency', 'USD')),
            default_payment_terms=get_value('purchase_default_payment_terms', 'net_30'),
            purchase_prefix=get_value('purchase_prefix', 'PO'),
            purchase_number_length=int(get_value('purchase_number_length', 5)),
            auto_generate_number=parse_bool(get_value('purchase_auto_generate_number', True)),
            require_supplier=parse_bool(get_value('require_supplier', True)),
            require_expected_delivery=parse_bool(get_value('require_expected_delivery', False)),
            auto_receive_on_post=parse_bool(get_value('auto_receive_on_post', False)),
        )
        
        products = ProductSettings(
            default_currency=Currency(get_value('product_default_currency', 'USD')),
            default_tax_rate=float(get_value('product_default_tax_rate', 0)),
            default_unit=get_value('product_default_unit', 'قطعة (pc)'),
            low_stock_threshold=int(get_value('low_stock_threshold', 10)),
            enable_batch_tracking=parse_bool(get_value('enable_batch_tracking', False)),
            enable_serial_tracking=parse_bool(get_value('enable_serial_tracking', False)),
            auto_generate_code=parse_bool(get_value('product_auto_generate_code', True)),
            code_prefix=get_value('product_code_prefix', 'P'),
            code_length=int(get_value('product_code_length', 5)),
        )
        
        customers = CustomerSettings(
            default_currency=Currency(get_value('customer_default_currency', 'USD')),
            default_payment_terms=get_value('customer_default_payment_terms', 'net_30'),
            auto_generate_code=parse_bool(get_value('customer_auto_generate_code', True)),
            code_prefix=get_value('customer_code_prefix', 'C'),
            code_length=int(get_value('customer_code_length', 5)),
            require_tax_number=parse_bool(get_value('require_tax_number', False)),
            default_credit_limit=float(get_value('customer_default_credit_limit', 0)),
            enable_credit_check=parse_bool(get_value('enable_credit_check', False)),
        )
        
        suppliers = SupplierSettings(
            default_currency=Currency(get_value('supplier_default_currency', 'USD')),
            default_payment_terms=get_value('supplier_default_payment_terms', 'net_30'),
            auto_generate_code=parse_bool(get_value('supplier_auto_generate_code', True)),
            code_prefix=get_value('supplier_code_prefix', 'S'),
            code_length=int(get_value('supplier_code_length', 5)),
            require_tax_number=parse_bool(get_value('supplier_require_tax_number', False)),
            default_credit_limit=float(get_value('supplier_default_credit_limit', 0)),
        )
        
        users = UserSettings(
            session_timeout_minutes=int(get_value('session_timeout_minutes', 30)),
            max_login_attempts=int(get_value('max_login_attempts', 5)),
            lockout_minutes=int(get_value('lockout_minutes', 15)),
            require_strong_password=parse_bool(get_value('require_strong_password', True)),
            password_min_length=int(get_value('password_min_length', 8)),
            enable_2fa=parse_bool(get_value('enable_2fa', False)),
            audit_log_enabled=parse_bool(get_value('audit_log_enabled', True)),
            max_sessions_per_user=int(get_value('max_sessions_per_user', 3)),
        )
        
        notifications = NotificationSettings(
            enable_system_notifications=parse_bool(get_value('enable_system_notifications', True)),
            enable_email_notifications=parse_bool(get_value('enable_email_notifications', False)),
            enable_sound_notifications=parse_bool(get_value('enable_sound_notifications', True)),
            notification_sound=get_value('notification_sound', 'default'),
            email_smtp_server=get_value('email_smtp_server', ''),
            email_smtp_port=int(get_value('email_smtp_port', 587)),
            email_username=get_value('email_username', ''),
            email_password=get_value('email_password', ''),
            email_from=get_value('email_from', ''),
            low_stock_alert=parse_bool(get_value('low_stock_alert', True)),
            overdue_invoice_alert=parse_bool(get_value('overdue_invoice_alert', True)),
            new_user_alert=parse_bool(get_value('new_user_alert', True)),
            system_update_alert=parse_bool(get_value('system_update_alert', True)),
        )
        
        printer = PrinterSettings(
            default_printer=get_value('default_printer', ''),
            paper_size=get_value('paper_size', 'A4'),
            copies=int(get_value('copies', 1)),
            print_duplex=parse_bool(get_value('print_duplex', False)),
            header_margin=int(get_value('header_margin', 20)),
            footer_margin=int(get_value('footer_margin', 20)),
            left_margin=int(get_value('left_margin', 15)),
            right_margin=int(get_value('right_margin', 15)),
            show_company_logo=parse_bool(get_value('show_company_logo', True)),
            show_company_info=parse_bool(get_value('show_company_info', True)),
            show_footer=parse_bool(get_value('show_footer', True)),
            footer_text=get_value('footer_text', 'شكراً لكم'),
        )
        
        backup = BackupSettings(
            auto_backup_enabled=parse_bool(get_value('auto_backup_enabled', False)),
            backup_interval_hours=int(get_value('backup_interval_hours', 24)),
            backup_retention_days=int(get_value('backup_retention_days', 30)),
            backup_path=get_value('backup_path', './backups'),
            backup_on_exit=parse_bool(get_value('backup_on_exit', True)),
            include_attachments=parse_bool(get_value('include_attachments', True)),
            compress_backup=parse_bool(get_value('compress_backup', True)),
            encrypt_backup=parse_bool(get_value('encrypt_backup', False)),
        )
        
        return Settings(
            ui=ui,
            invoicing=invoicing,
            purchasing=purchasing,
            products=products,
            customers=customers,
            suppliers=suppliers,
            users=users,
            notifications=notifications,
            printer=printer,
            backup=backup,
            version=int(get_value('settings_version', 1)),
            updated_by=get_value('settings_updated_by', 'system'),
        )
    
    # =========================================================================
    # ✅ الإصلاح 9: save() مع تحسين الأداء
    # =========================================================================
    
    def save(self, settings_obj) -> None:
        """
        حفظ إعدادات النظام
        
        ✅ محدث: يستخدم set_bulk() لتحسين الأداء
        """
        repo = SettingsRepository()
        
        # تجميع الإعدادات في قاموس واحد
        settings_dict = {}
        
        # حفظ UI settings
        settings_dict['theme'] = settings_obj.ui.theme.value
        settings_dict['language'] = settings_obj.ui.language.value
        settings_dict['font_size'] = str(settings_obj.ui.font_size)
        settings_dict['font_family'] = settings_obj.ui.font_family
        settings_dict['animations_enabled'] = str(settings_obj.ui.animations_enabled)
        settings_dict['animation_speed'] = str(settings_obj.ui.animation_speed)
        settings_dict['sidebar_collapsed'] = str(settings_obj.ui.sidebar_collapsed)
        settings_dict['recent_items_count'] = str(settings_obj.ui.recent_items_count)
        settings_dict['confirm_before_close'] = str(settings_obj.ui.confirm_before_close)
        settings_dict['show_tooltips'] = str(settings_obj.ui.show_tooltips)
        settings_dict['show_status_bar'] = str(settings_obj.ui.show_status_bar)
        settings_dict['auto_save_interval'] = str(settings_obj.ui.auto_save_interval)
        
        # حفظ Invoicing settings
        settings_dict['default_currency'] = settings_obj.invoicing.default_currency.value
        settings_dict['default_payment_terms'] = settings_obj.invoicing.default_payment_terms
        settings_dict['invoice_prefix'] = settings_obj.invoicing.invoice_prefix
        settings_dict['invoice_number_length'] = str(settings_obj.invoicing.invoice_number_length)
        settings_dict['auto_generate_number'] = str(settings_obj.invoicing.auto_generate_number)
        settings_dict['require_customer'] = str(settings_obj.invoicing.require_customer)
        settings_dict['require_site'] = str(settings_obj.invoicing.require_site)
        settings_dict['show_tax'] = str(settings_obj.invoicing.show_tax)
        settings_dict['default_tax_rate'] = str(settings_obj.invoicing.default_tax_rate)
        settings_dict['allow_draft_edit'] = str(settings_obj.invoicing.allow_draft_edit)
        settings_dict['days_before_due'] = str(settings_obj.invoicing.days_before_due)
        settings_dict['invoice_notes_template'] = settings_obj.invoicing.invoice_notes_template
        
        # حفظ الإعدادات العامة
        settings_dict['settings_version'] = str(settings_obj.version)
        settings_dict['settings_updated_by'] = settings_obj.updated_by
        
        # حفظ دفعة واحدة
        repo.set_bulk(settings_dict, category="system")
    
    def save_category(self, category: str, settings_dict: Dict[str, Any]) -> int:
        """
        حفظ إعدادات فئة محددة
        
        Args:
            category: اسم الفئة
            settings_dict: قاموس الإعدادات
        
        Returns:
            عدد الإعدادات المحفوظة
        """
        return SettingsRepository().set_bulk(settings_dict, category)


# =============================================================================
# دالة مساعدة للوصول السريع
# =============================================================================

_settings_repo = None


def get_settings_repo() -> SettingsRepository:
    """الحصول على نسخة واحدة من مستودع الإعدادات"""
    global _settings_repo
    if _settings_repo is None:
        _settings_repo = SettingsRepository()
    return _settings_repo