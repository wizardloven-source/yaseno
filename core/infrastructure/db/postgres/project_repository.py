# core/infrastructure/db/postgres/project_repository.py (ملف جديد)
"""
Projects PostgreSQL Repository - مستودع المشاريع
"""

import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum

from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import Session

from core.domain.projects.entities import Project
from core.domain.projects.value_objects import (
    ProjectId,
    ProjectCode,
    ProjectStatus,
    ProjectBudgetAlert,
)
from core.domain.projects.interfaces import IProjectRepository
from core.shared.exceptions import ConcurrentModificationError

from ..models.fund_advanced_models import ProjectModel

logger = logging.getLogger(__name__)


# =============================================================================
# تحويل الحالة (يتوافق مع قيمة التخزين الفعلية في قاعدة البيانات)
# =============================================================================

def _coerce_status(raw) -> ProjectStatus:
    """تحويل قيمة الحالة من قاعدة البيانات إلى ProjectStatus الدومين"""
    if raw is None:
        return ProjectStatus.PLANNING
    if isinstance(raw, Enum):
        raw = raw.name  # SQLAlchemy قد يُرجع عضو Enum من نموذج النموذج
    s = str(raw).lower()
    for member in ProjectStatus:
        if s == member.value or s == member.name.lower():
            return member
    logger.warning(f"Unknown project status value from DB: {raw}; defaulting to planning")
    return ProjectStatus.PLANNING


def _model_status_value(status: ProjectStatus) -> str:
    """إرجاع قيمة الحالة الموافقة لعمود النموذج (اسم العضو — enum المشروع بالحروف الكبيرة)"""
    return status.name


# =============================================================================
# دوال التحويل (Domain <-> Model)
# =============================================================================

def _model_to_domain(model: ProjectModel) -> Project:
    """تحويل نموذج ORM إلى كيان Domain - Project"""
    if not model:
        return None

    return Project(
        id=ProjectId(model.id),
        code=ProjectCode(model.code),
        name=model.name,
        description=model.description,
        customer_id=model.customer_id,
        customer_name=model.customer_name,
        manager_id=model.manager_id,
        manager_name=model.manager_name,
        budget_amount=Decimal(str(model.budget_amount or 0)),
        budget_currency=model.budget_currency or "USD",
        actual_amount=Decimal(str(model.actual_amount or 0)),
        remaining_amount=Decimal(str(model.remaining_amount or 0)),
        start_date=model.start_date,
        end_date=model.end_date,
        actual_end_date=model.actual_end_date,
        status=_coerce_status(model.status),
        associated_fund_id=model.associated_fund_id,
        alert_threshold_percent=model.alert_threshold_percent or 85,
        critical_threshold_percent=model.critical_threshold_percent or 95,
        auto_close_on_budget_exceed=model.auto_close_on_budget_exceed or False,
        tags=list(model.tags or []),
        project_metadata=dict(model.project_metadata or {}),
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version or 1,
    )


def _domain_to_model(project: Project) -> ProjectModel:
    """تحويل كيان Domain إلى نموذج ORM - Project"""
    return ProjectModel(
        id=project.id.value,
        code=project.code.value,
        name=project.name,
        description=project.description,
        customer_id=project.customer_id,
        customer_name=project.customer_name,
        manager_id=project.manager_id,
        manager_name=project.manager_name,
        budget_amount=project.budget_amount,
        budget_currency=project.budget_currency or "USD",
        actual_amount=project.actual_amount,
        remaining_amount=project.remaining_amount,
        start_date=project.start_date,
        end_date=project.end_date,
        actual_end_date=project.actual_end_date,
        status=_model_status_value(project.status),
        associated_fund_id=project.associated_fund_id,
        alert_threshold_percent=project.alert_threshold_percent,
        critical_threshold_percent=project.critical_threshold_percent,
        auto_close_on_budget_exceed=project.auto_close_on_budget_exceed,
        tags=project.tags,
        project_metadata=project.project_metadata,
        created_at=project.created_at,
        created_by=project.created_by,
        updated_at=project.updated_at,
        updated_by=project.updated_by,
        version=project.version,
    )


