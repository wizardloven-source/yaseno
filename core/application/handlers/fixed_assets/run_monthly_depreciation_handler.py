# core/application/handlers/fixed_assets/run_monthly_depreciation_handler.py
"""
Run Monthly Depreciation Handler - معالج تشغيل الإهلاك الشهري
"""

import logging
from typing import List

from core.domain.fixed_assets.services import FixedAssetService, DepreciationResult
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.fixed_assets.commands import RunMonthlyDepreciationCommand

logger = logging.getLogger(__name__)


class RunMonthlyDepreciationHandler(BaseHandler[RunMonthlyDepreciationCommand, List[dict]]):
    """
    معالج تشغيل الإهلاك الشهري لجميع الأصول
    
    يقوم بما يلي:
        1. جلب جميع الأصول النشطة
        2. حساب الإهلاك لكل أصل
        3. إنشاء القيود المحاسبية
        4. ترحيل القيود
        5. تحديث جداول الإهلاك
        6. إرجاع تقرير النتائج
    """
    
    def __init__(self, uow: IUnitOfWork, asset_service: FixedAssetService):
        super().__init__(uow)
        self._asset_service = asset_service
    
    @require_permission(Permission.POST_ENTRY)
    def handle(self, command: RunMonthlyDepreciationCommand, user_context: UserContext) -> List[dict]:
        """
        تنفيذ الإهلاك الشهري
        
        Args:
            command: أمر تشغيل الإهلاك الشهري
            user_context: سياق المستخدم
        
        Returns:
            List[dict]: قائمة بنتائج الإهلاك
        """
        logger.info(f"Running monthly depreciation as of {command.as_of_date or 'today'}")
        
        # تشغيل الإهلاك الشهري
        results = self._asset_service.run_monthly_depreciation(
            as_of_date=command.as_of_date,
            posted_by=user_context.user_id
        )
        
        # تحويل النتائج إلى قواميس
        output = []
        for result in results:
            if isinstance(result, DepreciationResult):
                output.append({
                    'success': result.success,
                    'asset_id': result.asset_id,
                    'asset_code': result.asset_code,
                    'period': result.period,
                    'depreciation_amount': float(result.depreciation_amount),
                    'journal_entry_id': result.journal_entry_id,
                    'message': result.message,
                    'errors': result.errors
                })
            else:
                output.append(result)
        
        success_count = len([r for r in output if r.get('success', False)])
        logger.info(f"Monthly depreciation completed: {success_count} entries posted successfully")
        
        return output