# core/application/centers/dtos.py
"""
Cost & Profit Centers DTOs - كائنات نقل البيانات لمراكز التكلفة والربح
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal


@dataclass
class CenterDTO:
    """مركز - DTO"""
    id: str
    code: str
    name: str
    center_type: str
    status: str
    parent_code: Optional[str] = None
    level: int = 0
    path: str = ""
    manager_id: Optional[str] = None
    manager_name: Optional[str] = None
    department: Optional[str] = None
    budget_total: Decimal = Decimal('0')
    budget_used: Decimal = Decimal('0')
    budget_remaining: Decimal = Decimal('0')
    budget_currency: str = "USD"
    budget_utilization: Decimal = Decimal('0')
    is_over_budget: bool = False
    description: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=datetime.now)
    updated_by: str = "system"
    version: int = 1
    
    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"
    
    @property
    def type_display(self) -> str:
        types = {
            "cost": "مركز تكلفة",
            "profit": "مركز ربح",
            "both": "مركز تكلفة وربح"
        }
        return types.get(self.center_type, self.center_type)
    
    @property
    def status_display(self) -> str:
        statuses = {
            "draft": "مسودة",
            "active": "نشط",
            "suspended": "معلق",
            "closed": "مغلق",
            "archived": "مؤرشف"
        }
        return statuses.get(self.status, self.status)
    
    @property
    def budget_formatted(self) -> str:
        return f"{self.budget_total:,.2f} {self.budget_currency}"
    
    @property
    def budget_used_formatted(self) -> str:
        return f"{self.budget_used:,.2f} {self.budget_currency}"
    
    @property
    def budget_remaining_formatted(self) -> str:
        return f"{self.budget_remaining:,.2f} {self.budget_currency}"


@dataclass
class CenterSummaryDTO:
    """ملخص مركز - DTO"""
    center: CenterDTO
    total_allocated: Decimal
    allocations_count: int
    budget_utilization: Decimal
    is_over_budget: bool
    
    @property
    def total_allocated_formatted(self) -> str:
        return f"{self.total_allocated:,.2f} {self.center.budget_currency}"


@dataclass
class CenterNodeDTO:
    """عقدة في الشجرة الهرمية - DTO"""
    id: str
    code: str
    name: str
    center_type: str
    status: str
    level: int
    children: List['CenterNodeDTO'] = field(default_factory=list)
    budget_total: Decimal = Decimal('0')
    budget_used: Decimal = Decimal('0')
    budget_currency: str = "USD"
    
    @property
    def display_name(self) -> str:
        indent = "  " * self.level
        return f"{indent}{self.code} - {self.name}"
    
    def add_child(self, child: 'CenterNodeDTO') -> None:
        self.children.append(child)


@dataclass
class AllocationDTO:
    """توزيع - DTO"""
    id: str
    source_center_code: str
    target_center_codes: List[str]
    total_amount: Decimal
    allocations: Dict[str, Decimal]
    period_start: date
    period_end: date
    status: str
    journal_entry_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None
    
    @property
    def is_posted(self) -> bool:
        return self.status == "posted"
    
    @property
    def period_display(self) -> str:
        return f"{self.period_start} - {self.period_end}"


# ✅ تم إعادة ترتيب الحقول: الإجبارية أولاً
@dataclass
class AllocationRuleDTO:
    """قاعدة توزيع - DTO"""
    # ========== الحقول الإجبارية (بدون قيم افتراضية) ==========
    id: str
    name: str
    source_center_code: str
    target_center_codes: List[str]
    method: str
    frequency: str          # ✅ أصبحت إجبارية (بدون قيمة افتراضية)
    is_active: bool         # ✅ أصبحت إجبارية (بدون قيمة افتراضية)
    
    # ========== الحقول الاختيارية (بقيم افتراضية) ==========
    percentage: Optional[Decimal] = None
    fixed_amount: Optional[Decimal] = None
    weights: Optional[Dict[str, Decimal]] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    description: Optional[str] = None
    
    @property
    def method_display(self) -> str:
        methods = {
            "percentage": "نسبة مئوية",
            "fixed_amount": "مبلغ ثابت",
            "manual": "يدوي",
            "equal": "بالتساوي",
            "weighted": "مرجح",
            "activity_based": "على أساس النشاط"
        }
        return methods.get(self.method, self.method)


# تحديث CenterNodeDTO للسماح بالمراجع الذاتية
CenterNodeDTO.children = field(default_factory=list)


__all__ = [
    "CenterDTO",
    "CenterSummaryDTO",
    "CenterNodeDTO",
    "AllocationDTO",
    "AllocationRuleDTO",
]