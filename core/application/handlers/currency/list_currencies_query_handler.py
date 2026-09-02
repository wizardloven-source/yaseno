# core/application/handlers/currency/list_currencies_query_handler.py
"""
List Currencies Query Handler - معالج استعلام لجلب قائمة العملات
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.currency.commands import ListCurrenciesQuery
from core.application.currency.dtos import CurrencyDTO
from core.application.currency.converters import currency_to_dto

logger = logging.getLogger(__name__)


class ListCurrenciesQueryHandler(BaseQueryHandler[ListCurrenciesQuery, List[CurrencyDTO]]):
    """
    معالج استعلام لجلب قائمة العملات مع فلترة التصفح
    
    الميزات:
        1. تصفية حسب الحالة (نشط/غير نشط)
        2. دعم Pagination (limit, offset)
        3. ترتيب حسب كود العملة
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: ListCurrenciesQuery) -> List[CurrencyDTO]:
        with self._uow:
            repo = self._uow.currencies
            
            # جلب العملات من المستودع
            currencies = repo.get_all(include_inactive=query.include_inactive)
            
            # تطبيق Pagination
            total_count = len(currencies)
            start = query.offset
            end = query.offset + query.limit
            
            paginated_currencies = currencies[start:end]
            
            logger.debug(f"Listed {len(paginated_currencies)} currencies (total: {total_count})")
            
            return [currency_to_dto(currency) for currency in paginated_currencies]