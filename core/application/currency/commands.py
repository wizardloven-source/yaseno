# core/application/currency/commands.py
"""
Commands and Queries for Currency Module
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID


# ========== COMMANDS (أوامر - عمليات الكتابة) ==========

@dataclass(frozen=True)
class CreateCurrencyCommand:
    """أمر إنشاء عملة جديدة"""
    code: str
    name: str
    symbol: str = ""
    decimal_places: int = 2
    is_base: bool = False
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateCurrencyCommand:
    """أمر تحديث عملة موجودة"""
    currency_id: UUID
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimal_places: Optional[int] = None
    is_active: Optional[bool] = None
    is_base: Optional[bool] = None
    updated_by: str = "system"
    version: int = 1


@dataclass(frozen=True)
class SetExchangeRateCommand:
    """أمر تعيين سعر الصرف"""
    from_currency_id: UUID
    to_currency_code: str
    rate: float
    updated_by: str = "system"


@dataclass(frozen=True)
class DeleteCurrencyCommand:
    """أمر حذف عملة"""
    currency_id: UUID
    deleted_by: str = "system"


@dataclass(frozen=True)
class SetBaseCurrencyCommand:
    """أمر تعيين العملة الأساسية للنظام"""
    currency_id: UUID
    set_by: str = "system"


# ✅ إضافة الأوامر المفقودة
@dataclass(frozen=True)
class UpdateExchangeRatesCommand:
    """أمر تحديث أسعار الصرف"""
    source: str = "api"  # api, manual, bank
    updated_by: str = "system"


@dataclass(frozen=True)
class FetchExchangeRatesCommand:
    """أمر جلب أسعار الصرف من الإنترنت"""
    provider: str = "default"  # default, exchangerate-api, etc.
    fetched_by: str = "system"


# ========== QUERIES (استعلامات - عمليات القراءة) ==========

@dataclass(frozen=True)
class GetCurrencyQuery:
    """استعلام لجلب عملة بواسطة المعرف"""
    currency_id: UUID


@dataclass(frozen=True)
class GetCurrencyByCodeQuery:
    """استعلام لجلب عملة بواسطة الكود"""
    code: str


@dataclass(frozen=True)
class ListCurrenciesQuery:
    """استعلام لجلب قائمة العملات"""
    include_inactive: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetBaseCurrencyQuery:
    """✅ استعلام لجلب العملة الأساسية للنظام"""
    pass


@dataclass(frozen=True)
class GetExchangeRateQuery:
    """استعلام لجلب سعر الصرف بين عملتين"""
    from_currency_code: str
    to_currency_code: str


__all__ = [
    # Commands
    "CreateCurrencyCommand",
    "UpdateCurrencyCommand",
    "SetExchangeRateCommand",
    "DeleteCurrencyCommand",
    "SetBaseCurrencyCommand",
    "UpdateExchangeRatesCommand",  # ✅ إضافة
    "FetchExchangeRatesCommand",   # ✅ إضافة
    
    # Queries
    "GetCurrencyQuery",
    "GetCurrencyByCodeQuery",
    "ListCurrenciesQuery",
    "GetBaseCurrencyQuery",
    "GetExchangeRateQuery",
]