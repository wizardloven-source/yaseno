# core/infrastructure/db/models/workflow_model.py
"""
Approval Workflow ORM Models - نماذج سير عمل الموافقات
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


class WorkflowModel(Base):
    """نموذج سير العمل"""
    __tablename__ = "workflows"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    entity_type: Mapped[str] = mapped_column(
        Enum('invoice', 'payment', 'journal_entry', 'purchase_order', 
             'sales_order', 'expense', 'budget', 'contract', 'user', 'custom',
             name='workflow_entity_type_enum'),
        nullable=False,
        index=True
    )
    
    status: Mapped[str] = mapped_column(
        Enum('draft', 'active', 'inactive', 'archived', name='workflow_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    steps: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_approve_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    auto_approve_after_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        CheckConstraint("auto_approve_threshold IS NULL OR auto_approve_threshold >= 0", name="chk_auto_approve_threshold"),
        CheckConstraint("auto_approve_after_days IS NULL OR auto_approve_after_days >= 0", name="chk_auto_approve_days"),
        UniqueConstraint("entity_type", name="uq_workflow_entity_type"),
        Index("idx_workflows_code_status", "code", "status"),
        Index("idx_workflows_entity_type_status", "entity_type", "status"),
    )

    def __repr__(self) -> str:
        return f"WorkflowModel(id={self.id}, code={self.code}, status={self.status})"


class ApprovalRequestModel(Base):
    """نموذج طلب الموافقة"""
    __tablename__ = "approval_requests"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workflows.id"),
        nullable=False,
        index=True
    )
    
    entity_type: Mapped[str] = mapped_column(
        Enum('invoice', 'payment', 'journal_entry', 'purchase_order', 
             'sales_order', 'expense', 'budget', 'contract', 'user', 'custom',
             name='workflow_entity_type_enum'),
        nullable=False,
        index=True
    )
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    status: Mapped[str] = mapped_column(
        Enum('draft', 'pending', 'in_review', 'approved', 'rejected', 'cancelled', 'expired',
             name='request_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    current_step_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        Enum('low', 'normal', 'high', 'urgent', name='request_priority_enum'),
        default='normal',
        nullable=False
    )
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    approvals: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    history: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    requested_by_name: Mapped[str] = mapped_column(String(200), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    approved_by_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    rejected_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rejected_by_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # ✅ تم التعديل: metadata → extra_data (لحل تعارض الاسم المحجوز)
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    __table_args__ = (
        CheckConstraint("amount IS NULL OR amount >= 0", name="chk_amount_non_negative"),
        Index("idx_requests_entity", "entity_type", "entity_id"),
        Index("idx_requests_status_priority", "status", "priority"),
        Index("idx_requests_requested_by", "requested_by", "status"),
        Index("idx_requests_due_date", "due_date"),
        Index("idx_requests_created_at", "requested_at"),
    )

    def __repr__(self) -> str:
        return f"ApprovalRequestModel(id={self.id}, title={self.title}, status={self.status})"