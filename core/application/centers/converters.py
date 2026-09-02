# core/application/centers/converters.py
"""
Cost & Profit Centers Converters - محولات مراكز التكلفة والربح
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal

from core.domain.centers.entities import Center, CenterAllocation
from core.domain.centers.value_objects import (
    CenterType, CenterStatus, CenterBudget,
    AllocationRule, AllocationMethod, AllocationFrequency
)

from .dtos import (
    CenterDTO,
    CenterSummaryDTO,
    CenterNodeDTO,
    AllocationDTO,
    AllocationRuleDTO
)


# =============================================================================
# دوال مساعدة
# =============================================================================

def _safe_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return Decimal('0')


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, 'value'):
        return str(value.value)
    return str(value)


# =============================================================================
# Center Converters
# =============================================================================

def center_to_dto(center: Center) -> CenterDTO:
    """تحويل Center إلى DTO"""
    if not center:
        return None

    budget = center.budget

    return CenterDTO(
        id=_safe_str(center.id),
        code=_safe_str(center.code),
        name=center.name,
        center_type=center.center_type.value,
        status=center.status.value,
        parent_code=center.parent_code,
        level=center.level,
        path=center.path,
        manager_id=center.manager_id,
        manager_name=center.manager_name,
        department=center.department,
        budget_total=budget.total_budget if budget else Decimal('0'),
        budget_used=budget.used_amount if budget else Decimal('0'),
        budget_remaining=budget.remaining if budget else Decimal('0'),
        budget_currency=budget.currency if budget else "USD",
        budget_utilization=budget.utilization_percent if budget else Decimal('0'),
        is_over_budget=budget.is_over_budget if budget else False,
        description=center.description,
        notes=center.notes,
        tags=center.tags,
        created_at=center.created_at,
        created_by=center.created_by,
        updated_at=center.updated_at,
        updated_by=center.updated_by,
        version=center.version
    )


def center_to_summary_dto(center: Center, allocations: List[CenterAllocation]) -> CenterSummaryDTO:
    """تحويل Center و allocations إلى Summary DTO"""
    if not center:
        return None

    total_allocated = sum(a.total_amount for a in allocations if a.is_posted)

    return CenterSummaryDTO(
        center=center_to_dto(center),
        total_allocated=total_allocated,
        allocations_count=len(allocations),
        budget_utilization=center.budget.utilization_percent if center.budget else Decimal('0'),
        is_over_budget=center.is_over_budget
    )


def center_to_node_dto(center: Center, children: List[CenterNodeDTO] = None) -> CenterNodeDTO:
    """تحويل Center إلى Node DTO"""
    if not center:
        return None

    return CenterNodeDTO(
        id=_safe_str(center.id),
        code=_safe_str(center.code),
        name=center.name,
        center_type=center.center_type.value,
        status=center.status.value,
        level=center.level,
        children=children or [],
        budget_total=center.budget.total_budget if center.budget else Decimal('0'),
        budget_used=center.budget.used_amount if center.budget else Decimal('0'),
        budget_currency=center.budget.currency if center.budget else "USD"
    )


def centers_to_dto_list(centers: List[Center]) -> List[CenterDTO]:
    """تحويل قائمة Centers إلى DTOs"""
    if not centers:
        return []
    return [center_to_dto(c) for c in centers if c]


# =============================================================================
# Allocation Converters
# =============================================================================

def allocation_to_dto(allocation: CenterAllocation) -> AllocationDTO:
    """تحويل Allocation إلى DTO"""
    if not allocation:
        return None

    return AllocationDTO(
        id=allocation.id,
        source_center_code=allocation.source_center_code,
        target_center_codes=list(allocation.allocations.keys()),
        total_amount=allocation.total_amount,
        allocations=allocation.allocations,
        period_start=allocation.period_start,
        period_end=allocation.period_end,
        status=allocation.status,
        journal_entry_id=allocation.journal_entry_id,
        description=allocation.description,
        created_at=allocation.created_at,
        created_by=allocation.created_by,
        posted_at=allocation.posted_at,
        posted_by=allocation.posted_by
    )


def allocations_to_dto_list(allocations: List[CenterAllocation]) -> List[AllocationDTO]:
    """تحويل قائمة Allocations إلى DTOs"""
    if not allocations:
        return []
    return [allocation_to_dto(a) for a in allocations if a]


# =============================================================================
# Allocation Rule Converters
# =============================================================================

def allocation_rule_to_dto(rule: AllocationRule) -> AllocationRuleDTO:
    """تحويل AllocationRule إلى DTO"""
    if not rule:
        return None

    return AllocationRuleDTO(
        id=rule.id,
        name=rule.name,
        source_center_code=rule.source_center_code,
        target_center_codes=rule.target_center_codes,
        method=rule.method.value,
        percentage=rule.percentage,
        fixed_amount=rule.fixed_amount,
        weights=rule.weights,
        frequency=rule.frequency.value,
        is_active=rule.is_active,
        valid_from=rule.valid_from,
        valid_to=rule.valid_to,
        description=rule.description
    )


def allocation_rules_to_dto_list(rules: List[AllocationRule]) -> List[AllocationRuleDTO]:
    """تحويل قائمة AllocationRules إلى DTOs"""
    if not rules:
        return []
    return [allocation_rule_to_dto(r) for r in rules if r]


# =============================================================================
# دوال إضافية
# =============================================================================

def center_to_dict(center: Center) -> Dict[str, Any]:
    """تحويل Center إلى قاموس (للاستخدام في API)"""
    if not center:
        return {}

    return {
        'id': _safe_str(center.id),
        'code': _safe_str(center.code),
        'name': center.name,
        'type': center.center_type.value,
        'status': center.status.value,
        'parent_code': center.parent_code,
        'level': center.level,
        'path': center.path,
        'manager_id': center.manager_id,
        'manager_name': center.manager_name,
        'department': center.department,
        'budget': {
            'total': float(center.budget.total_budget) if center.budget else 0,
            'used': float(center.budget.used_amount) if center.budget else 0,
            'remaining': float(center.budget.remaining) if center.budget else 0,
            'currency': center.budget.currency if center.budget else 'USD',
            'utilization': float(center.budget.utilization_percent) if center.budget else 0
        } if center.budget else None,
        'description': center.description,
        'notes': center.notes,
        'tags': center.tags,
        'created_at': center.created_at.isoformat() if center.created_at else None,
        'created_by': center.created_by,
        'updated_at': center.updated_at.isoformat() if center.updated_at else None,
        'updated_by': center.updated_by,
        'version': center.version
    }


__all__ = [
    # Center
    'center_to_dto',
    'center_to_summary_dto',
    'center_to_node_dto',
    'centers_to_dto_list',
    'center_to_dict',
    
    # Allocation
    'allocation_to_dto',
    'allocations_to_dto_list',
    
    # Allocation Rule
    'allocation_rule_to_dto',
    'allocation_rules_to_dto_list',
]