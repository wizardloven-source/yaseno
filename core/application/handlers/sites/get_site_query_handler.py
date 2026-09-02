# core/application/handlers/sites/get_site_query_handler.py
"""
Get Site Query Handler - معالج استعلام لجلب موقع واحد
"""

import logging
from uuid import UUID

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.sites.commands import GetSiteQuery
from core.application.sites.dtos import SiteDTO
from core.application.sites.converters import site_to_dto

logger = logging.getLogger(__name__)


class GetSiteQueryHandler(BaseQueryHandler[GetSiteQuery, SiteDTO]):
    """
    معالج استعلام لجلب موقع واحد بواسطة المعرف
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    def handle(self, query: GetSiteQuery) -> SiteDTO:
        with self._uow:
            repo = self._uow.sites
            site = repo.get_by_id(UUID(str(query.site_id)))
            
            if not site:
                return None
            
            logger.debug(f"Retrieved site: {site.code.value} - {site.name}")
            return site_to_dto(site)