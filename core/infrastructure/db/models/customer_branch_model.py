# core/infrastructure/db/models/customer_branch_model.py
"""
Customer Branch ORM Model - نموذج فروع العملاء في قاعدة البيانات
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text, Index, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CustomerBranchModel(Base):
    """نموذج فرع العميل في قاعدة البيانات"""
    __tablename__ = "customer_branches"

    # المفتاح الأساسي
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # كود الفرع (فريد)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # اسم الفرع
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # ربط العميل
    customer_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_code: Mapped[str] = mapped_column(String(50), nullable=False, default="")

    # العنوان
    street: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="LB")
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # معلومات الاتصال
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # الموقع الجغرافي
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # معلومات إضافية
    tax_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    working_hours: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    branch_type: Mapped[str] = mapped_column(String(50), default="store", nullable=False)

    # الحالة
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        index=True
    )

    # الحذف الناعم
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), default="system", nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    # ✅ القيود - تم التصحيح
    __table_args__ = (
        # فهارس للبحث
        Index("idx_customer_branches_code_status", "code", "status"),
        Index("idx_customer_branches_customer", "customer_id", "status"),
        Index("idx_customer_branches_customer_default", "customer_id", "is_default"),
        Index("idx_customer_branches_name", "name"),
        Index("idx_customer_branches_city", "city"),
        Index("idx_customer_branches_phone", "phone"),
        Index("idx_customer_branches_email", "email"),
        
        # قيود فريدة عادية
        UniqueConstraint("code", name="uq_customer_branches_code"),
        
        # ✅ قيد فريد جزئي باستخدام Index
        Index("uq_customer_branches_default", "customer_id", "is_default", 
              postgresql_where="is_default = true", unique=True),
    )

    def __repr__(self) -> str:
        return f"CustomerBranchModel(id={self.id}, code={self.code}, name={self.name}, customer={self.customer_name})"