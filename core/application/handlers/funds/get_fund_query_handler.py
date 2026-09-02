# core/application/handlers/funds/get_fund_query_handler.py

"""
Get Fund Query Handler - معالج استعلام لجلب صندوق بواسطة المعرف
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.funds.value_objects import FundId

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.funds.commands import GetFundQuery
from core.application.funds.dtos import FundDTO
from core.application.funds.converters import fund_to_dto

logger = logging.getLogger(__name__)


class GetFundQueryHandler(BaseQueryHandler[GetFundQuery, FundDTO]):
    """
    معالج استعلام لجلب صندوق واحد بواسطة المعرف
    
    مسؤولياته:
        1. البحث عن الصندوق في المستودع
        2. تحويل الكيان إلى DTO
        3. إرجاع None إذا لم يتم العثور على الصندوق
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetFundQuery) -> FundDTO:
        with self._uow:
            repo = self._uow.funds
            
            # ✅ أصبح الأمر أبسط بكثير، query.fund_id من النوع FundId
            fund_id = query.fund_id
            
            # التحقق من صحة النوع
            if not isinstance(fund_id, FundId):
                logger.error(f"Invalid fund_id type in query: {type(fund_id)}")
                return None
            
            fund = repo.get_by_id(fund_id)
            if not fund:
                logger.debug(f"Fund not found: {fund_id}")
                return None
            
            logger.debug(f"Retrieved fund: {fund.code.value} - {fund.name}")
            return fund_to_dto(fund)