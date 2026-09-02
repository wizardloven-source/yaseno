# core/application/handlers/fixed_assets/post_depreciation_handler.py
"""
Post Depreciation Handler - معالج ترحيل إهلاك أصل ثابت
"""

import logging

from core.domain.fixed_assets.services import FixedAssetService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.fixed_assets.commands import PostDepreciationCommand
from core.application.fixed_assets.dtos import DepreciationScheduleDTO
from core.application.fixed_assets.converters import schedule_to_dto

logger = logging.getLogger(__name__)


class PostDepreciationHandler(BaseHandler[PostDepreciationCommand, DepreciationScheduleDTO]):
    """
    معالج ترحيل إهلاك فترة محددة لأصل ثابت
    
    يقوم بما يلي:
        1. التحقق من وجود الأصل
        2. التحقق من صحة رقم الفترة
        3. حساب إهلاك الفترة
        4. إنشاء قيد محاسبي للإهلاك
        5. ترحيل القيد
        6. تحديث جدول الإهلاك
        7. تحديث حالة الأصل إذا اكتمل الإهلاك
    """
    
    def __init__(self, uow: IUnitOfWork, asset_service: FixedAssetService):
        super().__init__(uow)
        self._asset_service = asset_service
    
    @require_permission(Permission.POST_ENTRY)
    def handle(self, command: PostDepreciationCommand, user_context: UserContext) -> DepreciationScheduleDTO:
        """
        تنفيذ ترحيل إهلاك الفترة
        
        Args:
            command: أمر ترحيل الإهلاك
            user_context: سياق المستخدم
        
        Returns:
            DepreciationScheduleDTO: جدول الإهلاك المحدث
        """
        logger.info(f"Posting depreciation for asset {command.asset_id}, period {command.period}")
        
        # ترحيل الإهلاك
        result = self._asset_service.post_depreciation(
            asset_id=command.asset_id,
            period=command.period,
            posted_by=user_context.user_id
        )
        
        if not result.success:
            raise ValueError(f"Depreciation posting failed: {result.message}")
        
        # جلب الأصل المحدث
        asset = self._asset_service.get_asset(command.asset_id)
        
        logger.info(f"Depreciation posted: {result.asset_code} - Period {result.period}, Amount: {result.depreciation_amount}")
        
        return schedule_to_dto(asset)