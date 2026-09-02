# core/domain/customer_branch/events.py
"""
Customer Branch Events - أحداث المجال المستقلة
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from .value_objects import BranchId, BranchCode


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# أحداث الإنشاء والتحديث والحذف
# =============================================================================

@dataclass(frozen=True)
class BranchCreatedEvent:
    """يُرفع عند إنشاء فرع جديد"""
    branch_id: BranchId
    branch_code: BranchCode
    branch_name: str
    customer_id: str
    customer_name: str
    created_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "customer_branch.created"


@dataclass(frozen=True)
class BranchUpdatedEvent:
    """يُرفع عند تحديث فرع"""
    branch_id: BranchId
    changes: Dict[str, Any]
    updated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "customer_branch.updated"


@dataclass(frozen=True)
class BranchDeletedEvent:
    """يُرفع عند حذف فرع"""
    branch_id: BranchId
    branch_code: BranchCode
    branch_name: str
    deleted_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "customer_branch.deleted"


# =============================================================================
# أحداث تغيير الحالة
# =============================================================================

@dataclass(frozen=True)
class BranchActivatedEvent:
    """يُرفع عند تنشيط فرع"""
    branch_id: BranchId
    branch_code: BranchCode
    branch_name: str
    activated_by: str
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "customer_branch.activated"


@dataclass(frozen=True)
class BranchDeactivatedEvent:
    """يُرفع عند تعطيل فرع"""
    branch_id: BranchId
    branch_code: BranchCode
    branch_name: str
    deactivated_by: str
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)
    
    def get_event_name(self) -> str:
        return "customer_branch.deactivated"