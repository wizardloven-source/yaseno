# core/infrastructure/db/models/payment_allocation_model.py

"""
Payment Allocation ORM Model - نموذج توزيع الدفعات
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index, CheckConstraint, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PaymentAllocationModel(Base):
    """
    نموذج توزيع الدفعة على فاتورة
    
    يخزن تفاصيل توزيع مبلغ الدفعة على فاتورة محددة
    """
    __tablename__ = "payment_allocations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # المراجع
    payment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    invoice_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # المبلغ والعملة
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # الحالة
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True
    )
    # active, reversed, cancelled
    
    # بيانات الإلغاء
    reversed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reversed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reversal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # بيانات التدقيق
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    allocated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    
    # بيانات إضافية
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ✅ تغيير الاسم من 'metadata' إلى 'allocation_metadata' (لأن metadata محجوز في SQLAlchemy)
    allocation_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)

    __table_args__ = (
        Index("idx_payment_allocations_payment", "payment_id", "status"),
        Index("idx_payment_allocations_invoice", "invoice_id", "status"),
        Index("idx_payment_allocations_allocated_at", "allocated_at"),
        CheckConstraint("amount >= 0", name="non_negative_amount"),
        CheckConstraint("status IN ('active', 'reversed', 'cancelled')", name="valid_status"),
    )

    def __repr__(self) -> str:
        return f"PaymentAllocationModel(id={self.id}, payment={self.payment_id}, invoice={self.invoice_id}, amount={self.amount})"