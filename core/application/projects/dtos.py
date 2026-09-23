# core/application/projects/dtos.py (ملف جديد)
"""
Projects DTOs - كائنات نقل بيانات المشاريع
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


@dataclass
class ProjectDTO:
    """مشروع - DTO"""
    # الحقول الأساسية
    id: str
    code: str
    name: str
    status: str

    # بيانات اختيارية
    description: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None

    # الميزانية والمصروفات
    budget_amount: Decimal = Decimal('0')
    budget_currency: str = "USD"
    actual_amount: Decimal = Decimal('0')
    remaining_amount: Decimal = Decimal('0')
    budget_utilization_percent: Decimal = Decimal('0')
    budget_alert: str = "none"
    is_over_budget: bool = False

    # التواريخ
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    actual_end_date: Optional[datetime] = None

    # الصندوق المرتبط
    associated_fund_id: Optional[str] = None

    # إعدادات التنبيه
    alert_threshold_percent: int = 85
    critical_threshold_percent: int = 95
    auto_close_on_budget_exceed: bool = False

    # بيانات إضافية
    tags: List[str] = field(default_factory=list)
    project_metadata: Dict[str, Any] = field(default_factory=dict)

    # بيانات التدقيق
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    created_by: str = "system"
    updated_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_by: str = "system"
    version: int = 1

    # =========================================================================
    # خصائص العرض
    # =========================================================================

    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"

    @property
    def status_display(self) -> str:
        statuses = {
            "planning": "تخطيط",
            "active": "نشط",
            "on_hold": "معلق",
            "completed": "مكتمل",
            "cancelled": "ملغي",
            "archived": "مؤرشف",
        }
        return statuses.get(self.status, self.status)

    @property
    def alert_display(self) -> str:
        alerts = {
            "none": "ضمن الميزانية",
            "warning": "تنبيه",
            "critical": "حرج",
            "over": "تجاوز",
        }
        return alerts.get(self.budget_alert, self.budget_alert)

    @property
    def budget_formatted(self) -> str:
        return f"{self.budget_amount:,.2f} {self.budget_currency}"

    @property
    def actual_formatted(self) -> str:
        return f"{self.actual_amount:,.2f} {self.budget_currency}"

    @property
    def remaining_formatted(self) -> str:
        return f"{self.remaining_amount:,.2f} {self.budget_currency}"


@dataclass
class ProjectOverviewDTO:
    """إحصائيات عامة عن المشاريع - DTO"""
    total_projects: int = 0
    active_projects: int = 0
    total_budget: Decimal = Decimal('0')
    total_actual: Decimal = Decimal('0')
    total_remaining: Decimal = Decimal('0')
    currency: str = "USD"
    by_status: Dict[str, int] = field(default_factory=dict)
    alerts: Dict[str, int] = field(default_factory=dict)


__all__ = ["ProjectDTO", "ProjectOverviewDTO"]