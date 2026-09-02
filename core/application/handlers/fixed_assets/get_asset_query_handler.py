# core/application/handlers/fixed_assets/get_asset_query_handler.py
"""
Get Fixed Asset Query Handler - معالج استعلام جلب أصل ثابت
"""

import logging

from core.domain.fixed_assets.services import FixedAssetService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.fixed_assets.queries import GetFixedAssetQuery
from core.application.fixed_assets.dtos import FixedAssetDTO
from core.application.fixed_assets.converters import asset_to_dto

logger = logging.getLogger(__name__)


class GetFixedAssetQueryHandler(BaseQueryHandler[GetFixedAssetQuery, FixedAssetDTO]):
    """
    معالج استعلام جلب أصل ثابت بواسطة المعرف
    """
    
    def __init__(self, asset_service: FixedAssetService):
        self._asset_service = asset_service
    
    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetFixedAssetQuery, user_context: UserContext = None) -> FixedAssetDTO:
        """
        تنفيذ جلب الأصل
        
        Args:
            query: استعلام جلب الأصل
        
        Returns:
            FixedAssetDTO: بيانات الأصل أو None
        """
        logger.debug(f"Fetching fixed asset: {query.asset_id}")
        
        asset = self._asset_service.get_asset(query.asset_id)
        
        if not asset:
            logger.warning(f"Fixed asset not found: {query.asset_id}")
            return None
        
        return asset_to_dto(asset)