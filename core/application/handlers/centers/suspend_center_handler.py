# core/application/handlers/centers/suspend_center_handler.py
"""
Suspend Center Handler - معالج تعليق مركز
"""

import logging

from core.domain.centers.services import CenterService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import SuspendCenterCommand
from core.application.centers.dtos import CenterDTO
from core.application.centers.converters import center_to_dto

logger = logging.getLogger(__name__)


class SuspendCenterHandler(BaseHandler[SuspendCenterCommand, CenterDTO]):
    """
    معالج تعليق مركز
    
    يقوم بتعليق مركز مؤقتاً (لا يمكن استخدامه).
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @property
    def _service(self):
        return CenterService(
            center_repo=self._uow.centers,
            allocation_repo=self._uow.center_allocations,
            rule_repo=self._uow.center_allocation_rules
        )

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: SuspendCenterCommand, user_context: UserContext) -> CenterDTO:
        """
        تنفيذ تعليق المركز
        
        Args:
            command: أمر تعليق المركز
            user_context: سياق المستخدم
        
        Returns:
            CenterDTO: بيانات المركز بعد التعليق
        """
        logger.info(f"Suspending center: {command.center_id}")

        with self._uow:
            center = self._service.suspend_center(
                center_id=command.center_id,
                suspended_by=user_context.user_id,
                reason=command.reason
            )
            self._commit()

        logger.info(f"Center suspended: {center.code}")

        return center_to_dto(center)