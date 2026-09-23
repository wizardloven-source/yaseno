# core/application/handlers/projects/change_project_status_handler.py (ملف جديد)
"""
Change Project Status Handler - معالج تغيير حالة مشروع
"""

import logging

from core.domain.projects.services import ProjectService
from core.domain.projects.value_objects import ProjectStatus
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import ChangeProjectStatusCommand
from core.application.projects.dtos import ProjectDTO
from core.application.projects.converters import project_to_dto

logger = logging.getLogger(__name__)


class ChangeProjectStatusHandler(BaseHandler[ChangeProjectStatusCommand, ProjectDTO]):
    """معالج تغيير حالة مشروع"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        return ProjectService(project_repo=self._uow.projects)

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: ChangeProjectStatusCommand, user_context: UserContext) -> ProjectDTO:
        logger.info(f"Changing status of project {command.project_id} to {command.status}")

        status = ProjectStatus(command.status)

        with self._uow:
            service = self._get_service()
            project = service.change_status(
                project_id=command.project_id,
                new_status=status,
                reason=command.reason,
                changed_by=user_context.user_id,
            )
            self._commit()

        return project_to_dto(project)