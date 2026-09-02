# core/infrastructure/db/models/auth_models.py
"""
Authentication & Authorization Models - نظام المصادقة والصلاحيات المتقدم
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Table, Column, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property

from .account_model import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ========== جداول الربط (Many-to-Many) ==========

# ربط الأدوار بالصلاحيات
role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", PG_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", PG_UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

# ربط المستخدمين بالأدوار
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", PG_UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


# ========== نموذج المستخدم الموسع ==========

class UserModel(Base):
    """نموذج المستخدم الموسع مع دعم الصلاحيات"""
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    # العلاقات
    roles: Mapped[List["RoleModel"]] = relationship(
        "RoleModel",
        secondary=user_roles_table,
        back_populates="users",
        lazy="selectin"
    )

    @hybrid_property
    def is_admin(self) -> bool:
        """التحقق مما إذا كان المستخدم مديرًا أو سوبر أدمن"""
        if self.is_super_admin:
            return True
        return any(role.is_admin for role in self.roles)

    def has_permission(self, permission_code: str) -> bool:
        """التحقق من وجود صلاحية محددة للمستخدم"""
        if self.is_super_admin:
            return True
        for role in self.roles:
            if role.has_permission(permission_code):
                return True
        return False

    def has_any_permission(self, *permission_codes: str) -> bool:
        """التحقق من وجود أي من الصلاحيات المطلوبة"""
        return any(self.has_permission(p) for p in permission_codes)

    def has_all_permissions(self, *permission_codes: str) -> bool:
        """التحقق من وجود جميع الصلاحيات المطلوبة"""
        return all(self.has_permission(p) for p in permission_codes)

    __table_args__ = (
        Index("idx_users_email_active", "email", "is_active"),
        Index("idx_users_username_active", "username", "is_active"),
    )


# ========== نموذج الدور ==========

class RoleModel(Base):
    """نموذج الدور - مجموعة من الصلاحيات"""
    __tablename__ = "roles"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    # العلاقات
    permissions: Mapped[List["PermissionModel"]] = relationship(
        "PermissionModel",
        secondary=role_permissions_table,
        back_populates="roles",
        lazy="selectin"
    )
    users: Mapped[List["UserModel"]] = relationship(
        "UserModel",
        secondary=user_roles_table,
        back_populates="roles"
    )

    def has_permission(self, permission_code: str) -> bool:
        """التحقق من وجود صلاحية في الدور"""
        if self.is_admin:
            return True
        return any(p.code == permission_code for p in self.permissions)

    def add_permission(self, permission: "PermissionModel") -> None:
        """إضافة صلاحية للدور"""
        if permission not in self.permissions:
            self.permissions.append(permission)

    def remove_permission(self, permission: "PermissionModel") -> None:
        """إزالة صلاحية من الدور"""
        if permission in self.permissions:
            self.permissions.remove(permission)

    __table_args__ = (
        Index("idx_roles_name_active", "name", "is_active"),
    )


# ========== نموذج الصلاحية ==========

class PermissionModel(Base):
    """نموذج الصلاحية - إجراء يمكن تنفيذه في النظام"""
    __tablename__ = "permissions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # accounting, invoicing, products, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # بيانات التدقيق
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    # العلاقات
    roles: Mapped[List["RoleModel"]] = relationship(
        "RoleModel",
        secondary=role_permissions_table,
        back_populates="permissions"
    )

    __table_args__ = (
        Index("idx_permissions_code_active", "code", "is_active"),
        Index("idx_permissions_category", "category"),
    )


# ========== نموذج جلسة المستخدم ==========

class UserSessionModel(Base):
    """نموذج جلسة المستخدم - تتبع الجلسات النشطة وتدوير refresh token"""
    __tablename__ = "user_sessions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Token data
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    
    # Device/Session info
    device_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 can be 45 chars
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Revocation
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Token family tracking (for reuse detection)
    family_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    generation: Mapped[int] = mapped_column(default=1, nullable=False)

    __table_args__ = (
        Index("idx_user_sessions_user_id", "user_id"),
        Index("idx_user_sessions_jti", "jti"),
        Index("idx_user_sessions_refresh_hash", "refresh_token_hash"),
        Index("idx_user_sessions_expires", "expires_at"),
    )