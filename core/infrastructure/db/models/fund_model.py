# core/infrastructure/db/models/fund_model.py

"""
Fund ORM Models - Professional Edition
✅ يحافظ على التوافق مع الكود الحالي
✅ يضيف دعم الحركات مع balance_before/balance_after
✅ balance مخزن ولكن للقراءة فقط (يُحسب من الحركات)
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List

from sqlalchemy import String, Numeric, DateTime, Boolean, ForeignKey, Index, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FundModel(Base):
    """
    نموذج الصندوق في قاعدة البيانات
    ✅ balance مخزن ولكن يتم مزامنته مع الحركات تلقائياً
    ✅ يستخدم trigger أو computed column للحفاظ على التزامن
    """
    __tablename__ = "funds"
    
    # === الحقول الأساسية ===
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    fund_type: Mapped[str] = mapped_column(String(50), default="main", nullable=False)
    account_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # ⚠️ balance موجود للتوافق مع الكود الحالي
    # ولكن يتم تحديثه تلقائياً عبر trigger عند إضافة حركات
    # في الإصدارات القادمة يمكن إزالته والاعتماد فقط على الحركات
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    
    # === حدود الصندوق ===
    daily_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    monthly_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    min_balance_alert: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    max_balance_alert: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_threshold: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    
    # === بيانات التدقيق ===
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # === Optimistic Locking ===
    version: Mapped[int] = mapped_column(default=1)
    
    # === العلاقات ===
    movements: Mapped[List["FundMovementModel"]] = relationship(
        "FundMovementModel", back_populates="fund", cascade="all, delete-orphan"
    )
    
    # ✅ FIX: Use string with full module path or lambda for lazy loading
    advanced: Mapped[Optional["FundAdvancedModel"]] = relationship(
        "fund_advanced_models.FundAdvancedModel",  # Full module path
        back_populates="fund", 
        uselist=False, 
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        Index("idx_funds_code_status", "code", "status"),
        Index("idx_funds_type_status", "fund_type", "status"),
        Index("idx_funds_currency", "currency"),
        Index("idx_funds_account_code", "account_code"),
        CheckConstraint("balance >= 0", name="chk_balance_non_negative"),
        CheckConstraint("daily_limit >= 0", name="chk_daily_limit_non_negative"),
        CheckConstraint("monthly_limit >= 0", name="chk_monthly_limit_non_negative"),
    )
    
    def __repr__(self) -> str:
        return f"FundModel(id={self.id}, code={self.code}, name={self.name}, balance={self.balance})"


class FundMovementModel(Base):
    """
    نموذج حركة الصندوق - Source of Truth
    ✅ يحتوي على balance_before و balance_after للتتبع الكامل
    """
    __tablename__ = "fund_movements"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    fund_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)
    
    # === نوع الحركة ===
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # === تفاصيل الحركة ===
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # ✅ الرصيد قبل وبعد الحركة - للتتبع التاريخي
    balance_before: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # === معلومات إضافية ===
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    exchange_rate_used: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4), nullable=True)
    from_fund_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_fund_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # === بيانات التدقيق ===
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    
    # === بيانات إضافية (JSON) ===
    movement_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    
    # === العلاقات ===
    fund: Mapped["FundModel"] = relationship("FundModel", back_populates="movements")
    
    __table_args__ = (
        Index("idx_fund_movements_fund_date", "fund_id", "created_at"),
        Index("idx_fund_movements_type", "movement_type"),
        Index("idx_fund_movements_reference", "reference_id"),
        CheckConstraint("amount != 0", name="chk_amount_non_zero"),
        CheckConstraint("balance_before >= 0", name="chk_balance_before_non_negative"),
        CheckConstraint("balance_after >= 0", name="chk_balance_after_non_negative"),
    )
    
    def __repr__(self) -> str:
        return f"FundMovementModel(id={self.id}, type={self.movement_type}, amount={self.amount})"


class FundTransferModel(Base):
    """
    نموذج عملية التحويل بين الصناديق
    ✅ كيان مستقل لتتبع عمليات التحويل
    """
    __tablename__ = "fund_transfers"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # === الصندوقين ===
    from_fund_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)
    to_fund_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("funds.id"), nullable=False, index=True)
    
    # === تفاصيل التحويل ===
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    from_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    to_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False, default=1)
    converted_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # === الحالة ===
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    # pending, approved, processing, completed, failed, cancelled
    
    # === معلومات إضافية ===
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    journal_entry_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # === بيانات التدقيق ===
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # === العلاقات ===
    from_fund: Mapped["FundModel"] = relationship("FundModel", foreign_keys=[from_fund_id])
    to_fund: Mapped["FundModel"] = relationship("FundModel", foreign_keys=[to_fund_id])
    
    # الحركات المرتبطة
    from_movement_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    to_movement_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    
    __table_args__ = (
        Index("idx_fund_transfers_from_fund", "from_fund_id", "status"),
        Index("idx_fund_transfers_to_fund", "to_fund_id", "status"),
        Index("idx_fund_transfers_date", "created_at"),
        Index("idx_fund_transfers_journal", "journal_entry_id"),
        CheckConstraint("amount > 0", name="chk_transfer_amount_positive"),
        CheckConstraint("exchange_rate > 0", name="chk_exchange_rate_positive"),
        CheckConstraint("from_fund_id != to_fund_id", name="chk_different_funds"),
    )
    
    def __repr__(self) -> str:
        return f"FundTransferModel(id={self.id}, from={self.from_fund_id}, to={self.to_fund_id}, amount={self.amount})"


FundTransactionModel = FundMovementModel

# ✅ CRITICAL FIX: Import advanced models after all classes are defined
# This ensures SQLAlchemy can resolve the FundAdvancedModel reference
from . import fund_advanced_models  # noqa

# =============================================================================
# SQL Trigger لتحديث balance تلقائياً (اختياري - لضمان التزامن)
# =============================================================================

"""
-- PostgreSQL trigger لتحديث رصيد الصندوق تلقائياً عند إضافة حركة
CREATE OR REPLACE FUNCTION update_fund_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- تحديث رصيد الصندوق بناءً على آخر حركة
    UPDATE funds 
    SET balance = NEW.balance_after,
        updated_at = NOW()
    WHERE id = NEW.fund_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- إضافة trigger بعد إدراج حركة جديدة
CREATE TRIGGER trigger_update_fund_balance
    AFTER INSERT ON fund_movements
    FOR EACH ROW
    EXECUTE FUNCTION update_fund_balance();
"""