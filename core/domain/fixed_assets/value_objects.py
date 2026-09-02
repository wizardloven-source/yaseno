# core/domain/fixed_assets/value_objects.py
"""
Fixed Assets Value Objects - كائنات القيمة للأصول الثابتة
الإصدار: 1.0.0
"""

from dataclasses import dataclass
from enum import Enum
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4


class AssetType(Enum):
    """نوع الأصل الثابت"""
    BUILDING = "building"              # مبنى
    LAND = "land"                      # أرض
    MACHINERY = "machinery"            # آلات ومعدات
    VEHICLE = "vehicle"                # مركبات
    FURNITURE = "furniture"            # أثاث
    COMPUTER = "computer"              # أجهزة كمبيوتر
    SOFTWARE = "software"              # برمجيات
    INTANGIBLE = "intangible"          # أصول غير ملموسة
    OTHER = "other"                    # أخرى


class DepreciationMethod(Enum):
    """طريقة الإهلاك"""
    STRAIGHT_LINE = "straight_line"                    # القسط الثابت
    DECLINING_BALANCE = "declining_balance"            # القسط المتناقص
    DOUBLE_DECLINING = "double_declining"              # القسط المتناقص المزدوج
    SUM_OF_YEARS = "sum_of_years"                      # مجموع أرقام السنوات
    UNITS_OF_PRODUCTION = "units_of_production"        # وحدات الإنتاج
    NONE = "none"                                      # لا إهلاك


class AssetStatus(Enum):
    """حالة الأصل"""
    ACTIVE = "active"                  # نشط
    DEPRECIATING = "depreciating"      # قيد الإهلاك
    FULLY_DEPRECIATED = "fully_depreciated"  # تم الإهلاك بالكامل
    DISPOSED = "disposed"              # تم التصرف
    SOLD = "sold"                      # تم البيع
    UNDER_MAINTENANCE = "under_maintenance"  # تحت الصيانة
    DRAFT = "draft"                    # مسودة


class DisposalMethod(Enum):
    """طريقة التصرف في الأصل"""
    SALE = "sale"                      # بيع
    SCRAP = "scrap"                    # خردة
    DONATION = "donation"              # تبرع
    TRADE_IN = "trade_in"              # مقايضة
    LOSS = "loss"                      # تلف


@dataclass(frozen=True)
class AssetId:
    """معرف الأصل الثابت"""
    value: UUID
    
    @classmethod
    def generate(cls) -> 'AssetId':
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> 'AssetId':
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class AssetCode:
    """كود الأصل"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Asset code cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class AssetCategory:
    """تصنيف الأصل"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Asset category cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DepreciationRate:
    """نسبة الإهلاك السنوية"""
    rate: Decimal
    
    def __post_init__(self):
        if self.rate < 0 or self.rate > 100:
            raise ValueError(f"Depreciation rate must be between 0 and 100: {self.rate}")
    
    def as_decimal(self) -> Decimal:
        """تحويل النسبة إلى رقم عشري"""
        return self.rate / Decimal('100')
    
    def __str__(self) -> str:
        return f"{self.rate}%"


@dataclass(frozen=True)
class DepreciationScheduleEntry:
    """
    سطر في جدول الإهلاك
    
    يمثل إهلاك فترة واحدة (شهر أو سنة)
    """
    period: int                      # رقم الفترة (1, 2, 3, ...)
    year: int                        # السنة
    month: Optional[int] = None      # الشهر (اختياري)
    start_date: date = None          # تاريخ بداية الفترة
    end_date: date = None            # تاريخ نهاية الفترة
    depreciation_amount: Decimal = Decimal('0')  # مبلغ الإهلاك
    accumulated_depreciation: Decimal = Decimal('0')  # الإهلاك المتراكم
    net_book_value: Decimal = Decimal('0')  # القيمة الدفترية الصافية
    is_posted: bool = False          # هل تم ترحيله محاسبياً؟
    posted_at: Optional[datetime] = None
    journal_entry_id: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'period': self.period,
            'year': self.year,
            'month': self.month,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'depreciation_amount': float(self.depreciation_amount),
            'accumulated_depreciation': float(self.accumulated_depreciation),
            'net_book_value': float(self.net_book_value),
            'is_posted': self.is_posted,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'journal_entry_id': self.journal_entry_id
        }


@dataclass(frozen=True)
class DisposalRecord:
    """
    سجل التصرف في الأصل
    """
    disposal_date: date
    disposal_method: DisposalMethod
    sale_amount: Optional[Decimal] = None
    scrap_value: Optional[Decimal] = None
    reason: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    journal_entry_id: Optional[str] = None
    gain_loss_amount: Optional[Decimal] = None
    gain_loss_account: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'disposal_date': self.disposal_date.isoformat(),
            'disposal_method': self.disposal_method.value,
            'sale_amount': float(self.sale_amount) if self.sale_amount else None,
            'scrap_value': float(self.scrap_value) if self.scrap_value else None,
            'reason': self.reason,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'journal_entry_id': self.journal_entry_id,
            'gain_loss_amount': float(self.gain_loss_amount) if self.gain_loss_amount else None,
            'gain_loss_account': self.gain_loss_account
        }


@dataclass(frozen=True)
class AssetDepreciationSummary:
    """
    ملخص إهلاك الأصل
    """
    asset_id: str
    asset_code: str
    asset_name: str
    acquisition_cost: Decimal
    salvage_value: Decimal
    depreciable_amount: Decimal
    total_depreciation: Decimal
    accumulated_depreciation: Decimal
    net_book_value: Decimal
    depreciation_percentage: Decimal
    useful_life_years: int
    remaining_life_years: int
    current_period_depreciation: Decimal
    next_depreciation_date: Optional[date]
    is_fully_depreciated: bool
    
    def to_dict(self) -> dict:
        return {
            'asset_id': self.asset_id,
            'asset_code': self.asset_code,
            'asset_name': self.asset_name,
            'acquisition_cost': float(self.acquisition_cost),
            'salvage_value': float(self.salvage_value),
            'depreciable_amount': float(self.depreciable_amount),
            'total_depreciation': float(self.total_depreciation),
            'accumulated_depreciation': float(self.accumulated_depreciation),
            'net_book_value': float(self.net_book_value),
            'depreciation_percentage': float(self.depreciation_percentage),
            'useful_life_years': self.useful_life_years,
            'remaining_life_years': self.remaining_life_years,
            'current_period_depreciation': float(self.current_period_depreciation),
            'next_depreciation_date': self.next_depreciation_date.isoformat() if self.next_depreciation_date else None,
            'is_fully_depreciated': self.is_fully_depreciated
        }


__all__ = [
    'AssetType',
    'DepreciationMethod',
    'AssetStatus',
    'DisposalMethod',
    'AssetId',
    'AssetCode',
    'AssetCategory',
    'DepreciationRate',
    'DepreciationScheduleEntry',
    'DisposalRecord',
    'AssetDepreciationSummary',
]