# core/application/projects/converters.py (ملف جديد)
"""
Projects Converters - محولات المشاريع (Domain -> DTO)
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal

from core.domain.projects.entities import Project
from core.domain.projects.value_objects import ProjectBudgetAlert

from .dtos import ProjectDTO, ProjectOverviewDTO


# =============================================================================
# دوال مساعدة
# =============================================================================

def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, 'value'):
        return str(value.value)
    return str(value)


def _safe_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return Decimal('0')


# =============================================================================
# Project Converters
# =============================================================================

def project_to_dto(project: Project) -> ProjectDTO:
    """تحويل Project إلى DTO"""
    if not project:
        return None

    return ProjectDTO(
        id=_safe_str(project.id),
        code=_safe_str(project.code),
        name=project.name,
        status=project.status.value,
        description=project.description,
        customer_id=project.customer_id,
        customer_name=project.customer_name,
        manager_id=project.manager_id,
        manager_name=project.manager_name,
        budget_amount=_safe_decimal(project.budget_amount),
        budget_currency=project.budget_currency or "USD",
        actual_amount=_safe_decimal(project.actual_amount),
        remaining_amount=_safe_decimal(project.remaining_amount),
        budget_utilization_percent=project.budget_utilization_percent,
        budget_alert=project.budget_alert.value,
        is_over_budget=project.is_over_budget,
        start_date=project.start_date,
        end_date=project.end_date,
        actual_end_date=project.actual_end_date,
        associated_fund_id=str(project.associated_fund_id) if project.associated_fund_id else None,
        alert_threshold_percent=project.alert_threshold_percent,
        critical_threshold_percent=project.critical_threshold_percent,
        auto_close_on_budget_exceed=project.auto_close_on_budget_exceed,
        tags=list(project.tags or []),
        project_metadata=dict(project.project_metadata or {}),
        created_at=project.created_at,
        created_by=project.created_by,
        updated_at=project.updated_at,
        updated_by=project.updated_by,
        version=project.version,
    )


def projects_to_dto_list(projects: List[Project]) -> List[ProjectDTO]:
    """تحويل قائمة Projects إلى DTOs"""
    if not projects:
        return []
    return [project_to_dto(p) for p in projects if p]


def project_overview_to_dto(data: Dict[str, Any]) -> ProjectOverviewDTO:
    """تحويل بيانات الإحصائيات إلى DTO مع قيم افتراضية آمنة"""
    def _d(key: str) -> Decimal:
        v = data.get(key, 0)
        return _safe_decimal(v)

    by_status = data.get('by_status') or {}
    alerts = data.get('alerts') or {}

    return ProjectOverviewDTO(
        total_projects=int(data.get('total_projects', 0)),
        active_projects=int(data.get('active_projects', 0)),
        total_budget=_d('total_budget'),
        total_actual=_d('total_actual'),
        total_remaining=_d('total_remaining'),
        currency=data.get('currency', 'USD'),
        by_status={str(k): int(v) for k, v in by_status.items()},
        alerts={str(k): int(v) for k, v in alerts.items()},
    )


__all__ = [
    "project_to_dto",
    "projects_to_dto_list",
    "project_overview_to_dto",
]