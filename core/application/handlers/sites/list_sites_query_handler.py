# core/application/handlers/sites/list_sites_query_handler.py
"""
List Sites Query Handler - معالج استعلام لجلب قائمة المواقع
"""

import logging
from typing import List

from core.domain.sites.value_objects import SiteType
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.sites.commands import ListSitesQuery
from core.application.sites.dtos import SiteDTO
from core.application.sites.converters import site_to_dto

logger = logging.getLogger(__name__)


class ListSitesQueryHandler(BaseQueryHandler[ListSitesQuery, List[SiteDTO]]):
    """
    معالج استعلام لجلب قائمة المواقع مع فلترة وتصفح
    
    الميزات:
        1. تصفية حسب نوع الموقع (site_type)
        2. تضمين/استبعاد المواقع غير النشطة
        3. دعم Pagination (limit, offset)
        4. ترتيب حسب الكود
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: ListSitesQuery) -> List[SiteDTO]:
        with self._uow:
            repo = self._uow.sites
            
            # تحويل نوع الموقع إلى Enum إذا تم تحديده
            site_type = None
            if query.site_type:
                try:
                    site_type = SiteType(query.site_type)
                except ValueError:
                    pass
            
            # جلب المواقع من المستودع
            sites = repo.list_all(
                site_type=site_type,
                include_inactive=query.include_inactive,
                limit=query.limit,
                offset=query.offset
            )
            
            logger.debug(f"Listed {len(sites)} sites")
            
            return [site_to_dto(site) for site in sites]