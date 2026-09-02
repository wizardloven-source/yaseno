# core/infrastructure/db/models/reconciliation_model.py
"""
Bank Reconciliation ORM Models - نماذج التسوية البنكية
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Numeric, DateTime, Boolean, ForeignKey,
    Enum, Index, CheckConstraint, Text, Date,
    UniqueConstraint, BigInteger, Integer, JSON  # ✅ تمت إضافة Integer هنا
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BankStatementModel(Base):
    """
    نموذج كشف الحساب البنكي
    """
    __tablename__ = "bank_statements"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # معلومات الحساب
    account_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # تاريخ الكشف
    statement_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    
    # الأرصدة
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # بيانات الملف
    file_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    
    # بيانات التدقيق
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    # العلاقات
    reconciliation: Mapped[Optional["ReconciliationModel"]] = relationship(
        "ReconciliationModel",
        back_populates="bank_statement",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # البيانات الوصفية (JSON) - تم تغيير الاسم لتجنب التعارض
    statement_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_bank_statements_account_date", "account_code", "statement_date"),
        Index("idx_bank_statements_bank", "bank_name", "account_number"),
        Index("idx_bank_statements_uploaded", "uploaded_at"),
        Index("idx_bank_statements_hash", "file_hash"),
        CheckConstraint("opening_balance >= 0", name="chk_opening_balance_non_negative"),
        CheckConstraint("closing_balance >= 0", name="chk_closing_balance_non_negative"),
    )

    def __repr__(self) -> str:
        return f"BankStatementModel(id={self.id}, account={self.account_code}, bank={self.bank_name})"


class ReconciliationModel(Base):
    """
    نموذج التسوية البنكية
    """
    __tablename__ = "reconciliations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # الربط بكشف الحساب
    bank_statement_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bank_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True
    )
    
    # معلومات الحساب
    account_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    
    # تاريخ التسوية
    reconciliation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    
    # حالة التسوية
    status: Mapped[str] = mapped_column(
        Enum('draft', 'in_progress', 'reconciled', 'partial', 'failed', 'cancelled', name='reconciliation_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    # نوع التسوية
    reconciliation_type: Mapped[str] = mapped_column(
        Enum('bank', 'cash', 'customer', 'supplier', name='reconciliation_type_enum'),
        default='bank',
        nullable=False
    )
    
    # أرصدة دفتر الأستاذ
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    closing_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    
    # أرصدة البنك
    bank_opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    bank_closing_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, nullable=False)
    
    # العملة
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # القيد المحاسبي
    journal_entry_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("journal_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # بيانات إضافية
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # بيانات التدقيق
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    completed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # البيانات الوصفية - تم تغيير الاسم لتجنب التعارض
    reconciliation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    # العلاقات
    bank_statement: Mapped[BankStatementModel] = relationship(
        "BankStatementModel",
        back_populates="reconciliation"
    )
    matches: Mapped[List["ReconciliationMatchModel"]] = relationship(
        "ReconciliationMatchModel",
        back_populates="reconciliation",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        Index("idx_reconciliations_status_date", "status", "reconciliation_date"),
        Index("idx_reconciliations_account", "account_code"),
        Index("idx_reconciliations_created", "created_at"),
        Index("idx_reconciliations_completed", "completed_at"),
        CheckConstraint("closing_balance >= 0", name="chk_closing_balance_non_negative"),
        CheckConstraint("bank_closing_balance >= 0", name="chk_bank_closing_balance_non_negative"),
    )

    def __repr__(self) -> str:
        return f"ReconciliationModel(id={self.id}, account={self.account_code}, status={self.status})"


class ReconciliationMatchModel(Base):
    """
    نموذج سطر المطابقة في التسوية
    """
    __tablename__ = "reconciliation_matches"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # الربط بالتسوية
    reconciliation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("reconciliations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # معرفات الحركات
    bank_line_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ledger_entry_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # المبلغ
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # حالة المطابقة
    status: Mapped[str] = mapped_column(
        Enum('matched', 'unmatched', 'partial', 'manual', 'ignored', name='matching_status_enum'),
        default='matched',
        nullable=False,
        index=True
    )
    
    # بيانات المطابقة
    matched_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    # نسبة التطابق
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    
    # ملاحظات
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # البيانات الوصفية - تم تغيير الاسم لتجنب التعارض
    match_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    # العلاقات
    reconciliation: Mapped[ReconciliationModel] = relationship(
        "ReconciliationModel",
        back_populates="matches"
    )

    __table_args__ = (
        Index("idx_reconciliation_matches_reconciliation", "reconciliation_id"),
        Index("idx_reconciliation_matches_bank_line", "bank_line_id"),
        Index("idx_reconciliation_matches_ledger_entry", "ledger_entry_id"),
        Index("idx_reconciliation_matches_status", "status"),
        Index("idx_reconciliation_matches_score", "match_score"),
        UniqueConstraint(
            "reconciliation_id", "bank_line_id",
            name="uq_reconciliation_match_bank_line"
        ),
        UniqueConstraint(
            "reconciliation_id", "ledger_entry_id",
            name="uq_reconciliation_match_ledger_entry"
        ),
        CheckConstraint("match_score BETWEEN 0 AND 100", name="chk_match_score_range"),
        CheckConstraint("amount >= 0", name="chk_match_amount_non_negative"),
    )

    def __repr__(self) -> str:
        return f"ReconciliationMatchModel(id={self.id}, status={self.status}, amount={self.amount})"