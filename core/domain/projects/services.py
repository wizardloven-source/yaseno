# core/domain/projects/services.py (ملف جديد)
"""Projects Services - خدمات مجال المشاريع"""

import logging
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime

from .entities import Project
from .value_objects import (
    ProjectId,
    ProjectCode,
    ProjectStatus,
    ProjectBudgetAlert,
)
from .interfaces import IProjectRepository

logger = logging.getLogger(__name__)


class ProjectService:
    """خدمة المشاريع - تحتوي على منطق الأعمال الكامل"""

    def __init__(self, project_repo: IProjectRepository):
        self._project_repo = project_repo

    # =========================================================================
    # إدارة المشروع
    # =========================================================================

    def create_project(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        customer_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        manager_id: Optional[str] = None,
        manager_name: Optional[str] = None,
        budget_amount: Optional[Decimal] = None,
        budget_currency: str = "USD",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: ProjectStatus = ProjectStatus.PLANNING,
        tags: Optional[List[str]] = None,
        created_by: str = "system",
    ) -> Project:
        """إنشاء مشروع جديد"""
        if self._project_repo.exists_by_code(ProjectCode(code)):
            raise ValueError(f"Project code already exists: {code}")

        project = Project.create(
            code=code,
            name=name,
            description=description,
            customer_id=customer_id,
            customer_name=customer_name,
            manager_id=manager_id,
            manager_name=manager_name,
            budget_amount=budget_amount,
            budget_currency=budget_currency,
            start_date=start_date,
            end_date=end_date,
            status=status,
            tags=tags,
            created_by=created_by,
        )

        self._project_repo.save(project)
        logger.info(f"Project created: {project.code} ({project.name})")
        return project

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        customer_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        manager_id: Optional[str] = None,
        manager_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        updated_by: str = "system",
    ) -> Project:
        """تحديث بيانات مشروع"""
        project = self._get_or_raise(project_id)
        project.update(
            name=name,
            description=description,
            customer_id=customer_id,
            customer_name=customer_name,
            manager_id=manager_id,
            manager_name=manager_name,
            start_date=start_date,
            end_date=end_date,
            tags=tags,
            updated_by=updated_by,
        )
        self._project_repo.save(project)
        return project

    def change_status(
        self,
        project_id: str,
        new_status: ProjectStatus,
        reason: Optional[str] = None,
        changed_by: str = "system",
    ) -> Project:
        """تغيير حالة المشروع"""
        project = self._get_or_raise(project_id)
        project.change_status(new_status, reason, changed_by)
        self._project_repo.save(project)
        return project

    def delete_project(self, project_id: str, deleted_by: str = "system") -> bool:
        """حذف مشروع"""
        project = self._get_or_raise(project_id)
        return self._project_repo.delete(project.id)

    # =========================================================================
    # الميزانية والمصروفات (ديناميكية)
    # =========================================================================

    def set_budget(
        self,
        project_id: str,
        budget_amount: Decimal,
        currency: str,
        set_by: str = "system",
    ) -> Project:
        """تعيين ميزانية المشروع"""
        project = self._get_or_raise(project_id)
        project.set_budget(budget_amount, currency, set_by)
        self._project_repo.save(project)
        return project

    def record_expense(
        self,
        project_id: str,
        amount: Decimal,
        notes: Optional[str] = None,
        recorded_by: str = "system",
        reference: Optional[str] = None,
    ) -> Project:
        """تسجيل مصروف فعلي - يحدّث المصروف والمتبقي ديناميكياً"""
        project = self._get_or_raise(project_id)
        if project.status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED, ProjectStatus.ARCHIVED):
            raise ValueError(f"Cannot record expense on {project.status.value} project")
        alert = project.record_expense(amount, notes, recorded_by, reference)
        self._project_repo.save(project)
        if alert != ProjectBudgetAlert.NONE:
            logger.warning(
                f"Project {project.code} budget alert={alert.value} "
                f"(used={project.actual_amount}/{project.budget_amount})"
            )
        return project

    # =========================================================================
    # الاستعلامات
    # =========================================================================

    def get_project(self, project_id: str) -> Optional[Project]:
        return self._project_repo.get_by_id(ProjectId(project_id))

    def get_by_code(self, code: str) -> Optional[Project]:
        return self._project_repo.get_by_code(ProjectCode(code))

    def list_projects(
        self,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
        customer_id: Optional[str] = None,
        manager_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Project]:
        return self._project_repo.list_all(
            status=status,
            search=search,
            customer_id=customer_id,
            manager_id=manager_id,
            limit=limit,
            offset=offset,
        )

    def get_overview(self) -> Dict[str, Any]:
        """إحصائيات عامة ديناميكية عن المشاريع"""
        return self._project_repo.overview()

    def get_next_code(self, prefix: str = "PRJ") -> str:
        return self._project_repo.get_next_code(prefix)

    # =========================================================================
    # أدوات مساعدة
    # =========================================================================

    def _get_or_raise(self, project_id: str) -> Project:
        project = self._project_repo.get_by_id(ProjectId(project_id))
        if not project:
            raise ValueError(f"Project not found: {project_id}")
        return project