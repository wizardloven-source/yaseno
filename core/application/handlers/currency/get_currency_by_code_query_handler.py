# core/application/handlers/currency/get_currency_by_code_query_handler.py
"""
Get Currency By Code Query Handler - معالج استعلام جلب عملة بواسطة الكود
"""

import logging

from core.domain.currency.value_objects import CurrencyCode
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.currency.commands import GetCurrencyByCodeQuery
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class GetCurrencyByCodeQueryHandler(BaseQueryHandler[GetCurrencyByCodeQuery, CurrencyDTO]):
    """
    معالج استعلام لجلب عملة واحدة بواسطة الكود (مثل USD, EUR, LBP)
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetCurrencyByCodeQuery) -> CurrencyDTO:
        with self._uow:
            repo = self._uow.currencies
            
            currency = repo.get_by_code(CurrencyCode(query.code.upper()))
            if not currency:
                return None
            
            logger.debug(f"Retrieved currency by code: {currency.code.value} - {currency.name}")
            
            return currency_to_dto(currency)