# core/infrastructure/db/models/tax_model.py
"""
Tax ORM Models - نماذج الضرائب في قاعدة البيانات
✅ يدعم: TaxRule, TaxGroup, TaxExemption, TaxPeriod
✅ يدعم: Optimistic Locking عبر الـ version
✅ يدعم: JSONB لتخزين البيانات المرنة
✅ يدعم: الفهارس المحسنة للبحث السريع
"""

from datetime import datetime, timezone, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Integer, DateTime, Boolean, ForeignKey,
    Enum, Index, CheckConstraint, Text, Numeric, Date,
    UniqueConstraint, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


# =============================================================================
# TaxRuleModel - نموذج القاعدة الضريبية
# =============================================================================

class TaxRuleModel(Base):
    """
    ORM Model للقاعدة الضريبية
    
    تخزن القاعدة مع جميع خصائصها للتحكم في حساب الضرائب.
    """
    __tablename__ = "tax_rules"

    # ========== الحقول الأساسية ==========
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="المعرف الفريد للقاعدة"
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="كود القاعدة (فريد)"
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="اسم القاعدة"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="وصف القاعدة"
    )

    # ========== نوع الضريبة ==========
    tax_type: Mapped[str] = mapped_column(
        Enum(
            'vat', 'gst', 'sales_tax', 'excise', 'customs', 'withholding',
            name='tax_type_enum'
        ),
        nullable=False,
        index=True,
        doc="نوع الضريبة"
    )

    calculation_type: Mapped[str] = mapped_column(
        Enum(
            'inclusive', 'exclusive', 'compound', 'zero_rated', 'exempt',
            name='tax_calculation_type_enum'
        ),
        nullable=False,
        doc="نوع حساب الضريبة"
    )

    # ========== النسبة ==========
    rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        doc="نسبة الضريبة"
    )

    # ========== الجهة المختصة ==========
    jurisdiction: Mapped[str] = mapped_column(
        Enum(
            'federal', 'state', 'local', 'international',
            name='tax_jurisdiction_enum'
        ),
        nullable=False,
        doc="الجهة المختصة"
    )

    jurisdiction_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="كود الجهة المختصة"
    )

    # ========== نطاق التطبيق ==========
    application_scope: Mapped[str] = mapped_column(
        Enum(
            'all_products', 'product_category', 'specific_product',
            'all_customers', 'customer_group', 'specific_customer',
            'region', 'custom',
            name='tax_application_scope_enum'
        ),
        default='all_products',
        nullable=False,
        doc="نطاق تطبيق الضريبة"
    )

    applies_to: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="قائمة العناصر التي تنطبق عليها الضريبة"
    )

    # ========== صلاحية القاعدة ==========
    valid_from: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False,
        doc="تاريخ بدء الصلاحية"
    )

    valid_to: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="تاريخ انتهاء الصلاحية"
    )

    # ========== للضرائب المركبة ==========
    is_compound: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل هي ضريبة مركبة؟"
    )

    parent_tax_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tax_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="معرف الضريبة الأب (للضرائب المركبة)"
    )

    compound_calculation_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="ترتيب حساب الضريبة المركبة"
    )

    # ========== الإعفاءات ==========
    exempt_customer_groups: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="مجموعات العملاء المعفاة"
    )

    exempt_product_categories: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="تصنيفات المنتجات المعفاة"
    )

    exempt_countries: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="الدول المعفاة"
    )

    exempt_threshold_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        doc="حد المبلغ للإعفاء"
    )

    # ========== الحالة ==========
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="هل القاعدة نشطة؟"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل هي القاعدة الافتراضية؟"
    )

    is_mandatory: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل القاعدة إجبارية؟"
    )

    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="تاريخ الإنشاء"
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بالإنشاء"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        doc="تاريخ آخر تحديث"
    )

    updated_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بآخر تحديث"
    )

    # ========== Optimistic Locking ==========
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="رقم الإصدار"
    )

    # ========== العلاقات ==========
    parent_rule: Mapped[Optional["TaxRuleModel"]] = relationship(
        "TaxRuleModel",
        remote_side=[id],
        backref="child_rules"
    )

    # ========== الفهارس والقيود ==========
    __table_args__ = (
        # فهارس للبحث السريع
        Index("idx_tax_rules_code_active", "code", "is_active"),
        Index("idx_tax_rules_type", "tax_type"),
        Index("idx_tax_rules_jurisdiction", "jurisdiction"),
        Index("idx_tax_rules_validity", "valid_from", "valid_to"),
        Index("idx_tax_rules_default", "is_default"),

        # التحقق من صحة النسبة
        CheckConstraint(
            "rate >= 0 AND rate <= 100",
            name="chk_tax_rate_range"
        ),

        # التحقق من صحة التواريخ
        CheckConstraint(
            "valid_to IS NULL OR valid_from <= valid_to",
            name="chk_tax_valid_dates"
        ),

        # التحقق من صحة حد الإعفاء
        CheckConstraint(
            "exempt_threshold_amount IS NULL OR exempt_threshold_amount >= 0",
            name="chk_exempt_threshold_non_negative"
        ),
        
        # ✅ حل مشكلة الجدول المكرر
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"TaxRuleModel(id={self.id}, code={self.code}, rate={self.rate}%, status={status})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'tax_type': self.tax_type,
            'calculation_type': self.calculation_type,
            'rate': str(self.rate),
            'jurisdiction': self.jurisdiction,
            'jurisdiction_code': self.jurisdiction_code,
            'application_scope': self.application_scope,
            'applies_to': self.applies_to,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'is_compound': self.is_compound,
            'parent_tax_id': str(self.parent_tax_id) if self.parent_tax_id else None,
            'compound_calculation_order': self.compound_calculation_order,
            'exempt_customer_groups': self.exempt_customer_groups,
            'exempt_product_categories': self.exempt_product_categories,
            'exempt_countries': self.exempt_countries,
            'exempt_threshold_amount': str(self.exempt_threshold_amount) if self.exempt_threshold_amount else None,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'is_mandatory': self.is_mandatory,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
            'version': self.version,
        }


