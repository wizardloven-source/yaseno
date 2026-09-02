# domain/centers/entities.py (ملف جديد)
"""Cost & Profit Centers Entities - كيانات مراكز التكلفة والربح"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from .value_objects import (
    CenterId, CenterCode, CenterType, CenterStatus,
    CenterBudget, CenterHierarchy
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Center:
    """مركز تكلفة أو ربح"""
    
    id: CenterId = field(default_factory=CenterId.generate)
    code: CenterCode = field(default_factory=lambda: CenterCode(""))
    name: str = ""
    center_type: CenterType = CenterType.COST
    status: CenterStatus = CenterStatus.DRAFT
    
    parent_code: Optional[str] = None
    level: int = 0
    path: str = ""
    
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    department: Optional[str] = None
    
    budget: Optional[CenterBudget] = None
    
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"
    
    @property
    def is_active(self) -> bool:
        return self.status == CenterStatus.ACTIVE
    
    @property
    def is_over_budget(self) -> bool:
        if not self.budget:
            return False
        return self.budget.is_over_budget
    
    @property
    def budget_utilization(self) -> Decimal:
        if not self.budget:
            return Decimal('0')
        return self.budget.utilization_percent
    
    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        center_type: CenterType,
        parent_code: Optional[str] = None,
        manager_id: Optional[str] = None,
        manager_name: Optional[str] = None,
        department: Optional[str] = None,
        budget: Optional[CenterBudget] = None,
        description: Optional[str] = None,
        created_by: str = "system"
    ) -> 'Center':
        center = cls(
            code=CenterCode(code),
            name=name,
            center_type=center_type,
            parent_code=parent_code,
            manager_id=manager_id,
            manager_name=manager_name,
            department=department,
            budget=budget,
            description=description,
            created_by=created_by,
            updated_by=created_by
        )
        
        # حساب المستوى والمسار
        if parent_code:
            center.level = 1  # سيتم تحديثه من الخدمة
            center.path = parent_code
        
        from .events import CenterCreatedEvent
        center._events.append(CenterCreatedEvent(
            center_id=center.id,
            center_code=center.code,
            center_name=center.name,
            center_type=center.center_type,
            created_by=created_by
        ))
        
        return center
    
    def update(
        self,
        name: Optional[str] = None,
        center_type: Optional[CenterType] = None,
        parent_code: Optional[str] = None,
        manager_id: Optional[str] = None,
        manager_name: Optional[str] = None,
        department: Optional[str] = None,
        budget: Optional[CenterBudget] = None,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        tags: Optional[List[str]] = None,
        updated_by: str = "system"
    ) -> None:
        changes = {}
        
        if name and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name
        
        if center_type and center_type != self.center_type:
            changes['center_type'] = {'old': self.center_type.value, 'new': center_type.value}
            self.center_type = center_type
        
        if parent_code is not None and parent_code != self.parent_code:
            changes['parent_code'] = {'old': self.parent_code, 'new': parent_code}
            self.parent_code = parent_code
        
        if manager_id is not None and manager_id != self.manager_id:
            changes['manager_id'] = {'old': self.manager_id, 'new': manager_id}
            self.manager_id = manager_id
        
        if manager_name is not None and manager_name != self.manager_name:
            changes['manager_name'] = {'old': self.manager_name, 'new': manager_name}
            self.manager_name = manager_name
        
        if department is not None and department != self.department:
            changes['department'] = {'old': self.department, 'new': department}
            self.department = department
        
        if budget is not None and budget != self.budget:
            changes['budget'] = {'old': self.budget, 'new': budget}
            self.budget = budget
        
        if description is not None and description != self.description:
            changes['description'] = {'old': self.description, 'new': description}
            self.description = description
        
        if notes is not None and notes != self.notes:
            changes['notes'] = {'old': self.notes, 'new': notes}
            self.notes = notes
        
        if tags is not None and tags != self.tags:
            changes['tags'] = {'old': self.tags, 'new': tags}
            self.tags = tags
        
        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            self.version += 1
            
            from .events import CenterUpdatedEvent
            self._events.append(CenterUpdatedEvent(
                center_id=self.id,
                changes=changes,
                updated_by=updated_by
            ))
    
    def activate(self, activated_by: str) -> None:
        if self.is_active:
            return
        
        old_status = self.status
        self.status = CenterStatus.ACTIVE
        self.updated_at = utc_now()
        self.updated_by = activated_by
        self.version += 1
        
        from .events import CenterActivatedEvent
        self._events.append(CenterActivatedEvent(
            center_id=self.id,
            center_code=self.code,
            center_name=self.name,
            activated_by=activated_by
        ))
    
    def suspend(self, suspended_by: str, reason: Optional[str] = None) -> None:
        if self.status == CenterStatus.SUSPENDED:
            return
        
        old_status = self.status
        self.status = CenterStatus.SUSPENDED
        self.updated_at = utc_now()
        self.updated_by = suspended_by
        self.version += 1
        
        from .events import CenterSuspendedEvent
        self._events.append(CenterSuspendedEvent(
            center_id=self.id,
            center_code=self.code,
            center_name=self.name,
            suspended_by=suspended_by,
            reason=reason
        ))
    
    def close(self, closed_by: str, reason: Optional[str] = None) -> None:
        if self.status == CenterStatus.CLOSED:
            return
        
        old_status = self.status
        self.status = CenterStatus.CLOSED
        self.updated_at = utc_now()
        self.updated_by = closed_by
        self.version += 1
        
        from .events import CenterClosedEvent
        self._events.append(CenterClosedEvent(
            center_id=self.id,
            center_code=self.code,
            center_name=self.name,
            closed_by=closed_by,
            reason=reason
        ))
    
    def archive(self, archived_by: str) -> None:
        if self.status == CenterStatus.ARCHIVED:
            return
        
        self.status = CenterStatus.ARCHIVED
        self.updated_at = utc_now()
        self.updated_by = archived_by
        self.version += 1
        
        from .events import CenterArchivedEvent
        self._events.append(CenterArchivedEvent(
            center_id=self.id,
            center_code=self.code,
            center_name=self.name,
            archived_by=archived_by
        ))
    
    def set_budget(self, total_budget: Decimal, currency: str) -> None:
        self.budget = CenterBudget(
            total_budget=total_budget,
            currency=currency
        )
        self.updated_at = utc_now()
        self.version += 1
    
    def update_budget_usage(self, amount: Decimal) -> None:
        if not self.budget:
            return
        
        self.budget = CenterBudget(
            total_budget=self.budget.total_budget,
            used_amount=self.budget.used_amount + amount,
            currency=self.budget.currency
        )
        self.updated_at = utc_now()
        self.version += 1
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events
    
    def add_event(self, event: Any) -> None:
        self._events.append(event)


@dataclass
class CenterAllocation:
    """توزيع مصروفات بين المراكز"""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    source_center_code: str = ""
    period_start: datetime = field(default_factory=utc_now)
    period_end: datetime = field(default_factory=utc_now)
    total_amount: Decimal = Decimal('0')
    allocations: Dict[str, Decimal] = field(default_factory=dict)
    status: str = "draft"  # draft, posted, cancelled
    journal_entry_id: Optional[str] = None
    description: Optional[str] = None
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def is_posted(self) -> bool:
        return self.status == "posted"
    
    @property
    def total_allocated(self) -> Decimal:
        return sum(self.allocations.values())
    
    @property
    def is_balanced(self) -> bool:
        return abs(self.total_amount - self.total_allocated) < Decimal('0.01')
    
    def post(self, posted_by: str, journal_entry_id: str) -> None:
        if self.is_posted:
            return
        
        self.status = "posted"
        self.posted_at = utc_now()
        self.posted_by = posted_by
        self.journal_entry_id = journal_entry_id
        
        from .events import AllocationPostedEvent
        self._events.append(AllocationPostedEvent(
            allocation_id=self.id,
            source_center=self.source_center_code,
            total_amount=self.total_amount,
            posted_by=posted_by,
            journal_entry_id=journal_entry_id
        ))
    
    def cancel(self, cancelled_by: str, reason: Optional[str] = None) -> None:
        if self.status == "cancelled":
            return
        
        self.status = "cancelled"
        
        from .events import AllocationCancelledEvent
        self._events.append(AllocationCancelledEvent(
            allocation_id=self.id,
            source_center=self.source_center_code,
            cancelled_by=cancelled_by,
            reason=reason
        ))
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events