# core/application/handlers/funds/list_funds_query_handler.py
"""
List Funds Query Handler - معالج استعلام لجلب قائمة الصناديق
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.funds.commands import ListFundsQuery
from core.application.funds.dtos import FundDTO
from core.application.funds.converters import fund_to_dto

logger = logging.getLogger(__name__)


class ListFundsQueryHandler(BaseQueryHandler[ListFundsQuery, List[FundDTO]]):
    """
    معالج استعلام لجلب قائمة الصناديق مع فلترة وتصفح
    
    الميزات:
        1. تصفية حسب نوع الصندوق (fund_type)
        2. تصفية حسب العملة (currency)
        3. تضمين/استبعاد الصناديق غير النشطة
        4. دعم Pagination (limit, offset)
        5. ترتيب حسب الكود
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: ListFundsQuery) -> List[FundDTO]:
        with self._uow:
            repo = self._uow.funds
            
            # 1. جلب الصناديق من المستودع مع تطبيق الفلاتر
            funds = repo.list_all(
                fund_type=query.fund_type,
                include_inactive=query.include_inactive,
                limit=query.limit,
                offset=query.offset
            )
            
            # 2. تصفية إضافية حسب العملة (إذا تم تحديدها)
            if query.currency:
                funds = [f for f in funds if f.currency.upper() == query.currency.upper()]
            
            # 3. تحويل القائمة إلى DTOs
            result = [fund_to_dto(fund) for fund in funds if fund]
            
            logger.debug(f"Listed {len(result)} funds (total available: {len(funds)})")
            
            return result