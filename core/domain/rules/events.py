# core/domain/rules/events.py
"""
Accounting Rules Events - أحداث مجال القواعد المحاسبية
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from core.domain.shared.value_objects import BaseDomainEvent
from .value_objects import RuleId, RuleCode, RuleType, RulePriority


def _aware_utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# أحداث القواعد
# =============================================================================

@dataclass(frozen=True)
class RuleCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء قاعدة جديدة"""
    rule_id: RuleId
    rule_code: RuleCode
    rule_name: str
    rule_type: RuleType
    created_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "rules.rule.created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "rule_id": str(self.rule_id),
            "rule_code": str(self.rule_code),
            "rule_name": self.rule_name,
            "rule_type": self.rule_type.value,
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class RuleUpdatedEvent(BaseDomainEvent):
    """يُرفع عند تحديث قاعدة"""
    rule_id: RuleId
    rule_code: RuleCode
    changes: Dict[str, Any]
    updated_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "rules.rule.updated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "rule_id": str(self.rule_id),
            "rule_code": str(self.rule_code),
            "changes": self.changes,
            "updated_by": self.updated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class RuleActivatedEvent(BaseDomainEvent):
    """يُرفع عند تفعيل قاعدة"""
    rule_id: RuleId
    rule_code: RuleCode
    activated_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "rules.rule.activated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "rule_id": str(self.rule_id),
            "rule_code": str(self.rule_code),
            "activated_by": self.activated_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class RuleDeactivatedEvent(BaseDomainEvent):
    """يُرفع عند تعطيل قاعدة"""
    rule_id: RuleId
    rule_code: RuleCode
    deactivated_by: str = "system"
    reason: Optional[str] = None
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "rules.rule.deactivated"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "rule_id": str(self.rule_id),
            "rule_code": str(self.rule_code),
            "deactivated_by": self.deactivated_by,
            "reason": self.reason,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class RuleExecutedEvent(BaseDomainEvent):
    """يُرفع عند تنفيذ قاعدة"""
    rule_id: RuleId
    rule_code: RuleCode
    rule_name: str
    entity_type: str
    entity_id: str
    success: bool
    journal_entry_id: Optional[str] = None
    executed_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "rules.rule.executed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "rule_id": str(self.rule_id),
            "rule_code": str(self.rule_code),
            "rule_name": self.rule_name,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "success": self.success,
            "journal_entry_id": self.journal_entry_id,
            "executed_by": self.executed_by,
            "occurred_at": self.occurred_at.isoformat()
        }


@dataclass(frozen=True)
class RuleExecutionFailedEvent(BaseDomainEvent):
    """يُرفع عند فشل تنفيذ قاعدة"""
    rule_id: RuleId
    rule_code: RuleCode
    rule_name: str
    entity_type: str
    entity_id: str
    errors: List[str]
    executed_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "rules.rule.execution_failed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "rule_id": str(self.rule_id),
            "rule_code": str(self.rule_code),
            "rule_name": self.rule_name,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "errors": self.errors,
            "executed_by": self.executed_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# أحداث مجموعات القواعد
# =============================================================================

@dataclass(frozen=True)
class RuleGroupCreatedEvent(BaseDomainEvent):
    """يُرفع عند إنشاء مجموعة قواعد جديدة"""
    group_id: str
    group_code: str
    group_name: str
    rule_count: int
    created_by: str = "system"
    occurred_at: datetime = field(default_factory=_aware_utc_now)

    def get_event_name(self) -> str:
        return "rules.group.created"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.get_event_name(),
            "group_id": self.group_id,
            "group_code": self.group_code,
            "group_name": self.group_name,
            "rule_count": self.rule_count,
            "created_by": self.created_by,
            "occurred_at": self.occurred_at.isoformat()
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'RuleCreatedEvent',
    'RuleUpdatedEvent',
    'RuleActivatedEvent',
    'RuleDeactivatedEvent',
    'RuleExecutedEvent',
    'RuleExecutionFailedEvent',
    'RuleGroupCreatedEvent',
]