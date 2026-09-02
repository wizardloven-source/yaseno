from dataclasses import dataclass
from typing import Optional, List
from uuid import UUID
from datetime import datetime

@dataclass(frozen=True)
class ExchangeRateDTO:
    """سعر الصرف - DTO"""
    from_currency: str
    to_currency: str
    rate: float


@dataclass(frozen=True)
class CurrencyDTO:
    """
    العملة - DTO كامل
    ✅ محدث: يدعم created_by و updated_by
    """
    id: UUID
    code: str
    name: str
    symbol: str
    decimal_places: int
    is_active: bool
    is_base: bool
    exchange_rates: List[ExchangeRateDTO]
    created_at: datetime
    created_by: str          # ✅ أضف هذا الحقل
    updated_at: datetime
    updated_by: str          # ✅ أضف هذا الحقل
    version: int
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض للعملة"""
        return f"{self.code} - {self.name}"
    
    @property
    def symbol_display(self) -> str:
        """رمز العملة مع السعر"""
        return self.symbol if self.symbol else self.code