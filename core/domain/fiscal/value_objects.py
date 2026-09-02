# core/domain/fiscal/value_objects.py
"""
Fiscal Year Value Objects - كائنات القيمة للسنة المالية
"""

from dataclasses import dataclass
from enum import Enum
from datetime import date, datetime
from typing import Optional


class FiscalYearStatus(Enum):
    """حالة السنة المالية"""
    DRAFT = "draft"          # مسودة - لم تبدأ بعد
    OPEN = "open"            # مفتوحة - يمكن الترحيل فيها
    CLOSING = "closing"      # قيد الإغلاق
    CLOSED = "closed"        # مغلقة - لا يمكن الترحيل
    ARCHIVED = "archived"    # مؤرشفة - للقراءة فقط


class FiscalPeriodType(Enum):
    """نوع الفترة المالية"""
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ADJUSTMENT = "adjustment"  # فترة تعديل


class FiscalQuarter(Enum):
    """أرباع السنة المالية"""
    Q1 = 1
    Q2 = 2
    Q3 = 3
    Q4 = 4


@dataclass(frozen=True)
class FiscalYearId:
    """معرف السنة المالية"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("FiscalYearId cannot be empty")
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> 'FiscalYearId':
        return cls(value)


@dataclass(frozen=True)
class FiscalPeriodId:
    """معرف الفترة المالية"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("FiscalPeriodId cannot be empty")
    
    def __str__(self) -> str:
        return self.value
    
    @classmethod
    def from_string(cls, value: str) -> 'FiscalPeriodId':
        return cls(value)


@dataclass(frozen=True)
class FiscalYearCode:
    """كود السنة المالية"""
    value: str

    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("FiscalYearCode cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class FiscalPeriodReference:
    """مرجع الفترة المالية (مثل 2025-01)"""
    year: int
    period_number: int  # 1-12 للشهر، 1-4 للربع

    def __post_init__(self):
        if self.year < 2000:
            raise ValueError(f"Invalid year: {self.year}")
        if not (1 <= self.period_number <= 12):
            raise ValueError(f"Invalid period number: {self.period_number}")

    def __str__(self) -> str:
        return f"{self.year}-{self.period_number:02d}"

    @classmethod
    def from_string(cls, value: str) -> 'FiscalPeriodReference':
        parts = value.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid period reference format: {value}")
        return cls(year=int(parts[0]), period_number=int(parts[1]))

    def get_quarter(self) -> int:
        """الحصول على رقم الربع (1-4)"""
        return (self.period_number - 1) // 3 + 1

    def is_q1(self) -> bool: return self.get_quarter() == 1
    def is_q2(self) -> bool: return self.get_quarter() == 2
    def is_q3(self) -> bool: return self.get_quarter() == 3
    def is_q4(self) -> bool: return self.get_quarter() == 4

    def next_period(self) -> 'FiscalPeriodReference':
        """الحصول على الفترة التالية"""
        if self.period_number == 12:
            return FiscalPeriodReference(self.year + 1, 1)
        return FiscalPeriodReference(self.year, self.period_number + 1)

    def previous_period(self) -> 'FiscalPeriodReference':
        """الحصول على الفترة السابقة"""
        if self.period_number == 1:
            return FiscalPeriodReference(self.year - 1, 12)
        return FiscalPeriodReference(self.year, self.period_number - 1)


@dataclass(frozen=True)
class FiscalPeriodRange:
    """نطاق الفترات المالية"""
    from_period: FiscalPeriodReference
    to_period: FiscalPeriodReference

    def __post_init__(self):
        if self.from_period.year > self.to_period.year:
            raise ValueError("From period must be before to period")
        if (self.from_period.year == self.to_period.year and 
            self.from_period.period_number > self.to_period.period_number):
            raise ValueError("From period must be before to period")

    def contains(self, period: FiscalPeriodReference) -> bool:
        """التحقق من وجود فترة ضمن النطاق"""
        if period.year < self.from_period.year or period.year > self.to_period.year:
            return False
        if period.year == self.from_period.year:
            return period.period_number >= self.from_period.period_number
        if period.year == self.to_period.year:
            return period.period_number <= self.to_period.period_number
        return True

    def get_periods(self) -> list:
        """الحصول على قائمة بالفترات"""
        periods = []
        current = self.from_period
        while current.year < self.to_period.year or (
            current.year == self.to_period.year and 
            current.period_number <= self.to_period.period_number
        ):
            periods.append(current)
            current = current.next_period()
        return periods