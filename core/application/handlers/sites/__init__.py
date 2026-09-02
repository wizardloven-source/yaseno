# core/application/handlers/sites/__init__.py
"""
Sites Handlers - معالجات أوامر واستعلامات المواقع
"""

from .create_site_handler import CreateSiteHandler
from .update_site_handler import UpdateSiteHandler
from .delete_site_handler import DeleteSiteHandler
from .set_default_site_handler import SetDefaultSiteHandler  # ✅ إضافة
from .get_site_query_handler import GetSiteQueryHandler
from .list_sites_query_handler import ListSitesQueryHandler
from .get_default_site_query_handler import GetDefaultSiteQueryHandler  # ✅ إضافة
from .get_site_statistics_query_handler import GetSiteStatisticsQueryHandler  # ✅ إضافة
from .search_sites_query_handler import SearchSitesQueryHandler  # ✅ إضافة
from .get_sites_for_combo_query_handler import GetSitesForComboQueryHandler  # ✅ إضافة

__all__ = [
    "CreateSiteHandler",
    "UpdateSiteHandler",
    "DeleteSiteHandler",
    "SetDefaultSiteHandler",  # ✅ إضافة
    "GetSiteQueryHandler",
    "ListSitesQueryHandler",
    "GetDefaultSiteQueryHandler",  # ✅ إضافة
    "GetSiteStatisticsQueryHandler",  # ✅ إضافة
    "SearchSitesQueryHandler",  # ✅ إضافة
    "GetSitesForComboQueryHandler",  # ✅ إضافة
]