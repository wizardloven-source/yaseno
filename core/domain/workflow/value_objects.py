# core/domain/workflow/value_objects.py - الإصدار المُصحَّح بالكامل

"""
Approval Workflow Value Objects - كائنات القيمة لسير عمل الموافقات
"""

from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4  # ✅ تأكد من استيراد uuid4


class WorkflowStatus(Enum):
    """حالة سير العمل"""
    DRAFT = "draft"              # مسودة
    ACTIVE = "active"            # نشط
    INACTIVE = "inactive"        # غير نشط
    ARCHIVED = "archived"        # مؤرشف


class RequestStatus(Enum):
    """حالة طلب الموافقة"""
    DRAFT = "draft"              # مسودة
    PENDING = "pending"          # قيد الانتظار
    IN_REVIEW = "in_review"      # قيد المراجعة
    APPROVED = "approved"        # تمت الموافقة
    REJECTED = "rejected"        # مرفوض
    CANCELLED = "cancelled"      # ملغي
    EXPIRED = "expired"          # منتهي الصلاحية


class ApprovalAction(Enum):
    """إجراء الموافقة"""
    APPROVE = "approve"          # موافقة
    REJECT = "reject"            # رفض
    REVISE = "revise"            # مراجعة
    DELEGATE = "delegate"        # تفويض
    ESCALATE = "escalate"        # تصعيد


class WorkflowEntityType(Enum):
    """نوع الكيان المرتبط بسير العمل"""
    INVOICE = "invoice"
    PAYMENT = "payment"
    JOURNAL_ENTRY = "journal_entry"
    PURCHASE_ORDER = "purchase_order"
    SALES_ORDER = "sales_order"
    EXPENSE = "expense"
    BUDGET = "budget"
    CONTRACT = "contract"
    USER = "user"
    CUSTOM = "custom"


@dataclass(frozen=True)
class WorkflowId:
    """معرف سير العمل"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("WorkflowId cannot be empty")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> 'WorkflowId':
        return cls(value)
    
    @classmethod
    def generate(cls) -> 'WorkflowId':
        """✅ توليد معرف جديد لسير العمل"""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class RequestId:
    """معرف طلب الموافقة"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("RequestId cannot be empty")

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> 'RequestId':
        return cls(value)
    
    @classmethod
    def generate(cls) -> 'RequestId':
        """✅ توليد معرف جديد لطلب الموافقة"""
        return cls(str(uuid4()))


@dataclass(frozen=True)
class ApprovalStep:
    """خطوة في سير العمل"""
    id: str
    name: str
    order: int
    role: str                      # الدور المطلوب للموافقة
    required_approvals: int = 1    # عدد الموافقات المطلوبة
    requires_all: bool = False     # هل يحتاج موافقة الجميع؟
    is_final: bool = False         # هل هي الخطوة الأخيرة؟
    timeout_hours: Optional[int] = None  # مهلة زمنية
    escalation_role: Optional[str] = None  # دور التصعيد
    description: Optional[str] = None

    def __post_init__(self):
        if self.required_approvals < 1:
            raise ValueError("Required approvals must be at least 1")


@dataclass(frozen=True)
class ApprovalRecord:
    """سجل الموافقة"""
    approver_id: str
    approver_name: str
    action: ApprovalAction
    comment: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    is_delegated: bool = False
    delegated_to: Optional[str] = None

    @property
    def is_approved(self) -> bool:
        return self.action == ApprovalAction.APPROVE

    @property
    def is_rejected(self) -> bool:
        return self.action == ApprovalAction.REJECT


@dataclass(frozen=True)
class RequestHistory:
    """سجل تاريخ الطلب"""
    id: str
    request_id: str
    action: str
    performed_by: str
    performed_by_name: str
    performed_at: datetime
    from_status: str
    to_status: str
    comment: Optional[str] = None
    details: Optional[Dict[str, Any]] = None