# core/application/handlers/sites/get_default_site_query_handler.py
"""
Get Default Site Query Handler - معالج استعلام جلب الموقع الافتراضي
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.sites.commands import GetDefaultSiteQuery
from core.application.sites.dtos import SiteDTO
from core.application.sites.converters import site_to_dto

logger = logging.getLogger(__name__)


class GetDefaultSiteQueryHandler(BaseQueryHandler[GetDefaultSiteQuery, SiteDTO]):
    """
    معالج استعلام جلب الموقع الافتراضي للنظام
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetDefaultSiteQuery, user_context: UserContext = None) -> SiteDTO:
        """
        تنفيذ جلب الموقع الافتراضي
        
        Args:
            query: استعلام جلب الموقع الافتراضي
        
        Returns:
            SiteDTO: بيانات الموقع الافتراضي أو None
        """
        logger.debug("Fetching default site")

        with self._uow:
            site_repo = self._uow.sites
            site = site_repo.get_default_site()

            if not site:
                logger.warning("No default site found")
                return None

            return site_to_dto(site)