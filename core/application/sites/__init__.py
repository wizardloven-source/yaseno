# core/application/sites/__init__.py
"""
Sites Application Layer - Commands, Queries, DTOs
"""

from .commands import (
    # Commands
    CreateSiteCommand,
    UpdateSiteCommand,
    DeleteSiteCommand,
    SetDefaultSiteCommand,  # ✅ جديد
    
    # Queries
    GetSiteQuery,
    GetSiteByCodeQuery,  # ✅ جديد
    ListSitesQuery,
    GetDefaultSiteQuery,  # ✅ جديد
    GetSiteStatisticsQuery,  # ✅ جديد
    SearchSitesQuery,  # ✅ جديد
    GetSitesForComboQuery,  # ✅ جديد
)
from .dtos import SiteDTO
from .converters import site_to_dto, dto_to_site  # ✅ إضافة dto_to_site

__all__ = [
    # Commands
    "CreateSiteCommand",
    "UpdateSiteCommand",
    "DeleteSiteCommand",
    "SetDefaultSiteCommand",  # ✅ جديد
    
    # Queries
    "GetSiteQuery",
    "GetSiteByCodeQuery",  # ✅ جديد
    "ListSitesQuery",
    "GetDefaultSiteQuery",  # ✅ جديد
    "GetSiteStatisticsQuery",  # ✅ جديد
    "SearchSitesQuery",  # ✅ جديد
    "GetSitesForComboQuery",  # ✅ جديد
    
    # DTOs
    "SiteDTO",
    
    # Converters
    "site_to_dto",
    "dto_to_site",  # ✅ إضافة
]