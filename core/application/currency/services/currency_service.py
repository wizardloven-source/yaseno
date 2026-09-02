# core/application/currency/services/currency_service.py
"""
Currency Service - خدمة العملات الأساسية
"""

import logging
from typing import Optional, List  # ✅ إضافة List
from uuid import UUID

from core.domain.currency.entities import Currency
from core.domain.currency.value_objects import CurrencyCode
from core.domain.currency.interfaces import ICurrencyRepository

logger = logging.getLogger(__name__)


class CurrencyService:
    """
    خدمة العملات - إدارة العملات في النظام
    """
    
    def __init__(self, currency_repo: ICurrencyRepository, uow):
        self._currency_repo = currency_repo
        self._uow = uow
    
    def get_currency(self, currency_id: UUID) -> Optional[Currency]:
        """الحصول على عملة بواسطة المعرف"""
        return self._currency_repo.get_by_id(currency_id)
    
    def get_currency_by_code(self, code: str) -> Optional[Currency]:
        """الحصول على عملة بواسطة الكود"""
        return self._currency_repo.get_by_code(CurrencyCode(code))
    
    def get_all_currencies(self, include_inactive: bool = False) -> List[Currency]:
        """الحصول على جميع العملات"""
        return self._currency_repo.get_all(include_inactive=include_inactive)
    
    def get_active_currencies(self) -> List[Currency]:
        """الحصول على العملات النشطة فقط"""
        return self._currency_repo.get_active_currencies()
    
    def get_base_currency(self) -> Optional[Currency]:
        """الحصول على العملة الأساسية"""
        return self._currency_repo.get_base_currency()
    
    def create_currency(self, code: str, name: str, symbol: str = "", decimal_places: int = 2, is_base: bool = False, created_by: str = "system") -> Currency:
        """إنشاء عملة جديدة"""
        currency = Currency.create(
            code=code,
            name=name,
            symbol=symbol,
            decimal_places=decimal_places,
            is_base=is_base,
            created_by=created_by
        )
        self._currency_repo.save(currency)
        return currency
    
    def delete_currency(self, currency_id: UUID) -> bool:
        """حذف عملة"""
        return self._currency_repo.delete(currency_id)