# =============================================================================
# TaxGroupModel - نموذج مجموعة الضرائب
# =============================================================================

class TaxGroupModel(Base):
    """
    ORM Model لمجموعة الضرائب
    
    تستخدم لتجميع عدة قواعد ضريبية معاً.
    """
    __tablename__ = "tax_groups"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="المعرف الفريد للمجموعة"
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="كود المجموعة (فريد)"
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="اسم المجموعة"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="وصف المجموعة"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="هل المجموعة نشطة؟"
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل هي المجموعة الافتراضية؟"
    )

    # ========== العلاقات ==========
    # Many-to-Many مع TaxRuleModel عبر جدول وسيط
    tax_rules: Mapped[List["TaxRuleModel"]] = relationship(
        "TaxRuleModel",
        secondary="tax_group_rules",
        lazy="selectin",
        backref="groups"
    )

    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="تاريخ الإنشاء"
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بالإنشاء"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        doc="تاريخ آخر تحديث"
    )

    updated_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بآخر تحديث"
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="رقم الإصدار"
    )

    __table_args__ = (
        Index("idx_tax_groups_code_active", "code", "is_active"),
        Index("idx_tax_groups_default", "is_default"),
        # ✅ حل مشكلة الجدول المكرر
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"TaxGroupModel(id={self.id}, code={self.code}, status={status})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'rule_count': len(self.tax_rules) if self.tax_rules else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
            'version': self.version,
        }


# =============================================================================
# TaxGroupRulesModel - جدول الربط بين المجموعات والقواعد
# =============================================================================

class TaxGroupRulesModel(Base):
    """
    جدول الربط بين مجموعات الضرائب والقواعد (Many-to-Many)
    """
    __tablename__ = "tax_group_rules"

    group_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tax_groups.id", ondelete="CASCADE"),
        primary_key=True,
        doc="معرف المجموعة"
    )

    rule_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tax_rules.id", ondelete="CASCADE"),
        primary_key=True,
        doc="معرف القاعدة"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="تاريخ الربط"
    )

    __table_args__ = (
        Index("idx_tax_group_rules_group", "group_id"),
        Index("idx_tax_group_rules_rule", "rule_id"),
        # ✅ حل مشكلة الجدول المكرر
        {"extend_existing": True},
    )


# =============================================================================
# TaxExemptionModel - نموذج الإعفاء الضريبي
# =============================================================================

