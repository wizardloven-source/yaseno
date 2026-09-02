# core/application/handlers/centers/activate_center_handler.py
"""
Activate Center Handler - معالج تفعيل مركز
"""

import logging

from core.domain.centers.services import CenterService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import ActivateCenterCommand
from core.application.centers.dtos import CenterDTO
from core.application.centers.converters import center_to_dto

logger = logging.getLogger(__name__)


class ActivateCenterHandler(BaseHandler[ActivateCenterCommand, CenterDTO]):
    """
    معالج تفعيل مركز
    
    يقوم بتفعيل مركز ليصبح نشطاً ومتاحاً للاستخدام.
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
    def handle(self, command: ActivateCenterCommand, user_context: UserContext) -> CenterDTO:
        """
        تنفيذ تفعيل المركز
        
        Args:
            command: أمر تفعيل المركز
            user_context: سياق المستخدم
        
        Returns:
            CenterDTO: بيانات المركز بعد التفعيل
        """
        logger.info(f"Activating center: {command.center_id}")

        with self._uow:
            center = self._service.activate_center(
                center_id=command.center_id,
                activated_by=user_context.user_id
            )
            self._commit()

        logger.info(f"Center activated: {center.code}")

        return center_to_dto(center)