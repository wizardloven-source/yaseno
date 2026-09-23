# core/domain/projects/entities.py (ملف جديد)
"""Projects Entities - كيانات المشاريع"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from .value_objects import (
    ProjectId,
    ProjectCode,
    ProjectStatus,
    ProjectBudgetAlert,
    ALLOWED_STATUS_TRANSITIONS,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Project:
    """مشروع - متوافق مع جدول projects في قاعدة البيانات"""

    id: ProjectId = field(default_factory=ProjectId.generate)
    code: ProjectCode = field(default_factory=lambda: ProjectCode(""))
    name: str = ""
    description: Optional[str] = None

    # العميل / المسؤول
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None

    # الميزانية والمصروفات
    budget_amount: Decimal = Decimal('0')
    budget_currency: str = "USD"
    actual_amount: Decimal = Decimal('0')
    remaining_amount: Decimal = Decimal('0')

    # التواريخ
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None

    # الحالة
    status: ProjectStatus = ProjectStatus.PLANNING

    # الصندوق المرتبط
    associated_fund_id: Optional[UUID] = None

    # إعدادات التنبيه
    alert_threshold_percent: int = 85
    critical_threshold_percent: int = 95
    auto_close_on_budget_exceed: bool = False

    # بيانات إضافية
    tags: List[str] = field(default_factory=list)
    project_metadata: Dict[str, Any] = field(default_factory=dict)

    # بيانات التدقيق
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    version: int = 1

    _events: List[Any] = field(default_factory=list, repr=False)

    # =========================================================================
    # خصائص حسابية
    # =========================================================================

    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"

    @property
    def is_active(self) -> bool:
        return self.status == ProjectStatus.ACTIVE

    @property
    def budget_utilization_percent(self) -> Decimal:
        if self.budget_amount <= 0:
            return Decimal('0')
        return (self.actual_amount / self.budget_amount) * Decimal('100')

    @property
    def is_over_budget(self) -> bool:
        return self.actual_amount > self.budget_amount

    @property
    def budget_alert(self) -> ProjectBudgetAlert:
        if self.budget_amount <= 0:
            return ProjectBudgetAlert.NONE
        utilization = self.budget_utilization_percent
        if self.is_over_budget:
            return ProjectBudgetAlert.OVER
        if utilization >= self.critical_threshold_percent:
            return ProjectBudgetAlert.CRITICAL
        if utilization >= self.alert_threshold_percent:
            return ProjectBudgetAlert.WARNING
        return ProjectBudgetAlert.NONE

    # =========================================================================
    # إنشاء وتحديث
    # =========================================================================

    @classmethod
    def create(
        cls,
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
    ) -> 'Project':
        budget = Decimal(budget_amount) if budget_amount is not None else Decimal('0')
        if budget < 0:
            raise ValueError("Budget cannot be negative")

        project = cls(
            code=ProjectCode(code),
            name=name,
            description=description,
            customer_id=customer_id,
            customer_name=customer_name,
            manager_id=manager_id,
            manager_name=manager_name,
            budget_amount=budget,
            budget_currency=budget_currency,
            actual_amount=Decimal('0'),
            remaining_amount=budget,
            start_date=start_date,
            end_date=end_date,
            status=status,
            tags=list(tags or []),
            created_by=created_by,
            updated_by=created_by,
        )

        from .events import ProjectCreatedEvent
        project._events.append(ProjectCreatedEvent(
            project_id=project.id,
            project_code=project.code,
            project_name=project.name,
            created_by=created_by,
        ))

        return project

    def update(
        self,
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
    ) -> None:
        changes = {}

        if name and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name

        if description is not None and description != self.description:
            changes['description'] = {'old': self.description, 'new': description}
            self.description = description

        if customer_id is not None and customer_id != self.customer_id:
            changes['customer_id'] = {'old': self.customer_id, 'new': customer_id}
            self.customer_id = customer_id

        if customer_name is not None and customer_name != self.customer_name:
            changes['customer_name'] = {'old': self.customer_name, 'new': customer_name}
            self.customer_name = customer_name

        if manager_id is not None and manager_id != self.manager_id:
            changes['manager_id'] = {'old': self.manager_id, 'new': manager_id}
            self.manager_id = manager_id

        if manager_name is not None and manager_name != self.manager_name:
            changes['manager_name'] = {'old': self.manager_name, 'new': manager_name}
            self.manager_name = manager_name

        if start_date is not None and start_date != self.start_date:
            changes['start_date'] = {'old': self.start_date, 'new': start_date}
            self.start_date = start_date

        if end_date is not None and end_date != self.end_date:
            changes['end_date'] = {'old': self.end_date, 'new': end_date}
            self.end_date = end_date

        if tags is not None and tags != self.tags:
            changes['tags'] = {'old': self.tags, 'new': tags}
            self.tags = list(tags)

        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            self.version += 1

            from .events import ProjectUpdatedEvent
            self._events.append(ProjectUpdatedEvent(
                project_id=self.id,
                changes=changes,
                updated_by=updated_by,
            ))

    # =========================================================================
    # الميزانية والمصروفات (ديناميكية)
    # =========================================================================

    def set_budget(self, budget_amount: Decimal, currency: str, set_by: str = "system") -> None:
        """تعيين ميزانية جديدة وإعادة حساب المتبقي فوراً"""
        new_budget = Decimal(budget_amount)
        if new_budget < 0:
            raise ValueError("Budget cannot be negative")

        old_budget = self.budget_amount
        self.budget_amount = new_budget
        self.budget_currency = currency
        self.remaining_amount = new_budget - self.actual_amount
        self.updated_at = utc_now()
        self.updated_by = set_by
        self.version += 1

        from .events import ProjectBudgetUpdatedEvent
        self._events.append(ProjectBudgetUpdatedEvent(
            project_id=self.id,
            project_code=self.code,
            project_name=self.name,
            old_budget=old_budget,
            new_budget=new_budget,
            currency=currency,
            updated_by=set_by,
        ))

    def record_expense(
        self,
        amount: Decimal,
        notes: Optional[str] = None,
        recorded_by: str = "system",
        reference: Optional[str] = None,
    ) -> ProjectBudgetAlert:
        """تسجيل مصروف فعلي وتحديث المتبقي ديناميكياً"""
        expense = Decimal(amount)
        if expense < 0:
            raise ValueError("Expense amount cannot be negative")

        old_actual = self.actual_amount
        self.actual_amount = old_actual + expense
        self.remaining_amount = self.budget_amount - self.actual_amount
        self.updated_at = utc_now()
        self.updated_by = recorded_by
        self.version += 1

        # تسجيل المصروف في السجل الداخلي (project_metadata)
        expense_log = self.project_metadata.get('expense_log') or []
        expense_log.append({
            'amount': str(expense),
            'balance_before': str(old_actual),
            'balance_after': str(self.actual_amount),
            'recorded_at': utc_now().isoformat(),
            'recorded_by': recorded_by,
            'notes': notes,
            'reference': reference,
        })
        self.project_metadata['expense_log'] = expense_log

        from .events import ProjectExpenseRecordedEvent
        self._events.append(ProjectExpenseRecordedEvent(
            project_id=self.id,
            project_code=self.code,
            project_name=self.name,
            amount=expense,
            balance_before=old_actual,
            balance_after=self.actual_amount,
            recorded_by=recorded_by,
            notes=notes,
        ))

        alert = self.budget_alert

        # إصدار حدث تنبيه عند الوصول لعتبة الميزانية
        if alert != ProjectBudgetAlert.NONE:
            from .events import ProjectBudgetAlertEvent
            self._events.append(ProjectBudgetAlertEvent(
                project_id=self.id,
                project_code=self.code,
                project_name=self.name,
                alert_level=alert,
                budget_limit=self.budget_amount,
                actual_usage=self.actual_amount,
                remaining=self.remaining_amount,
                utilization=self.budget_utilization_percent,
            ))

        # إغلاق تلقائي عند تجاوز الميزانية إذا كان مفعلاً
        if self.auto_close_on_budget_exceed and self.is_over_budget and self.status in (ProjectStatus.PLANNING, ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD):
            self.change_status(ProjectStatus.COMPLETED, "auto_close", recorded_by)

        return alert

    # =========================================================================
    # الحالة
    # =========================================================================

    def change_status(self, new_status: ProjectStatus, reason: Optional[str] = None, changed_by: str = "system") -> None:
        """تغيير حالة المشروع مع التحقق من الانتقال المسموح"""
        if not isinstance(new_status, ProjectStatus):
            new_status = ProjectStatus(new_status)

        if new_status == self.status:
            return

        allowed = ALLOWED_STATUS_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid status transition: {self.status.value} -> {new_status.value}"
            )

        old_status = self.status
        self.status = new_status
        self.updated_at = utc_now()
        self.updated_by = changed_by
        self.version += 1

        # عند الإكمال أو الإلغاء تسجيل تاريخ الإنهاء الفعلي
        if new_status in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
            self.actual_end_date = utc_now()

        from .events import ProjectStatusChangedEvent
        self._events.append(ProjectStatusChangedEvent(
            project_id=self.id,
            project_code=self.code,
            project_name=self.name,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            changed_by=changed_by,
        ))

    # =========================================================================
    # الأحداث
    # =========================================================================

    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events

    def add_event(self, event: Any) -> None:
        self._events.append(event)