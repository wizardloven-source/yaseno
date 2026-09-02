# core/application/handlers/sites/get_sites_for_combo_query_handler.py
"""
Get Sites For Combo Query Handler - معالج استعلام جلب المواقع للقوائم المنسدلة
"""

import logging
from typing import List, Dict, Any

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.sites.commands import GetSitesForComboQuery

logger = logging.getLogger(__name__)


class GetSitesForComboQueryHandler(BaseQueryHandler[GetSitesForComboQuery, List[Dict[str, Any]]]):
    """
    معالج استعلام جلب المواقع للقوائم المنسدلة
    
    يقوم بجلب المواقع بتنسيق مناسب للقوائم المنسدلة (Combo Boxes).
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetSitesForComboQuery, user_context: UserContext = None) -> List[Dict[str, Any]]:
        """
        تنفيذ جلب المواقع للقوائم المنسدلة
        
        Args:
            query: استعلام جلب المواقع للقوائم المنسدلة
        
        Returns:
            List[Dict[str, Any]]: قائمة المواقع بتنسيق مناسب
        """
        logger.debug("Fetching sites for combo boxes")

        with self._uow:
            site_repo = self._uow.sites
            
            # جلب المواقع النشطة
            sites = site_repo.list_all(
                include_inactive=query.include_inactive or False,
                limit=query.limit or 1000
            )

            return [
                {
                    "id": str(site.id),
                    "code": site.code.value,
                    "name": site.name,
                    "display_name": f"{site.code} - {site.name}",
                    "city": site.city,
                    "country": site.country,
                    "is_default": site.is_default,
                    "is_active": site.is_active
                }
                for site in sites
            ]