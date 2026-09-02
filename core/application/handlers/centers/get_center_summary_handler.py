# core/application/handlers/centers/get_center_summary_handler.py
"""
Get Center Summary Handler - معالج استعلام ملخص مركز
"""

import logging
from typing import Dict, Any
from datetime import date

from core.domain.centers.value_objects import CenterId, CenterCode
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import GetCenterSummaryQuery
from core.application.centers.dtos import CenterSummaryDTO
from core.application.centers.converters import center_to_summary_dto

logger = logging.getLogger(__name__)


class GetCenterSummaryHandler(BaseQueryHandler[GetCenterSummaryQuery, CenterSummaryDTO]):
    """
    معالج استعلام ملخص مركز
    
    يقوم بجلب ملخص المركز بما في ذلك التوزيعات والميزانية.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetCenterSummaryQuery, user_context: UserContext = None) -> CenterSummaryDTO:
        """
        تنفيذ جلب ملخص المركز
        
        Args:
            query: استعلام ملخص المركز
        
        Returns:
            CenterSummaryDTO: ملخص المركز
        """
        logger.debug(f"Fetching summary for center: {query.center_code}")

        with self._uow:
            center_repo = self._uow.centers
            allocation_repo = self._uow.center_allocations
            
            # جلب المركز
            center = center_repo.get_by_code(CenterCode(query.center_code))
            if not center:
                logger.warning(f"Center not found: {query.center_code}")
                return None
            
            # جلب التوزيعات
            from_date = query.from_date or date(2000, 1, 1)
            to_date = query.to_date or date.today()
            
            allocations = allocation_repo.list_by_center(
                center_code=query.center_code,
                from_date=from_date,
                to_date=to_date
            )
            
            return center_to_summary_dto(center, allocations)