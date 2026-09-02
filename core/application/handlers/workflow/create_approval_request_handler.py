# core/application/handlers/workflow/create_approval_request_handler.py
"""
Create Approval Request Handler - معالج إنشاء طلب موافقة
"""

import logging
from typing import Dict, Any

from core.domain.workflow.services import WorkflowService
from core.domain.workflow.value_objects import WorkflowEntityType
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import CreateApprovalRequestCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class CreateApprovalRequestHandler(BaseHandler[CreateApprovalRequestCommand, ApprovalRequestDTO]):
    """
    معالج إنشاء طلب موافقة جديد
    
    ✅ مصحح: استخدام Lazy Initialization للوصول إلى الـ Repositories
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
        # ✅ Lazy Initialization - لا نصل إلى uow في المُنشئ
        self._service = None

    def _get_service(self) -> WorkflowService:
        """تهيئة الخدمة عند الحاجة فقط (Lazy Initialization)"""
        return WorkflowService(
            workflow_repo=self._uow.workflows,
            request_repo=self._uow.approval_requests
        )

    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateApprovalRequestCommand, user_context: UserContext) -> ApprovalRequestDTO:
        """
        تنفيذ إنشاء طلب الموافقة
        
        Args:
            command: أمر إنشاء طلب الموافقة
            user_context: سياق المستخدم
        
        Returns:
            ApprovalRequestDTO: بيانات طلب الموافقة الجديد
        """
        logger.info(f"Creating approval request for {command.entity_type}: {command.entity_id}")

        entity_type_map = {
            'invoice': WorkflowEntityType.INVOICE,
            'payment': WorkflowEntityType.PAYMENT,
            'journal_entry': WorkflowEntityType.JOURNAL_ENTRY,
            'purchase_order': WorkflowEntityType.PURCHASE_ORDER,
            'sales_order': WorkflowEntityType.SALES_ORDER,
            'expense': WorkflowEntityType.EXPENSE,
            'budget': WorkflowEntityType.BUDGET,
            'contract': WorkflowEntityType.CONTRACT,
            'user': WorkflowEntityType.USER,
            'custom': WorkflowEntityType.CUSTOM
        }
        entity_type = entity_type_map.get(command.entity_type, WorkflowEntityType.CUSTOM)

        with self._uow:
            # ✅ الحصول على الخدمة (لن يتم إنشاؤها إلا الآن)
            service = self._get_service()
            request = service.create_request(
                entity_type=entity_type,
                entity_id=command.entity_id,
                title=command.title,
                requested_by=user_context.user_id,
                requested_by_name=user_context.username,
                description=command.description,
                amount=command.amount,
                currency=command.currency,
                priority=command.priority,
                due_date=command.due_date,
                entity_data=command.entity_data,
                metadata=command.metadata
            )
            self._commit()

        logger.info(f"Approval request created: {request.id}")

        return request_to_dto(request)