class TaxExemptionModel(Base):
    """
    ORM Model للإعفاء الضريبي
    
    يسمح بإعفاء معاملات معينة من الضريبة.
    """
    __tablename__ = "tax_exemptions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="المعرف الفريد للإعفاء"
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="كود الإعفاء (فريد)"
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="اسم الإعفاء"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="وصف الإعفاء"
    )

    # ========== الكيانات المعفاة ==========
    customer_ids: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="معرفات العملاء المعفيين"
    )

    customer_groups: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="مجموعات العملاء المعفيين"
    )

    product_codes: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="أكواد المنتجات المعفاة"
    )

    product_categories: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="تصنيفات المنتجات المعفاة"
    )

    countries: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        default=list,
        nullable=True,
        doc="الدول المعفاة"
    )

    # ========== صلاحية الإعفاء ==========
    valid_from: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        nullable=False,
        doc="تاريخ بدء الإعفاء"
    )

    valid_to: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        doc="تاريخ انتهاء الإعفاء"
    )

    # ========== حد المبلغ ==========
    threshold_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        doc="حد المبلغ للإعفاء"
    )

    threshold_currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
        doc="عملة حد المبلغ"
    )

    # ========== الحالة ==========
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="هل الإعفاء نشط؟"
    )

    is_automatic: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="هل الإعفاء تلقائي؟"
    )

    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="تاريخ الإنشاء"
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بالإنشاء"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        doc="تاريخ آخر تحديث"
    )

    updated_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بآخر تحديث"
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="رقم الإصدار"
    )

    __table_args__ = (
        Index("idx_tax_exemptions_code_active", "code", "is_active"),
        Index("idx_tax_exemptions_validity", "valid_from", "valid_to"),
        Index("idx_tax_exemptions_customer", "customer_ids", postgresql_using="gin"),
        Index("idx_tax_exemptions_product", "product_codes", postgresql_using="gin"),
        CheckConstraint(
            "valid_to IS NULL OR valid_from <= valid_to",
            name="chk_exemption_valid_dates"
        ),
        CheckConstraint(
            "threshold_amount IS NULL OR threshold_amount >= 0",
            name="chk_exemption_threshold_non_negative"
        ),
        # ✅ حل مشكلة الجدول المكرر
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"TaxExemptionModel(id={self.id}, code={self.code}, status={status})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'customer_ids': self.customer_ids,
            'customer_groups': self.customer_groups,
            'product_codes': self.product_codes,
            'product_categories': self.product_categories,
            'countries': self.countries,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'threshold_amount': str(self.threshold_amount) if self.threshold_amount else None,
            'threshold_currency': self.threshold_currency,
            'is_active': self.is_active,
            'is_automatic': self.is_automatic,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
            'version': self.version,
        }


# =============================================================================
# TaxPeriodModel - نموذج الفترة الضريبية
# =============================================================================

