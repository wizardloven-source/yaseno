# core/infrastructure/db/models/customer_model.py
"""Customer ORM Model"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional
from sqlalchemy import String, Numeric, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .account_model import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class CustomerModel(Base):
    __tablename__ = "customers"
    
    # المفتاح الأساسي
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # المعلومات الأساسية
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # معلومات الاتصال
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # العنوان
    street: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="LB")  # ✅ تم التعديل: 2 → 100
    
    # المعلومات المالية
    tax_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # الحالة
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False, index=True
    )
    
    # الحذف الناعم
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=current_utc_time, onupdate=current_utc_time)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")
    version: Mapped[int] = mapped_column(default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("idx_customers_code_status", "code", "status"),
        Index("idx_customers_name", "name"),
        Index("idx_customers_status_deleted", "status", "is_deleted"),
        Index("idx_customers_phone", "phone"),
        Index("idx_customers_email", "email"),
    )

    def __repr__(self) -> str:
        return f"CustomerModel(id={self.id}, code={self.code}, name={self.name}, status={self.status})"