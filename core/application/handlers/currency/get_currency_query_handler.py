# core/application/handlers/currency/get_currency_query_handler.py
"""
Get Currency Query Handler - معالج استعلام جلب عملة بواسطة المعرف
"""

import logging
from uuid import UUID

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.currency.commands import GetCurrencyQuery
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class GetCurrencyQueryHandler(BaseQueryHandler[GetCurrencyQuery, CurrencyDTO]):
    """
    معالج استعلام لجلب عملة واحدة بواسطة المعرف
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetCurrencyQuery) -> CurrencyDTO:
        with self._uow:
            repo = self._uow.currencies
            
            currency = repo.get_by_id(query.currency_id)
            if not currency:
                return None
            
            logger.debug(f"Retrieved currency: {currency.code.value} - {currency.name}")
            
            return currency_to_dto(currency)