# core/application/handlers/currency/update_exchange_rates_handler.py
"""
Update Exchange Rates Handler - معالج تحديث أسعار الصرف
"""

import logging
from typing import Dict, Any

from core.domain.accounting.interfaces import IUnitOfWork
from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.currency.commands import UpdateExchangeRatesCommand
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class UpdateExchangeRatesHandler(BaseHandler[UpdateExchangeRatesCommand, Dict[str, Any]]):
    """
    معالج تحديث أسعار الصرف لجميع العملات
    
    مسؤولياته:
        1. تحديث أسعار الصرف من مصدر خارجي
        2. حفظ الأسعار الجديدة في قاعدة البيانات
        3. تسجيل التغييرات في سجل التدقيق
    """
    
    def __init__(self, uow: IUnitOfWork, exchange_rate_service):
        super().__init__(uow)
        self._exchange_rate_service = exchange_rate_service
    
    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: UpdateExchangeRatesCommand, user_context: UserContext = None) -> Dict[str, Any]:
        with self._uow:
            repo = self._uow.currencies
            
            # الحصول على جميع العملات النشطة
            currencies = repo.get_all(include_inactive=False)
            
            updated_rates = {}
            for currency in currencies:
                if currency.code.value != "USD":  # لا نحدث سعر الدولار لنفسه
                    try:
                        # الحصول على سعر الصرف من الخدمة
                        rate = self._exchange_rate_service.get_rate("USD", currency.code.value)
                        if rate:
                            currency.set_exchange_rate(currency.code.value, rate, user_context.user_id)
                            repo.save(currency)
                            updated_rates[currency.code.value] = rate
                            logger.info(f"Updated exchange rate for {currency.code.value}: {rate}")
                    except Exception as e:
                        logger.error(f"Failed to update rate for {currency.code.value}: {e}")
            
            self._commit()
            
            return {
                "success": True,
                "updated_currencies": len(updated_rates),
                "rates": updated_rates,
                "message": f"Updated {len(updated_rates)} exchange rates"
            }