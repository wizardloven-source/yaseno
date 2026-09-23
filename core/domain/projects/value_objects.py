# core/domain/projects/value_objects.py (ملف جديد)
"""Projects Value Objects - قيم كائنات المشاريع"""

from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from uuid import UUID, uuid4


class ProjectStatus(Enum):
    """حالات المشروع"""
    PLANNING = "planning"       # تخطيط
    ACTIVE = "active"           # نشط
    ON_HOLD = "on_hold"         # معلق
    COMPLETED = "completed"     # مكتمل
    CANCELLED = "cancelled"     # ملغي
    ARCHIVED = "archived"       # مؤرشف


class ProjectBudgetAlert(Enum):
    """مستويات التنبيه على الميزانية"""
    NONE = "none"
    WARNING = "warning"     # تجاوز عتبة التنبيه (الافتراضي 85%)
    CRITICAL = "critical"   # تجاوز العتبة الحرجة (الافتراضي 95%)
    OVER = "over"           # تجاوز الميزانية بالكامل


# التحويلات المسموح بها بين حالات المشروع
ALLOWED_STATUS_TRANSITIONS = {
    ProjectStatus.PLANNING: {ProjectStatus.ACTIVE, ProjectStatus.ON_HOLD, ProjectStatus.CANCELLED, ProjectStatus.ARCHIVED},
    ProjectStatus.ACTIVE: {ProjectStatus.ON_HOLD, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED, ProjectStatus.ARCHIVED},
    ProjectStatus.ON_HOLD: {ProjectStatus.ACTIVE, ProjectStatus.COMPLETED, ProjectStatus.CANCELLED, ProjectStatus.ARCHIVED},
    ProjectStatus.COMPLETED: {ProjectStatus.ARCHIVED, ProjectStatus.ACTIVE},
    ProjectStatus.CANCELLED: {ProjectStatus.ARCHIVED},
    ProjectStatus.ARCHIVED: set(),
}


@dataclass(frozen=True)
class ProjectId:
    """معرف المشروع"""
    value: UUID

    def __post_init__(self):
        if isinstance(self.value, str):
            object.__setattr__(self, 'value', UUID(self.value))

    @classmethod
    def generate(cls) -> 'ProjectId':
        return cls(uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class ProjectCode:
    """كود المشروع - مطلوب وفريد"""
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Project code cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value