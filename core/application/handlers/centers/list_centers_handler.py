# core/application/handlers/centers/list_centers_handler.py
"""
List Centers Handler - معالج استعلام قائمة المراكز
"""

import logging
from typing import List

from core.domain.centers.value_objects import CenterType, CenterStatus
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import ListCentersQuery
from core.application.centers.dtos import CenterDTO
from core.application.centers.converters import centers_to_dto_list

logger = logging.getLogger(__name__)


class ListCentersHandler(BaseQueryHandler[ListCentersQuery, List[CenterDTO]]):
    """
    معالج استعلام قائمة المراكز مع خيارات التصفية والترقيم
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: ListCentersQuery, user_context: UserContext = None) -> List[CenterDTO]:
        """
        تنفيذ جلب قائمة المراكز
        
        Args:
            query: استعلام قائمة المراكز
        
        Returns:
            List[CenterDTO]: قائمة المراكز
        """
        logger.debug(f"Listing centers: type={query.center_type}, status={query.status}")

        with self._uow:
            center_repo = self._uow.centers

            # تحويل الفلاتر
            center_type = None
            if query.center_type:
                type_map = {
                    'cost': CenterType.COST,
                    'profit': CenterType.PROFIT,
                    'both': CenterType.BOTH
                }
                center_type = type_map.get(query.center_type)

            status = None
            if query.status:
                status_map = {
                    'draft': CenterStatus.DRAFT,
                    'active': CenterStatus.ACTIVE,
                    'suspended': CenterStatus.SUSPENDED,
                    'closed': CenterStatus.CLOSED,
                    'archived': CenterStatus.ARCHIVED
                }
                status = status_map.get(query.status)

            centers = center_repo.list_all(
                center_type=center_type,
                status=status,
                parent_code=query.parent_code,
                include_inactive=query.include_inactive,
                limit=query.limit,
                offset=query.offset
            )

            logger.info(f"Found {len(centers)} centers")

            return centers_to_dto_list(centers)