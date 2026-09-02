# core/infrastructure/db/models/account_model.py
"""
SQLALCHEMY ORM ENTERPRISE MODELS - YASEEN ERP STABLE SCHEMA

This module defines the relational database schema mapped to the domain entities.
All timestamps enforce absolute timezone awareness (UTC) to secure cross-border compliance.

DATABASE COMPLIANCE: PostgreSQL 14+ Optimized.
"""

from datetime import datetime, timezone, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Numeric, DateTime, Boolean, ForeignKey, 
    Enum, Index, CheckConstraint, UniqueConstraint, Text,
    Integer, BigInteger, Date as SQLDate
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# اعتماد أسلوب الفئة الأساسية الحديث لـ SQLAlchemy 2.0+
class Base(DeclarativeBase):
    """Base declarative class for type-hinted ORM mapping."""
    pass


def current_utc_time() -> datetime:
    """توليد توقيت واعي بالمنطقة الزمنية UTC لمنع فروقات السيرفرات المحلية."""
    return datetime.now(timezone.utc)


class AccountModel(Base):
    """ORM Model for Chart of Accounts (COA)."""
    __tablename__ = "accounts"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(
        Enum('asset', 'liability', 'equity', 'revenue', 'expense', name='account_type_enum'),
        nullable=False
    )
    parent_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    journal_lines: Mapped[List["JournalLineModel"]] = relationship(
        "JournalLineModel", back_populates="account", passive_deletes="RESTRICT"
    )
    ledger_entries: Mapped[List["LedgerEntryModel"]] = relationship(
        "LedgerEntryModel", back_populates="account", passive_deletes="RESTRICT"
    )

    __mapper_args__ = {"version_id_col": version}
    
    __table_args__ = (
        CheckConstraint("code ~ '^[1-9][0-9]{3,19}(\\.[0-9]{1,4})?$'", name="valid_account_code_format"),
        CheckConstraint("account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')", name="valid_account_type"),
        Index("idx_accounts_code_active", "code", "is_active"),
        Index("idx_accounts_type", "account_type"),
    )
    
    def __repr__(self) -> str:
        return f"AccountModel(code={self.code}, name={self.name}, type={self.account_type})"


class JournalEntryModel(Base):
    """ORM Model representing Double-Entry Accounting Journal Vouchers."""
    __tablename__ = "journal_entries"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    transaction_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    reversed_entry_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=True, index=True)
    reverses_entry_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    lines: Mapped[List["JournalLineModel"]] = relationship(
        "JournalLineModel", back_populates="journal_entry", cascade="all, delete-orphan", order_by="JournalLineModel.line_order"
    )
    ledger_entries: Mapped[List["LedgerEntryModel"]] = relationship(
        "LedgerEntryModel", back_populates="journal_entry", cascade="all, delete"
    )

    __mapper_args__ = {"version_id_col": version}
    
    __table_args__ = (
        CheckConstraint("NOT (is_posted = TRUE AND posted_at IS NULL)", name="posted_entry_must_have_posted_at"),
        CheckConstraint("NOT (is_posted = FALSE AND posted_at IS NOT NULL)", name="unposted_entry_must_not_have_posted_at"),
        Index("idx_je_posted_date", "is_posted", "entry_date"),
        Index("idx_je_date_range", "entry_date"),
        Index("idx_je_reference", "reference"),
    )
    
    def __repr__(self) -> str:
        status = "POSTED" if self.is_posted else "DRAFT"
        return f"JournalEntryModel(id={self.id}, status={status}, date={self.entry_date}, version={self.version})"


class JournalLineModel(Base):
    """ORM Model representing individual debit/credit transaction lines."""
    __tablename__ = "journal_lines"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    journal_entry_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal('0.00'), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal('0.00'), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False, index=True)
    
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    line_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    journal_entry: Mapped[JournalEntryModel] = relationship("JournalEntryModel", back_populates="lines")
    account: Mapped[AccountModel] = relationship("AccountModel", back_populates="journal_lines")
    
    __table_args__ = (
        CheckConstraint("(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)", name="xor_debit_credit"),
        CheckConstraint("debit_amount >= 0 AND credit_amount >= 0", name="non_negative_amounts"),
        Index("idx_jl_journal_entry", "journal_entry_id", "line_order"),
        Index("idx_jl_account", "account_id"),
        Index("idx_jl_currency", "currency"),
    )
    
    def __repr__(self) -> str:
        if self.debit_amount > 0:
            return f"JournalLineModel(debit={self.debit_amount})"
        return f"JournalLineModel(credit={self.credit_amount})"


