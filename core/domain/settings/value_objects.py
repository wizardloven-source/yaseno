# core/domain/settings/value_objects.py
"""Value Objects for Settings Domain - النسخة المتطورة مع دعم التسعير"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal


# =============================================================================
# الأنواع الأساسية (Enums)
# =============================================================================

class Theme(Enum):
    """الثيمات المتاحة"""
    LIGHT = "light"
    DARK = "dark"
    MODERN_LIGHT = "modern_light"
    MODERN_DARK = "modern_dark"
    SYSTEM = "system"

    @classmethod
    def get_display_name(cls, theme: str) -> str:
        names = {
            cls.LIGHT.value: "فاتح",
            cls.DARK.value: "داكن",
            cls.MODERN_LIGHT.value: "عصري فاتح",
            cls.MODERN_DARK.value: "عصري داكن",
            cls.SYSTEM.value: "نظام",
        }
        return names.get(theme, theme)


class Language(Enum):
    """اللغات المدعومة"""
    ARABIC = "ar"
    ENGLISH = "en"
    FRENCH = "fr"

    @classmethod
    def get_display_name(cls, lang: str) -> str:
        names = {
            cls.ARABIC.value: "العربية",
            cls.ENGLISH.value: "English",
            cls.FRENCH.value: "Français",
        }
        return names.get(lang, lang)


class Currency(Enum):
    """العملات المدعومة"""
    USD = "USD"
    EUR = "EUR"
    LBP = "LBP"
    GBP = "GBP"

    @classmethod
    def get_display_name(cls, currency: str) -> str:
        names = {
            cls.USD.value: "دولار أمريكي",
            cls.EUR.value: "يورو",
            cls.LBP.value: "ليرة لبنانية",
            cls.GBP.value: "جنيه إسترليني",
        }
        return names.get(currency, currency)


class NotificationSound(Enum):
    """أصوات الإشعارات"""
    NONE = "none"
    DEFAULT = "default"
    SOFT = "soft"
    URGENT = "urgent"
    CUSTOM = "custom"

    @classmethod
    def get_display_name(cls, sound: str) -> str:
        names = {
            cls.NONE.value: "بدون صوت",
            cls.DEFAULT.value: "افتراضي",
            cls.SOFT.value: "هادئ",
            cls.URGENT.value: "طارئ",
            cls.CUSTOM.value: "مخصص",
        }
        return names.get(sound, sound)


class PaperSize(Enum):
    """أحجام الورق"""
    A4 = "A4"
    A5 = "A5"
    LETTER = "Letter"
    THERMAL_80 = "80mm"
    THERMAL_58 = "58mm"

    @classmethod
    def get_display_name(cls, size: str) -> str:
        names = {
            cls.A4.value: "A4",
            cls.A5.value: "A5",
            cls.LETTER.value: "Letter",
            cls.THERMAL_80.value: "80mm (حراري)",
            cls.THERMAL_58.value: "58mm (حراري)",
        }
        return names.get(size, size)


# =============================================================================
# إضافة أنواع جديدة للتسعير
# =============================================================================

class PriceListType(Enum):
    """أنواع قوائم الأسعار"""
    STANDARD = "standard"          # قياسية
    CUSTOMER = "customer"          # مخصصة للعميل
    GROUP = "group"                # مخصصة لمجموعة عملاء
    PROMOTIONAL = "promotional"    # ترويجية
    WHOLESALE = "wholesale"        # جملة
    RETAIL = "retail"              # تجزئة
    SEASONAL = "seasonal"          # موسمية
    CONTRACT = "contract"          # عقود

    @classmethod
    def get_display_name(cls, value: str) -> str:
        names = {
            cls.STANDARD.value: "قياسية",
            cls.CUSTOMER.value: "مخصصة للعميل",
            cls.GROUP.value: "مجموعة عملاء",
            cls.PROMOTIONAL.value: "ترويجية",
            cls.WHOLESALE.value: "جملة",
            cls.RETAIL.value: "تجزئة",
            cls.SEASONAL.value: "موسمية",
            cls.CONTRACT.value: "عقود",
        }
        return names.get(value, value)


class DiscountType(Enum):
    """أنواع الخصومات"""
    PERCENTAGE = "percentage"      # نسبة مئوية
    FIXED_AMOUNT = "fixed_amount"  # مبلغ ثابت
    BUY_X_GET_Y = "buy_x_get_y"    # اشترِ X واحصل على Y
    BUNDLE = "bundle"              # عروض الحزم
    VOLUME = "volume"              # خصم الكميات

    @classmethod
    def get_display_name(cls, value: str) -> str:
        names = {
            cls.PERCENTAGE.value: "نسبة مئوية",
            cls.FIXED_AMOUNT.value: "مبلغ ثابت",
            cls.BUY_X_GET_Y.value: "اشترِ X واحصل على Y",
            cls.BUNDLE.value: "عروض الحزم",
            cls.VOLUME.value: "خصم الكميات",
        }
        return names.get(value, value)


class PricingRuleType(Enum):
    """أنواع قواعد التسعير"""
    PERCENTAGE = "percentage"      # نسبة مئوية
    FIXED_AMOUNT = "fixed_amount"  # مبلغ ثابت
    BUNDLE = "bundle"              # عروض الحزم
    TIERED = "tiered"              # تسعير متدرج

    @classmethod
    def get_display_name(cls, value: str) -> str:
        names = {
            cls.PERCENTAGE.value: "نسبة مئوية",
            cls.FIXED_AMOUNT.value: "مبلغ ثابت",
            cls.BUNDLE.value: "حزمة",
            cls.TIERED.value: "متدرج",
        }
        return names.get(value, value)


# =============================================================================
# الكلاسات الأساسية للإعدادات
# =============================================================================

@dataclass(frozen=True)
class UiSettings:
    """إعدادات واجهة المستخدم"""
    theme: Theme = Theme.LIGHT
    language: Language = Language.ARABIC
    font_size: int = 12
    font_family: str = "Segoe UI"
    animations_enabled: bool = True
    animation_speed: int = 250
    sidebar_collapsed: bool = False
    recent_items_count: int = 10
    confirm_before_close: bool = True
    show_tooltips: bool = True
    show_status_bar: bool = True
    auto_save_interval: int = 60

    def to_dict(self) -> dict:
        return {
            'theme': self.theme.value,
            'language': self.language.value,
            'font_size': self.font_size,
            'font_family': self.font_family,
            'animations_enabled': self.animations_enabled,
            'animation_speed': self.animation_speed,
            'sidebar_collapsed': self.sidebar_collapsed,
            'recent_items_count': self.recent_items_count,
            'confirm_before_close': self.confirm_before_close,
            'show_tooltips': self.show_tooltips,
            'show_status_bar': self.show_status_bar,
            'auto_save_interval': self.auto_save_interval,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UiSettings':
        return cls(
            theme=Theme(data.get('theme', 'light')),
            language=Language(data.get('language', 'ar')),
            font_size=data.get('font_size', 12),
            font_family=data.get('font_family', 'Segoe UI'),
            animations_enabled=data.get('animations_enabled', True),
            animation_speed=data.get('animation_speed', 250),
            sidebar_collapsed=data.get('sidebar_collapsed', False),
            recent_items_count=data.get('recent_items_count', 10),
            confirm_before_close=data.get('confirm_before_close', True),
            show_tooltips=data.get('show_tooltips', True),
            show_status_bar=data.get('show_status_bar', True),
            auto_save_interval=data.get('auto_save_interval', 60),
        )


@dataclass(frozen=True)
class InvoicingSettings:
    """إعدادات الفواتير"""
    default_currency: Currency = Currency.USD
    default_payment_terms: str = "net_30"
    invoice_prefix: str = "INV"
    invoice_number_length: int = 5
    auto_generate_number: bool = True
    require_customer: bool = True
    require_site: bool = False
    show_tax: bool = True
    default_tax_rate: float = 0.0
    allow_draft_edit: bool = True
    days_before_due: int = 30
    invoice_notes_template: str = "شكراً لتسوقكم معنا"


@dataclass(frozen=True)
class PurchasingSettings:
    """إعدادات المشتريات"""
    default_currency: Currency = Currency.USD
    default_payment_terms: str = "net_30"
    purchase_prefix: str = "PO"
    purchase_number_length: int = 5
    auto_generate_number: bool = True
    require_supplier: bool = True
    require_expected_delivery: bool = False
    auto_receive_on_post: bool = False


@dataclass(frozen=True)
class ProductSettings:
    """إعدادات المنتجات"""
    default_currency: Currency = Currency.USD
    default_tax_rate: float = 0.0
    default_unit: str = "قطعة (pc)"
    low_stock_threshold: int = 10
    enable_batch_tracking: bool = False
    enable_serial_tracking: bool = False
    auto_generate_code: bool = True
    code_prefix: str = "P"
    code_length: int = 5


@dataclass(frozen=True)
class CustomerSettings:
    """إعدادات العملاء"""
    default_currency: Currency = Currency.USD
    default_payment_terms: str = "net_30"
    auto_generate_code: bool = True
    code_prefix: str = "C"
    code_length: int = 5
    require_tax_number: bool = False
    default_credit_limit: float = 0.0
    enable_credit_check: bool = False


@dataclass(frozen=True)
class SupplierSettings:
    """إعدادات الموردين"""
    default_currency: Currency = Currency.USD
    default_payment_terms: str = "net_30"
    auto_generate_code: bool = True
    code_prefix: str = "S"
    code_length: int = 5
    require_tax_number: bool = False
    default_credit_limit: float = 0.0


@dataclass(frozen=True)
class UserSettings:
    """إعدادات المستخدمين"""
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    require_strong_password: bool = True
    password_min_length: int = 8
    enable_2fa: bool = False
    audit_log_enabled: bool = True
    max_sessions_per_user: int = 3


@dataclass(frozen=True)
class NotificationSettings:
    """إعدادات الإشعارات"""
    enable_system_notifications: bool = True
    enable_email_notifications: bool = False
    enable_sound_notifications: bool = True
    notification_sound: NotificationSound = NotificationSound.DEFAULT
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    low_stock_alert: bool = True
    overdue_invoice_alert: bool = True
    new_user_alert: bool = True
    system_update_alert: bool = True


@dataclass(frozen=True)
class PrinterSettings:
    """إعدادات الطباعة"""
    default_printer: str = ""
    paper_size: PaperSize = PaperSize.A4
    copies: int = 1
    print_duplex: bool = False
    header_margin: int = 20
    footer_margin: int = 20
    left_margin: int = 15
    right_margin: int = 15
    show_company_logo: bool = True
    show_company_info: bool = True
    show_footer: bool = True
    footer_text: str = "شكراً لكم"


@dataclass(frozen=True)
class BackupSettings:
    """إعدادات النسخ الاحتياطي"""
    auto_backup_enabled: bool = False
    backup_interval_hours: int = 24
    backup_retention_days: int = 30
    backup_path: str = "./backups"
    backup_on_exit: bool = True
    include_attachments: bool = True
    compress_backup: bool = True
    encrypt_backup: bool = False


# =============================================================================
# إعدادات التسعير المتقدمة
# =============================================================================

@dataclass(frozen=True)
class PricingSettings:
    """
    إعدادات التسعير وقوائم الأسعار المتقدمة
    
    هذه الإعدادات تتحكم في:
    - قوائم الأسعار المتعددة
    - تسعير العملاء والمجموعات
    - الخصومات والعروض الترويجية
    - قواعد التسعير الديناميكي
    - تسعير الكميات
    """
    
    # ========== الإعدادات العامة ==========
    
    # تفعيل نظام قوائم الأسعار
    enable_price_lists: bool = True
    
    # قائمة الأسعار الافتراضية
    default_price_list_code: Optional[str] = None
    
    # تطبيق أفضل سعر تلقائياً
    auto_apply_best_price: bool = True
    
    # عرض الخصومات في الفواتير
    show_discounts: bool = True
    
    # تفعيل تسعير العملاء
    enable_customer_pricing: bool = True
    
    # تفعيل تسعير المجموعات
    enable_group_pricing: bool = True
    
    # تفعيل تسعير الكميات
    enable_quantity_pricing: bool = True
    
    # تفعيل العروض الترويجية
    enable_promotional_pricing: bool = True
    
    # تفعيل قواعد التسعير الديناميكي
    enable_pricing_rules: bool = True
    
    # ========== إعدادات الخصومات ==========
    
    # الحد الأقصى للخصم بالنسبة المئوية
    max_discount_percent: Decimal = Decimal('50')
    
    # الحد الأقصى للخصم بالمبلغ
    max_discount_amount: Decimal = Decimal('10000')
    
    # طلب موافقة على الخصومات الكبيرة
    require_approval_for_discount: bool = True
    
    # حد الموافقة على الخصم (نسبة مئوية)
    approval_threshold_percent: Decimal = Decimal('20')
    
    # حد الموافقة على الخصم (مبلغ)
    approval_threshold_amount: Decimal = Decimal('1000')
    
    # السماح بخصم تراكمي
    allow_cumulative_discounts: bool = True
    
    # الحد الأقصى للخصم التراكمي
    max_cumulative_discount_percent: Decimal = Decimal('70')
    
    # ========== إعدادات قواعد التسعير ==========
    
    # ترتيب تطبيق القواعد
    rules_priority: List[str] = field(default_factory=lambda: [
        'customer_specific',  # قواعد خاصة بالعميل
        'group_specific',     # قواعد خاصة بالمجموعة
        'promotional',        # قواعد ترويجية
        'quantity_based',     # قواعد حسب الكمية
        'general'             # قواعد عامة
    ])
    
    # السماح بتجاوز القواعد
    allow_rule_override: bool = True
    
    # ========== إعدادات التسعير حسب الكمية ==========
    
    # تفعيل التسعير المتدرج حسب الكمية
    enable_tiered_pricing: bool = True
    
    # المستويات الافتراضية للتسعير المتدرج
    default_tiers: Dict[int, Decimal] = field(default_factory=lambda: {
        1: Decimal('100'),
        5: Decimal('95'),
        10: Decimal('90'),
        25: Decimal('85'),
        50: Decimal('80'),
        100: Decimal('75'),
    })
    
    # ========== إعدادات العروض الترويجية ==========
    
    # تفعيل العروض الترويجية التلقائية
    enable_auto_promotions: bool = False
    
    # مدة العرض الترويجي الافتراضية (بالأيام)
    default_promotion_duration: int = 7
    
    # الحد الأقصى للعروض الترويجية المتزامنة
    max_active_promotions: int = 5
    
    # ========== إعدادات العملات ==========
    
    # العملة الافتراضية للتسعير
    default_pricing_currency: str = "USD"
    
    # تفعيل تحويل العملات التلقائي
    enable_currency_conversion: bool = True
    
    # مصدر أسعار الصرف
    exchange_rate_source: str = "database"  # database, api, manual
    
    # ========== إعدادات التقارير ==========
    
    # تفعيل تقارير التسعير
    enable_pricing_reports: bool = True
    
    # الاحتفاظ بسجل تغييرات الأسعار (بالأيام)
    price_history_retention_days: int = 365
    
    # تفعيل تحليل أداء التسعير
    enable_pricing_analytics: bool = True
    
    @classmethod
    def default(cls) -> 'PricingSettings':
        """الإعدادات الافتراضية"""
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الإعدادات إلى قاموس"""
        return {
            'enable_price_lists': self.enable_price_lists,
            'default_price_list_code': self.default_price_list_code,
            'auto_apply_best_price': self.auto_apply_best_price,
            'show_discounts': self.show_discounts,
            'enable_customer_pricing': self.enable_customer_pricing,
            'enable_group_pricing': self.enable_group_pricing,
            'enable_quantity_pricing': self.enable_quantity_pricing,
            'enable_promotional_pricing': self.enable_promotional_pricing,
            'enable_pricing_rules': self.enable_pricing_rules,
            'max_discount_percent': float(self.max_discount_percent),
            'max_discount_amount': float(self.max_discount_amount),
            'require_approval_for_discount': self.require_approval_for_discount,
            'approval_threshold_percent': float(self.approval_threshold_percent),
            'approval_threshold_amount': float(self.approval_threshold_amount),
            'allow_cumulative_discounts': self.allow_cumulative_discounts,
            'max_cumulative_discount_percent': float(self.max_cumulative_discount_percent),
            'rules_priority': self.rules_priority,
            'allow_rule_override': self.allow_rule_override,
            'enable_tiered_pricing': self.enable_tiered_pricing,
            'default_tiers': {str(k): float(v) for k, v in self.default_tiers.items()},
            'enable_auto_promotions': self.enable_auto_promotions,
            'default_promotion_duration': self.default_promotion_duration,
            'max_active_promotions': self.max_active_promotions,
            'default_pricing_currency': self.default_pricing_currency,
            'enable_currency_conversion': self.enable_currency_conversion,
            'exchange_rate_source': self.exchange_rate_source,
            'enable_pricing_reports': self.enable_pricing_reports,
            'price_history_retention_days': self.price_history_retention_days,
            'enable_pricing_analytics': self.enable_pricing_analytics,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PricingSettings':
        """إنشاء إعدادات من قاموس"""
        return cls(
            enable_price_lists=data.get('enable_price_lists', True),
            default_price_list_code=data.get('default_price_list_code'),
            auto_apply_best_price=data.get('auto_apply_best_price', True),
            show_discounts=data.get('show_discounts', True),
            enable_customer_pricing=data.get('enable_customer_pricing', True),
            enable_group_pricing=data.get('enable_group_pricing', True),
            enable_quantity_pricing=data.get('enable_quantity_pricing', True),
            enable_promotional_pricing=data.get('enable_promotional_pricing', True),
            enable_pricing_rules=data.get('enable_pricing_rules', True),
            max_discount_percent=Decimal(str(data.get('max_discount_percent', 50))),
            max_discount_amount=Decimal(str(data.get('max_discount_amount', 10000))),
            require_approval_for_discount=data.get('require_approval_for_discount', True),
            approval_threshold_percent=Decimal(str(data.get('approval_threshold_percent', 20))),
            approval_threshold_amount=Decimal(str(data.get('approval_threshold_amount', 1000))),
            allow_cumulative_discounts=data.get('allow_cumulative_discounts', True),
            max_cumulative_discount_percent=Decimal(str(data.get('max_cumulative_discount_percent', 70))),
            rules_priority=data.get('rules_priority', [
                'customer_specific', 'group_specific', 'promotional', 'quantity_based', 'general'
            ]),
            allow_rule_override=data.get('allow_rule_override', True),
            enable_tiered_pricing=data.get('enable_tiered_pricing', True),
            default_tiers={
                int(k): Decimal(str(v)) 
                for k, v in data.get('default_tiers', {}).items()
            } if data.get('default_tiers') else {
                1: Decimal('100'),
                5: Decimal('95'),
                10: Decimal('90'),
                25: Decimal('85'),
                50: Decimal('80'),
                100: Decimal('75'),
            },
            enable_auto_promotions=data.get('enable_auto_promotions', False),
            default_promotion_duration=data.get('default_promotion_duration', 7),
            max_active_promotions=data.get('max_active_promotions', 5),
            default_pricing_currency=data.get('default_pricing_currency', 'USD'),
            enable_currency_conversion=data.get('enable_currency_conversion', True),
            exchange_rate_source=data.get('exchange_rate_source', 'database'),
            enable_pricing_reports=data.get('enable_pricing_reports', True),
            price_history_retention_days=data.get('price_history_retention_days', 365),
            enable_pricing_analytics=data.get('enable_pricing_analytics', True),
        )


@dataclass(frozen=True)
class DiscountSettings:
    """
    إعدادات الخصومات والعروض الترويجية
    """
    
    # أنواع الخصومات المسموحة
    allowed_discount_types: List[str] = field(default_factory=lambda: [
        'percentage', 'fixed_amount', 'buy_x_get_y', 'bundle', 'volume'
    ])
    
    # تفعيل الخصومات التلقائية
    enable_auto_discounts: bool = True
    
    # الحد الأقصى لعدد الخصومات على منتج واحد
    max_discounts_per_product: int = 3
    
    # صلاحية الخصم الافتراضية (بالأيام)
    default_discount_validity_days: int = 30
    
    # السماح بدمج الخصومات
    allow_discount_combining: bool = True
    
    # الخصم الأدنى للتفعيل
    min_discount_amount: Decimal = Decimal('0.50')
    
    # ========== إعدادات العروض ==========
    
    # تفعيل عروض "اشترِ X واحصل على Y"
    enable_buy_x_get_y: bool = True
    
    # تفعيل عروض الحزم
    enable_bundle_discounts: bool = True
    
    # تفعيل خصم الكميات
    enable_volume_discounts: bool = True
    
    # ========== إعدادات الكوبونات ==========
    
    # تفعيل نظام الكوبونات
    enable_coupons: bool = True
    
    # الحد الأقصى لاستخدام الكوبون
    max_coupon_usage_per_customer: int = 1
    
    # صلاحية الكوبون الافتراضية (بالأيام)
    default_coupon_validity_days: int = 14


@dataclass(frozen=True)
class CustomerPricingSettings:
    """
    إعدادات تسعير العملاء
    """
    
    # تفعيل تسعير مخصص للعملاء
    enable_customer_specific_pricing: bool = True
    
    # تفعيل مجموعات العملاء للتسعير
    enable_customer_group_pricing: bool = True
    
    # المجموعات الافتراضية
    default_groups: List[str] = field(default_factory=lambda: [
        'retail', 'wholesale', 'premium', 'vip'
    ])
    
    # تفعيل نقاط الولاء في التسعير
    enable_loyalty_pricing: bool = False
    
    # خصم نقاط الولاء (لكل 100 نقطة)
    loyalty_discount_per_100_points: Decimal = Decimal('1.00')


# =============================================================================
# الكيان الرئيسي للإعدادات
# =============================================================================

@dataclass(frozen=True)
class Settings:
    """الكيان الرئيسي للإعدادات - يحتوي على جميع فئات الإعدادات"""
    
    # الإعدادات الأساسية
    ui: UiSettings = None
    invoicing: InvoicingSettings = None
    purchasing: PurchasingSettings = None
    products: ProductSettings = None
    customers: CustomerSettings = None
    suppliers: SupplierSettings = None
    users: UserSettings = None
    notifications: NotificationSettings = None
    printer: PrinterSettings = None
    backup: BackupSettings = None
    
    # إعدادات التسعير
    pricing: PricingSettings = None
    discounts: DiscountSettings = None
    customer_pricing: CustomerPricingSettings = None
    
    version: int = 1
    updated_at: Optional[datetime] = None
    updated_by: str = "system"

    def __post_init__(self):
        """تهيئة الإعدادات الافتراضية"""
        if self.ui is None:
            object.__setattr__(self, 'ui', UiSettings())
        if self.invoicing is None:
            object.__setattr__(self, 'invoicing', InvoicingSettings())
        if self.purchasing is None:
            object.__setattr__(self, 'purchasing', PurchasingSettings())
        if self.products is None:
            object.__setattr__(self, 'products', ProductSettings())
        if self.customers is None:
            object.__setattr__(self, 'customers', CustomerSettings())
        if self.suppliers is None:
            object.__setattr__(self, 'suppliers', SupplierSettings())
        if self.users is None:
            object.__setattr__(self, 'users', UserSettings())
        if self.notifications is None:
            object.__setattr__(self, 'notifications', NotificationSettings())
        if self.printer is None:
            object.__setattr__(self, 'printer', PrinterSettings())
        if self.backup is None:
            object.__setattr__(self, 'backup', BackupSettings())
        
        # تهيئة إعدادات التسعير
        if self.pricing is None:
            object.__setattr__(self, 'pricing', PricingSettings.default())
        if self.discounts is None:
            object.__setattr__(self, 'discounts', DiscountSettings())
        if self.customer_pricing is None:
            object.__setattr__(self, 'customer_pricing', CustomerPricingSettings())

    def to_dict(self) -> Dict[str, Any]:
        """تحويل الإعدادات إلى قاموس للتسلسل"""
        return {
            'ui': {
                'theme': self.ui.theme.value,
                'language': self.ui.language.value,
                'font_size': self.ui.font_size,
                'font_family': self.ui.font_family,
                'animations_enabled': self.ui.animations_enabled,
                'animation_speed': self.ui.animation_speed,
                'sidebar_collapsed': self.ui.sidebar_collapsed,
                'recent_items_count': self.ui.recent_items_count,
                'confirm_before_close': self.ui.confirm_before_close,
                'show_tooltips': self.ui.show_tooltips,
                'show_status_bar': self.ui.show_status_bar,
                'auto_save_interval': self.ui.auto_save_interval,
            },
            'invoicing': {
                'default_currency': self.invoicing.default_currency.value,
                'default_payment_terms': self.invoicing.default_payment_terms,
                'invoice_prefix': self.invoicing.invoice_prefix,
                'invoice_number_length': self.invoicing.invoice_number_length,
                'auto_generate_number': self.invoicing.auto_generate_number,
                'require_customer': self.invoicing.require_customer,
                'require_site': self.invoicing.require_site,
                'show_tax': self.invoicing.show_tax,
                'default_tax_rate': self.invoicing.default_tax_rate,
                'allow_draft_edit': self.invoicing.allow_draft_edit,
                'days_before_due': self.invoicing.days_before_due,
                'invoice_notes_template': self.invoicing.invoice_notes_template,
            },
            'purchasing': {
                'default_currency': self.purchasing.default_currency.value,
                'default_payment_terms': self.purchasing.default_payment_terms,
                'purchase_prefix': self.purchasing.purchase_prefix,
                'purchase_number_length': self.purchasing.purchase_number_length,
                'auto_generate_number': self.purchasing.auto_generate_number,
                'require_supplier': self.purchasing.require_supplier,
                'require_expected_delivery': self.purchasing.require_expected_delivery,
                'auto_receive_on_post': self.purchasing.auto_receive_on_post,
            },
            'products': {
                'default_currency': self.products.default_currency.value,
                'default_tax_rate': self.products.default_tax_rate,
                'default_unit': self.products.default_unit,
                'low_stock_threshold': self.products.low_stock_threshold,
                'enable_batch_tracking': self.products.enable_batch_tracking,
                'enable_serial_tracking': self.products.enable_serial_tracking,
                'auto_generate_code': self.products.auto_generate_code,
                'code_prefix': self.products.code_prefix,
                'code_length': self.products.code_length,
            },
            'customers': {
                'default_currency': self.customers.default_currency.value,
                'default_payment_terms': self.customers.default_payment_terms,
                'auto_generate_code': self.customers.auto_generate_code,
                'code_prefix': self.customers.code_prefix,
                'code_length': self.customers.code_length,
                'require_tax_number': self.customers.require_tax_number,
                'default_credit_limit': self.customers.default_credit_limit,
                'enable_credit_check': self.customers.enable_credit_check,
            },
            'suppliers': {
                'default_currency': self.suppliers.default_currency.value,
                'default_payment_terms': self.suppliers.default_payment_terms,
                'auto_generate_code': self.suppliers.auto_generate_code,
                'code_prefix': self.suppliers.code_prefix,
                'code_length': self.suppliers.code_length,
                'require_tax_number': self.suppliers.require_tax_number,
                'default_credit_limit': self.suppliers.default_credit_limit,
            },
            'users': {
                'session_timeout_minutes': self.users.session_timeout_minutes,
                'max_login_attempts': self.users.max_login_attempts,
                'lockout_minutes': self.users.lockout_minutes,
                'require_strong_password': self.users.require_strong_password,
                'password_min_length': self.users.password_min_length,
                'enable_2fa': self.users.enable_2fa,
                'audit_log_enabled': self.users.audit_log_enabled,
                'max_sessions_per_user': self.users.max_sessions_per_user,
            },
            'notifications': {
                'enable_system_notifications': self.notifications.enable_system_notifications,
                'enable_email_notifications': self.notifications.enable_email_notifications,
                'enable_sound_notifications': self.notifications.enable_sound_notifications,
                'notification_sound': self.notifications.notification_sound.value,
                'email_smtp_server': self.notifications.email_smtp_server,
                'email_smtp_port': self.notifications.email_smtp_port,
                'email_username': self.notifications.email_username,
                'email_password': self.notifications.email_password,
                'email_from': self.notifications.email_from,
                'low_stock_alert': self.notifications.low_stock_alert,
                'overdue_invoice_alert': self.notifications.overdue_invoice_alert,
                'new_user_alert': self.notifications.new_user_alert,
                'system_update_alert': self.notifications.system_update_alert,
            },
            'printer': {
                'default_printer': self.printer.default_printer,
                'paper_size': self.printer.paper_size.value,
                'copies': self.printer.copies,
                'print_duplex': self.printer.print_duplex,
                'header_margin': self.printer.header_margin,
                'footer_margin': self.printer.footer_margin,
                'left_margin': self.printer.left_margin,
                'right_margin': self.printer.right_margin,
                'show_company_logo': self.printer.show_company_logo,
                'show_company_info': self.printer.show_company_info,
                'show_footer': self.printer.show_footer,
                'footer_text': self.printer.footer_text,
            },
            'backup': {
                'auto_backup_enabled': self.backup.auto_backup_enabled,
                'backup_interval_hours': self.backup.backup_interval_hours,
                'backup_retention_days': self.backup.backup_retention_days,
                'backup_path': self.backup.backup_path,
                'backup_on_exit': self.backup.backup_on_exit,
                'include_attachments': self.backup.include_attachments,
                'compress_backup': self.backup.compress_backup,
                'encrypt_backup': self.backup.encrypt_backup,
            },
            # إضافة إعدادات التسعير
            'pricing': self.pricing.to_dict(),
            'discounts': {
                'allowed_discount_types': self.discounts.allowed_discount_types,
                'enable_auto_discounts': self.discounts.enable_auto_discounts,
                'max_discounts_per_product': self.discounts.max_discounts_per_product,
                'default_discount_validity_days': self.discounts.default_discount_validity_days,
                'allow_discount_combining': self.discounts.allow_discount_combining,
                'min_discount_amount': float(self.discounts.min_discount_amount),
                'enable_buy_x_get_y': self.discounts.enable_buy_x_get_y,
                'enable_bundle_discounts': self.discounts.enable_bundle_discounts,
                'enable_volume_discounts': self.discounts.enable_volume_discounts,
                'enable_coupons': self.discounts.enable_coupons,
                'max_coupon_usage_per_customer': self.discounts.max_coupon_usage_per_customer,
                'default_coupon_validity_days': self.discounts.default_coupon_validity_days,
            },
            'customer_pricing': {
                'enable_customer_specific_pricing': self.customer_pricing.enable_customer_specific_pricing,
                'enable_customer_group_pricing': self.customer_pricing.enable_customer_group_pricing,
                'default_groups': self.customer_pricing.default_groups,
                'enable_loyalty_pricing': self.customer_pricing.enable_loyalty_pricing,
                'loyalty_discount_per_100_points': float(self.customer_pricing.loyalty_discount_per_100_points),
            },
            'version': self.version,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Settings':
        """إنشاء إعدادات من قاموس"""
        return cls(
            ui=UiSettings(
                theme=Theme(data.get('ui', {}).get('theme', 'light')),
                language=Language(data.get('ui', {}).get('language', 'ar')),
                font_size=data.get('ui', {}).get('font_size', 12),
                font_family=data.get('ui', {}).get('font_family', 'Segoe UI'),
                animations_enabled=data.get('ui', {}).get('animations_enabled', True),
                animation_speed=data.get('ui', {}).get('animation_speed', 250),
                sidebar_collapsed=data.get('ui', {}).get('sidebar_collapsed', False),
                recent_items_count=data.get('ui', {}).get('recent_items_count', 10),
                confirm_before_close=data.get('ui', {}).get('confirm_before_close', True),
                show_tooltips=data.get('ui', {}).get('show_tooltips', True),
                show_status_bar=data.get('ui', {}).get('show_status_bar', True),
                auto_save_interval=data.get('ui', {}).get('auto_save_interval', 60),
            ),
            invoicing=InvoicingSettings(
                default_currency=Currency(data.get('invoicing', {}).get('default_currency', 'USD')),
                default_payment_terms=data.get('invoicing', {}).get('default_payment_terms', 'net_30'),
                invoice_prefix=data.get('invoicing', {}).get('invoice_prefix', 'INV'),
                invoice_number_length=data.get('invoicing', {}).get('invoice_number_length', 5),
                auto_generate_number=data.get('invoicing', {}).get('auto_generate_number', True),
                require_customer=data.get('invoicing', {}).get('require_customer', True),
                require_site=data.get('invoicing', {}).get('require_site', False),
                show_tax=data.get('invoicing', {}).get('show_tax', True),
                default_tax_rate=data.get('invoicing', {}).get('default_tax_rate', 0.0),
                allow_draft_edit=data.get('invoicing', {}).get('allow_draft_edit', True),
                days_before_due=data.get('invoicing', {}).get('days_before_due', 30),
                invoice_notes_template=data.get('invoicing', {}).get('invoice_notes_template', 'شكراً لتسوقكم معنا'),
            ),
            purchasing=PurchasingSettings(
                default_currency=Currency(data.get('purchasing', {}).get('default_currency', 'USD')),
                default_payment_terms=data.get('purchasing', {}).get('default_payment_terms', 'net_30'),
                purchase_prefix=data.get('purchasing', {}).get('purchase_prefix', 'PO'),
                purchase_number_length=data.get('purchasing', {}).get('purchase_number_length', 5),
                auto_generate_number=data.get('purchasing', {}).get('auto_generate_number', True),
                require_supplier=data.get('purchasing', {}).get('require_supplier', True),
                require_expected_delivery=data.get('purchasing', {}).get('require_expected_delivery', False),
                auto_receive_on_post=data.get('purchasing', {}).get('auto_receive_on_post', False),
            ),
            products=ProductSettings(
                default_currency=Currency(data.get('products', {}).get('default_currency', 'USD')),
                default_tax_rate=data.get('products', {}).get('default_tax_rate', 0.0),
                default_unit=data.get('products', {}).get('default_unit', 'قطعة (pc)'),
                low_stock_threshold=data.get('products', {}).get('low_stock_threshold', 10),
                enable_batch_tracking=data.get('products', {}).get('enable_batch_tracking', False),
                enable_serial_tracking=data.get('products', {}).get('enable_serial_tracking', False),
                auto_generate_code=data.get('products', {}).get('auto_generate_code', True),
                code_prefix=data.get('products', {}).get('code_prefix', 'P'),
                code_length=data.get('products', {}).get('code_length', 5),
            ),
            customers=CustomerSettings(
                default_currency=Currency(data.get('customers', {}).get('default_currency', 'USD')),
                default_payment_terms=data.get('customers', {}).get('default_payment_terms', 'net_30'),
                auto_generate_code=data.get('customers', {}).get('auto_generate_code', True),
                code_prefix=data.get('customers', {}).get('code_prefix', 'C'),
                code_length=data.get('customers', {}).get('code_length', 5),
                require_tax_number=data.get('customers', {}).get('require_tax_number', False),
                default_credit_limit=data.get('customers', {}).get('default_credit_limit', 0.0),
                enable_credit_check=data.get('customers', {}).get('enable_credit_check', False),
            ),
            suppliers=SupplierSettings(
                default_currency=Currency(data.get('suppliers', {}).get('default_currency', 'USD')),
                default_payment_terms=data.get('suppliers', {}).get('default_payment_terms', 'net_30'),
                auto_generate_code=data.get('suppliers', {}).get('auto_generate_code', True),
                code_prefix=data.get('suppliers', {}).get('code_prefix', 'S'),
                code_length=data.get('suppliers', {}).get('code_length', 5),
                require_tax_number=data.get('suppliers', {}).get('require_tax_number', False),
                default_credit_limit=data.get('suppliers', {}).get('default_credit_limit', 0.0),
            ),
            users=UserSettings(
                session_timeout_minutes=data.get('users', {}).get('session_timeout_minutes', 30),
                max_login_attempts=data.get('users', {}).get('max_login_attempts', 5),
                lockout_minutes=data.get('users', {}).get('lockout_minutes', 15),
                require_strong_password=data.get('users', {}).get('require_strong_password', True),
                password_min_length=data.get('users', {}).get('password_min_length', 8),
                enable_2fa=data.get('users', {}).get('enable_2fa', False),
                audit_log_enabled=data.get('users', {}).get('audit_log_enabled', True),
                max_sessions_per_user=data.get('users', {}).get('max_sessions_per_user', 3),
            ),
            notifications=NotificationSettings(
                enable_system_notifications=data.get('notifications', {}).get('enable_system_notifications', True),
                enable_email_notifications=data.get('notifications', {}).get('enable_email_notifications', False),
                enable_sound_notifications=data.get('notifications', {}).get('enable_sound_notifications', True),
                notification_sound=NotificationSound(data.get('notifications', {}).get('notification_sound', 'default')),
                email_smtp_server=data.get('notifications', {}).get('email_smtp_server', ''),
                email_smtp_port=data.get('notifications', {}).get('email_smtp_port', 587),
                email_username=data.get('notifications', {}).get('email_username', ''),
                email_password=data.get('notifications', {}).get('email_password', ''),
                email_from=data.get('notifications', {}).get('email_from', ''),
                low_stock_alert=data.get('notifications', {}).get('low_stock_alert', True),
                overdue_invoice_alert=data.get('notifications', {}).get('overdue_invoice_alert', True),
                new_user_alert=data.get('notifications', {}).get('new_user_alert', True),
                system_update_alert=data.get('notifications', {}).get('system_update_alert', True),
            ),
            printer=PrinterSettings(
                default_printer=data.get('printer', {}).get('default_printer', ''),
                paper_size=PaperSize(data.get('printer', {}).get('paper_size', 'A4')),
                copies=data.get('printer', {}).get('copies', 1),
                print_duplex=data.get('printer', {}).get('print_duplex', False),
                header_margin=data.get('printer', {}).get('header_margin', 20),
                footer_margin=data.get('printer', {}).get('footer_margin', 20),
                left_margin=data.get('printer', {}).get('left_margin', 15),
                right_margin=data.get('printer', {}).get('right_margin', 15),
                show_company_logo=data.get('printer', {}).get('show_company_logo', True),
                show_company_info=data.get('printer', {}).get('show_company_info', True),
                show_footer=data.get('printer', {}).get('show_footer', True),
                footer_text=data.get('printer', {}).get('footer_text', 'شكراً لكم'),
            ),
            backup=BackupSettings(
                auto_backup_enabled=data.get('backup', {}).get('auto_backup_enabled', False),
                backup_interval_hours=data.get('backup', {}).get('backup_interval_hours', 24),
                backup_retention_days=data.get('backup', {}).get('backup_retention_days', 30),
                backup_path=data.get('backup', {}).get('backup_path', './backups'),
                backup_on_exit=data.get('backup', {}).get('backup_on_exit', True),
                include_attachments=data.get('backup', {}).get('include_attachments', True),
                compress_backup=data.get('backup', {}).get('compress_backup', True),
                encrypt_backup=data.get('backup', {}).get('encrypt_backup', False),
            ),
            pricing=PricingSettings.from_dict(data.get('pricing', {})),
            discounts=DiscountSettings(
                allowed_discount_types=data.get('discounts', {}).get('allowed_discount_types', [
                    'percentage', 'fixed_amount', 'buy_x_get_y', 'bundle', 'volume'
                ]),
                enable_auto_discounts=data.get('discounts', {}).get('enable_auto_discounts', True),
                max_discounts_per_product=data.get('discounts', {}).get('max_discounts_per_product', 3),
                default_discount_validity_days=data.get('discounts', {}).get('default_discount_validity_days', 30),
                allow_discount_combining=data.get('discounts', {}).get('allow_discount_combining', True),
                min_discount_amount=Decimal(str(data.get('discounts', {}).get('min_discount_amount', 0.50))),
                enable_buy_x_get_y=data.get('discounts', {}).get('enable_buy_x_get_y', True),
                enable_bundle_discounts=data.get('discounts', {}).get('enable_bundle_discounts', True),
                enable_volume_discounts=data.get('discounts', {}).get('enable_volume_discounts', True),
                enable_coupons=data.get('discounts', {}).get('enable_coupons', True),
                max_coupon_usage_per_customer=data.get('discounts', {}).get('max_coupon_usage_per_customer', 1),
                default_coupon_validity_days=data.get('discounts', {}).get('default_coupon_validity_days', 14),
            ),
            customer_pricing=CustomerPricingSettings(
                enable_customer_specific_pricing=data.get('customer_pricing', {}).get('enable_customer_specific_pricing', True),
                enable_customer_group_pricing=data.get('customer_pricing', {}).get('enable_customer_group_pricing', True),
                default_groups=data.get('customer_pricing', {}).get('default_groups', ['retail', 'wholesale', 'premium', 'vip']),
                enable_loyalty_pricing=data.get('customer_pricing', {}).get('enable_loyalty_pricing', False),
                loyalty_discount_per_100_points=Decimal(str(data.get('customer_pricing', {}).get('loyalty_discount_per_100_points', 1.00))),
            ),
            version=data.get('version', 1),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            updated_by=data.get('updated_by', 'system'),
        )