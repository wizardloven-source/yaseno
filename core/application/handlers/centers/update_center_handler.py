# core/application/handlers/centers/update_center_handler.py
"""
Update Center Handler - معالج تحديث مركز
"""

import logging

from core.domain.centers.services import CenterService
from core.domain.centers.value_objects import CenterType, CenterBudget
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import UpdateCenterCommand
from core.application.centers.dtos import CenterDTO
from core.application.centers.converters import center_to_dto

logger = logging.getLogger(__name__)


class UpdateCenterHandler(BaseHandler[UpdateCenterCommand, CenterDTO]):
    """
    معالج تحديث مركز
    
    يقوم بتحديث بيانات المركز مع:
    - التحقق من الإصدار (Optimistic Locking)
    - تحديث الميزانية إذا تغيرت
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
    def handle(self, command: UpdateCenterCommand, user_context: UserContext) -> CenterDTO:
        """
        تنفيذ تحديث المركز
        
        Args:
            command: أمر تحديث المركز
            user_context: سياق المستخدم
        
        Returns:
            CenterDTO: بيانات المركز المحدث
        """
        logger.info(f"Updating center: {command.center_id}")

        # تحويل نوع المركز
        center_type = None
        if command.center_type:
            center_type_map = {
                'cost': CenterType.COST,
                'profit': CenterType.PROFIT,
                'both': CenterType.BOTH
            }
            center_type = center_type_map.get(command.center_type)

        # إنشاء الميزانية إذا تم تحديدها
        budget = None
        if command.budget_amount is not None:
            budget = CenterBudget(
                total_budget=command.budget_amount,
                currency=command.budget_currency or "USD"
            )

        # ✅ استخدام with self._uow ثم الحصول على الخدمة داخل السياق
        with self._uow:
            # ✅ الحصول على الخدمة (سيتم إنشاؤها الآن داخل السياق)
            service = self._get_service()
            
            try:
                center = service.update_center(
                    center_id=command.center_id,
                    name=command.name,
                    center_type=center_type,
                    parent_code=command.parent_code,
                    manager_id=command.manager_id,
                    manager_name=command.manager_name,
                    department=command.department,
                    budget=budget,
                    description=command.description,
                    notes=command.notes,
                    tags=command.tags,
                    updated_by=user_context.user_id
                )
            except ConcurrentModificationError as e:
                logger.warning(f"Concurrent modification on center {command.center_id}")
                raise

            self._commit()

        logger.info(f"Center updated: {center.code} (version {center.version})")

        return center_to_dto(center)