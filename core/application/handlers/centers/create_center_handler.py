# core/application/handlers/centers/create_center_handler.py
"""
Create Center Handler - معالج إنشاء مركز تكلفة/ربح جديد
"""

import logging
from decimal import Decimal

from core.domain.centers.services import CenterService
from core.domain.centers.value_objects import CenterType, CenterBudget
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import CreateCenterCommand
from core.application.centers.dtos import CenterDTO
from core.application.centers.converters import center_to_dto

logger = logging.getLogger(__name__)


class CreateCenterHandler(BaseHandler[CreateCenterCommand, CenterDTO]):
    """
    معالج إنشاء مركز تكلفة/ربح جديد
    
    يقوم بإنشاء مركز جديد مع التحقق من:
    - عدم وجود كود مكرر
    - وجود المركز الأب (إذا تم تحديده)
    - صحة نوع المركز
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

    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateCenterCommand, user_context: UserContext) -> CenterDTO:
        """
        تنفيذ إنشاء مركز جديد
        
        Args:
            command: أمر إنشاء المركز
            user_context: سياق المستخدم
        
        Returns:
            CenterDTO: بيانات المركز الجديد
        """
        logger.info(f"Creating center: {command.code} - {command.name}")

        # تحويل نوع المركز
        center_type_map = {
            'cost': CenterType.COST,
            'profit': CenterType.PROFIT,
            'both': CenterType.BOTH
        }
        center_type = center_type_map.get(command.center_type, CenterType.COST)

        # إنشاء الميزانية إذا تم تحديدها
        budget = None
        if command.budget_amount and command.budget_amount > 0:
            budget = CenterBudget(
                total_budget=command.budget_amount,
                currency=command.budget_currency
            )

        # ✅ استخدام with self._uow ثم إنشاء الخدمة داخل السياق
        with self._uow:
            # ✅ الحصول على الخدمة (سيتم إنشاؤها الآن داخل السياق)
            service = self._get_service()
            
            center = service.create_center(
                code=command.code,
                name=command.name,
                center_type=center_type,
                parent_code=command.parent_code,
                manager_id=command.manager_id,
                manager_name=command.manager_name,
                department=command.department,
                budget=budget,
                description=command.description,
                created_by=user_context.user_id
            )

            self._commit()

        logger.info(f"Center created: {center.code} (ID: {center.id})")

        return center_to_dto(center)