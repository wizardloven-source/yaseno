from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import String, Numeric, DateTime, Boolean, ForeignKey, Enum, Index, CheckConstraint, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class PurchaseOrderModel(Base):
    __tablename__ = "purchase_orders"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_delivery_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    supplier_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    site_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    site_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_terms: Mapped[str] = mapped_column(
        Enum('cash', 'net_15', 'net_30', 'net_45', 'net_60', name='payment_terms_enum'),
        nullable=False
    )
    
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    status: Mapped[str] = mapped_column(
        Enum('draft', 'posted', 'cancelled', 'partially_received', 'fully_received', name='purchase_order_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    journal_entry_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default='system', nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    lines: Mapped[List["PurchaseOrderLineModel"]] = relationship(
        "PurchaseOrderLineModel",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderLineModel.line_order"
    )
    
    __table_args__ = (
        Index("idx_po_supplier", "supplier_id", "status"),
        Index("idx_po_date", "order_date"),
        Index("idx_po_journal", "journal_entry_id"),
        CheckConstraint("total_amount >= 0", name="non_negative_total"),
    )


class PurchaseOrderLineModel(Base):
    __tablename__ = "purchase_order_lines"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    received_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal('0'), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    line_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    order: Mapped["PurchaseOrderModel"] = relationship("PurchaseOrderModel", back_populates="lines")
    
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("unit_price >= 0", name="non_negative_price"),
        CheckConstraint("received_quantity >= 0", name="non_negative_received"),
        CheckConstraint("received_quantity <= quantity", name="received_not_exceed_quantity"),
        Index("idx_pl_order", "order_id", "line_order"),
    )