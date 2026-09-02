# core/application/handlers/currency/get_base_currency_query_handler.py
"""
Get Base Currency Query Handler - معالج استعلام لجلب العملة الأساسية
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.currency.commands import GetBaseCurrencyQuery
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class GetBaseCurrencyQueryHandler(BaseQueryHandler[GetBaseCurrencyQuery, CurrencyDTO]):
    """
    معالج استعلام لجلب العملة الأساسية للنظام
    
    العملة الأساسية هي العملة التي تعتمد عليها جميع العمليات المحاسبية
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetBaseCurrencyQuery) -> CurrencyDTO:
        with self._uow:
            repo = self._uow.currencies
            
            currency = repo.get_base_currency()
            if not currency:
                logger.warning("No base currency found in system")
                return None
            
            logger.debug(f"Base currency: {currency.code.value} - {currency.name}")
            
            return currency_to_dto(currency)