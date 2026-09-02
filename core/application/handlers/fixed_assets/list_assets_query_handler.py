# core/application/handlers/fixed_assets/list_assets_query_handler.py
"""
List Fixed Assets Query Handler - معالج استعلام قائمة الأصول الثابتة
"""

import logging
from typing import List

from core.domain.fixed_assets.services import FixedAssetService
from core.domain.fixed_assets.value_objects import AssetType, AssetStatus
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.fixed_assets.queries import ListFixedAssetsQuery
from core.application.fixed_assets.dtos import FixedAssetDTO
from core.application.fixed_assets.converters import assets_to_dto_list

logger = logging.getLogger(__name__)


class ListFixedAssetsQueryHandler(BaseQueryHandler[ListFixedAssetsQuery, List[FixedAssetDTO]]):
    """
    معالج استعلام قائمة الأصول الثابتة مع خيارات التصفية والترقيم
    """
    
    def __init__(self, asset_service: FixedAssetService):
        self._asset_service = asset_service
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: ListFixedAssetsQuery, user_context: UserContext = None) -> List[FixedAssetDTO]:
        """
        تنفيذ جلب قائمة الأصول
        
        Args:
            query: استعلام قائمة الأصول
        
        Returns:
            List[FixedAssetDTO]: قائمة الأصول
        """
        logger.debug(f"Listing fixed assets: type={query.asset_type}, status={query.status}")
        
        # تحويل الفلاتر
        asset_type = None
        if query.asset_type:
            try:
                asset_type = AssetType(query.asset_type)
            except ValueError:
                pass
        
        status = None
        if query.status:
            try:
                status = AssetStatus(query.status)
            except ValueError:
                pass
        
        # جلب الأصول
        assets = self._asset_service.list_assets(
            asset_type=asset_type,
            status=status,
            include_inactive=query.include_inactive,
            limit=query.limit,
            offset=query.offset
        )
        
        logger.info(f"Found {len(assets)} assets")
        
        return assets_to_dto_list(assets)