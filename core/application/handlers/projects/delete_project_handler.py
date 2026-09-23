# core/application/handlers/projects/delete_project_handler.py (ملف جديد)
"""
Delete Project Handler - معالج حذف مشروع
"""

import logging

from core.domain.projects.services import ProjectService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import DeleteProjectCommand

logger = logging.getLogger(__name__)


class DeleteProjectHandler(BaseHandler[DeleteProjectCommand, bool]):
    """معالج حذف مشروع"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        return ProjectService(project_repo=self._uow.projects)

    @require_permission(Permission.DELETE_DRAFT)
    def handle(self, command: DeleteProjectCommand, user_context: UserContext) -> bool:
        logger.info(f"Deleting project: {command.project_id}")

        with self._uow:
            service = self._get_service()
            result = service.delete_project(
                project_id=command.project_id,
                deleted_by=user_context.user_id,
            )
            self._commit()

        return result