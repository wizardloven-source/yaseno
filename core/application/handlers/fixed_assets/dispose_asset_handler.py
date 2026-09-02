# core/application/handlers/fixed_assets/dispose_asset_handler.py
"""
Dispose Fixed Asset Handler - معالج التصرف في أصل ثابت
"""

import logging

from core.domain.fixed_assets.services import FixedAssetService
from core.domain.fixed_assets.value_objects import DisposalMethod
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.fixed_assets.commands import DisposeFixedAssetCommand
from core.application.fixed_assets.dtos import FixedAssetDTO
from core.application.fixed_assets.converters import asset_to_dto

logger = logging.getLogger(__name__)


class DisposeFixedAssetHandler(BaseHandler[DisposeFixedAssetCommand, FixedAssetDTO]):
    """
    معالج التصرف في أصل ثابت
    
    يقوم بما يلي:
        1. التحقق من وجود الأصل
        2. التحقق من إمكانية التصرف
        3. إنشاء قيد محاسبي للتصرف
        4. تحديث حالة الأصل
        5. تسجيل سجل التصرف
    """
    
    def __init__(self, uow: IUnitOfWork, asset_service: FixedAssetService):
        super().__init__(uow)
        self._asset_service = asset_service
    
    @require_permission(Permission.POST_ENTRY)
    def handle(self, command: DisposeFixedAssetCommand, user_context: UserContext) -> FixedAssetDTO:
        """
        تنفيذ التصرف في الأصل
        
        Args:
            command: أمر التصرف في الأصل
            user_context: سياق المستخدم
        
        Returns:
            FixedAssetDTO: بيانات الأصل بعد التصرف
        """
        logger.info(f"Disposing asset {command.asset_id} via {command.disposal_method}")
        
        # تحويل طريقة التصرف
        try:
            disposal_method = DisposalMethod(command.disposal_method)
        except ValueError:
            raise ValueError(f"Invalid disposal method: {command.disposal_method}")
        
        # تنفيذ التصرف
        result = self._asset_service.dispose_asset(
            asset_id=command.asset_id,
            disposal_date=command.disposal_date,
            disposal_method=disposal_method,
            sale_amount=command.sale_amount,
            scrap_value=command.scrap_value,
            reason=command.reason,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
            posted_by=user_context.user_id
        )
        
        if not result.get('success', False):
            raise ValueError(f"Disposal failed: {result.get('message', 'Unknown error')}")
        
        # جلب الأصل المحدث
        asset = self._asset_service.get_asset(command.asset_id)
        
        logger.info(f"Asset disposed: {asset.code} - {command.disposal_method}")
        
        return asset_to_dto(asset)