class LedgerEntryModel(Base):
    """ORM Model representing finalized posts inside the General Ledger book."""
    __tablename__ = "ledger_entries"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    journal_entry_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("journal_entries.id", ondelete="RESTRICT"), nullable=False, index=True)
    account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    debit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal('0.00'), nullable=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 3), default=Decimal('0.00'), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False, index=True)
    
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fiscal_period: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True)
    
    journal_entry: Mapped[JournalEntryModel] = relationship("JournalEntryModel", back_populates="ledger_entries")
    account: Mapped[AccountModel] = relationship("AccountModel", back_populates="ledger_entries")
    
    __table_args__ = (
        CheckConstraint("(debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0)", name="xor_debit_credit"),
        Index("idx_le_account_date", "account_id", "entry_date"),
        Index("idx_le_period", "fiscal_period"),
        Index("idx_le_posted_at", "posted_at"),
        Index("idx_le_currency", "currency"),
    )
    
    def __repr__(self) -> str:
        return f"LedgerEntryModel(entry_date={self.entry_date}, account_id={self.account_id})"


# =============================================================================
# ✅ FISCAL YEAR MODEL
# =============================================================================

class FiscalYearModel(Base):
    """
    ORM Model for Fiscal Year.
    Represents a financial year with its periods.
    """
    __tablename__ = "fiscal_years"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    start_date: Mapped[date] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[date] = mapped_column(DateTime(timezone=True), nullable=False)
    
    status: Mapped[str] = mapped_column(
        Enum('draft', 'open', 'closing', 'closed', 'archived', name='fiscal_year_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    periods_per_year: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    period_type: Mapped[str] = mapped_column(
        Enum('month', 'quarter', 'adjustment', name='fiscal_period_type_enum'),
        default='month',
        nullable=False
    )
    
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    periods: Mapped[List["FiscalPeriodModel"]] = relationship(
        "FiscalPeriodModel",
        back_populates="fiscal_year",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("start_date < end_date", name="chk_fiscal_year_dates"),
        CheckConstraint("periods_per_year IN (4, 12)", name="chk_periods_per_year"),
        Index("idx_fiscal_years_status", "status"),
        Index("idx_fiscal_years_dates", "start_date", "end_date"),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"FiscalYearModel(id={self.id}, code={self.code}, status={self.status})"


# =============================================================================
# ✅ FISCAL PERIOD MODEL - مع جميع الحقول المطلوبة
# =============================================================================

class FiscalPeriodModel(Base):
    """
    ORM Model governing corporate financial period closings constraints.
    
    ✅ تم التعديل: تغيير طول عمود name من 10 إلى 50 للسماح بأسماء كاملة
    ✅ تم التعديل: تغيير Enum من ('MONTH', 'QUARTER', 'YEAR') إلى ('month', 'quarter', 'year')
    للتوافق مع كود المجال (Domain) وبقية النظام.
    """
    __tablename__ = "fiscal_periods"
    
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    fiscal_year_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("fiscal_years.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # ✅ تغيير الطول من 10 إلى 50 للسماح بأسماء كاملة مثل "ديسمبر 2026"
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # ✅ التعديل المطلوب: استخدام القيم الصغيرة للتوافق مع كود المجال
    period_type: Mapped[str] = mapped_column(
        Enum('month', 'quarter', 'year', name='period_type_enum'),
        nullable=False
    )
    
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ✅ الحقول المضافة - مطلوبة بواسطة fiscal_repository.py
    is_adjustment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    adjustment_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # ✅ حقل version للتحكم في التزامن (Optimistic Locking)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False)
    
    fiscal_year: Mapped["FiscalYearModel"] = relationship(
        "FiscalYearModel",
        back_populates="periods",
        foreign_keys=[fiscal_year_id]
    )
    
    __table_args__ = (
        CheckConstraint("start_date < end_date", name="valid_date_range"),
        UniqueConstraint("year", "period_number", "period_type", name="uq_period"),
        Index("idx_fp_date_range", "start_date", "end_date"),
        Index("idx_fp_fiscal_year", "fiscal_year_id"),
        {"extend_existing": True},
    )
    
    def __repr__(self) -> str:
        status = "CLOSED" if self.is_closed else "OPEN"
        return f"FiscalPeriodModel(name={self.name}, status={status}, version={self.version})"


class AuditLogModel(Base):
    """
    ORM Model for tracking system modifications and administrative user actions.
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    operation: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    old_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    new_state: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, nullable=False, index=True)
    
    __table_args__ = (
        Index("idx_audit_entity", "entity_type", "entity_id"),
        Index("idx_audit_user_time", "user_id", "created_at"),
        Index("idx_audit_operation_time", "operation", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"AuditLogModel(id={self.id}, operation={self.operation}, entity={self.entity_type})"


# ========== STRUCTURAL CORRIDOR EXPORTS ==========

__all__ = [
    "Base",
    "AccountModel",
    "JournalEntryModel",
    "JournalLineModel",
    "LedgerEntryModel",
    "FiscalYearModel",
    "FiscalPeriodModel",
    "AuditLogModel",
]