# core/infrastructure/db/models/notification_model.py
"""
Notification ORM Models - نماذج الإشعارات في قاعدة البيانات
✅ مصحح: إضافة extend_existing=True لحل مشكلة DuplicateTable
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional, Dict, Any

from sqlalchemy import String, Boolean, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), default="system", nullable=False, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_notifications_user_read", "user_id", "is_read"),
        Index("idx_notifications_type", "notification_type"),
        Index("idx_notifications_created", "created_at"),
        {"extend_existing": True},
    )


class NotificationPreferenceModel(Base):
    __tablename__ = "notification_preferences"

    user_id: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    email_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    system_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sound_notifications: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preferences: Mapped[Optional[Dict[str, bool]]] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        {"extend_existing": True},
    )


class NotificationTemplateModel(Base):
    __tablename__ = "notification_templates"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[Dict[str, str]]] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        Index("idx_notification_templates_code", "code"),
        Index("idx_notification_templates_active", "is_active"),
        {"extend_existing": True},
    )


class FundsNotificationModel(Base):
    """نموذج إشعارات الصناديق"""
    __tablename__ = "funds_notifications"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    
    data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, default=dict)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # ✅ 🔑 الحل الأساسي: إضافة extend_existing=True
    __table_args__ = (
        Index("ix_funds_notifications_user_id", "user_id"),
        Index("ix_funds_notifications_is_read", "is_read"),
        Index("ix_funds_notifications_notification_type", "notification_type"),
        Index("ix_funds_notifications_role", "role"),
        Index("ix_funds_notifications_created_at", "created_at"),
        Index("idx_funds_notifications_user_read", "user_id", "is_read"),
        Index("idx_funds_notifications_created", "created_at"),
        Index("idx_funds_notifications_type_sent", "notification_type", "is_sent"),
        Index("idx_funds_notifications_role", "role", "is_read"),
        {"extend_existing": True},  # 🔑 هذا يحل المشكلة
    )

    def __repr__(self) -> str:
        return f"FundsNotificationModel(id={self.id}, user={self.user_id}, type={self.notification_type})"


__all__ = [
    "NotificationModel",
    "NotificationPreferenceModel",
    "NotificationTemplateModel",
    "FundsNotificationModel",
]