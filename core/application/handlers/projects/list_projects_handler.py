# core/application/handlers/projects/list_projects_handler.py (ملف جديد)
"""
List Projects Handler - معالج استعلام قائمة المشاريع
"""

import logging
from typing import List

from core.domain.projects.value_objects import ProjectStatus
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import ListProjectsQuery
from core.application.projects.dtos import ProjectDTO
from core.application.projects.converters import projects_to_dto_list

logger = logging.getLogger(__name__)


class ListProjectsHandler(BaseQueryHandler[ListProjectsQuery, List[ProjectDTO]]):
    """معالج استعلام قائمة المشاريع مع الفلاتر والبحث"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: ListProjectsQuery, user_context: UserContext = None) -> List[ProjectDTO]:
        logger.debug(
            f"Listing projects: status={query.status}, search={query.search}"
        )

        status = None
        if query.status:
            try:
                status = ProjectStatus(query.status)
            except ValueError:
                status = None

        with self._uow:
            projects = self._uow.projects.list_all(
                status=status,
                search=query.search,
                customer_id=query.customer_id,
                manager_id=query.manager_id,
                limit=query.limit,
                offset=query.offset,
            )
            return projects_to_dto_list(projects)