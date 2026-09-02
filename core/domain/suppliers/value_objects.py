# core/domain/suppliers/value_objects.py
"""Value Objects for Suppliers Domain"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class SupplierStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SupplierId:
    value: UUID

    def __post_init__(self):
        if not isinstance(self.value, UUID):
            if isinstance(self.value, str):
                object.__setattr__(self, 'value', UUID(self.value))
            else:
                raise ValueError("SupplierId must be UUID or UUID string")

    @classmethod
    def generate(cls) -> 'SupplierId':
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> 'SupplierId':
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class SupplierCode:
    value: str

    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("Supplier code cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ContactInfo:
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None


@dataclass(frozen=True)
class Address:
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"