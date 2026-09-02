# core/application/handlers/funds/get_fund_by_code_query_handler.py
"""
Get Fund By Code Query Handler - معالج استعلام لجلب صندوق بواسطة الكود
"""

import logging

from core.domain.funds.value_objects import FundCode
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.funds.commands import GetFundByCodeQuery
from core.application.funds.dtos import FundDTO
from core.application.funds.converters import fund_to_dto

logger = logging.getLogger(__name__)


class GetFundByCodeQueryHandler(BaseQueryHandler[GetFundByCodeQuery, FundDTO]):
    """
    معالج استعلام لجلب صندوق واحد بواسطة الكود
    
    مسؤولياته:
        1. البحث عن الصندوق في المستودع باستخدام الكود
        2. تحويل الكيان إلى DTO
        3. إرجاع None إذا لم يتم العثور على الصندوق
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetFundByCodeQuery) -> FundDTO:
        with self._uow:
            repo = self._uow.funds
            
            fund = repo.get_by_code(FundCode(query.code))
            if not fund:
                logger.debug(f"Fund not found by code: {query.code}")
                return None
            
            logger.debug(f"Retrieved fund by code: {fund.code.value} - {fund.name}")
            return fund_to_dto(fund)