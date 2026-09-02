# core/domain/customer_branch/__init__.py
"""
Customer Branch Domain - وحدة مستقلة لإدارة فروع العملاء
"""

from .entities import CustomerBranch
from .value_objects import (
    BranchId, BranchCode, BranchStatus,
    BranchAddress, BranchContact, BranchGeoLocation
)
from .events import (
    BranchCreatedEvent, BranchUpdatedEvent, BranchDeletedEvent,
    BranchActivatedEvent, BranchDeactivatedEvent
)
from .interfaces import ICustomerBranchRepository

__all__ = [
    # Entities
    "CustomerBranch",
    
    # Value Objects
    "BranchId",
    "BranchCode",
    "BranchStatus",
    "BranchAddress",
    "BranchContact",
    "BranchGeoLocation",
    
    # Events
    "BranchCreatedEvent",
    "BranchUpdatedEvent",
    "BranchDeletedEvent",
    "BranchActivatedEvent",
    "BranchDeactivatedEvent",
    
    # Interfaces
    "ICustomerBranchRepository",
]