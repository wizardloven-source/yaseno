# core/application/handlers/workflow/create_workflow_handler.py
"""
Create Workflow Handler - معالج إنشاء سير عمل جديد
"""

import logging
from typing import Dict, Any, List

from core.domain.workflow.services import WorkflowService
from core.domain.workflow.value_objects import WorkflowEntityType
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import CreateWorkflowCommand
from core.application.workflow.dtos import WorkflowDTO
from core.application.workflow.converters import workflow_to_dto

logger = logging.getLogger(__name__)


class CreateWorkflowHandler(BaseHandler[CreateWorkflowCommand, WorkflowDTO]):
    """
    معالج إنشاء سير عمل جديد
    
    ✅ مصحح: استخدام Lazy Initialization للوصول إلى الـ Repositories
    ✅ لا يتم الوصول إلى uow في المُنشئ
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

    @require_permission(Permission.SYSTEM_CONFIG)
    def handle(self, command: CreateWorkflowCommand, user_context: UserContext) -> WorkflowDTO:
        """
        تنفيذ إنشاء سير العمل
        
        Args:
            command: أمر إنشاء سير العمل
            user_context: سياق المستخدم
        
        Returns:
            WorkflowDTO: بيانات سير العمل الجديد
        """
        logger.info(f"Creating workflow: {command.code} - {command.name}")

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
            workflow = service.create_workflow(
                name=command.name,
                code=command.code,
                entity_type=entity_type,
                steps=command.steps,
                description=command.description,
                is_mandatory=command.is_mandatory,
                auto_approve_threshold=command.auto_approve_threshold,
                auto_approve_after_days=command.auto_approve_after_days,
                created_by=user_context.user_id
            )
            self._commit()

        logger.info(f"Workflow created: {workflow.code} (ID: {workflow.id})")

        return workflow_to_dto(workflow)