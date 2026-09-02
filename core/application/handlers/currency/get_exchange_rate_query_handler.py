# core/application/handlers/currency/get_exchange_rate_query_handler.py
"""
Get Exchange Rate Query Handler - معالج استعلام لجلب سعر الصرف
"""

import logging
from typing import Optional

from core.domain.currency.value_objects import CurrencyCode
from core.domain.currency.interfaces import ICurrencyRepository

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.currency.commands import GetExchangeRateQuery
from core.application.currency.dtos import ExchangeRateDTO

logger = logging.getLogger(__name__)


class GetExchangeRateQueryHandler(BaseQueryHandler[GetExchangeRateQuery, Optional[ExchangeRateDTO]]):
    """
    معالج استعلام لجلب سعر الصرف بين عملتين
    """
    
    def __init__(self, currency_repo: ICurrencyRepository):
        self._currency_repo = currency_repo
    
    def handle(self, query: GetExchangeRateQuery) -> Optional[ExchangeRateDTO]:
        """تنفيذ استعلام جلب سعر الصرف"""
        from_currency_code = CurrencyCode(query.from_currency_code.upper())
        to_currency_code = CurrencyCode(query.to_currency_code.upper())
        
        # الحصول على العملة المصدر
        currency = self._currency_repo.get_by_code(from_currency_code)
        if not currency:
            return None
        
        # الحصول على سعر الصرف
        rate = currency.get_exchange_rate(to_currency_code.value)
        if rate is None:
            return None
        
        return ExchangeRateDTO(
            from_currency=from_currency_code.value,
            to_currency=to_currency_code.value,
            rate=rate
        )