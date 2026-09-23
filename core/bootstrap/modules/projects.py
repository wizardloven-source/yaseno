# core/bootstrap/modules/projects.py
"""
وحدة المشاريع - تسجيل جميع خدمات المشاريع والميزانيات
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class ProjectsModule(Module):
    """وحدة المشاريع - إدارة المشاريع والميزانيات والمصروفات"""
    
    name = "projects"
    description = "إدارة المشاريع، الميزانيات، والمصروفات"
    dependencies = ["database", "accounting"]
    version = "1.0.0"
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات المشاريع"""
        
        # ========== Repositories ==========
        container.register(
            "project_repo",
            "core.infrastructure.db.postgres.project_repository.PostgresProjectRepository",
            lifetime=ServiceLifetime.SCOPED,
            dependencies=["session"]
        )
        
        # ========== Services ==========
        container.register(
            "project_service",
            "core.domain.projects.services.ProjectService",
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["project_repo"]
        )
        
        # ========== Command Handlers ==========
        container.register(
            "create_project_handler",
            "core.application.handlers.projects.CreateProjectHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "update_project_handler",
            "core.application.handlers.projects.UpdateProjectHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "delete_project_handler",
            "core.application.handlers.projects.DeleteProjectHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "change_project_status_handler",
            "core.application.handlers.projects.ChangeProjectStatusHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "record_project_expense_handler",
            "core.application.handlers.projects.RecordProjectExpenseHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "set_project_budget_handler",
            "core.application.handlers.projects.SetProjectBudgetHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        
        # ========== Query Handlers ==========
        container.register(
            "get_project_handler",
            "core.application.handlers.projects.GetProjectHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "list_projects_handler",
            "core.application.handlers.projects.ListProjectsHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
        container.register(
            "get_project_overview_handler",
            "core.application.handlers.projects.GetProjectOverviewHandler",
            lifetime=ServiceLifetime.TRANSIENT,
            dependencies=["uow"]
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تسجيل Handlers في Command/Query Bus"""
        command_bus = container.resolve("command_bus")
        query_bus = container.resolve("query_bus")
        
        with container.scope() as scoped_container:
            # ========== Command Handlers ==========
            for handler_name, command_name in [
                ("create_project_handler", "CreateProjectCommand"),
                ("update_project_handler", "UpdateProjectCommand"),
                ("delete_project_handler", "DeleteProjectCommand"),
                ("change_project_status_handler", "ChangeProjectStatusCommand"),
                ("record_project_expense_handler", "RecordProjectExpenseCommand"),
                ("set_project_budget_handler", "SetProjectBudgetCommand"),
            ]:
                try:
                    command_bus.register(command_name, handler_name)
                    logger.info(f"✅ Registered {command_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to register {command_name}: {e}")
            
            # ========== Query Handlers ==========
            for handler_name, query_name in [
                ("get_project_handler", "GetProjectQuery"),
                ("list_projects_handler", "ListProjectsQuery"),
                ("get_project_overview_handler", "GetProjectOverviewQuery"),
            ]:
                try:
                    query_bus.register(query_name, handler_name)
                    logger.info(f"✅ Registered {query_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to register {query_name}: {e}")