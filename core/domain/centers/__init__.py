# core/domain/centers/__init__.py
"""
Cost & Profit Centers Domain - مراكز التكلفة والربح

نظام متكامل لإدارة مراكز التكلفة والربح مع:
- تسلسل هرمي للمراكز
- ميزانيات
- توزيع المصروفات
- قواعد توزيع آلية
- تكامل مع المحاسبة
"""

from .entities import Center, CenterAllocation
from .value_objects import (
    CenterId, CenterCode, CenterType, CenterStatus,
    CenterBudget, CenterHierarchy,
    AllocationRule, AllocationMethod, AllocationFrequency
)
from .events import (
    CenterCreatedEvent,
    CenterUpdatedEvent,
    CenterActivatedEvent,
    CenterSuspendedEvent,
    CenterClosedEvent,
    CenterArchivedEvent,
    CenterBudgetUpdatedEvent,
    CenterBudgetExceededEvent,
    AllocationPostedEvent,
    AllocationCancelledEvent
)
from .interfaces import (
    ICenterRepository,
    IAllocationRepository,
    IAllocationRuleRepository
)
from .services import CenterService

__all__ = [
    # Entities
    "Center",
    "CenterAllocation",
    
    # Value Objects
    "CenterId",
    "CenterCode",
    "CenterType",
    "CenterStatus",
    "CenterBudget",
    "CenterHierarchy",
    "AllocationRule",
    "AllocationMethod",
    "AllocationFrequency",
    
    # Events
    "CenterCreatedEvent",
    "CenterUpdatedEvent",
    "CenterActivatedEvent",
    "CenterSuspendedEvent",
    "CenterClosedEvent",
    "CenterArchivedEvent",
    "CenterBudgetUpdatedEvent",
    "CenterBudgetExceededEvent",
    "AllocationPostedEvent",
    "AllocationCancelledEvent",
    
    # Interfaces
    "ICenterRepository",
    "IAllocationRepository",
    "IAllocationRuleRepository",
    
    # Services
    "CenterService",
]