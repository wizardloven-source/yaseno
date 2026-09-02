# core/application/handlers/sites/search_sites_query_handler.py
"""
Search Sites Query Handler - معالج استعلام البحث عن المواقع
"""

import logging
from typing import List

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.sites.commands import SearchSitesQuery
from core.application.sites.dtos import SiteDTO
from core.application.sites.converters import site_to_dto

logger = logging.getLogger(__name__)


class SearchSitesQueryHandler(BaseQueryHandler[SearchSitesQuery, List[SiteDTO]]):
    """
    معالج استعلام البحث عن المواقع
    
    يقوم بالبحث عن المواقع باستخدام النص المدخل في الكود أو الاسم أو المدينة.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: SearchSitesQuery, user_context: UserContext = None) -> List[SiteDTO]:
        """
        تنفيذ البحث عن المواقع
        
        Args:
            query: استعلام البحث عن المواقع
        
        Returns:
            List[SiteDTO]: قائمة المواقع المطابقة للبحث
        """
        logger.debug(f"Searching sites with text: {query.search_text}")

        with self._uow:
            site_repo = self._uow.sites
            
            # البحث عن المواقع
            sites = site_repo.search(
                search_text=query.search_text,
                limit=query.limit,
                offset=query.offset
            )

            logger.info(f"Found {len(sites)} sites matching '{query.search_text}'")

            return [site_to_dto(site) for site in sites]