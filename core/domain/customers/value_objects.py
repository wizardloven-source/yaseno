# core/domain/customers/value_objects.py
"""Value Objects for Customers Domain"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class CustomerStatus(Enum):
    """حالة العميل"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class CustomerId:
    """معرف العميل الفريد"""
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            if isinstance(self.value, str):
                object.__setattr__(self, 'value', UUID(self.value))
            else:
                raise ValueError("CustomerId must be UUID or UUID string")

    @classmethod
    def generate(cls) -> 'CustomerId':
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> 'CustomerId':
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class CustomerCode:
    """كود العميل"""
    value: str

    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("Customer code cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ContactInfo:
    """معلومات الاتصال"""
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None


@dataclass(frozen=True)
class Address:
    """العنوان"""
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"