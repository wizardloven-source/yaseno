# core/application/handlers/centers/close_center_handler.py
"""
Close Center Handler - معالج إغلاق مركز
"""

import logging

from core.domain.centers.services import CenterService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import CloseCenterCommand
from core.application.centers.dtos import CenterDTO
from core.application.centers.converters import center_to_dto

logger = logging.getLogger(__name__)


class CloseCenterHandler(BaseHandler[CloseCenterCommand, CenterDTO]):
    """
    معالج إغلاق مركز
    
    يقوم بإغلاق مركز نهائياً (لا يمكن إعادة فتحه).
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        """بناء الخدمة دائماً بجلسة جديدة (بدون تخزين مؤقت)"""
        return CenterService(
            center_repo=self._uow.centers,
            allocation_repo=self._uow.center_allocations,
            rule_repo=self._uow.center_allocation_rules
        )

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: CloseCenterCommand, user_context: UserContext) -> CenterDTO:
        """
        تنفيذ إغلاق المركز
        
        Args:
            command: أمر إغلاق المركز
            user_context: سياق المستخدم
        
        Returns:
            CenterDTO: بيانات المركز بعد الإغلاق
        """
        logger.info(f"Closing center: {command.center_id}")

        # ✅ استخدام with self._uow ثم الحصول على الخدمة داخل السياق
        with self._uow:
            # ✅ الحصول على الخدمة (سيتم إنشاؤها الآن داخل السياق)
            service = self._get_service()
            
            center = service.close_center(
                center_id=command.center_id,
                closed_by=user_context.user_id,
                reason=command.reason
            )
            self._commit()

        logger.info(f"Center closed: {center.code}")

        return center_to_dto(center)