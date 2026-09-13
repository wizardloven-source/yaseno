# core/infrastructure/db/models/sales_return_model.py
"""ORM Models for Sales Returns Module
✅ جديد: دعم إرجاع المبيعات ومذكرات الدائنة
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


class SalesReturnModel(Base):
    """ORM Model for Sales Returns"""
    __tablename__ = "sales_returns"
    
    # ========== المفتاح الأساسي ==========
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    return_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # ========== روابط المستندات الأصلية ==========
    original_invoice_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("invoices.id"), 
        nullable=True, 
        index=True
    )
    original_delivery_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    original_invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # ========== العميل ==========
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # ========== حالة الإرجاع ==========
    status: Mapped[str] = mapped_column(
        Enum(
            'draft', 'submitted', 'approved', 'rejected', 
            'received', 'inspected', 'completed', 'cancelled',
            name='sales_return_status_enum'
        ),
        default='draft',
        nullable=False,
        index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ========== معلومات مالية ==========
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    # ========== مذكرة الدائنة ==========
    credit_note_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        nullable=True, 
        index=True
    )
    credit_note_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # ========== الربط مع المحاسبة ==========
    journal_entry_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default='system', nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    received_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    inspected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    inspected_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ========== التحكم في التزامن ==========
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # ========== العلاقات ==========
    lines: Mapped[List["SalesReturnLineModel"]] = relationship(
        "SalesReturnLineModel",
        back_populates="sales_return",
        cascade="all, delete-orphan",
        order_by="SalesReturnLineModel.line_order"
    )
    
    # ========== الفهارس والقيود ==========
    __table_args__ = (
        Index("idx_sales_returns_customer", "customer_id", "status"),
        Index("idx_sales_returns_invoice", "original_invoice_id"),
        Index("idx_sales_returns_date", "return_date"),
        Index("idx_sales_returns_credit_note", "credit_note_id"),
        CheckConstraint("total_amount >= 0", name="non_negative_return_total"),
    )
    
    def __repr__(self) -> str:
        return f"SalesReturnModel(id={self.id}, number={self.number}, customer={self.customer_name}, status={self.status})"


class SalesReturnLineModel(Base):
    """ORM Model for Sales Return Lines"""
    __tablename__ = "sales_return_lines"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    sales_return_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sales_returns.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ========== معلومات المنتج ==========
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # ========== الكميات ==========
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # ========== الخصومات ==========
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal('0'), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    # ========== الضريبة ==========
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal('0'), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    # ========== سبب الإرجاع وحالة البضاعة ==========
    reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    condition: Mapped[str] = mapped_column(
        Enum('good', 'damaged', 'expired', 'defective', name='return_condition_enum'),
        default='good',
        nullable=False
    )
    
    # ========== العملة والملاحظات ==========
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # ========== الترتيب ==========
    line_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # ========== Relationships ==========
    sales_return: Mapped["SalesReturnModel"] = relationship("SalesReturnModel", back_populates="lines")
    
    # ========== الفهارس والقيود ==========
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_return_quantity"),
        CheckConstraint("unit_price >= 0", name="non_negative_return_price"),
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="valid_discount_percent"),
        CheckConstraint("tax_rate >= 0", name="non_negative_tax_rate"),
        Index("idx_srl_return", "sales_return_id", "line_order"),
    )
    
    def __repr__(self) -> str:
        return f"SalesReturnLineModel(product={self.product_code}, qty={self.quantity}, condition={self.condition})"


class CreditNoteModel(Base):
    """ORM Model for Credit Notes"""
    __tablename__ = "credit_notes"
    
    # ========== المفتاح الأساسي ==========
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # ========== روابط المستندات ==========
    sales_return_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("sales_returns.id"), 
        nullable=True, 
        index=True
    )
    original_invoice_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        ForeignKey("invoices.id"), 
        nullable=True, 
        index=True
    )
    original_invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # ========== العميل ==========
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # ========== الحالة ==========
    status: Mapped[str] = mapped_column(
        Enum('draft', 'issued', 'posted', 'applied', 'cancelled', name='credit_note_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    # ========== معلومات مالية ==========
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    # ========== الربط مع المحاسبة ==========
    journal_entry_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # ========== الملاحظات ==========
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default='system', nullable=False)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ========== التحكم في التزامن ==========
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # ========== العلاقات ==========
    lines: Mapped[List["CreditNoteLineModel"]] = relationship(
        "CreditNoteLineModel",
        back_populates="credit_note",
        cascade="all, delete-orphan",
        order_by="CreditNoteLineModel.line_order"
    )
    
    # ========== الفهارس والقيود ==========
    __table_args__ = (
        Index("idx_credit_notes_customer", "customer_id", "status"),
        Index("idx_credit_notes_return", "sales_return_id"),
        Index("idx_credit_notes_invoice", "original_invoice_id"),
        Index("idx_credit_notes_date", "issue_date"),
        CheckConstraint("total_amount >= 0", name="non_negative_credit_total"),
    )
    
    def __repr__(self) -> str:
        return f"CreditNoteModel(id={self.id}, number={self.number}, customer={self.customer_name}, status={self.status})"


class CreditNoteLineModel(Base):
    """ORM Model for Credit Note Lines"""
    __tablename__ = "credit_note_lines"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    credit_note_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("credit_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ========== معلومات المنتج ==========
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # ========== الكميات ==========
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # ========== الخصومات ==========
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal('0'), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    # ========== الضريبة ==========
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal('0'), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    # ========== العملة والملاحظات ==========
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # ========== الترتيب ==========
    line_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # ========== Relationships ==========
    credit_note: Mapped["CreditNoteModel"] = relationship("CreditNoteModel", back_populates="lines")
    
    # ========== الفهارس والقيود ==========
    __table_args__ = (
        CheckConstraint("quantity > 0", name="positive_cn_quantity"),
        CheckConstraint("unit_price >= 0", name="non_negative_cn_price"),
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="valid_cn_discount_percent"),
        CheckConstraint("tax_rate >= 0", name="non_negative_cn_tax_rate"),
        Index("idx_cnl_credit_note", "credit_note_id", "line_order"),
    )
    
    def __repr__(self) -> str:
        return f"CreditNoteLineModel(product={self.product_code}, qty={self.quantity})"


class DebitNoteModel(Base):
    """ORM Model for Debit Notes (Purchase Returns)"""
    __tablename__ = "debit_notes"
    
    # ========== المفتاح الأساسي ==========
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    issue_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # ========== روابط المستندات ==========
    purchase_return_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        nullable=True, 
        index=True
    )
    original_invoice_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), 
        nullable=True, 
        index=True
    )
    original_invoice_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # ========== المورد ==========
    supplier_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    supplier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # ========== الحالة ==========
    status: Mapped[str] = mapped_column(
        Enum('draft', 'issued', 'posted', 'applied', 'cancelled', name='debit_note_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    # ========== معلومات مالية ==========
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal('0'), nullable=False)
    
    # ========== الربط مع المحاسبة ==========
    journal_entry_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # ========== الملاحظات ==========
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ========== بيانات التدقيق ==========
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default='system', nullable=False)
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    issued_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ========== التحكم في التزامن ==========
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # ========== الفهارس والقيود ==========
    __table_args__ = (
        Index("idx_debit_notes_supplier", "supplier_id", "status"),
        Index("idx_debit_notes_date", "issue_date"),
        CheckConstraint("total_amount >= 0", name="non_negative_debit_total"),
    )
    
    def __repr__(self) -> str:
        return f"DebitNoteModel(id={self.id}, number={self.number}, supplier={self.supplier_name}, status={self.status})"


__all__ = [
    "SalesReturnModel",
    "SalesReturnLineModel",
    "CreditNoteModel",
    "CreditNoteLineModel",
    "DebitNoteModel",
]
