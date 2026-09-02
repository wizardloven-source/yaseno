# core/infrastructure/db/models/product_model.py
"""Product ORM Model - محدث بدعم الحقول الجديدة"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List

from sqlalchemy import String, Numeric, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .account_model import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class ProductModel(Base):
    __tablename__ = "products"
    
    # الحقول الأساسية
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # التسعير
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    
    # أسعار إضافية
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    wholesale_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    
    # المخزون
    stock_quantity: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=0)
    min_stock: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=0)
    max_stock: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=0)
    
    # الوحدات
    base_unit: Mapped[str] = mapped_column(String(50), default="قطعة (pc)")
    
    # الباركود
    barcode: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, index=True)
    
    # الموقع
    main_location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # العلامات (Tags) - مصفوفة نصية
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    
    # الأبعاد والوزن
    weight: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0)
    weight_unit: Mapped[str] = mapped_column(String(10), default="kg")
    length: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    width: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    height: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    
    # الإعدادات
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_backorder: Mapped[bool] = mapped_column(Boolean, default=False)
    batch_tracking: Mapped[bool] = mapped_column(Boolean, default=False)
    low_stock_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)
    version: Mapped[int] = mapped_column(default=1)
    
    __table_args__ = (
        Index("idx_products_code_active", "code", "is_active"),
        Index("idx_products_category", "category"),
        Index("idx_products_barcode", "barcode"),
        Index("idx_products_tags", "tags", postgresql_using="gin"),
    )
    
    def __repr__(self) -> str:
        return f"ProductModel(code={self.code}, name={self.name}, price={self.unit_price})"