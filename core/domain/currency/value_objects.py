from dataclasses import dataclass
from typing import Optional
import re

@dataclass(frozen=True)
class CurrencyCode:
    """Value Object لرمز العملة (مثل USD, EUR, LBP)"""
    value: str

    def __post_init__(self):
        if not self.value or len(self.value) != 3:
            raise ValueError("Currency code must be exactly 3 characters")
        if not re.match(r'^[A-Z]{3}$', self.value):
            raise ValueError(f"Invalid currency code format: {self.value}")

    def __str__(self) -> str:
        return self.value

@dataclass(frozen=True)
class ExchangeRate:
    """Value Object لسعر الصرف"""
    from_currency: CurrencyCode
    to_currency: CurrencyCode
    rate: float  # مثال: 1 USD = 13000 LBP

    def __post_init__(self):
        if self.rate <= 0:
            raise ValueError("Exchange rate must be greater than zero")
        if self.from_currency == self.to_currency:
            raise ValueError("Cannot set exchange rate for the same currency")

    def convert(self, amount: float) -> float:
        """تحويل المبلغ من عملة إلى أخرى"""
        return amount * self.rate