def _values_for_update(project: Project) -> Dict[str, Any]:
    """قيم التحديث الموافقة لأعمدة النموذج"""
    return {
        "code": project.code.value,
        "name": project.name,
        "description": project.description,
        "customer_id": project.customer_id,
        "customer_name": project.customer_name,
        "manager_id": project.manager_id,
        "manager_name": project.manager_name,
        "budget_amount": project.budget_amount,
        "budget_currency": project.budget_currency or "USD",
        "actual_amount": project.actual_amount,
        "remaining_amount": project.remaining_amount,
        "start_date": project.start_date,
        "end_date": project.end_date,
        "actual_end_date": project.actual_end_date,
        "status": _model_status_value(project.status),
        "associated_fund_id": project.associated_fund_id,
        "alert_threshold_percent": project.alert_threshold_percent,
        "critical_threshold_percent": project.critical_threshold_percent,
        "auto_close_on_budget_exceed": project.auto_close_on_budget_exceed,
        "tags": project.tags,
        "project_metadata": project.project_metadata,
        "updated_at": project.updated_at,
        "updated_by": project.updated_by,
        "version": project.version,
    }


# =============================================================================
# PostgresProjectRepository
# =============================================================================

class PostgresProjectRepository(IProjectRepository):
    """تطبيق PostgreSQL لمستودع المشاريع"""

    def __init__(self, session: Session):
        self._session = session

    # -------------------------------------------------------------------------
    # حفظ وتحديث
    # -------------------------------------------------------------------------

    def save(self, project: Project) -> None:
        """حفظ المشروع (جديد أو محدث) مع Optimistic Locking"""
        existing = self._session.execute(
            select(ProjectModel).where(ProjectModel.id == project.id.value)
        ).scalar_one_or_none()

        if existing:
            self._update_existing(existing, project)
        else:
            self._create_new(project)

    def _update_existing(self, existing: ProjectModel, project: Project) -> None:
        if existing.version != project.version and existing.version != project.version - 1:
            raise ConcurrentModificationError(
                "Project", str(project.id), project.version, existing.version
            )

        expected_version = existing.version
        new_version = existing.version + 1
        values = _values_for_update(project)
        values["version"] = new_version

        result = self._session.execute(
            update(ProjectModel)
            .where(
                ProjectModel.id == project.id.value,
                ProjectModel.version == expected_version,
            )
            .values(**values)
        )

        if result.rowcount == 0:
            raise ConcurrentModificationError(
                "Project", str(project.id), project.version, existing.version
            )

        project.version = new_version

    def _create_new(self, project: Project) -> None:
        model = _domain_to_model(project)
        self._session.add(model)
        self._session.flush()
        project.version = 1

    # -------------------------------------------------------------------------
    # جلب
    # -------------------------------------------------------------------------

    def get_by_id(self, project_id: ProjectId) -> Optional[Project]:
        model = self._session.execute(
            select(ProjectModel).where(ProjectModel.id == project_id.value)
        ).scalar_one_or_none()

        if not model:
            return None
        return _model_to_domain(model)

    def get_by_code(self, code: ProjectCode) -> Optional[Project]:
        model = self._session.execute(
            select(ProjectModel).where(ProjectModel.code == code.value)
        ).scalar_one_or_none()

        if not model:
            return None
        return _model_to_domain(model)

    def list_all(
        self,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
        customer_id: Optional[str] = None,
        manager_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Project]:
        query = select(ProjectModel)

        if status:
            query = query.where(ProjectModel.status == _model_status_value(status))

        if customer_id:
            query = query.where(ProjectModel.customer_id == customer_id)

        if manager_id:
            query = query.where(ProjectModel.manager_id == manager_id)

        if search:
            term = f"%{search}%"
            query = query.where(
                (ProjectModel.name.ilike(term)) |
                (ProjectModel.code.ilike(term)) |
                (ProjectModel.description.ilike(term))
            )

        models = self._session.execute(
            query
            .order_by(ProjectModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()

        return [_model_to_domain(m) for m in models]

    def search(self, search_text: str, limit: int = 50) -> List[Project]:
        return self.list_all(search=search_text, limit=limit)

    def exists_by_code(self, code: ProjectCode) -> bool:
        result = self._session.execute(
            select(ProjectModel.id).where(ProjectModel.code == code.value)
        ).first()
        return result is not None

    def delete(self, project_id: ProjectId) -> bool:
        result = self._session.execute(
            delete(ProjectModel).where(ProjectModel.id == project_id.value)
        )
        self._session.flush()
        return result.rowcount > 0

    def get_next_code(self, prefix: str = "PRJ") -> str:
        """توليد كود تلقائي للمشروع (PRJ0001, PRJ0002, ...)"""
        result = self._session.execute(
            select(ProjectModel.code)
            .where(ProjectModel.code.startswith(prefix))
            .order_by(ProjectModel.code.desc())
        ).first()

        if result:
            last_code = result[0]
            try:
                num = int(last_code[len(prefix):])
                next_num = num + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}{next_num:04d}"

    # -------------------------------------------------------------------------
    # إحصائيات عامة (Overview)
    # -------------------------------------------------------------------------

    def overview(self) -> Dict[str, Any]:
        """إحصائيات عامة عن المشاريع"""
        rows = self._session.execute(
            select(
                ProjectModel.status,
                ProjectModel.budget_amount,
                ProjectModel.actual_amount,
                ProjectModel.budget_currency,
                ProjectModel.alert_threshold_percent,
                ProjectModel.critical_threshold_percent,
            )
        ).all()

        total_projects = len(rows)
        active_projects = 0
        total_budget = Decimal('0')
        total_actual = Decimal('0')
        by_status: Dict[str, int] = {}
        alerts: Dict[str, int] = {}
        currencies: Dict[str, Dict[str, Decimal]] = {}

        for status_raw, budget, actual, currency, alert_p, critical_p in rows:
            status = _coerce_status(status_raw).value
            by_status[status] = by_status.get(status, 0) + 1
            if status == ProjectStatus.ACTIVE.value:
                active_projects += 1

            budget = Decimal(str(budget or 0))
            actual = Decimal(str(actual or 0))
            total_budget += budget
            total_actual += actual
            currency = currency or "USD"

            cur = currencies.setdefault(currency, {'budget': Decimal('0'), 'actual': Decimal('0')})
            cur['budget'] += budget
            cur['actual'] += actual

            # تصنيف التنبيه
            if actual > budget:
                alert = ProjectBudgetAlert.OVER.value
            elif budget > 0:
                utilization = (actual / budget) * Decimal('100')
                if utilization >= (critical_p or 95):
                    alert = ProjectBudgetAlert.CRITICAL.value
                elif utilization >= (alert_p or 85):
                    alert = ProjectBudgetAlert.WARNING.value
                else:
                    alert = ProjectBudgetAlert.NONE.value
            else:
                alert = ProjectBudgetAlert.NONE.value

            alerts[alert] = alerts.get(alert, 0) + 1

        main_currency = "USD"
        if currencies:
            main_currency = max(currencies, key=lambda c: currencies[c]['budget'])

        return {
            'total_projects': total_projects,
            'active_projects': active_projects,
            'total_budget': total_budget,
            'total_actual': total_actual,
            'total_remaining': total_budget - total_actual,
            'currency': main_currency,
            'by_status': by_status,
            'alerts': alerts,
            'by_currency': {
                c: {'budget': v['budget'], 'actual': v['actual']}
                for c, v in currencies.items()
            },
        }


__all__ = ["PostgresProjectRepository"]