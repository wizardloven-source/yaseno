# core/application/handlers/currency/convert_currency_query_handler.py
"""
Convert Currency Query Handler - معالج استعلام تحويل العملات
"""

import logging
from typing import Optional

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.currency.services.currency_converter import CurrencyConverter

logger = logging.getLogger(__name__)


class ConvertCurrencyQueryHandler(BaseQueryHandler):
    """
    معالج استعلام تحويل العملات
    """
    
    def __init__(self, currency_converter: CurrencyConverter):
        self._currency_converter = currency_converter
    
    def handle(self, query) -> dict:
        """تنفيذ استعلام تحويل العملات"""
        result = self._currency_converter.convert_money(
            amount=query.amount,
            from_currency=query.from_currency,
            to_currency=query.to_currency
        )
        
        return result