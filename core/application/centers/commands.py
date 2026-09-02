# core/application/centers/commands.py
"""
Cost & Profit Centers Commands - أوامر مراكز التكلفة والربح
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from core.domain.centers.value_objects import CenterType, CenterStatus, AllocationMethod


# =============================================================================
# COMMANDS - أوامر إدارة المراكز
# =============================================================================

@dataclass(frozen=True)
class CreateCenterCommand:
    """أمر إنشاء مركز جديد"""
    code: str
    name: str
    center_type: str  # cost, profit, both
    parent_code: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    department: Optional[str] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: str = "USD"
    description: Optional[str] = None
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateCenterCommand:
    """أمر تحديث مركز"""
    center_id: str
    version: int  # ✅ نقل version إلى الأعلى (إجباري)
    name: Optional[str] = None
    center_type: Optional[str] = None
    parent_code: Optional[str] = None
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    department: Optional[str] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class ActivateCenterCommand:
    """أمر تفعيل مركز"""
    center_id: str
    activated_by: str = "system"


@dataclass(frozen=True)
class SuspendCenterCommand:
    """أمر تعليق مركز"""
    center_id: str
    reason: Optional[str] = None
    suspended_by: str = "system"


@dataclass(frozen=True)
class CloseCenterCommand:
    """أمر إغلاق مركز"""
    center_id: str
    reason: Optional[str] = None
    closed_by: str = "system"


@dataclass(frozen=True)
class DeleteCenterCommand:
    """أمر حذف مركز"""
    center_id: str
    permanent: bool = False
    deleted_by: str = "system"


@dataclass(frozen=True)
class SetCenterBudgetCommand:
    """أمر تعيين ميزانية مركز"""
    center_id: str
    amount: Decimal
    currency: str = "USD"
    set_by: str = "system"


# =============================================================================
# COMMANDS - أوامر التوزيع
# =============================================================================

@dataclass(frozen=True)
class CreateAllocationCommand:
    """أمر إنشاء توزيع مصروفات"""
    source_center_code: str
    target_center_codes: List[str]
    amount: Decimal
    period_start: date
    period_end: date
    method: str = "equal"  # equal, percentage, fixed, weighted
    percentage: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    weights: Optional[Dict[str, Decimal]] = None
    description: Optional[str] = None
    created_by: str = "system"


@dataclass(frozen=True)
class PostAllocationCommand:
    """أمر ترحيل توزيع مصروفات"""
    allocation_id: str
    posted_by: str = "system"


@dataclass(frozen=True)
class CancelAllocationCommand:
    """أمر إلغاء توزيع مصروفات"""
    allocation_id: str
    reason: Optional[str] = None
    cancelled_by: str = "system"


@dataclass(frozen=True)
class CreateAllocationRuleCommand:
    """أمر إنشاء قاعدة توزيع"""
    # ✅ جميع المعاملات الإجبارية أولاً
    name: str
    source_center_code: str
    target_center_codes: List[str]
    method: str
    frequency: str  # ✅ نقل إلى الأعلى (إجباري)
    # ✅ المعاملات الاختيارية بعد ذلك
    percentage: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    weights: Optional[Dict[str, Decimal]] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    description: Optional[str] = None
    created_by: str = "system"


@dataclass(frozen=True)
class RunAllocationRuleCommand:
    """أمر تنفيذ قاعدة توزيع"""
    rule_id: str
    period_start: date
    period_end: date
    executed_by: str = "system"


# =============================================================================
# QUERIES - استعلامات المراكز
# =============================================================================

@dataclass(frozen=True)
class GetCenterQuery:
    """استعلام لجلب مركز"""
    center_id: str


@dataclass(frozen=True)
class GetCenterByCodeQuery:
    """استعلام لجلب مركز بالكود"""
    code: str


@dataclass(frozen=True)
class ListCentersQuery:
    """استعلام لقائمة المراكز"""
    center_type: Optional[str] = None
    status: Optional[str] = None
    parent_code: Optional[str] = None
    include_inactive: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetCenterTreeQuery:
    """استعلام للحصول على الشجرة الهرمية"""
    root_code: Optional[str] = None


@dataclass(frozen=True)
class GetCenterSummaryQuery:
    """استعلام للحصول على ملخص مركز"""
    center_code: str
    from_date: date
    to_date: date


@dataclass(frozen=True)
class SearchCentersQuery:
    """استعلام للبحث عن مراكز"""
    search_text: str
    limit: int = 50


@dataclass(frozen=True)
class ListAllocationsQuery:
    """استعلام لقائمة التوزيعات"""
    center_code: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    status: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class ListAllocationRulesQuery:
    """استعلام لقائمة قواعد التوزيع"""
    source_center_code: Optional[str] = None
    is_active: Optional[bool] = None
    limit: int = 100
    offset: int = 0


__all__ = [
    # Center Commands
    "CreateCenterCommand",
    "UpdateCenterCommand",
    "ActivateCenterCommand",
    "SuspendCenterCommand",
    "CloseCenterCommand",
    "DeleteCenterCommand",
    "SetCenterBudgetCommand",
    
    # Allocation Commands
    "CreateAllocationCommand",
    "PostAllocationCommand",
    "CancelAllocationCommand",
    "CreateAllocationRuleCommand",
    "RunAllocationRuleCommand",
    
    # Queries
    "GetCenterQuery",
    "GetCenterByCodeQuery",
    "ListCentersQuery",
    "GetCenterTreeQuery",
    "GetCenterSummaryQuery",
    "SearchCentersQuery",
    "ListAllocationsQuery",
    "ListAllocationRulesQuery",
]