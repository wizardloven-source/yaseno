# core/application/handlers/workflow/batch_approve_requests_handler.py
"""
Batch Approve Requests Handler - معالج الموافقة الجماعية على طلبات
"""

import logging
from typing import List, Dict, Any

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import BatchApproveRequestsCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class BatchApproveRequestsHandler(BaseHandler[BatchApproveRequestsCommand, List[ApprovalRequestDTO]]):
    """
    معالج الموافقة الجماعية على طلبات
    
    ✅ مصحح: استخدام Lazy Initialization
    """

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    def _get_service(self) -> WorkflowService:
        return WorkflowService(
            workflow_repo=self._uow.workflows,
            request_repo=self._uow.approval_requests
        )

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: BatchApproveRequestsCommand, user_context: UserContext) -> List[ApprovalRequestDTO]:
        """
        تنفيذ الموافقة الجماعية على الطلبات
        
        Args:
            command: أمر الموافقة الجماعية
            user_context: سياق المستخدم
        
        Returns:
            List[ApprovalRequestDTO]: قائمة الطلبات بعد الموافقة
        """
        logger.info(f"Batch approving {len(command.request_ids)} requests")

        approved_requests = []

        with self._uow:
            service = self._get_service()
            
            for request_id in command.request_ids:
                try:
                    request = service.approve_request(
                        request_id=request_id,
                        approver_id=user_context.user_id,
                        approver_name=user_context.username,
                        comment=command.comment
                    )
                    approved_requests.append(request)
                except Exception as e:
                    logger.error(f"Failed to approve request {request_id}: {e}")
            
            self._commit()

        logger.info(f"Batch approved {len(approved_requests)} requests")

        return [request_to_dto(req) for req in approved_requests]