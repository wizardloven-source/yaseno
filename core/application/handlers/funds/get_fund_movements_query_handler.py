# core/application/handlers/funds/get_fund_movements_query_handler.py
"""
Get Fund Movements Query Handler - معالج استعلام لجلب حركات الصندوق
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.funds.commands import GetFundMovementsQuery
from core.application.funds.dtos import FundMovementDTO
from core.application.funds.converters import movement_to_dto

logger = logging.getLogger(__name__)


class GetFundMovementsQueryHandler(BaseQueryHandler[GetFundMovementsQuery, List[FundMovementDTO]]):
    """
    معالج استعلام لجلب حركات الصندوق مع فلترة وتصفح
    
    الميزات:
        1. تصفية حسب نطاق التاريخ (from_date, to_date)
        2. تصفية حسب نوع الحركة (deposit, withdraw, transfer_from, transfer_to)
        3. دعم Pagination (limit, offset)
        4. ترتيب تنازلي حسب تاريخ الإنشاء
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetFundMovementsQuery) -> List[FundMovementDTO]:
        with self._uow:
            repo = self._uow.fund_movements
            
            # 1. جلب الحركات من المستودع مع تطبيق الفلاتر
            movements = repo.get_by_date_range(
                fund_id=query.fund_id,
                from_date=query.from_date,
                to_date=query.to_date,
                movement_type=query.movement_type,
                limit=query.limit,
                offset=query.offset
            )
            
            # 2. تحويل القائمة إلى DTOs
            result = [movement_to_dto(movement) for movement in movements if movement]
            
            logger.debug(f"Listed {len(result)} movements for fund {query.fund_id}")
            
            return result