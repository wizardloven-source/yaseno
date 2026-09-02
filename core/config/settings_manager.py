# core/config/settings_manager.py

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import logging

logger = logging.getLogger(__name__)

@dataclass
class FiscalSettings:
    start_year: int = 2025
    periods_per_year: int = 12
    auto_create_periods: bool = True

@dataclass
class AccountSettings:
    default_accounts: list = None
    allow_delete_default: bool = False
    allow_edit_default: bool = True
    max_account_depth: int = 5
    code_separator: str = "."
    
    def __post_init__(self):
        if self.default_accounts is None:
            self.default_accounts = []

@dataclass
class SystemSettings:
    company_name: str = "شركتي"
    tax_number: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    date_format: str = "YYYY-MM-DD"
    timezone: str = "Asia/Beirut"
    start_of_week: str = "monday"

@dataclass
class InvoicingSettings:
    prefix: str = "INV-"
    number_length: int = 6
    default_currency: str = "USD"
    default_payment_terms: str = "net_30"
    default_tax_rate: float = 0.0
    tax_inclusive: bool = False
    notes_template: str = "شكراً لتسوقكم معنا"
    auto_generate_number: bool = True
    require_customer: bool = True
    require_payment_method: bool = False

@dataclass
class ProductsSettings:
    code_prefix: str = "P"
    number_length: int = 5
    default_unit: str = "piece"
    default_tax_rate: float = 0.0
    low_stock_threshold: int = 5
    enable_low_stock_alerts: bool = True
    block_sale_out_of_stock: bool = False
    enable_batch_tracking: bool = False
    enable_serial_tracking: bool = False

@dataclass
class CustomersSettings:
    code_prefix: str = "C"
    number_length: int = 5
    default_credit_limit: float = 0.0
    enable_credit_check: bool = False
    allow_negative_credit: bool = False
    enable_loyalty_points: bool = False

@dataclass
class SuppliersSettings:
    code_prefix: str = "S"
    number_length: int = 5
    default_credit_limit: float = 0.0
    enable_supplier_rating: bool = False

@dataclass
class AppSettings:
    fiscal: FiscalSettings = None
    accounts: AccountSettings = None
    system: SystemSettings = None
    invoicing: InvoicingSettings = None
    products: ProductsSettings = None
    customers: CustomersSettings = None
    suppliers: SuppliersSettings = None
    
    def __post_init__(self):
        if self.fiscal is None:
            self.fiscal = FiscalSettings()
        if self.accounts is None:
            self.accounts = AccountSettings()
        if self.system is None:
            self.system = SystemSettings()
        if self.invoicing is None:
            self.invoicing = InvoicingSettings()
        if self.products is None:
            self.products = ProductsSettings()
        if self.customers is None:
            self.customers = CustomersSettings()
        if self.suppliers is None:
            self.suppliers = SuppliersSettings()


class SettingsManager:
    """مدير الإعدادات - يدعم التخصيص الكامل"""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            # مسار ملف الإعدادات في مجلد المستخدم
            self.config_dir = Path.home() / ".ya_seen_erp"
            self.config_file = self.config_dir / "settings.json"
        else:
            self.config_file = Path(config_path)
            self.config_dir = self.config_file.parent
        
        self._settings: Optional[AppSettings] = None
        self._load_settings()
    
    def _ensure_config_dir(self):
        """تأكد من وجود مجلد الإعدادات"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_defaults(self) -> AppSettings:
        """تحميل الإعدادات الافتراضية من ملف JSON"""
        defaults_path = Path(__file__).parent / "defaults.json"
        
        if defaults_path.exists():
            with open(defaults_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return self._dict_to_settings(data)
        
        # إذا لم يوجد ملف defaults.json، استخدم الإعدادات المضمنة
        return AppSettings()
    
    def _dict_to_settings(self, data: Dict) -> AppSettings:
        """تحويل القاموس إلى كائن AppSettings"""
        return AppSettings(
            fiscal=FiscalSettings(**data.get('fiscal', {})),
            accounts=AccountSettings(**data.get('accounts', {})),
            system=SystemSettings(**data.get('system', {})),
            invoicing=InvoicingSettings(**data.get('invoicing', {})),
            products=ProductsSettings(**data.get('products', {})),
            customers=CustomersSettings(**data.get('customers', {})),
            suppliers=SuppliersSettings(**data.get('suppliers', {}))
        )
    
    def _settings_to_dict(self) -> Dict:
        """تحويل كائن AppSettings إلى قاموس"""
        return {
            'fiscal': asdict(self._settings.fiscal),
            'accounts': asdict(self._settings.accounts),
            'system': asdict(self._settings.system),
            'invoicing': asdict(self._settings.invoicing),
            'products': asdict(self._settings.products),
            'customers': asdict(self._settings.customers),
            'suppliers': asdict(self._settings.suppliers),
            'updated_at': datetime.now().isoformat()
        }
    
    def _load_settings(self):
        """تحميل الإعدادات من ملف المستخدم"""
        self._ensure_config_dir()
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._settings = self._dict_to_settings(data)
                    logger.info(f"Settings loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self._settings = self._load_defaults()
        else:
            # أول مرة - استخدم الإعدادات الافتراضية
            self._settings = self._load_defaults()
            self._save_settings()
            logger.info(f"Default settings created at {self.config_file}")
    
    def _save_settings(self):
        """حفظ الإعدادات إلى ملف المستخدم"""
        try:
            self._ensure_config_dir()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings_to_dict(), f, indent=2, ensure_ascii=False)
            logger.info(f"Settings saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def get(self) -> AppSettings:
        """الحصول على الإعدادات الحالية"""
        return self._settings
    
    def update(self, **kwargs):
        """تحديث الإعدادات"""
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                old_value = getattr(self._settings, key)
                setattr(self._settings, key, value)
                logger.info(f"Setting updated: {key} = {value} (was {old_value})")
        
        self._save_settings()
    
    def update_section(self, section: str, values: Dict):
        """تحديث قسم معين من الإعدادات"""
        if hasattr(self._settings, section):
            section_obj = getattr(self._settings, section)
            for key, value in values.items():
                if hasattr(section_obj, key):
                    setattr(section_obj, key, value)
            self._save_settings()
    
    def reset_to_defaults(self):
        """إعادة تعيين الإعدادات إلى القيم الافتراضية"""
        self._settings = self._load_defaults()
        self._save_settings()
        logger.info("Settings reset to defaults")
    
    def export_settings(self, file_path: str):
        """تصدير الإعدادات إلى ملف"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self._settings_to_dict(), f, indent=2, ensure_ascii=False)
        logger.info(f"Settings exported to {file_path}")
    
    def import_settings(self, file_path: str):
        """استيراد الإعدادات من ملف"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self._settings = self._dict_to_settings(data)
            self._save_settings()
        logger.info(f"Settings imported from {file_path}")


# إنشاء نسخة عالمية من مدير الإعدادات
settings_manager = SettingsManager()