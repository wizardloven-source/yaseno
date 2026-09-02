# core/infrastructure/db/models/inventory_models.py
"""
Inventory ORM Models - نماذج المخزون
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    String, Numeric, DateTime, Boolean, ForeignKey,
    Enum, Index, CheckConstraint, Text, Date, Integer
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StockMovementModel(Base):
    """
    نموذج حركة المخزون
    """
    __tablename__ = "stock_movements"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # الكيان المرتبط (منتج، مادة خام، إلخ)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # نوع الحركة
    movement_type: Mapped[str] = mapped_column(
        Enum(
            'purchase', 'sale', 'return', 'adjustment_in', 'adjustment_out',
            'transfer_in', 'transfer_out', 'damage', 'expired',
            name='stock_movement_type_enum'
        ),
        nullable=False,
        index=True
    )
    
    # الكميات والتكاليف
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # المرجع
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # الدفعات والأرقام التسلسلية
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # الموقع
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # ملاحظات
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # تاريخ الحركة
    movement_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # البيانات الوصفية
    movement_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_stock_movements_entity", "entity_type", "entity_id"),
        Index("idx_stock_movements_reference", "reference_type", "reference_id"),
        Index("idx_stock_movements_type_date", "movement_type", "movement_date"),
        Index("idx_stock_movements_batch", "batch_number"),
        Index("idx_stock_movements_created", "created_at"),
        CheckConstraint("quantity >= 0", name="chk_stock_movement_quantity_non_negative"),
        CheckConstraint("unit_cost >= 0", name="chk_stock_movement_unit_cost_non_negative"),
        CheckConstraint("total_cost >= 0", name="chk_stock_movement_total_cost_non_negative"),
    )

    def __repr__(self) -> str:
        return f"StockMovementModel(id={self.id}, type={self.movement_type}, qty={self.quantity}, entity={self.entity_type}:{self.entity_id})"


class StockBatchModel(Base):
    """
    نموذج دفعة المخزون
    """
    __tablename__ = "stock_batches"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # الكيان المرتبط
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # رقم الدفعة
    batch_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    
    # الكميات
    initial_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    
    # التكاليف
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # التواريخ
    production_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # الموقع
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # الحالة
    status: Mapped[str] = mapped_column(
        Enum(
            'active', 'partially_consumed', 'fully_consumed', 'expired', 'quarantined',
            name='stock_batch_status_enum'
        ),
        default='active',
        nullable=False,
        index=True
    )
    
    # ملاحظات
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # البيانات الوصفية
    batch_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_stock_batches_entity", "entity_type", "entity_id"),
        Index("idx_stock_batches_status", "status"),
        Index("idx_stock_batches_expiry", "expiry_date"),
        Index("idx_stock_batches_created", "created_at"),
        CheckConstraint("initial_quantity >= 0", name="chk_batch_initial_quantity_non_negative"),
        CheckConstraint("current_quantity >= 0", name="chk_batch_current_quantity_non_negative"),
        CheckConstraint("current_quantity <= initial_quantity", name="chk_batch_quantity_consistency"),
        CheckConstraint("unit_cost >= 0", name="chk_batch_unit_cost_non_negative"),
    )

    def __repr__(self) -> str:
        return f"StockBatchModel(id={self.id}, batch={self.batch_number}, qty={self.current_quantity}/{self.initial_quantity}, status={self.status})"


class StockTransferModel(Base):
    """
    نموذج تحويل المخزون
    """
    __tablename__ = "stock_transfers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # الكيان المرتبط
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # الكميات والتكاليف
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # المواقع
    from_location: Mapped[str] = mapped_column(String(200), nullable=False)
    to_location: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # المرجع
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # الدفعات
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    serial_numbers: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    
    # الحالة
    status: Mapped[str] = mapped_column(
        String(20),
        default='pending',
        nullable=False,
        index=True
    )
    
    # ملاحظات
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # البيانات الوصفية
    transfer_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_stock_transfers_entity", "entity_type", "entity_id"),
        Index("idx_stock_transfers_status", "status"),
        Index("idx_stock_transfers_locations", "from_location", "to_location"),
        Index("idx_stock_transfers_created", "created_at"),
        CheckConstraint("quantity >= 0", name="chk_transfer_quantity_non_negative"),
        CheckConstraint("unit_cost >= 0", name="chk_transfer_unit_cost_non_negative"),
        CheckConstraint("total_cost >= 0", name="chk_transfer_total_cost_non_negative"),
    )

    def __repr__(self) -> str:
        return f"StockTransferModel(id={self.id}, status={self.status}, qty={self.quantity}, from={self.from_location}, to={self.to_location})"


class StockLayerModel(Base):
    """
    نموذج طبقة المخزون - يستخدم لتقييم FIFO/LIFO
    """
    __tablename__ = "stock_layers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # الكيان المرتبط
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # الكمية والتكلفة
    quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    
    # رقم الدفعة (اختياري)
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # تاريخ الشراء
    purchase_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # تاريخ الانتهاء (اختياري)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # البيانات الوصفية
    layer_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_stock_layers_entity", "entity_type", "entity_id"),
        Index("idx_stock_layers_batch", "batch_number"),
        CheckConstraint("quantity >= 0", name="chk_layer_quantity_non_negative"),
        CheckConstraint("unit_cost >= 0", name="chk_layer_unit_cost_non_negative"),
    )

    def __repr__(self) -> str:
        return f"StockLayerModel(id={self.id}, entity={self.entity_type}:{self.entity_id}, qty={self.quantity}, cost={self.unit_cost})"


class StockSerialNumberModel(Base):
    """
    نموذج الأرقام التسلسلية للمخزون
    """
    __tablename__ = "stock_serial_numbers"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # الكيان المرتبط (منتج)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # الرقم التسلسلي
    serial_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    
    # رقم الدفعة (اختياري)
    batch_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    # الحالة
    status: Mapped[str] = mapped_column(
        Enum(
            'available', 'sold', 'reserved', 'damaged', 'returned',
            name='serial_number_status_enum'
        ),
        default='available',
        nullable=False,
        index=True
    )
    
    # الموقع
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # تاريخ الإنتاج
    production_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # تاريخ الانتهاء (اختياري)
    expiry_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # المرجع (فاتورة، أمر شراء، إلخ)
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    
    # ملاحظات
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    
    # Optimistic Locking
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # البيانات الوصفية
    serial_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index("idx_serial_numbers_entity", "entity_type", "entity_id"),
        Index("idx_serial_numbers_status", "status"),
        Index("idx_serial_numbers_batch", "batch_number"),
        Index("idx_serial_numbers_reference", "reference_type", "reference_id"),
        Index("idx_serial_numbers_created", "created_at"),
        CheckConstraint("serial_number != ''", name="chk_serial_number_not_empty"),
    )

    def __repr__(self) -> str:
        return f"StockSerialNumberModel(id={self.id}, serial={self.serial_number}, status={self.status}, entity={self.entity_type}:{self.entity_id})"