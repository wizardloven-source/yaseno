# core/application/users/commands.py
"""Commands and Queries for Users Module"""

from dataclasses import dataclass
from typing import Optional, List


# ========== COMMANDS ==========

@dataclass(frozen=True)
class CreateUserCommand:
    """أمر إنشاء مستخدم جديد"""
    username: str
    email: str
    full_name: str
    password: str
    role_ids: Optional[List[str]] = None
    is_active: bool = True
    is_super_admin: bool = False
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateUserCommand:
    """أمر تحديث مستخدم"""
    user_id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_super_admin: Optional[bool] = None
    updated_by: str = "system"
    version: int = 1


@dataclass(frozen=True)
class DeleteUserCommand:
    """أمر حذف مستخدم"""
    user_id: str
    permanent: bool = False
    deleted_by: str = "system"


@dataclass(frozen=True)
class ChangePasswordCommand:
    """أمر تغيير كلمة المرور"""
    user_id: str
    old_password: str
    new_password: str
    version: int = 1


@dataclass(frozen=True)
class ResetPasswordCommand:
    """أمر إعادة تعيين كلمة المرور"""
    user_id: str
    new_password: str
    reset_by: str = "system"


# ========== QUERIES ==========

@dataclass(frozen=True)
class GetUserQuery:
    """استعلام لجلب مستخدم"""
    user_id: str


@dataclass(frozen=True)
class ListUsersQuery:
    """استعلام لقائمة المستخدمين"""
    include_inactive: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetUserPermissionsQuery:
    """استعلام لجلب صلاحيات المستخدم"""
    user_id: str


__all__ = [
    "CreateUserCommand",
    "UpdateUserCommand",
    "DeleteUserCommand",
    "ChangePasswordCommand",
    "ResetPasswordCommand",
    "GetUserQuery",
    "ListUsersQuery",
    "GetUserPermissionsQuery",
]