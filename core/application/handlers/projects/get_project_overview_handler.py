# core/application/handlers/projects/get_project_overview_handler.py (ملف جديد)
"""
Get Project Overview Handler - معالج استعلام الإحصائيات العامة للمشاريع
"""

import logging

from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseQueryHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.projects.commands import GetProjectOverviewQuery
from core.application.projects.dtos import ProjectOverviewDTO
from core.application.projects.converters import project_overview_to_dto

logger = logging.getLogger(__name__)


class GetProjectOverviewHandler(BaseQueryHandler[GetProjectOverviewQuery, ProjectOverviewDTO]):
    """معالج استعلام إحصائيات عامة عن المشاريع"""

    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)

    @require_permission(Permission.VIEW_JOURNAL_ENTRY)
    def handle(self, query: GetProjectOverviewQuery, user_context: UserContext = None) -> ProjectOverviewDTO:
        logger.debug("Fetching projects overview")

        with self._uow:
            data = self._uow.projects.overview()
            return project_overview_to_dto(data)