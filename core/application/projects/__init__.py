# core/application/projects/__init__.py
"""
طبقة التطبيق لوحدة المشاريع (Projects Application)
"""

from .commands import (
    CreateProjectCommand,
    UpdateProjectCommand,
    DeleteProjectCommand,
    ChangeProjectStatusCommand,
    RecordProjectExpenseCommand,
    SetProjectBudgetCommand,
    GetProjectQuery,
    ListProjectsQuery,
    GetProjectOverviewQuery,
)
from .dtos import ProjectDTO, ProjectOverviewDTO
from .converters import (
    project_to_dto,
    projects_to_dto_list,
    project_overview_to_dto,
)

__all__ = [
    # Commands
    "CreateProjectCommand",
    "UpdateProjectCommand",
    "DeleteProjectCommand",
    "ChangeProjectStatusCommand",
    "RecordProjectExpenseCommand",
    "SetProjectBudgetCommand",
    # Queries
    "GetProjectQuery",
    "ListProjectsQuery",
    "GetProjectOverviewQuery",
    # DTOs
    "ProjectDTO",
    "ProjectOverviewDTO",
    # Converters
    "project_to_dto",
    "projects_to_dto_list",
    "project_overview_to_dto",
]