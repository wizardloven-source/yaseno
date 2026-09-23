# core/application/projects/commands.py (ملف جديد)
"""
Projects Commands & Queries - أوامر واستعلامات المشاريع
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal


# =============================================================================
# COMMANDS - أوامر إدارة المشاريع
# =============================================================================

@dataclass(frozen=True)
class CreateProjectCommand:
    """أمر إنشاء مشروع جديد"""
    name: str
    code: Optional[str] = None  # يُولّد تلقائياً إذا لم يُحدد
    description: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: str = "USD"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "planning"
    tags: Optional[List[str]] = None
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateProjectCommand:
    """أمر تحديث مشروع"""
    project_id: str
    version: int
    name: Optional[str] = None
    description: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tags: Optional[List[str]] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class DeleteProjectCommand:
    """أمر حذف مشروع"""
    project_id: str
    deleted_by: str = "system"


@dataclass(frozen=True)
class ChangeProjectStatusCommand:
    """أمر تغيير حالة مشروع"""
    project_id: str
    status: str
    reason: Optional[str] = None
    changed_by: str = "system"


@dataclass(frozen=True)
class RecordProjectExpenseCommand:
    """أمر تسجيل مصروف فعلي على مشروع"""
    project_id: str
    amount: Decimal
    notes: Optional[str] = None
    reference: Optional[str] = None
    recorded_by: str = "system"


@dataclass(frozen=True)
class SetProjectBudgetCommand:
    """أمر تعيين ميزانية مشروع"""
    project_id: str
    amount: Decimal
    currency: str = "USD"
    set_by: str = "system"


# =============================================================================
# QUERIES - استعلامات المشاريع
# =============================================================================

@dataclass(frozen=True)
class GetProjectQuery:
    """استعلام لجلب مشروع"""
    project_id: str


@dataclass(frozen=True)
class ListProjectsQuery:
    """استعلام لقائمة المشاريع"""
    status: Optional[str] = None
    search: Optional[str] = None
    customer_id: Optional[str] = None
    manager_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetProjectOverviewQuery:
    """استعلام لإحصائيات عامة عن المشاريع"""


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
]