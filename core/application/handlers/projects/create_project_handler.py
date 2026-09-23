# core/application/handlers/projects/create_project_handler.py (ملف جديد)
"""
Create Project Handler - معالج إنشاء مشروع جديد
"""

import logging
from decimal import Decimal

from core.domain.projects.services import ProjectService
from core.domain.projects.value_objects import ProjectStatus
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import CreateProjectCommand
from core.application.projects.dtos import ProjectDTO
from core.application.projects.converters import project_to_dto
from core.application.projects.utils import parse_datetime, to_decimal

logger = logging.getLogger(__name__)


class CreateProjectHandler(BaseHandler[CreateProjectCommand, ProjectDTO]):
    """معالج إنشاء مشروع جديد"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        return ProjectService(project_repo=self._uow.projects)

    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateProjectCommand, user_context: UserContext) -> ProjectDTO:
        logger.info(f"Creating project: {command.name}")

        with self._uow:
            service = self._get_service()

            # توليد كود تلقائي إذا لم يُحدد
            code = command.code
            if not code or not code.strip():
                code = service.get_next_code()

            status = ProjectStatus(command.status) if command.status else ProjectStatus.PLANNING

            project = service.create_project(
                code=code.strip().upper(),
                name=command.name,
                description=command.description,
                customer_id=command.customer_id,
                customer_name=command.customer_name,
                manager_id=command.manager_id,
                manager_name=command.manager_name,
                budget_amount=to_decimal(command.budget_amount),
                budget_currency=command.budget_currency or "USD",
                start_date=parse_datetime(command.start_date),
                end_date=parse_datetime(command.end_date),
                status=status,
                tags=command.tags,
                created_by=user_context.user_id,
            )

            self._commit()

        logger.info(f"Project created: {project.code} (ID: {project.id})")
        return project_to_dto(project)