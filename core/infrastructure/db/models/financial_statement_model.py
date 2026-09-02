# core/infrastructure/db/models/financial_statement_model.py
"""
Financial Statements ORM Models - نماذج القوائم المالية
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Integer, DateTime, Boolean, ForeignKey,
    Enum, Index, CheckConstraint, Text, Date, Numeric,
    UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FinancialStatementModel(Base):
    """نموذج القائمة المالية"""
    __tablename__ = "financial_statements"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # نوع القائمة
    statement_type: Mapped[str] = mapped_column(
        Enum(
            'income_statement', 'balance_sheet', 'cash_flow', 
            'equity_statement', 'trial_balance',
            name='statement_type_enum'
        ),
        nullable=False,
        index=True
    )
    
    # معلومات الفترة
    period_start: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    period_name: Mapped[str] = mapped_column(String(100), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(
        Enum('monthly', 'quarterly', 'yearly', 'custom', name='period_type_enum'),
        default='custom',
        nullable=False
    )
    
    # العملة
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # الإجماليات (مخزنة كـ JSON للمرونة)
    totals: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # البيانات الكاملة للقائمة (JSON)
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    
    # للقوائم المقارنة
    is_comparative: Mapped[bool] = mapped_column(Boolean, default=False)
    previous_period_start: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    previous_period_end: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    previous_totals: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # بيانات التدقيق
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        CheckConstraint("period_start <= period_end", name="chk_period_dates"),
        Index("idx_fs_type_period", "statement_type", "period_start", "period_end"),
        Index("idx_fs_year", "fiscal_year"),
        Index("idx_fs_generated", "generated_at"),
        UniqueConstraint(
            "statement_type", "period_start", "period_end", "currency",
            name="uq_fs_period"
        ),
    )

    def __repr__(self) -> str:
        return f"FinancialStatementModel(id={self.id}, type={self.statement_type}, period={self.period_start}-{self.period_end})"


class FinancialStatementLineModel(Base):
    """نموذج سطر القائمة المالية (للتخزين المنفصل - اختياري)"""
    __tablename__ = "financial_statement_lines"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    statement_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("financial_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # معلومات السطر
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # التصنيف
    category: Mapped[str] = mapped_column(
        Enum(
            'revenue', 'cogs', 'operating_expense', 'other_income', 'other_expense',
            'income_tax', 'current_asset', 'fixed_asset', 'intangible_asset',
            'current_liability', 'long_term_liability', 'equity',
            name='account_category_enum'
        ),
        nullable=False
    )
    
    # الهيكل الهرمي
    parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # خصائص السطر
    is_total: Mapped[bool] = mapped_column(Boolean, default=False)
    is_subtotal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_section_header: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_fsl_statement", "statement_id", "category"),
        Index("idx_fsl_parent", "parent_id"),
        Index("idx_fsl_order", "order"),
    )

    def __repr__(self) -> str:
        return f"FinancialStatementLineModel(code={self.code}, name={self.name}, amount={self.amount})"