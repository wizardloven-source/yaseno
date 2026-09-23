# core/domain/projects/__init__.py
"""
واجهة مجال المشاريع (Projects Domain)

يوفر هذا المجلد كيانات المشاريع وقيم الكائنات والواجهات والأحداث والخدمات
لمنطق أعمال إدارة المشاريع والميزانيات والمصروفات.
"""

from .value_objects import (
    ProjectId,
    ProjectCode,
    ProjectStatus,
    ProjectBudgetAlert,
)
from .entities import Project
from .interfaces import IProjectRepository
from .services import ProjectService

__all__ = [
    "ProjectId",
    "ProjectCode",
    "ProjectStatus",
    "ProjectBudgetAlert",
    "Project",
    "IProjectRepository",
    "ProjectService",
]