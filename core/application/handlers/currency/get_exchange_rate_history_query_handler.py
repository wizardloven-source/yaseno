# core/application/handlers/currency/get_exchange_rate_history_query_handler.py
"""
Get Exchange Rate History Query Handler - معالج استعلام تاريخ أسعار الصرف
"""

import logging
from typing import List

from core.domain.currency.interfaces import ICurrencyRepository

from core.application.handlers.base_handler import BaseQueryHandler

logger = logging.getLogger(__name__)


class GetExchangeRateHistoryQueryHandler(BaseQueryHandler):
    """
    معالج استعلام تاريخ أسعار الصرف
    """
    
    def __init__(self, currency_repo: ICurrencyRepository):
        self._currency_repo = currency_repo
    
    def handle(self, query) -> List[dict]:
        """تنفيذ استعلام تاريخ أسعار الصرف"""
        # TODO: تنفيذ جلب تاريخ أسعار الصرف
        return []