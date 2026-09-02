# core/domain/accounting/value_objects.py

from dataclasses import dataclass
from typing import Optional
import uuid
from core.domain.shared.value_objects import Money, AccountCode


@dataclass(frozen=True)
class JournalEntryId:
    """معرف فريد لقيد اليومية."""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("JournalEntryId cannot be empty.")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> 'JournalEntryId':
        """توليد معرف جديد."""
        return cls(value=str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> 'JournalEntryId':
        """إنشاء من نص."""
        return cls(value=value)


@dataclass(frozen=True)
class EntryId:
    """معرف لسطر القيد المحاسبي في دفتر الأستاذ."""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("EntryId cannot be empty.")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> 'EntryId':
        """توليد معرف جديد."""
        return cls(value=str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> 'EntryId':
        """إنشاء من نص."""
        return cls(value=value)


@dataclass(frozen=True)
class TransactionType:
    """نوع الحركة."""
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class PostingStatus:
    """حالة الترحيل."""
    status: str

    def __post_init__(self):
        valid_statuses = {"Draft", "Posted", "Reversed"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid Posting Status: {self.status}")

    def __str__(self) -> str:
        return self.status


@dataclass(frozen=True)
class PeriodReference:
    """مرجع الفترة المالية."""
    year: int
    month: int

    def __post_init__(self):
        if not (1 <= self.month <= 12):
            raise ValueError("Invalid month in PeriodReference.")
        if self.year < 2000:
            raise ValueError("Invalid fiscal year.")

    def __str__(self) -> str:
        return f"{self.year}-{self.month:02d}"

    @classmethod
    def from_string(cls, value: str) -> 'PeriodReference':
        """إنشاء PeriodReference من نص (مثال: '2024-01')"""
        parts = value.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid PeriodReference format: {value}")
        return cls(year=int(parts[0]), month=int(parts[1]))

    def get_year(self) -> int:
        return self.year

    def get_month(self) -> Optional[int]:
        return self.month

    def get_quarter(self) -> Optional[int]:
        return (self.month - 1) // 3 + 1 if self.month else None

    def is_month(self) -> bool:
        return True

    def is_quarter(self) -> bool:
        return False

    def is_year(self) -> bool:
        return False


__all__ = [
    "AccountCode",
    "JournalEntryId",
    "EntryId",
    "TransactionType",
    "PostingStatus",
    "PeriodReference",
]