# core/domain/auth/entities.py
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List

from .value_objects import UserId, RoleId, PermissionId


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Permission:
    """صلاحية - إجراء يمكن تنفيذه في النظام"""
    id: PermissionId
    code: str
    name: str
    category: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=utc_now)
    created_by: Optional[str] = None
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: Optional[str] = None
    version: int = 1


@dataclass
class Role:
    """دور - مجموعة من الصلاحيات"""
    id: RoleId
    name: str
    display_name: str
    description: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True
    permissions: List[Permission] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    created_by: Optional[str] = None
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: Optional[str] = None
    version: int = 1

    def has_permission(self, permission_code: str) -> bool:
        if self.is_admin:
            return True
        return any(p.code == permission_code for p in self.permissions)


@dataclass
class User:
    """مستخدم النظام"""
    id: UserId
    username: str
    email: str
    full_name: str
    password_hash: str = ""
    is_active: bool = True
    is_super_admin: bool = False
    roles: List[Role] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    created_by: Optional[str] = None
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: Optional[str] = None
    last_login: Optional[datetime] = None
    version: int = 1

    def has_permission(self, permission_code: str) -> bool:
        if self.is_super_admin:
            return True
        return any(role.has_permission(permission_code) for role in self.roles)