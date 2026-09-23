# core/application/handlers/projects/__init__.py (ملف جديد)
"""
Projects Handlers - معالجات المشاريع

هذا المجلد يحتوي على جميع معالجات المشاريع
(Commands و Queries) مقسمة حسب الوظيفة.
"""

from .create_project_handler import CreateProjectHandler
from .update_project_handler import UpdateProjectHandler
from .delete_project_handler import DeleteProjectHandler
from .change_project_status_handler import ChangeProjectStatusHandler
from .record_project_expense_handler import RecordProjectExpenseHandler
from .set_project_budget_handler import SetProjectBudgetHandler
from .get_project_handler import GetProjectHandler
from .list_projects_handler import ListProjectsHandler
from .get_project_overview_handler import GetProjectOverviewHandler

__all__ = [
    # Command Handlers
    "CreateProjectHandler",
    "UpdateProjectHandler",
    "DeleteProjectHandler",
    "ChangeProjectStatusHandler",
    "RecordProjectExpenseHandler",
    "SetProjectBudgetHandler",
    # Query Handlers
    "GetProjectHandler",
    "ListProjectsHandler",
    "GetProjectOverviewHandler",
]