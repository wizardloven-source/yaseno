# core/infrastructure/db/models/site_model.py
"""
Site Model - نموذج المواقع متكامل مع العملاء والموردين والعملات الحقيقية
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text, Index, UniqueConstraint, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SiteModel(Base):
    """
    نموذج الموقع - متكامل مع:
    - العملاء (Customers)
    - الموردين (Suppliers)
    - العملات الحقيقية من نظام العملات
    """
    __tablename__ = "sites"

    # المفتاح الأساسي
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # معلومات الموقع الأساسية
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # نوع الموقع (مكتب، بناء، مستودع، مدجنة، أو مخصص)
    site_type: Mapped[str] = mapped_column(String(50), default="building", nullable=False, index=True)
    
    # ✅ نوع المسؤول (customer أو supplier)
    responsible_type: Mapped[str] = mapped_column(String(20), default="customer", nullable=False)
    
    # ✅ معرف المسؤول (من العملاء أو الموردين)
    responsible_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    responsible_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    responsible_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # ✅ عملة الموقع (من نظام العملات الحقيقي)
    currency_code: Mapped[str] = mapped_column(String(3), default="USD", nullable=False, index=True)

    # العنوان
    street: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default="LB")

    # معلومات الاتصال
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    mobile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    fax: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # شخص مسؤول الاتصال
    contact_person: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    contact_position: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # معلومات ضريبية
    tax_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # معلومات إضافية
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    working_hours: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # الإحداثيات (للخريطة)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # مساحة الموقع (متر مربع)
    area_sqm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # حالة الموقع
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # الحذف الناعم
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_by: Mapped[str] = mapped_column(String(100), default="system")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    updated_by: Mapped[str] = mapped_column(String(100), default="system")
    version: Mapped[int] = mapped_column(default=1)

    __table_args__ = (
        Index("idx_sites_code_status", "code", "is_active"),
        Index("idx_sites_name", "name"),
        Index("idx_sites_type", "site_type"),
        Index("idx_sites_city", "city"),
        Index("idx_sites_responsible", "responsible_type", "responsible_id", "is_active"),
        Index("idx_sites_currency", "currency_code"),
        UniqueConstraint("code", name="uq_sites_code"),
    )

    def __repr__(self) -> str:
        return f"SiteModel(id={self.id}, code={self.code}, name={self.name}, type={self.site_type}, responsible={self.responsible_name})"