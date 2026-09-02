# core/application/handlers/currency/fetch_exchange_rates_handler.py
"""
Fetch Exchange Rates Handler - معالج جلب أسعار الصرف من الإنترنت
"""

import logging
from typing import Dict, Any

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.currency.commands import FetchExchangeRatesCommand

logger = logging.getLogger(__name__)


class FetchExchangeRatesHandler(BaseHandler[FetchExchangeRatesCommand, Dict[str, Any]]):
    """
    معالج جلب أسعار الصرف من الإنترنت
    
    مسؤولياته:
        1. جلب أسعار الصرف من API خارجي
        2. تحديث قاعدة البيانات بالأسعار الجديدة
        3. تسجيل التغييرات
    """
    
    def __init__(self, uow: IUnitOfWork, exchange_rate_service):
        super().__init__(uow)
        self._exchange_rate_service = exchange_rate_service
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: FetchExchangeRatesCommand, user_context: UserContext = None) -> Dict[str, Any]:
        with self._uow:
            repo = self._uow.currencies
            
            # جلب الأسعار من الخدمة
            rates = self._exchange_rate_service.fetch_latest_rates()
            
            if not rates:
                return {
                    "success": False,
                    "message": "Failed to fetch exchange rates",
                    "rates": {}
                }
            
            updated_rates = {}
            for currency_code, rate in rates.items():
                currency = repo.get_by_code(currency_code)
                if currency:
                    currency.set_exchange_rate("USD", rate, user_context.user_id)
                    repo.save(currency)
                    updated_rates[currency_code] = rate
                    logger.info(f"Fetched rate for {currency_code}: {rate}")
            
            self._commit()
            
            return {
                "success": True,
                "fetched_currencies": len(updated_rates),
                "rates": updated_rates,
                "message": f"Fetched {len(updated_rates)} exchange rates from API"
            }