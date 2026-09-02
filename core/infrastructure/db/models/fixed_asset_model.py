# core/infrastructure/db/models/fixed_asset_model.py
"""
Fixed Assets ORM Models - نماذج الأصول الثابتة
"""

from datetime import datetime, timezone, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Numeric, DateTime, Boolean, ForeignKey, Integer,
    Enum, Index, CheckConstraint, Text, Date,
    UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FixedAssetModel(Base):
    """نموذج الأصل الثابت"""
    __tablename__ = "fixed_assets"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # معلومات أساسية
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    asset_type: Mapped[str] = mapped_column(
        Enum('building', 'land', 'machinery', 'vehicle', 'furniture', 
             'computer', 'software', 'intangible', 'other', 
             name='asset_type_enum'),
        nullable=False
    )
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        Enum('draft', 'active', 'depreciating', 'fully_depreciated', 
             'disposed', 'sold', 'under_maintenance',
             name='asset_status_enum'),
        default='draft',
        nullable=False,
        index=True
    )
    
    # معلومات الشراء
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    acquisition_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    purchase_order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # معلومات الإهلاك
    salvage_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    useful_life_years: Mapped[int] = mapped_column(default=5)
    depreciation_method: Mapped[str] = mapped_column(
        Enum('straight_line', 'declining_balance', 'double_declining',
             'sum_of_years', 'units_of_production', 'none',
             name='depreciation_method_enum'),
        default='straight_line',
        nullable=False
    )
    depreciation_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    
    # معلومات الموقع
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    responsible_person: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    supplier_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # الحالة والإهلاك
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_fully_depreciated: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    depreciated_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    accumulated_depreciation: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    net_book_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    last_depreciation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_depreciation_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # جدول الإهلاك (مخزن كـ JSON)
    schedule: Mapped[List[Dict[str, Any]]] = mapped_column(JSONB, default=list)
    
    # سجل التصرف
    disposal_record: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # ملاحظات
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)

    __table_args__ = (
        Index("idx_fixed_assets_code_status", "code", "status"),
        Index("idx_fixed_assets_type", "asset_type"),
        Index("idx_fixed_assets_category", "category"),
        Index("idx_fixed_assets_status", "status"),
        Index("idx_fixed_assets_active", "is_active"),
        Index("idx_fixed_assets_depreciated", "is_fully_depreciated"),
        Index("idx_fixed_assets_responsible", "responsible_person"),
        Index("idx_fixed_assets_supplier", "supplier_id"),
        Index("idx_fixed_assets_serial", "serial_number"),
        Index("idx_fixed_assets_barcode", "barcode"),
        CheckConstraint("acquisition_cost >= 0", name="chk_acquisition_cost_non_negative"),
        CheckConstraint("salvage_value >= 0", name="chk_salvage_value_non_negative"),
        CheckConstraint("useful_life_years > 0", name="chk_useful_life_positive"),
        CheckConstraint("net_book_value >= 0", name="chk_net_book_value_non_negative"),
        CheckConstraint("accumulated_depreciation >= 0", name="chk_accumulated_depreciation_non_negative"),
    )

    def __repr__(self) -> str:
        return f"FixedAssetModel(id={self.id}, code={self.code}, name={self.name}, status={self.status})"


class DepreciationScheduleModel(Base):
    """نموذج جدول الإهلاك"""
    __tablename__ = "depreciation_schedule"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("fixed_assets.id"), nullable=False, index=True)
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    depreciation_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    accumulated_depreciation: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    net_book_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("asset_id", "period", name="uq_asset_period"),
        Index("idx_dep_schedule_asset", "asset_id"),
        Index("idx_dep_schedule_posted", "is_posted"),
    )

    def __repr__(self) -> str:
        return f"DepreciationScheduleModel(asset_id={self.asset_id}, period={self.period})"