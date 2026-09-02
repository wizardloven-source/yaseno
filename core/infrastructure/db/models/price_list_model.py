# core/infrastructure/db/models/price_list_model.py
"""
Price List Models - نماذج قوائم الأسعار المتقدمة
✅ دعم قوائم أسعار متعددة
✅ دعم الأسعار حسب العميل والمجموعة والكمية والتواريخ
✅ دعم الخصومات والعروض الترويجية
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List

from sqlalchemy import (
    String, Numeric, DateTime, Boolean, ForeignKey, 
    Enum, Index, CheckConstraint, Text, Integer, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# نماذج قوائم الأسعار
# =============================================================================

class PriceListModel(Base):
    """
    نموذج قائمة الأسعار الرئيسية
    كل قائمة تحتوي على مجموعة من الأسعار للمنتجات
    """
    __tablename__ = "price_lists"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # معلومات القائمة
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # نوع القائمة
    list_type: Mapped[str] = mapped_column(
        Enum(
            'standard', 'customer', 'group', 'promotional', 
            'wholesale', 'retail', 'seasonal',
            name='price_list_type_enum'
        ),
        default='standard',
        nullable=False,
        index=True
    )
    
    # العملة الأساسية للقائمة
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # صلاحية القائمة
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # إعدادات القائمة
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    apply_discounts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_update: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # شروط التطبيق (JSON)
    conditions: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # العلاقات
    items: Mapped[List["PriceListItemModel"]] = relationship(
        "PriceListItemModel",
        back_populates="price_list",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # العلاقات مع العملاء والمجموعات
    customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    customer_group: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    __table_args__ = (
        Index("idx_price_lists_code_active", "code", "is_active"),
        Index("idx_price_lists_type_active", "list_type", "is_active"),
        Index("idx_price_lists_validity", "valid_from", "valid_to"),
        Index("idx_price_lists_customer", "customer_id"),
        Index("idx_price_lists_group", "customer_group"),
        CheckConstraint("valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to", name="chk_valid_dates"),
    )

    def __repr__(self) -> str:
        return f"PriceListModel(code={self.code}, name={self.name}, type={self.list_type})"


# =============================================================================
# نموذج بنود قائمة الأسعار
# =============================================================================

class PriceListItemModel(Base):
    """
    نموذج سعر منتج في قائمة الأسعار
    يدعم الأسعار حسب الكمية والخصومات
    """
    __tablename__ = "price_list_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    price_list_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("price_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # المنتج
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # التسعير
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # التسعير حسب الكمية (JSON)
    quantity_prices: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    # مثال: {"5": 95.00, "10": 90.00, "25": 85.00}
    
    # الخصومات
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    discount_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discount_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # السعر الأساسي (للمقارنة)
    base_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    
    # الحد الأدنى والحد الأقصى للكمية
    min_quantity: Mapped[int] = mapped_column(Integer, default=1)
    max_quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # الحالة
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # بيانات إضافية
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # العلاقات
    price_list: Mapped["PriceListModel"] = relationship("PriceListModel", back_populates="items")

    __table_args__ = (
        Index("idx_price_list_items_product", "price_list_id", "product_id"),
        Index("idx_price_list_items_code", "price_list_id", "product_code"),
        Index("idx_price_list_items_active", "price_list_id", "is_active"),
        UniqueConstraint("price_list_id", "product_id", name="uq_price_list_product"),
        CheckConstraint("price >= 0", name="chk_non_negative_price"),
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="chk_discount_percent"),
        CheckConstraint("min_quantity > 0", name="chk_min_quantity"),
    )

    @property
    def final_price(self) -> Decimal:
        """الحصول على السعر النهائي بعد الخصم"""
        if self.discount_percent > 0:
            return self.price * (1 - self.discount_percent / 100)
        if self.discount_amount > 0:
            return max(0, self.price - self.discount_amount)
        return self.price

    def get_price_for_quantity(self, quantity: int) -> Decimal:
        """الحصول على السعر حسب الكمية"""
        if not self.quantity_prices:
            return self.final_price
        
        # البحث عن أفضل سعر حسب الكمية
        best_price = self.final_price
        for qty_str, price in sorted(self.quantity_prices.items(), key=lambda x: int(x[0])):
            if quantity >= int(qty_str):
                best_price = Decimal(str(price))
        return best_price


# =============================================================================
# نموذج تاريخ أسعار المنتج
# =============================================================================

class ProductPriceHistoryModel(Base):
    """
    نموذج تاريخ أسعار المنتج - لتتبع التغيرات السعرية
    """
    __tablename__ = "product_price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # السعر القديم والجديد
    old_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    new_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # سبب التغيير
    change_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    price_list_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True)
    
    # بيانات التدقيق
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    __table_args__ = (
        Index("idx_price_history_product_date", "product_id", "changed_at"),
        Index("idx_price_history_price_list", "price_list_id", "changed_at"),
    )

    def __repr__(self) -> str:
        return f"ProductPriceHistory(product={self.product_code}, {self.old_price} -> {self.new_price})"


# =============================================================================
# نموذج قواعد الأسعار الديناميكية
# =============================================================================

class PricingRuleModel(Base):
    """
    نموذج قواعد التسعير الديناميكي
    يمكن استخدامها لحساب الأسعار تلقائياً بناءً على شروط محددة
    """
    __tablename__ = "pricing_rules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # معلومات القاعدة
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # نوع القاعدة
    rule_type: Mapped[str] = mapped_column(
        Enum(
            'percentage', 'fixed_amount', 'bundle', 'tiered',
            name='pricing_rule_type_enum'
        ),
        nullable=False,
        index=True
    )
    
    # القيمة (نسبة مئوية أو مبلغ ثابت)
    value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # العملة (للقيم الثابتة)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # شروط التطبيق (JSON)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # مثال: {"min_quantity": 10, "customer_group": "wholesale", "product_category": "electronics"}
    
    # الترتيب (لتطبيق القواعد بالترتيب الصحيح)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # الحالة
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    
    # صلاحية القاعدة
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        Index("idx_pricing_rules_code_active", "code", "is_active"),
        Index("idx_pricing_rules_type", "rule_type"),
        Index("idx_pricing_rules_priority", "priority"),
        Index("idx_pricing_rules_validity", "valid_from", "valid_to"),
        CheckConstraint("valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to", name="chk_rule_valid_dates"),
    )

    def __repr__(self) -> str:
        return f"PricingRule(code={self.code}, type={self.rule_type}, value={self.value})"