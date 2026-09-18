"""
CRM Commands - أوامر طبقة التطبيق

تعريف جميع الأوامر (Commands) المستخدمة في نظام CRM
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, date


# ============================================================================
# Lead Commands
# ============================================================================

@dataclass
class CreateLeadCommand:
    """إنشاء عميل محتمل جديد"""
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    source: str = "other"
    assigned_to: Optional[str] = None
    description: Optional[str] = None
    expected_value: Optional[float] = None
    currency: str = "SAR"
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateLeadCommand:
    """تحديث بيانات عميل محتمل"""
    lead_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    description: Optional[str] = None
    expected_value: Optional[float] = None
    currency: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


@dataclass
class ContactLeadCommand:
    """تسجيل تواصل مع عميل محتمل"""
    lead_id: str
    contact_method: str  # call, email, meeting, etc.
    notes: str = ""
    contacted_by: Optional[str] = None


@dataclass
class QualifyLeadCommand:
    """تأهيل عميل محتمل وتحويله لفرصة"""
    lead_id: str
    expected_value: float
    probability: float = 0.5
    currency: str = "SAR"
    qualified_by: Optional[str] = None


@dataclass
class ConvertLeadToCustomerCommand:
    """تحويل عميل محتمل إلى عميل فعلي"""
    lead_id: str
    customer_id: str
    converted_by: Optional[str] = None


@dataclass
class LoseLeadCommand:
    """فقدان عميل محتمل"""
    lead_id: str
    reason: str
    lost_by: Optional[str] = None


@dataclass
class AssignLeadCommand:
    """تعيين عميل محتمل لمستخدم"""
    lead_id: str
    assigned_to: str
    assigned_by: Optional[str] = None


@dataclass
class RateLeadCommand:
    """تقييم عميل محتمل"""
    lead_id: str
    rating: int  # 1-5
    rated_by: Optional[str] = None


# ============================================================================
# Opportunity Commands
# ============================================================================

@dataclass
class CreateOpportunityCommand:
    """إنشاء فرصة بيعية جديدة"""
    name: str
    customer_id: Optional[str] = None
    lead_id: Optional[str] = None
    stage: str = "prospecting"
    type: str = "new_business"
    expected_value: float = 0.0
    probability: float = 0.0
    close_date: Optional[date] = None
    assigned_to: Optional[str] = None
    description: Optional[str] = None
    competitor_info: Optional[str] = None
    next_step: Optional[str] = None
    next_step_date: Optional[date] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateOpportunityCommand:
    """تحديث فرصة بيعية"""
    opportunity_id: str
    name: Optional[str] = None
    stage: Optional[str] = None
    expected_value: Optional[float] = None
    probability: Optional[float] = None
    close_date: Optional[date] = None
    description: Optional[str] = None
    competitor_info: Optional[str] = None
    next_step: Optional[str] = None
    next_step_date: Optional[date] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


@dataclass
class AdvanceOpportunityStageCommand:
    """تقدم الفرصة لمرحلة تالية"""
    opportunity_id: str
    new_stage: str
    changed_by: Optional[str] = None


@dataclass
class CloseOpportunityWonCommand:
    """إغلاق الفرصة كـ مكسوبة"""
    opportunity_id: str
    won_reason: str = ""
    closed_by: Optional[str] = None


@dataclass
class CloseOpportunityLostCommand:
    """إغلاق الفرصة كـ خاسرة"""
    opportunity_id: str
    lost_reason: str
    closed_by: Optional[str] = None


@dataclass
class AddQuoteToOpportunityCommand:
    """ربط عرض سعر بالفرصة"""
    opportunity_id: str
    quote_id: str
    added_by: Optional[str] = None


@dataclass
class AddOrderToOpportunityCommand:
    """ربط أمر بيع بالفرصة"""
    opportunity_id: str
    order_id: str
    added_by: Optional[str] = None


# ============================================================================
# Activity Commands
# ============================================================================

@dataclass
class CreateActivityCommand:
    """إنشاء نشاط جديد"""
    activity_type: str  # call, email, meeting, task, note, demo, follow_up
    subject: str
    description: str = ""
    lead_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    customer_id: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[datetime] = None
    assigned_to: Optional[str] = None
    location: Optional[str] = None
    attendees: List[str] = field(default_factory=list)


@dataclass
class UpdateActivityCommand:
    """تحديث نشاط"""
    activity_id: str
    subject: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None


@dataclass
class CompleteActivityCommand:
    """إكمال نشاط"""
    activity_id: str
    completed_by: Optional[str] = None


@dataclass
class CancelActivityCommand:
    """إلغاء نشاط"""
    activity_id: str
    reason: str = ""
    cancelled_by: Optional[str] = None


# ============================================================================
# Task Commands
# ============================================================================

@dataclass
class CreateTaskCommand:
    """إنشاء مهمة جديدة"""
    title: str
    description: str = ""
    lead_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    customer_id: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_by: Optional[str] = None


@dataclass
class UpdateTaskCommand:
    """تحديث مهمة"""
    task_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    tags: Optional[List[str]] = None


@dataclass
class StartTaskCommand:
    """بدء المهمة"""
    task_id: str
    started_by: Optional[str] = None


@dataclass
class CompleteTaskCommand:
    """إكمال المهمة"""
    task_id: str
    completion_notes: str = ""
    completed_by: Optional[str] = None


@dataclass
class CancelTaskCommand:
    """إلغاء المهمة"""
    task_id: str
    reason: str = ""
    cancelled_by: Optional[str] = None


# ============================================================================
# Pipeline Commands
# ============================================================================

@dataclass
class CreatePipelineCommand:
    """إنشاء خط أنابيب مبيعات"""
    name: str
    description: Optional[str] = None
    stages: List[Dict[str, Any]] = field(default_factory=list)
    owner_id: Optional[str] = None
    team_ids: List[str] = field(default_factory=list)


@dataclass
class UpdatePipelineCommand:
    """تحديث خط أنابيب المبيعات"""
    pipeline_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    stages: Optional[List[Dict[str, Any]]] = None
    team_ids: Optional[List[str]] = None
    is_active: Optional[bool] = None


@dataclass
class GetPipelineAnalyticsCommand:
    """الحصول على تحليلات خط الأنابيب"""
    pipeline_id: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    assigned_to: Optional[str] = None
