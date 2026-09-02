# core/infrastructure/db/models/idempotency_model.py
"""
Idempotency Key Model - مفتاح\Idempotency لمنع العمليات المزدوجة
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional

from sqlalchemy import String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Index

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class IdempotencyKeyModel(Base):
    """
    نموذج مفتاح Idempotency
    يمنع تنفيذ العمليات المالية المزدوجة عند إعادة الإرسال
    """
    __tablename__ = "idempotency_keys"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # The idempotency key from the client
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    
    # The endpoint this key is for
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # User who made the request
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Request hash (for detecting different requests with same key)
    request_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    # Response data (cached)
    response_status: Mapped[int] = mapped_column(Integer, nullable=True)
    response_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Status
    is_processing: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (
        Index("idx_idempotency_key_endpoint", "idempotency_key", "endpoint"),
        Index("idx_idempotency_expires", "expires_at"),
    )
