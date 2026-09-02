# core/application/handlers/workflow/batch_reject_requests_handler.py
"""
Batch Reject Requests Handler - معالج الرفض الجماعي للطلبات
"""

import logging
from typing import List

from core.domain.workflow.services import WorkflowService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.workflow.commands import BatchRejectRequestsCommand
from core.application.workflow.dtos import ApprovalRequestDTO
from core.application.workflow.converters import request_to_dto

logger = logging.getLogger(__name__)


class BatchRejectRequestsHandler(BaseHandler[BatchRejectRequestsCommand, List[ApprovalRequestDTO]]):
    """
    معالج الرفض الجماعي للطلبات
    
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
    def handle(self, command: BatchRejectRequestsCommand, user_context: UserContext) -> List[ApprovalRequestDTO]:
        """
        تنفيذ الرفض الجماعي للطلبات
        
        Args:
            command: أمر الرفض الجماعي
            user_context: سياق المستخدم
        
        Returns:
            List[ApprovalRequestDTO]: قائمة الطلبات بعد الرفض
        """
        logger.info(f"Batch rejecting {len(command.request_ids)} requests")

        rejected_requests = []

        with self._uow:
            service = self._get_service()
            
            for request_id in command.request_ids:
                try:
                    request = service.reject_request(
                        request_id=request_id,
                        approver_id=user_context.user_id,
                        approver_name=user_context.username,
                        reason=command.reason
                    )
                    rejected_requests.append(request)
                except Exception as e:
                    logger.error(f"Failed to reject request {request_id}: {e}")
            
            self._commit()

        logger.info(f"Batch rejected {len(rejected_requests)} requests")

        return [request_to_dto(req) for req in rejected_requests]