# core/infrastructure/db/models/payment_model.py
"""
Payment ORM Models - نماذج الدفعات في قاعدة البيانات
✅ محدث: إضافة دعم فروع العملاء (Customer Branches)
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List

from sqlalchemy import (
    String, Numeric, DateTime, Boolean, ForeignKey,
    Enum, Index, CheckConstraint, Text, Integer,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class PaymentModel(Base):
    """نموذج الدفعة في قاعدة البيانات
    ✅ محدث: إضافة حقول فروع العملاء
    """
    __tablename__ = "payments"

    # ========== المفتاح الأساسي ==========
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # ========== الكود والتاريخ ==========
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # ========== نوع العملية وطريقة الدفع ==========
    payment_type: Mapped[str] = mapped_column(
        Enum('receive', 'pay', 'transfer', name='payment_type_enum'),
        nullable=False,
        index=True,
    )
    payment_method: Mapped[str] = mapped_column(
        Enum('cash', 'check', 'transfer', 'credit', 'card', name='payment_method_enum'),
        nullable=False,
    )

    # ========== المبالغ ==========
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # ========== الأطراف ==========
    # العميل
    customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # ✅ فروع العميل (جديد)
    customer_branch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    customer_branch_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_branch_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # المورد
    supplier_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # ========== الصندوق ==========
    fund_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    fund_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # ========== المراجع ==========
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    # ========== الحالة ==========
    status: Mapped[str] = mapped_column(
        Enum('draft', 'pending', 'approved', 'completed', 'rejected', 'cancelled', name='payment_status_enum'),
        default='draft',
        nullable=False,
        index=True,
    )

    # ========== الملاحظات ==========
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ========== بيانات الموافقة ==========
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ========== بيانات الإكمال ==========
    completed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default='system', nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default='system', nullable=False)

    # ========== التحكم في التزامن ==========
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # ========== العلاقات ==========
    lines: Mapped[List["PaymentLineModel"]] = relationship(
        "PaymentLineModel",
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="PaymentLineModel.line_order",
    )

    # ========== الفهارس والقيود ==========
    __table_args__ = (
        Index("idx_payments_code_status", "code", "status"),
        Index("idx_payments_customer", "customer_id", "status"),
        Index("idx_payments_customer_branch", "customer_branch_id", "status"),  # ✅ جديد
        Index("idx_payments_customer_branch_customer", "customer_id", "customer_branch_id"),  # ✅ جديد
        Index("idx_payments_supplier", "supplier_id", "status"),
        Index("idx_payments_date", "payment_date"),
        Index("idx_payments_type", "payment_type"),
        Index("idx_payments_reference", "reference_type", "reference_id"),
        Index("idx_payments_status_created", "status", "created_at"),
        Index("idx_payments_fund", "fund_id"),
        CheckConstraint("amount >= 0", name="non_negative_amount"),
    )

    def __repr__(self) -> str:
        branch_info = f", branch={self.customer_branch_name or self.customer_branch_id}" if self.customer_branch_id else ""
        return f"PaymentModel(id={self.id}, code={self.code}, type={self.payment_type}, customer={self.customer_name}{branch_info}, amount={self.amount})"


class PaymentLineModel(Base):
    """نموذج سطر الدفعة في قاعدة البيانات"""
    __tablename__ = "payment_lines"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    payment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # المراجع
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # المبلغ
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # الملاحظات
    notes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # الترتيب
    line_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # العلاقة
    payment: Mapped["PaymentModel"] = relationship("PaymentModel", back_populates="lines")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="non_negative_line_amount"),
        Index("idx_pl_payment", "payment_id", "line_order"),
        Index("idx_pl_reference", "reference_type", "reference_id"),
    )

    def __repr__(self) -> str:
        return f"PaymentLineModel(id={self.id}, reference={self.reference_type}:{self.reference_id})"


# ========== إضافة العلاقة العكسية في PaymentModel ==========

# PaymentModel.lines = relationship("PaymentLineModel", back_populates="payment", cascade="all, delete-orphan")