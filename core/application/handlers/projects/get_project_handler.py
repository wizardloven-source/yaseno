# core/application/handlers/projects/get_project_handler.py (ملف جديد)
"""
Get Project Handler - معالج استعلام جلب مشروع
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.projects.value_objects import ProjectId

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import GetProjectQuery
from core.application.projects.dtos import ProjectDTO
from core.application.projects.converters import project_to_dto

logger = logging.getLogger(__name__)


class GetProjectHandler(BaseQueryHandler[GetProjectQuery, ProjectDTO]):
    """معالج استعلام جلب مشروع"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetProjectQuery, user_context: UserContext = None) -> ProjectDTO:
        logger.debug(f"Fetching project: {query.project_id}")

        with self._uow:
            project = self._uow.projects.get_by_id(ProjectId(query.project_id))
            if not project:
                logger.warning(f"Project not found: {query.project_id}")
                return None
            return project_to_dto(project)