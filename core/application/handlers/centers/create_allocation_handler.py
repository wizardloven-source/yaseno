# core/application/handlers/centers/create_allocation_handler.py
"""
Create Allocation Handler - معالج إنشاء توزيع مصروفات
"""

import logging
from decimal import Decimal

from core.domain.centers.services import CenterService
from core.domain.centers.value_objects import AllocationMethod
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.centers.commands import CreateAllocationCommand
from core.application.centers.dtos import AllocationDTO
from core.application.centers.converters import allocation_to_dto

logger = logging.getLogger(__name__)


class CreateAllocationHandler(BaseHandler[CreateAllocationCommand, AllocationDTO]):
    """
    معالج إنشاء توزيع مصروفات
    
    يقوم بإنشاء توزيع مصروفات جديد بين المراكز.
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        return CenterService(
            center_repo=self._uow.centers,
            allocation_repo=self._uow.center_allocations,
            rule_repo=self._uow.center_allocation_rules
        )

    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateAllocationCommand, user_context: UserContext) -> AllocationDTO:
        """
        تنفيذ إنشاء توزيع المصروفات
        
        Args:
            command: أمر إنشاء التوزيع
            user_context: سياق المستخدم
        
        Returns:
            AllocationDTO: بيانات التوزيع الجديد
        """
        logger.info(f"Creating allocation from {command.source_center_code} to {len(command.target_center_codes)} centers")

        # تحويل طريقة التوزيع
        method_map = {
            'percentage': AllocationMethod.PERCENTAGE,
            'fixed_amount': AllocationMethod.FIXED_AMOUNT,
            'manual': AllocationMethod.MANUAL,
            'equal': AllocationMethod.EQUAL,
            'weighted': AllocationMethod.WEIGHTED,
            'activity_based': AllocationMethod.ACTIVITY_BASED
        }
        method = method_map.get(command.method, AllocationMethod.EQUAL)

        with self._uow:
            service = self._get_service()
            allocation = service.create_allocation(
                source_center_code=command.source_center_code,
                target_center_codes=command.target_center_codes,
                amount=command.amount,
                period_start=command.period_start,
                period_end=command.period_end,
                method=method,
                description=command.description,
                created_by=user_context.user_id
            )

            self._commit()

        logger.info(f"Allocation created: {allocation.id}")

        return allocation_to_dto(allocation)