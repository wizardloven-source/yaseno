# core/infrastructure/db/models/invoice_model.py
"""ORM Models for Invoicing Module
✅ محدث: إضافة دعم فروع العملاء (Customer Branches)
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    String, Numeric, DateTime, Boolean, ForeignKey, 
    Enum, Index, CheckConstraint, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class InvoiceModel(Base):
    """ORM Model for Invoices
    ✅ محدث: إضافة حقول فروع العملاء
    """
    __tablename__ = "invoices"
    
    # ========== المفتاح الأساسي ==========
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    invoice_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # ========== أطراف المعاملة ==========
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # ✅ فروع العميل (جديد)
    customer_branch_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    customer_branch_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    customer_branch_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # موقع الشركة (مصدر الفاتورة)
    site_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    site_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # ========== معلومات مالية ==========
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    payment_currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False
    )
    payment_type: Mapped[str] = mapped_column(
        Enum('cash', 'credit', 'check', 'transfer', name='payment_type_enum'),
        nullable=False
    )
    fund_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # ========== المبالغ ==========
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    # ========== حالة الفاتورة ==========
    status: Mapped[str] = mapped_column(
        Enum('draft', 'posted', 'cancelled', name='invoice_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    # ========== الربط مع المحاسبة ==========
    journal_entry_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # ========== معلومات إضافية ==========
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default='system', nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ========== التحكم في التزامن ==========
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # ========== العلاقات ==========
    lines: Mapped[List["InvoiceLineModel"]] = relationship(
        "InvoiceLineModel",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLineModel.line_order"
    )
    
    # ========== الفهارس والقيود ==========
    __table_args__ = (
        Index("idx_invoices_customer", "customer_id", "status"),
        Index("idx_invoices_customer_branch", "customer_branch_id", "status"),  # ✅ جديد
        Index("idx_invoices_customer_branch_customer", "customer_id", "customer_branch_id"),  # ✅ جديد
        Index("idx_invoices_date", "invoice_date"),
        Index("idx_invoices_journal", "journal_entry_id"),
        Index("idx_invoices_site", "site_id"),
        Index("idx_invoices_fund", "fund_id"),
        CheckConstraint("total_amount >= 0", name="non_negative_total"),
    )
    
    def __repr__(self) -> str:
        branch_info = f", branch={self.customer_branch_name or self.customer_branch_id}" if self.customer_branch_id else ""
        return f"InvoiceModel(id={self.id}, number={self.number}, customer={self.customer_name}{branch_info}, status={self.status})"


class InvoiceLineModel(Base):
    """ORM Model for Invoice Lines"""
    __tablename__ = "invoice_lines"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    invoice_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    line_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    invoice: Mapped["InvoiceModel"] = relationship("InvoiceModel", back_populates="lines")
    
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_quantity"),
        CheckConstraint("unit_price >= 0", name="non_negative_price"),
        Index("idx_il_invoice", "invoice_id", "line_order"),
    )
    
    def __repr__(self) -> str:
        return f"InvoiceLineModel(product={self.product_code}, qty={self.quantity})"


__all__ = [
    "InvoiceModel",
    "InvoiceLineModel",
]