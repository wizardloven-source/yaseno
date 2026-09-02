# domain/centers/value_objects.py (ملف جديد)
"""Cost & Profit Centers Value Objects"""

from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4
from datetime import date, datetime  # ✅ أضف هذا السطر


class CenterType(Enum):
    COST = "cost"
    PROFIT = "profit"
    BOTH = "both"


class CenterStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    ARCHIVED = "archived"


class AllocationMethod(Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    MANUAL = "manual"
    EQUAL = "equal"
    WEIGHTED = "weighted"
    ACTIVITY_BASED = "activity_based"


class AllocationFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONE_TIME = "one_time"


@dataclass(frozen=True)
class CenterId:
    value: UUID
    
    def __post_init__(self):
        if isinstance(self.value, str):
            object.__setattr__(self, 'value', UUID(self.value))
    
    @classmethod
    def generate(cls) -> 'CenterId':
        return cls(uuid4())
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class CenterCode:
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Center code cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CenterBudget:
    total_budget: Decimal
    used_amount: Decimal = Decimal('0')
    currency: str = "USD"
    
    def __post_init__(self):
        if self.total_budget < 0:
            raise ValueError("Budget cannot be negative")
        if self.used_amount < 0:
            raise ValueError("Used amount cannot be negative")
        if self.used_amount > self.total_budget:
            raise ValueError("Used amount cannot exceed total budget")
    
    @property
    def remaining(self) -> Decimal:
        return self.total_budget - self.used_amount
    
    @property
    def utilization_percent(self) -> Decimal:
        if self.total_budget == 0:
            return Decimal('0')
        return (self.used_amount / self.total_budget) * 100
    
    @property
    def is_over_budget(self) -> bool:
        return self.used_amount > self.total_budget


@dataclass(frozen=True)
class CenterHierarchy:
    """تسلسل هرمي للمراكز"""
    code: str
    name: str
    level: int
    children: list = None
    
    def __post_init__(self):
        if self.children is None:
            object.__setattr__(self, 'children', [])
    
    def add_child(self, child: 'CenterHierarchy') -> None:
        self.children.append(child)
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'level': self.level,
            'children': [c.to_dict() for c in self.children]
        }


@dataclass(frozen=True)
class AllocationRule:
    """قاعدة توزيع المصروفات"""
    id: str
    name: str
    source_center_code: str
    target_center_codes: list
    method: AllocationMethod
    percentage: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    weights: Optional[dict] = None
    frequency: AllocationFrequency = AllocationFrequency.MONTHLY
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.method == AllocationMethod.PERCENTAGE and self.percentage is None:
            raise ValueError("Percentage method requires percentage value")
        if self.method == AllocationMethod.FIXED_AMOUNT and self.fixed_amount is None:
            raise ValueError("Fixed amount method requires fixed_amount value")
        if self.method == AllocationMethod.WEIGHTED and not self.weights:
            raise ValueError("Weighted method requires weights dictionary")
    
    @property
    def is_active(self) -> bool:
        if not self.valid_to:
            return True
        return datetime.now(timezone.utc) <= self.valid_to
    
    @property
    def total_targets(self) -> int:
        return len(self.target_center_codes)