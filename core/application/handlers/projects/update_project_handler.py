# core/application/handlers/projects/update_project_handler.py (ملف جديد)
"""
Update Project Handler - معالج تحديث مشروع
"""

import logging

from core.domain.projects.services import ProjectService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import UpdateProjectCommand
from core.application.projects.dtos import ProjectDTO
from core.application.projects.converters import project_to_dto
from core.application.projects.utils import parse_datetime

logger = logging.getLogger(__name__)


class UpdateProjectHandler(BaseHandler[UpdateProjectCommand, ProjectDTO]):
    """معالج تحديث مشروع"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        return ProjectService(project_repo=self._uow.projects)

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateProjectCommand, user_context: UserContext) -> ProjectDTO:
        logger.info(f"Updating project: {command.project_id}")

        with self._uow:
            service = self._get_service()
            project = service.update_project(
                project_id=command.project_id,
                name=command.name,
                description=command.description,
                customer_id=command.customer_id,
                customer_name=command.customer_name,
                manager_id=command.manager_id,
                manager_name=command.manager_name,
                start_date=parse_datetime(command.start_date),
                end_date=parse_datetime(command.end_date),
                tags=command.tags,
                updated_by=user_context.user_id,
            )
            self._commit()

        return project_to_dto(project)