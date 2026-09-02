# core/domain/sites/value_objects.py
from dataclasses import dataclass
from enum import Enum
from uuid import UUID, uuid4


class SiteType(str, Enum):
    """أنواع المواقع"""
    GENERAL = "general"          # عام
    WAREHOUSE = "warehouse"      # مستودع
    BRANCH = "branch"            # فرع
    STORE = "store"              # متجر
    OFFICE = "office"            # مكتب
    DELIVERY = "delivery"        # نقطة تسليم


@dataclass(frozen=True)
class SiteId:
    """معرف الموقع"""
    value: UUID

    def __post_init__(self):
        if isinstance(self.value, str):
            object.__setattr__(self, 'value', UUID(self.value))

    @classmethod
    def generate(cls) -> 'SiteId':
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> 'SiteId':
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class SiteCode:
    """كود الموقع"""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Site code cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value