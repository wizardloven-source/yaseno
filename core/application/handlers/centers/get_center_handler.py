# core/application/handlers/centers/get_center_handler.py
"""
Get Center Handler - معالج استعلام جلب مركز
"""

import logging

from core.domain.centers.value_objects import CenterId
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import GetCenterQuery
from core.application.centers.dtos import CenterDTO
from core.application.centers.converters import center_to_dto

logger = logging.getLogger(__name__)


class GetCenterHandler(BaseQueryHandler[GetCenterQuery, CenterDTO]):
    """
    معالج استعلام جلب مركز بواسطة المعرف
    """

    def __init__(self, uow: IUnitOfWork):
        # ✅ BaseQueryHandler يتوقع uow في المُنشئ
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetCenterQuery, user_context: UserContext = None) -> CenterDTO:
        """
        تنفيذ جلب المركز
        
        Args:
            query: استعلام جلب المركز
        
        Returns:
            CenterDTO: بيانات المركز أو None
        """
        logger.debug(f"Fetching center: {query.center_id}")

        # ✅ استخدام with self._uow (BaseQueryHandler يوفر self._uow)
        with self._uow:
            center_repo = self._uow.centers
            center = center_repo.get_by_id(CenterId(query.center_id))

            if not center:
                logger.warning(f"Center not found: {query.center_id}")
                return None

            return center_to_dto(center)