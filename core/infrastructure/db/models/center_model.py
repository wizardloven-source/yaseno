# core/infrastructure/db/models/center_model.py
"""
Cost & Profit Centers ORM Models - نماذج مراكز التكلفة والربح
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Integer, DateTime, Boolean, ForeignKey,
    Enum, Index, CheckConstraint, Text, Date, Numeric,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CenterModel(Base):
    """نموذج مركز التكلفة/الربح"""
    __tablename__ = "centers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    center_type: Mapped[str] = mapped_column(
        Enum('cost', 'profit', 'both', name='center_type_enum'),
        nullable=False,
        index=True
    )
    
    status: Mapped[str] = mapped_column(
        Enum('draft', 'active', 'suspended', 'closed', 'archived', name='center_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    parent_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    path: Mapped[str] = mapped_column(String(500), default="", nullable=False, index=True)
    
    manager_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    manager_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    budget_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    budget_used: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    budget_currency: Mapped[str] = mapped_column(String(3), default="USD")
    budget_period_start: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    budget_period_end: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    
    # ✅ تغيير اسم الحقل من 'metadata' إلى 'center_metadata'
    center_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        CheckConstraint("budget_total >= 0", name="chk_budget_total_non_negative"),
        CheckConstraint("budget_used >= 0", name="chk_budget_used_non_negative"),
        Index("idx_centers_code_status", "code", "status"),
        Index("idx_centers_parent", "parent_code"),
        Index("idx_centers_path", "path"),
        Index("idx_centers_type_status", "center_type", "status"),
        Index("idx_centers_manager", "manager_id"),
    )

    def __repr__(self) -> str:
        return f"CenterModel(id={self.id}, code={self.code}, name={self.name}, type={self.center_type})"


class CenterAllocationModel(Base):
    """نموذج توزيع المصروفات"""
    __tablename__ = "center_allocations"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    allocation_rule_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    source_center_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    allocations: Mapped[Dict[str, Decimal]] = mapped_column(JSONB, nullable=False, default=dict)
    period_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    period_end: Mapped[datetime] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum('draft', 'posted', 'cancelled', name='allocation_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    journal_entry_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="chk_allocation_amount_non_negative"),
        Index("idx_allocation_source", "source_center_code", "period_start", "period_end"),
        Index("idx_allocation_status", "status"),
        Index("idx_allocation_journal", "journal_entry_id"),
    )

    def __repr__(self) -> str:
        return f"CenterAllocationModel(id={self.id}, source={self.source_center_code}, amount={self.total_amount})"


class CenterAllocationRuleModel(Base):
    """نموذج قاعدة توزيع المصروفات"""
    __tablename__ = "center_allocation_rules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_center_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_center_codes: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False, default=list)
    method: Mapped[str] = mapped_column(
        Enum('percentage', 'fixed_amount', 'manual', 'equal', 'weighted', 'activity_based', name='allocation_method_enum'),
        nullable=False
    )
    percentage: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    fixed_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    weights: Mapped[Optional[Dict[str, Decimal]]] = mapped_column(JSONB, nullable=True)
    frequency: Mapped[str] = mapped_column(
        Enum('daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'one_time', name='allocation_frequency_enum'),
        default='monthly',
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    valid_from: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    valid_to: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        CheckConstraint("percentage IS NULL OR (percentage >= 0 AND percentage <= 100)", name="chk_percentage_range"),
        CheckConstraint("fixed_amount IS NULL OR fixed_amount >= 0", name="chk_fixed_amount_non_negative"),
        Index("idx_rule_source", "source_center_code", "is_active"),
        Index("idx_rule_method", "method"),
        Index("idx_rule_frequency", "frequency"),
    )

    def __repr__(self) -> str:
        return f"CenterAllocationRuleModel(id={self.id}, name={self.name}, method={self.method})"