# core/domain/customer_branch/value_objects.py
"""
Customer Branch Value Objects - كائنات القيمة
"""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4
from typing import Optional


class BranchStatus(str, Enum):
    """حالة فرع العميل"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass(frozen=True)
class BranchId:
    """معرف فرع العميل"""
    value: UUID

    @classmethod
    def generate(cls) -> 'BranchId':
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> 'BranchId':
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class BranchCode:
    """كود فرع العميل"""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Branch code cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class BranchAddress:
    """عنوان فرع العميل"""
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    postal_code: Optional[str] = None

    @property
    def full_address(self) -> str:
        parts = [self.street, self.city, self.country]
        return ", ".join([p for p in parts if p])


@dataclass(frozen=True)
class BranchContact:
    """معلومات الاتصال"""
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None


@dataclass(frozen=True)
class BranchGeoLocation:
    """الموقع الجغرافي"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None