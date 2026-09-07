"""
CRM Domain Events

أحداث النطاق لربط وحدة CRM مع الوحدات الأخرى
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class DomainEvent:
    """حدث نطاق أساسي"""
    event_id: str = field(default_factory=lambda: str(id(self)))
    occurred_on: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: Optional[str] = None
    aggregate_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "occurred_on": self.occurred_on.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_type": self.__class__.__name__
        }


# ============================================================================
# Lead Events
# ============================================================================

@dataclass
class LeadCreatedEvent(DomainEvent):
    """تم إنشاء عميل محتمل جديد"""
    lead_id: str = ""
    first_name: str = ""
    last_name: str = ""
    company_name: Optional[str] = None
    source: str = ""
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.lead_id
        self.aggregate_type = "Lead"


@dataclass
class LeadContactedEvent(DomainEvent):
    """تم التواصل مع عميل محتمل"""
    lead_id: str = ""
    contact_method: str = ""
    contacted_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.lead_id
        self.aggregate_type = "Lead"


@dataclass
class LeadQualifiedEvent(DomainEvent):
    """تم تأهيل عميل محتمل"""
    lead_id: str = ""
    opportunity_id: str = ""
    expected_value: float = 0.0
    qualified_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.lead_id
        self.aggregate_type = "Lead"


@dataclass
class LeadConvertedEvent(DomainEvent):
    """تم تحويل عميل محتمل إلى عميل"""
    lead_id: str = ""
    customer_id: str = ""
    converted_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.lead_id
        self.aggregate_type = "Lead"


@dataclass
class LeadLostEvent(DomainEvent):
    """فقدان عميل محتمل"""
    lead_id: str = ""
    reason: str = ""
    lost_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.lead_id
        self.aggregate_type = "Lead"


# ============================================================================
# Opportunity Events
# ============================================================================

@dataclass
class OpportunityCreatedEvent(DomainEvent):
    """تم إنشاء فرصة بيعية جديدة"""
    opportunity_id: str = ""
    name: str = ""
    stage: str = ""
    expected_value: float = 0.0
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.opportunity_id
        self.aggregate_type = "Opportunity"


@dataclass
class OpportunityStageChangedEvent(DomainEvent):
    """تم تغيير مرحلة الفرصة"""
    opportunity_id: str = ""
    old_stage: str = ""
    new_stage: str = ""
    changed_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.opportunity_id
        self.aggregate_type = "Opportunity"


@dataclass
class OpportunityClosedWonEvent(DomainEvent):
    """تم إغلاق الفرصة كـ مكسوبة"""
    opportunity_id: str = ""
    closed_at: datetime = field(default_factory=datetime.utcnow)
    won_reason: str = ""
    closed_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.opportunity_id
        self.aggregate_type = "Opportunity"


@dataclass
class OpportunityClosedLostEvent(DomainEvent):
    """تم إغلاق الفرصة كـ خاسرة"""
    opportunity_id: str = ""
    closed_at: datetime = field(default_factory=datetime.utcnow)
    lost_reason: str = ""
    closed_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.opportunity_id
        self.aggregate_type = "Opportunity"


@dataclass
class OpportunityQuoteAddedEvent(DomainEvent):
    """تم إضافة عرض سعر للفرصة"""
    opportunity_id: str = ""
    quote_id: str = ""
    added_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.opportunity_id
        self.aggregate_type = "Opportunity"


@dataclass
class OpportunityOrderAddedEvent(DomainEvent):
    """تم إضافة أمر بيع للفرصة"""
    opportunity_id: str = ""
    order_id: str = ""
    added_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.opportunity_id
        self.aggregate_type = "Opportunity"


# ============================================================================
# Activity Events
# ============================================================================

@dataclass
class ActivityCreatedEvent(DomainEvent):
    """تم إنشاء نشاط جديد"""
    activity_id: str = ""
    activity_type: str = ""
    subject: str = ""
    related_to: Optional[str] = None
    related_id: Optional[str] = None
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.activity_id
        self.aggregate_type = "Activity"


@dataclass
class ActivityCompletedEvent(DomainEvent):
    """تم إكمال نشاط"""
    activity_id: str = ""
    completed_at: datetime = field(default_factory=datetime.utcnow)
    completed_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.activity_id
        self.aggregate_type = "Activity"


# ============================================================================
# Task Events
# ============================================================================

@dataclass
class TaskCreatedEvent(DomainEvent):
    """تم إنشاء مهمة جديدة"""
    task_id: str = ""
    title: str = ""
    priority: str = ""
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.task_id
        self.aggregate_type = "Task"


@dataclass
class TaskCompletedEvent(DomainEvent):
    """تم إكمال مهمة"""
    task_id: str = ""
    completed_at: datetime = field(default_factory=datetime.utcnow)
    completed_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.task_id
        self.aggregate_type = "Task"


# ============================================================================
# Integration Events (للربط مع الوحدات الأخرى)
# ============================================================================

@dataclass
class CustomerCreatedFromLeadEvent(DomainEvent):
    """
    حدث لإنشاء عميل من Lead
    يُستخدم للتكامل مع وحدة العملاء
    """
    lead_id: str = ""
    customer_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.aggregate_id = self.lead_id
        self.aggregate_type = "Lead"


@dataclass
class QuoteRequestedForOpportunityEvent(DomainEvent):
    """
    طلب إنشاء عرض سعر للفرصة
    يُستخدم للتكامل مع وحدة المبيعات
    """
    opportunity_id: str = ""
    customer_id: str = ""
    items: list = field(default_factory=list)
    requested_by: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.opportunity_id
        self.aggregate_type = "Opportunity"


@dataclass
class OrderCreatedFromOpportunityEvent(DomainEvent):
    """
    تم إنشاء أمر بيع من الفرصة
    يُستخدم للتكامل مع وحدة المبيعات
    """
    opportunity_id: str = ""
    order_id: str = ""
    quote_id: Optional[str] = None
    
    def __post_init__(self):
        self.aggregate_id = self.opportunity_id
        self.aggregate_type = "Opportunity"