class TaxPeriodModel(Base):
    """
    ORM Model للفترة الضريبية
    
    تستخدم لتتبع الضرائب حسب الفترات الزمنية.
    """
    __tablename__ = "tax_periods"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="المعرف الفريد للفترة"
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        doc="كود الفترة (فريد)"
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="اسم الفترة"
    )

    # ========== تاريخ الفترة ==========
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        doc="تاريخ بدء الفترة"
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        doc="تاريخ انتهاء الفترة"
    )

    period_type: Mapped[str] = mapped_column(
        String(20),
        default="monthly",
        nullable=False,
        doc="نوع الفترة (monthly, quarterly, yearly)"
    )

    # ========== حالة الفترة ==========
    status: Mapped[str] = mapped_column(
        String(20),
        default="open",
        nullable=False,
        index=True,
        doc="حالة الفترة (open, closed, locked)"
    )

    # ========== إجماليات الضرائب ==========
    total_taxable_sales: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal('0'),
        nullable=False,
        doc="إجمالي المبيعات الخاضعة للضريبة"
    )

    total_tax_collected: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal('0'),
        nullable=False,
        doc="إجمالي الضريبة المحصلة"
    )

    total_tax_paid: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal('0'),
        nullable=False,
        doc="إجمالي الضريبة المدفوعة"
    )

    total_tax_due: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal('0'),
        nullable=False,
        doc="إجمالي الضريبة المستحقة"
    )

    total_tax_credit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal('0'),
        nullable=False,
        doc="إجمالي رصيد الضريبة"
    )

    net_tax_due: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal('0'),
        nullable=False,
        doc="صافي الضريبة المستحقة"
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
        doc="عملة الفترة"
    )

    # ========== بيانات إضافية ==========
    tax_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=dict,
        doc="بيانات إضافية"
    )

    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="تاريخ الإنشاء"
    )

    created_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بالإنشاء"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        doc="تاريخ آخر تحديث"
    )

    updated_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بآخر تحديث"
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="رقم الإصدار"
    )

    # ========== الفهارس والقيود ==========
    __table_args__ = (
        Index("idx_tax_periods_dates", "start_date", "end_date"),
        Index("idx_tax_periods_status", "status"),
        Index("idx_tax_periods_code", "code"),
        CheckConstraint(
            "start_date <= end_date",
            name="chk_period_valid_dates"
        ),
        CheckConstraint(
            "status IN ('open', 'closed', 'locked')",
            name="chk_period_status"
        ),
        CheckConstraint(
            "period_type IN ('monthly', 'quarterly', 'yearly', 'custom')",
            name="chk_period_type"
        ),
        # ✅ حل مشكلة الجدول المكرر
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"TaxPeriodModel(id={self.id}, code={self.code}, status={self.status})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'code': self.code,
            'name': self.name,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'period_type': self.period_type,
            'status': self.status,
            'currency': self.currency,
            'total_taxable_sales': str(self.total_taxable_sales),
            'total_tax_collected': str(self.total_tax_collected),
            'total_tax_paid': str(self.total_tax_paid),
            'total_tax_due': str(self.total_tax_due),
            'total_tax_credit': str(self.total_tax_credit),
            'net_tax_due': str(self.net_tax_due),
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
            'version': self.version,
        }


# =============================================================================
# TaxCalculationLogModel - نموذج سجل حسابات الضريبة
# =============================================================================

class TaxCalculationLogModel(Base):
    """
    ORM Model لسجل حسابات الضريبة
    
    يستخدم لتتبع حسابات الضريبة لأغراض التدقيق.
    """
    __tablename__ = "tax_calculation_logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        doc="المعرف الفريد للسجل"
    )

    # ========== المعلومات الأساسية ==========
    invoice_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="معرف الفاتورة"
    )

    rule_ids: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        doc="معرفات القواعد المطبقة"
    )

    # ========== المبالغ ==========
    taxable_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        doc="المبلغ الخاضع للضريبة"
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        doc="مبلغ الضريبة"
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        doc="المبلغ الإجمالي"
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
        doc="العملة"
    )

    # ========== تفصيل الضريبة ==========
    tax_breakdown: Mapped[Optional[Dict[str, Decimal]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="تفصيل الضريبة حسب القاعدة"
    )

    # ========== السياق ==========
    context_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="لقطة من سياق الحساب"
    )

    # ========== معلومات التنفيذ ==========
    executed_by: Mapped[str] = mapped_column(
        String(100),
        default="system",
        nullable=False,
        doc="من قام بالحساب"
    )

    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
        doc="وقت الحساب"
    )

    execution_time_ms: Mapped[float] = mapped_column(
        Numeric(10, 2),
        default=0.0,
        nullable=False,
        doc="وقت التنفيذ بالمللي ثانية"
    )

    # ========== الفهارس ==========
    __table_args__ = (
        Index("idx_tax_calc_logs_invoice", "invoice_id"),
        Index("idx_tax_calc_logs_executed_at", "executed_at"),
        # ✅ حل مشكلة الجدول المكرر
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"TaxCalculationLogModel(id={self.id}, invoice={self.invoice_id}, tax={self.tax_amount})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'rule_ids': self.rule_ids,
            'taxable_amount': str(self.taxable_amount),
            'tax_amount': str(self.tax_amount),
            'total_amount': str(self.total_amount),
            'currency': self.currency,
            'tax_breakdown': self.tax_breakdown,
            'context_snapshot': self.context_snapshot,
            'executed_by': self.executed_by,
            'executed_at': self.executed_at.isoformat() if self.executed_at else None,
            'execution_time_ms': float(self.execution_time_ms) if self.execution_time_ms else 0.0,
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'TaxRuleModel',
    'TaxGroupModel',
    'TaxGroupRulesModel',
    'TaxExemptionModel',
    'TaxPeriodModel',
    'TaxCalculationLogModel',
]