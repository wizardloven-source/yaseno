# core/application/handlers/projects/record_project_expense_handler.py (ملف جديد)
"""
Record Project Expense Handler - معالج تسجيل مصروف مشروع (ديناميكي)
"""

import logging

from core.domain.projects.services import ProjectService
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import RecordProjectExpenseCommand
from core.application.projects.dtos import ProjectDTO
from core.application.projects.converters import project_to_dto
from core.application.projects.utils import to_decimal

logger = logging.getLogger(__name__)


class RecordProjectExpenseHandler(BaseHandler[RecordProjectExpenseCommand, ProjectDTO]):
    """معالج تسجيل مصروف فعلي - يحدّث المصروف والمتبقي ديناميكياً"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    def _get_service(self):
        return ProjectService(project_repo=self._uow.projects)

    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: RecordProjectExpenseCommand, user_context: UserContext) -> ProjectDTO:
        amount = to_decimal(command.amount)
        if amount is None or amount < 0:
            raise ValueError("A valid non-negative expense amount is required")

        logger.info(f"Recording expense {amount} on project {command.project_id}")

        with self._uow:
            service = self._get_service()
            project = service.record_expense(
                project_id=command.project_id,
                amount=amount,
                notes=command.notes,
                recorded_by=user_context.user_id,
                reference=command.reference,
            )
            self._commit()

        logger.info(
            f"Project {project.code}: actual={project.actual_amount} remaining={project.remaining_amount}"
        )
        return project_to_dto(project)