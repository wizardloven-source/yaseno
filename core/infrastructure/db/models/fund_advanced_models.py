# core/infrastructure/db/models/fund_advanced_models.py
"""
نماذج متقدمة للصناديق النقدية - دعم العملات المتعددة والتحويل التلقائي
نسخة إنتاج كاملة - بدون بيانات تجريبية
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String, Numeric, DateTime, Boolean, ForeignKey, 
    Index, CheckConstraint, Text, Enum as SQLEnum, 
    UniqueConstraint, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.infrastructure.db.models.account_model import Base
from enum import Enum


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


# =============================================================================
# أنواع الفئات (Enums)
# =============================================================================

class FundAdvancedType(str, Enum):
    """أنواع الصناديق المتقدمة"""
    MAIN = "main"           # رئيسي
    PROJECT = "project"     # مشروع
    RESERVE = "reserve"     # احتياطي
    CLEARING = "clearing"   # وسيط
    ESCROW = "escrow"       # ضمان
    MARGIN = "margin"       # هامش


class ProjectStatus(str, Enum):
    """حالات المشروع"""
    PLANNING = "planning"       # تخطيط
    ACTIVE = "active"           # نشط
    ON_HOLD = "on_hold"         # معلق
    COMPLETED = "completed"     # مكتمل
    CANCELLED = "cancelled"     # ملغي
    ARCHIVED = "archived"       # مؤرشف


class NotificationType(str, Enum):
    """أنواع الإشعارات"""
    BALANCE_ALERT = "balance_alert"
    LIMIT_EXCEEDED = "limit_exceeded"
    TRANSFER_COMPLETED = "transfer_completed"
    TRANSFER_FAILED = "transfer_failed"
    APPROVAL_REQUIRED = "approval_required"
    DAILY_SUMMARY = "daily_summary"
    MONTHLY_REPORT = "monthly_report"


class GainLossType(str, Enum):
    """نوع ربح/خسارة فروقات العملة"""
    GAIN = "GAIN"
    LOSS = "LOSS"
    NONE = "NONE"


class PriceType(str, Enum):
    """نوع السعر"""
    FIXED = "fixed"
    DYNAMIC = "dynamic"
    DISCOUNTED = "discounted"
    PROMOTIONAL = "promotional"


# =============================================================================
# سجل أسعار الصرف التاريخي
# =============================================================================

class ExchangeRateHistoryModel(Base):
    """
    سجل أسعار الصرف التاريخي - لتتبع فروقات العملة
    يخزن جميع أسعار الصرف التاريخية للتدقيق والحسابات
    """
    __tablename__ = "exchange_rate_history"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # العملات
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    
    # سعر الصرف
    buy_rate: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    sell_rate: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    mid_rate: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)  # متوسط السعر
    
    # تاريخ السريان
    effective_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual, api, auto, bank
    
    # مصدر السعر
    provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # central_bank, market, custom
    
    rate_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index("idx_exchange_rate_history_date_currencies", "effective_date", "from_currency", "to_currency"),
        Index("idx_exchange_rate_history_created", "created_at"),
        Index("idx_exchange_rate_history_source", "source"),
        UniqueConstraint("from_currency", "to_currency", "effective_date", name="uq_exchange_rate_period"),
    )


# =============================================================================
# سجل أرباح/خسائر فروقات العملة
# =============================================================================

class CurrencyGainLossModel(Base):
    """
    سجل أرباح/خسائر فروقات العملة
    يوثق جميع فروقات العملة الناتجة عن التحويلات بين العملات المختلفة
    """
    __tablename__ = "currency_gain_loss"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # الحركة المرتبطة
    movement_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    transfer_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    invoice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # تفاصيل العملات
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_from: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    amount_to: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # أسعار الصرف
    rate_used: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    cost_rate: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)  # سعر الشراء الأصلي
    market_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)  # سعر السوق وقت التحويل
    
    # الربح/الخسارة
    gain_loss_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    gain_loss_type: Mapped[str] = mapped_column(String(10), nullable=False)  # GAIN, LOSS
    gain_loss_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=0)
    
    # القيد المحاسبي المرتبط
    journal_entry_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # الفترة المالية
    fiscal_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    fiscal_year: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # بيانات إضافية
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    gain_loss_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index("idx_currency_gain_loss_movement", "movement_id"),
        Index("idx_currency_gain_loss_transfer", "transfer_id"),
        Index("idx_currency_gain_loss_invoice", "invoice_id"),
        Index("idx_currency_gain_loss_date", "created_at"),
        Index("idx_currency_gain_loss_period", "fiscal_period", "fiscal_year"),
        Index("idx_currency_gain_loss_currencies", "from_currency", "to_currency"),
        Index("idx_currency_gain_loss_type", "gain_loss_type"),
        CheckConstraint("gain_loss_amount != 0", name="chk_gain_loss_non_zero"),
    )


# =============================================================================
# نموذج المشروع الموسع
# =============================================================================

class ProjectModel(Base):
    """
    نموذج المشروع - لدعم صناديق المشاريع
    يربط الصناديق النقدية بالمشاريع لتتبع الميزانية والمصروفات
    """
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # معلومات المشروع
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # العميل / المسؤول
    customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    manager_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    manager_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # الميزانية
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    budget_currency: Mapped[str] = mapped_column(String(3), default="USD")
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # المصروف الفعلي
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # المتبقي
    
    # تواريخ المشروع
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # الحالة
    status: Mapped[str] = mapped_column(
        SQLEnum(ProjectStatus, name="project_status_enum"),
        default=ProjectStatus.PLANNING,
        nullable=False,
        index=True
    )
    
    # الصندوق المرتبط
    associated_fund_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    
    # إعدادات التنبيه
    alert_threshold_percent: Mapped[int] = mapped_column(default=85)  # تنبيه عند 85% من الميزانية
    critical_threshold_percent: Mapped[int] = mapped_column(default=95)  # تنبيه حرج عند 95%
    auto_close_on_budget_exceed: Mapped[bool] = mapped_column(default=False)
    
    # بيانات إضافية
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list)
    project_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")
    version: Mapped[int] = mapped_column(default=1)
    
    __table_args__ = (
        Index("idx_projects_status_dates", "status", "start_date", "end_date"),
        Index("idx_projects_customer", "customer_id"),
        Index("idx_projects_manager", "manager_id"),
        Index("idx_projects_associated_fund", "associated_fund_id"),
        Index("idx_projects_budget", "budget_amount", "actual_amount"),
        CheckConstraint("budget_amount >= 0", name="chk_budget_non_negative"),
        CheckConstraint("actual_amount >= 0", name="chk_actual_non_negative"),
        CheckConstraint("alert_threshold_percent BETWEEN 0 AND 100", name="chk_alert_threshold"),
        CheckConstraint("critical_threshold_percent BETWEEN 0 AND 100", name="chk_critical_threshold"),
    )


# =============================================================================
# نموذج الصندوق الموسع (إضافة حقول جديدة)
# =============================================================================

class FundAdvancedModel(Base):
    """
    نموذج الصندوق الموسع - حقول إضافية للصناديق المتقدمة
    يرتبط مع FundModel بعلاقة one-to-one
    """
    __tablename__ = "funds_advanced"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # معرف الصندوق الأساسي (علاقة one-to-one)
    fund_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, unique=True, index=True)
    
    # نوع الصندوق المتقدم
    fund_type: Mapped[str] = mapped_column(
        SQLEnum(FundAdvancedType, name="fund_advanced_type_enum"),
        default=FundAdvancedType.MAIN,
        nullable=False,
        index=True
    )
    
    # للمشاريع
    project_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    
    # حدود الصندوق المتقدمة
    daily_transfer_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # 0 = غير محدود
    monthly_transfer_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    yearly_transfer_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    min_balance_alert: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # تنبيه عند انخفاض الرصيد
    max_balance_alert: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)  # تنبيه عند ارتفاع الرصيد
    
    # صلاحيات وموافقات
    requires_approval_for_transfer: Mapped[bool] = mapped_column(default=False)
    approval_threshold: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    requires_dual_authorization: Mapped[bool] = mapped_column(default=False)  # توقيع مزدوج
    
    # إعدادات العملات والتحويل
    auto_convert_currency: Mapped[bool] = mapped_column(default=True)  # تحويل تلقائي بين العملات
    gain_loss_account_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # حساب فروقات العملة
    default_exchange_rate_provider: Mapped[str] = mapped_column(String(50), default="bank")  # bank, market, custom
    
    # إعدادات التقارير
    include_in_reports: Mapped[bool] = mapped_column(default=True)
    report_group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # بيانات إضافية
    bank_account_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    iban: Mapped[Optional[str]] = mapped_column(String(34), nullable=True)
    swift_code: Mapped[Optional[str]] = mapped_column(String(11), nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")
    version: Mapped[int] = mapped_column(default=1)
    
    advanced_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index("idx_funds_advanced_fund_type", "fund_type", "fund_id"),
        Index("idx_funds_advanced_project", "project_id"),
        Index("idx_funds_advanced_limits", "daily_transfer_limit", "monthly_transfer_limit", "yearly_transfer_limit"),
        Index("idx_funds_advanced_bank", "bank_name", "iban"),
        CheckConstraint("daily_transfer_limit >= 0", name="chk_daily_transfer_limit"),
        CheckConstraint("monthly_transfer_limit >= 0", name="chk_monthly_transfer_limit"),
        CheckConstraint("yearly_transfer_limit >= 0", name="chk_yearly_transfer_limit"),
        CheckConstraint("approval_threshold >= 0", name="chk_approval_threshold"),
    )


# =============================================================================
# جدول أسعار المنتجات متعددة العملات
# =============================================================================

class ProductPriceMultiCurrencyModel(Base):
    """
    أسعار المنتجات بعدة عملات
    يدعم قوائم أسعار متعددة وعملات مختلفة
    """
    __tablename__ = "product_prices_multi_currency"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    
    # العملة والسعر
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # نوع السعر
    price_type: Mapped[str] = mapped_column(
        SQLEnum(PriceType, name="price_type_enum"),
        default=PriceType.FIXED,
        nullable=False
    )
    
    # للأسعار الديناميكية
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)  # السعر بالعملة الأساسية
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")
    markup_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)  # نسبة الربح
    
    # صلاحية السعر
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # قائمة الأسعار (Price List)
    price_list_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    price_list_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # بيانات إضافية
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")
    version: Mapped[int] = mapped_column(default=1)
    
    __table_args__ = (
        Index("idx_product_prices_product_currency", "product_id", "currency"),
        Index("idx_product_prices_validity", "valid_from", "valid_to"),
        Index("idx_product_prices_price_list", "price_list_id"),
        Index("idx_product_prices_type", "price_type"),
        UniqueConstraint("product_id", "currency", "price_list_id", name="uq_product_price_per_list"),
        CheckConstraint("price >= 0", name="chk_price_non_negative"),
        CheckConstraint("markup_percentage >= -100", name="chk_markup_range"),
    )


# =============================================================================
# جدول الفلاتر المحفوظة
# =============================================================================

class SavedFilterModel(Base):
    """
    الفلاتر المحفوظة للمستخدمين
    يسمح بحفظ وتحميل فلاتر البحث في جميع وحدات النظام
    """
    __tablename__ = "saved_filters"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    filter_name: Mapped[str] = mapped_column(String(100), nullable=False)
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # funds, movements, transfers, etc.
    
    # الفلتر مخزن كـ JSON
    filter_data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    
    # هل هو الفلتر الافتراضي؟
    is_default: Mapped[bool] = mapped_column(default=False)
    
    # مشاركة الفلتر مع مستخدمين آخرين
    is_shared: Mapped[bool] = mapped_column(default=False)
    shared_with_roles: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list)
    
    # بيانات إضافية
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(default=0)
    
    filter_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index("idx_saved_filters_user_module", "user_id", "module"),
        Index("idx_saved_filters_default", "user_id", "is_default"),
        Index("idx_saved_filters_name", "user_id", "filter_name"),
        Index("idx_saved_filters_shared", "is_shared"),
        Index("idx_saved_filters_last_used", "last_used_at"),
        UniqueConstraint("user_id", "filter_name", name="uq_filter_per_user"),
    )


# =============================================================================
# ⚠️ ملاحظة: تم نقل نموذج RealTimeNotificationModel إلى notification_model.py
# =============================================================================
# لتجنب التعريف المكرر لجدول funds_notifications،
# يتم استيراد FundsNotificationModel من notification_model.py

try:
    from .notification_model import FundsNotificationModel
    
    # ✅ إضافة اسم مستعار للتوافق مع الكود القديم
    RealTimeNotificationModel = FundsNotificationModel
    
except ImportError as e:
    import warnings
    warnings.warn(
        f"⚠️ فشل استيراد FundsNotificationModel: {e}\n"
        "سيتم إنشاء نموذج وهمي لمنع الأخطاء.",
        ImportWarning
    )
    
    # نموذج وهمي لمنع الأخطاء (لن يتم إنشاء الجدول)
    class RealTimeNotificationModel:
        __tablename__ = "funds_notifications"
        pass


# =============================================================================
# ذاكرة التخزين المؤقت (Cache) - هيكل بيانات للتخزين المؤقت
# =============================================================================

class CacheEntryModel(Base):
    """
    نموذج للتخزين المؤقت في قاعدة البيانات (احتياطي عند إعادة التشغيل)
    يستخدم لتخزين البيانات المؤقتة التي تحتاج إلى بقاء بعد إعادة تشغيل التطبيق
    """
    __tablename__ = "cache_entries"

    cache_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    cache_value: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    
    # بيانات إضافية
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONB, default=list)  # للتصنيف والإبطال الجماعي
    
    cache_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index("idx_cache_expires", "expires_at"),
        Index("idx_cache_tags", "tags", postgresql_using="gin"),
    )


# =============================================================================
# سجل عمليات الصناديق (للتدقيق المتقدم)
# =============================================================================

class FundAuditLogModel(Base):
    """
    سجل تدقيق متقدم لعمليات الصناديق
    يخزن جميع التغييرات على الصناديق والحركات
    """
    __tablename__ = "fund_audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # نوع العملية
    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # CREATE, UPDATE, DELETE, TRANSFER, DEPOSIT, WITHDRAW
    
    # الكيان المتأثر
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # fund, movement, transfer
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    
    # بيانات قبل وبعد التغيير
    old_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # من قام بالعملية
    performed_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # وقت العملية
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    
    # ملاحظات
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    audit_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    __table_args__ = (
        Index("idx_fund_audit_entity", "entity_type", "entity_id"),
        Index("idx_fund_audit_user_time", "performed_by", "performed_at"),
        Index("idx_fund_audit_operation_time", "operation", "performed_at"),
    )


# =============================================================================
# إضافة العلاقات بين النماذج
# =============================================================================

# إضافة العلاقة من FundAdvancedModel إلى FundModel
FundAdvancedModel.fund = relationship(
    "FundModel", 
    back_populates="advanced", 
    foreign_keys=[FundAdvancedModel.fund_id]
)

# إضافة العلاقة من FundAdvancedModel إلى ProjectModel
FundAdvancedModel.project = relationship(
    "ProjectModel", 
    back_populates="fund_advanced", 
    foreign_keys=[FundAdvancedModel.project_id]
)

# إضافة العلاقة العكسية في ProjectModel
ProjectModel.fund_advanced = relationship(
    "FundAdvancedModel", 
    back_populates="project", 
    uselist=False
)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "FundAdvancedType",
    "ProjectStatus",
    "NotificationType",
    "GainLossType",
    "PriceType",
    # Models
    "ExchangeRateHistoryModel",
    "CurrencyGainLossModel",
    "ProjectModel",
    "FundAdvancedModel",
    "ProductPriceMultiCurrencyModel",
    "SavedFilterModel",
    "RealTimeNotificationModel",  # ✅ تمت إضافته
    "CacheEntryModel",
    "FundAuditLogModel",
]