# core/application/users/dtos.py
"""Data Transfer Objects for Users Module"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass(frozen=True)
class UserDTO:
    """مستخدم - DTO كامل"""
    id: str
    username: str
    email: str
    full_name: str
    is_active: bool
    is_super_admin: bool
    roles: List[str]
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    last_login: Optional[datetime]
    version: int

    @property
    def display_name(self) -> str:
        return f"{self.username} - {self.full_name}"

    @property
    def is_admin(self) -> bool:
        return self.is_super_admin or "admin" in self.roles


@dataclass(frozen=True)
class UserListDTO:
    """قائمة المستخدمين مع معلومات التصفح"""
    users: List[UserDTO]
    total_count: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return (self.total_count + self.page_size - 1) // self.page_size if self.page_size > 0 else 1


__all__ = [
    "UserDTO",
    "UserListDTO",
]