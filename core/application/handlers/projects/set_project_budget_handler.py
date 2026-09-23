# core/application/handlers/projects/set_project_budget_handler.py (ملف جديد)
"""
Set Project Budget Handler - معالج تعيين ميزانية مشروع
"""

import logging

from core.domain.projects.services import ProjectService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import SetProjectBudgetCommand
from core.application.projects.dtos import ProjectDTO
from core.application.projects.converters import project_to_dto
from core.application.projects.utils import to_decimal

logger = logging.getLogger(__name__)


class SetProjectBudgetHandler(BaseHandler[SetProjectBudgetCommand, ProjectDTO]):
    """معالج تعيين ميزانية مشروع"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        return ProjectService(project_repo=self._uow.projects)

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: SetProjectBudgetCommand, user_context: UserContext) -> ProjectDTO:
        amount = to_decimal(command.amount)
        if amount is None or amount < 0:
            raise ValueError("A valid non-negative budget is required")

        logger.info(f"Setting budget {amount} {command.currency} on project {command.project_id}")

        with self._uow:
            service = self._get_service()
            project = service.set_budget(
                project_id=command.project_id,
                budget_amount=amount,
                currency=command.currency,
                set_by=user_context.user_id,
            )
            self._commit()

        return project_to_dto(project)