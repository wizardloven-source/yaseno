"""
CRM Domain Entities - Core Business Logic

This module contains the core domain entities for CRM functionality:
- Lead: Potential customer before qualification
- Opportunity: Qualified lead with potential deal
- Activity: Interactions and follow-ups
- Task: Sales team assignments
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from uuid import uuid4


# ============================================================================
# Value Objects
# ============================================================================

class LeadStatus(str, Enum):
    """حالات العميل المحتمل"""
    NEW = "new"  # جديد
    CONTACTED = "contacted"  # تم التواصل
    QUALIFIED = "qualified"  # مؤهل
    UNQUALIFIED = "unqualified"  # غير مؤهل
    CONVERTED = "converted"  # تم التحويل
    LOST = "lost"  # ضائع


class LeadSource(str, Enum):
    """مصادر العملاء المحتملين"""
    WEBSITE = "website"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    EMAIL_CAMPAIGN = "email_campaign"
    PHONE_CALL = "phone_call"
    WALK_IN = "walk_in"
    TRADE_SHOW = "trade_show"
    ADVERTISING = "advertising"
    OTHER = "other"


class OpportunityStage(str, Enum):
    """مراحل الفرصة البيعية"""
    PROSPECTING = "prospecting"  # اكتشاف
    QUALIFICATION = "qualification"  # تأهيل
    PROPOSAL = "proposal"  # عرض
    NEGOTIATION = "negotiation"  # تفاوض
    CLOSED_WON = "closed_won"  # مكسوبة
    CLOSED_LOST = "closed_lost"  # خاسرة


class OpportunityType(str, Enum):
    """نوع الفرصة"""
    NEW_BUSINESS = "new_business"  # عمل جديد
    EXISTING_CUSTOMER = "existing_customer"  # عميل حالي
    UPSELL = "upsell"  # بيع إضافي
    CROSS_SELL = "cross_sell"  # بيع متقاطع
    RENEWAL = "renewal"  # تجديد


class ActivityType(str, Enum):
    """أنواع الأنشطة"""
    CALL = "call"  # مكالمة
    EMAIL = "email"  # بريد إلكتروني
    MEETING = "meeting"  # اجتماع
    TASK = "task"  # مهمة
    NOTE = "note"  # ملاحظة
    DEMO = "demo"  # عرض توضيحي
    FOLLOW_UP = "follow_up"  # متابعة


class Priority(str, Enum):
    """أولوية المهمة/النشاط"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass(frozen=True)
class ContactInfo:
    """معلومات الاتصال"""
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    twitter: Optional[str] = None
    
    def validate_email(self) -> bool:
        """التحقق من صحة البريد الإلكتروني"""
        if not self.email:
            return True
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, self.email))
    
    def validate_phone(self) -> bool:
        """التحقق من صحة رقم الهاتف"""
        if not self.phone and not self.mobile:
            return True
        # تحقق بسيط - يمكن تخصيصه حسب الدولة
        return len(self.phone or self.mobile or '') >= 8


@dataclass(frozen=True)
class Address:
    """العنوان"""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    def format_full_address(self) -> str:
        """تنسيق العنوان الكامل"""
        parts = [self.street, self.city, self.state, self.postal_code, self.country]
        return ', '.join([p for p in parts if p])


@dataclass(frozen=True)
class Money:
    """قيمة مالية"""
    amount: float
    currency: str = "SAR"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("المبلغ لا يمكن أن يكون سالباً")
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("العملات يجب أن تكون متطابقة")
        return Money(self.amount + other.amount, self.currency)
    
    def to_dict(self) -> Dict[str, Any]:
        return {"amount": self.amount, "currency": self.currency}


# ============================================================================
# Domain Entities
# ============================================================================

@dataclass
class Lead:
    """
    عميل محتمل (Lead)
    
    يمثل شخص أو شركة قد تصبح عميلاً في المستقبل.
    يتم تحويلها إلى Opportunity عند التأهيل.
    """
    id: str
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    status: LeadStatus = LeadStatus.NEW
    source: LeadSource = LeadSource.OTHER
    contact_info: ContactInfo = field(default_factory=ContactInfo)
    address: Optional[Address] = None
    assigned_to: Optional[str] = None  # معرف المستخدم المسؤول
    description: Optional[str] = None
    rating: Optional[int] = None  # تقييم من 1-5
    expected_value: Optional[Money] = None
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    converted_at: Optional[datetime] = None
    lost_reason: Optional[str] = None
    
    # علاقات
    activities: List['Activity'] = field(default_factory=list)
    tasks: List['Task'] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.first_name or not self.last_name:
            raise ValueError("الاسم الأول واسم العائلة مطلوبان")
    
    def contact(self, contact_method: str, notes: str = "") -> None:
        """تسجيل تواصل مع العميل المحتمل"""
        if self.status == LeadStatus.NEW:
            self.status = LeadStatus.CONTACTED
        self.updated_at = datetime.utcnow()
        
        activity = Activity(
            id=str(uuid4()),
            lead_id=self.id,
            activity_type=ActivityType(contact_method),
            subject=f"تواصل عبر {contact_method}",
            description=notes,
            due_date=datetime.utcnow(),
            priority=Priority.MEDIUM,
            status="completed"
        )
        self.activities.append(activity)
    
    def qualify(self, expected_value: Money, probability: float = 0.5) -> 'Opportunity':
        """
        تأهيل العميل المحتمل وتحويله إلى فرصة
        
        Args:
            expected_value: القيمة المتوقعة للصفقة
            probability: احتمال الإغلاق (0-1)
            
        Returns:
            Opportunity: الفرصة الجديدة
        """
        if self.status not in [LeadStatus.CONTACTED, LeadStatus.QUALIFIED]:
            raise ValueError("يجب التواصل مع العميل قبل التأهيل")
        
        self.status = LeadStatus.QUALIFIED
        
        opportunity = Opportunity(
            id=str(uuid4()),
            name=f"{self.company_name or self.first_name} - فرصة",
            lead=self,
            stage=OpportunityStage.QUALIFICATION,
            type=OpportunityType.NEW_BUSINESS,
            expected_value=expected_value,
            probability=probability,
            close_date=date.today().replace(month=date.today().month + 3),  # خلال 3 أشهر
            assigned_to=self.assigned_to,
            description=self.description,
            contact_info=self.contact_info,
            address=self.address
        )
        
        return opportunity
    
    def convert_to_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        تحويل العميل المحتمل إلى عميل فعلي
        
        Returns:
            بيانات العميل للتكامل مع وحدة العملاء
        """
        if self.status != LeadStatus.QUALIFIED:
            raise ValueError("يجب تأهيل العميل قبل التحويل")
        
        self.status = LeadStatus.CONVERTED
        self.converted_at = datetime.utcnow()
        
        return {
            "customer_id": customer_id,
            "name": f"{self.first_name} {self.last_name}",
            "company_name": self.company_name,
            "contact_info": self.contact_info,
            "address": self.address,
            "source": "lead_conversion",
            "original_lead_id": self.id
        }
    
    def lose(self, reason: str) -> None:
        """فقدان العميل المحتمل مع تحديد السبب"""
        self.status = LeadStatus.LOST
        self.lost_reason = reason
        self.updated_at = datetime.utcnow()
    
    def add_note(self, note: str) -> None:
        """إضافة ملاحظة"""
        if self.notes:
            self.notes += f"\n{note}"
        else:
            self.notes = note
        self.updated_at = datetime.utcnow()
    
    def assign_to(self, user_id: str) -> None:
        """تعيين العميل المحتمل لمستخدم"""
        self.assigned_to = user_id
        self.updated_at = datetime.utcnow()
    
    def update_rating(self, rating: int) -> None:
        """تحديث التقييم (1-5)"""
        if rating < 1 or rating > 5:
            raise ValueError("التقييم يجب أن يكون بين 1 و 5")
        self.rating = rating
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الكيان إلى قاموس"""
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "company_name": self.company_name,
            "job_title": self.job_title,
            "status": self.status.value,
            "source": self.source.value,
            "contact_info": {
                "phone": self.contact_info.phone,
                "mobile": self.contact_info.mobile,
                "email": self.contact_info.email,
                "website": self.contact_info.website
            },
            "address": self.address.format_full_address() if self.address else None,
            "assigned_to": self.assigned_to,
            "description": self.description,
            "rating": self.rating,
            "expected_value": self.expected_value.to_dict() if self.expected_value else None,
            "notes": self.notes,
            "tags": self.tags,
            "custom_fields": self.custom_fields,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "converted_at": self.converted_at.isoformat() if self.converted_at else None,
            "lost_reason": self.lost_reason,
            "activities_count": len(self.activities),
            "tasks_count": len(self.tasks)
        }


@dataclass
class Opportunity:
    """
    فرصة بيعية (Opportunity)
    
    تمثل صفقة محتملة مع عميل، تتبع مراحل مختلفة حتى الإغلاق.
    """
    id: str
    name: str
    lead: Optional[Lead] = None
    customer_id: Optional[str] = None  # إذا كانت من عميل حالي
    stage: OpportunityStage = OpportunityStage.PROSPECTING
    type: OpportunityType = OpportunityType.NEW_BUSINESS
    expected_value: Money = field(default_factory=lambda: Money(0.0))
    probability: float = 0.0  # 0-1
    weighted_value: float = field(init=False)  # القيمة المرجحة
    close_date: Optional[date] = None
    assigned_to: Optional[str] = None
    description: Optional[str] = None
    contact_info: Optional[ContactInfo] = None
    address: Optional[Address] = None
    competitor_info: Optional[str] = None
    next_step: Optional[str] = None
    next_step_date: Optional[date] = None
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    lost_reason: Optional[str] = None
    won_reason: Optional[str] = None
    
    # علاقات
    activities: List['Activity'] = field(default_factory=list)
    tasks: List['Task'] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)  # معرفات عروض الأسعار
    orders: List[str] = field(default_factory=list)  # معرفات أوامر البيع
    
    def __post_init__(self):
        self.weighted_value = self.expected_value.amount * self.probability
        if not self.name:
            raise ValueError("اسم الفرصة مطلوب")
    
    def advance_stage(self, new_stage: OpportunityStage) -> None:
        """
        تقدم الفرصة إلى المرحلة التالية
        
        Args:
            new_stage: المرحلة الجديدة
        """
        stage_order = list(OpportunityStage)
        current_index = stage_order.index(self.stage)
        new_index = stage_order.index(new_stage)
        
        if new_index <= current_index and new_stage not in [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]:
            raise ValueError("يجب التقدم للمرحلة التالية فقط")
        
        self.stage = new_stage
        self.updated_at = datetime.utcnow()
        
        if new_stage == OpportunityStage.CLOSED_WON:
            self.close_won()
        elif new_stage == OpportunityStage.CLOSED_LOST:
            self.close_lost("لم يتم الإغلاق")
    
    def update_probability(self, probability: float) -> None:
        """تحديث احتمال الإغلاق"""
        if probability < 0 or probability > 1:
            raise ValueError("الاحتمال يجب أن يكون بين 0 و 1")
        self.probability = probability
        self.weighted_value = self.expected_value.amount * probability
        self.updated_at = datetime.utcnow()
    
    def update_expected_value(self, amount: float, currency: str = "SAR") -> None:
        """تحديث القيمة المتوقعة"""
        self.expected_value = Money(amount, currency)
        self.weighted_value = amount * self.probability
        self.updated_at = datetime.utcnow()
    
    def set_next_step(self, step: str, due_date: date) -> None:
        """تحديد الخطوة التالية"""
        self.next_step = step
        self.next_step_date = due_date
        self.updated_at = datetime.utcnow()
    
    def close_won(self, reason: str = "") -> None:
        """إغلاق الفرصة كـ مكسوبة"""
        self.stage = OpportunityStage.CLOSED_WON
        self.closed_at = datetime.utcnow()
        self.won_reason = reason or "تم الإغلاق بنجاح"
        self.updated_at = datetime.utcnow()
    
    def close_lost(self, reason: str) -> None:
        """إغلاق الفرصة كـ خاسرة"""
        self.stage = OpportunityStage.CLOSED_LOST
        self.closed_at = datetime.utcnow()
        self.lost_reason = reason
        self.updated_at = datetime.utcnow()
    
    def add_quote(self, quote_id: str) -> None:
        """ربط عرض سعر بالفرصة"""
        if quote_id not in self.quotes:
            self.quotes.append(quote_id)
            self.updated_at = datetime.utcnow()
    
    def add_order(self, order_id: str) -> None:
        """ربط أمر بيع بالفرصة"""
        if order_id not in self.orders:
            self.orders.append(order_id)
            self.updated_at = datetime.utcnow()
    
    def is_overdue(self) -> bool:
        """التحقق مما إذا كانت الفرصة متأخرة"""
        if self.close_date and self.stage not in [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST]:
            return date.today() > self.close_date
        return False
    
    def days_until_close(self) -> Optional[int]:
        """عدد الأيام المتبقية للإغلاق"""
        if self.close_date:
            delta = self.close_date - date.today()
            return delta.days
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الكيان إلى قاموس"""
        return {
            "id": self.id,
            "name": self.name,
            "lead_id": self.lead.id if self.lead else None,
            "customer_id": self.customer_id,
            "stage": self.stage.value,
            "type": self.type.value,
            "expected_value": self.expected_value.to_dict(),
            "probability": self.probability,
            "weighted_value": self.weighted_value,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "assigned_to": self.assigned_to,
            "description": self.description,
            "competitor_info": self.competitor_info,
            "next_step": self.next_step,
            "next_step_date": self.next_step_date.isoformat() if self.next_step_date else None,
            "tags": self.tags,
            "custom_fields": self.custom_fields,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "lost_reason": self.lost_reason,
            "won_reason": self.won_reason,
            "quotes_count": len(self.quotes),
            "orders_count": len(self.orders),
            "activities_count": len(self.activities),
            "tasks_count": len(self.tasks),
            "is_overdue": self.is_overdue(),
            "days_until_close": self.days_until_close()
        }


@dataclass
class Activity:
    """
    نشاط (Activity)
    
    يمثل تفاعل أو متابعة مع عميل محتمل أو فرصة.
    """
    id: str
    lead_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    customer_id: Optional[str] = None
    activity_type: ActivityType = ActivityType.NOTE
    subject: str = ""
    description: str = ""
    status: str = "pending"  # pending, completed, cancelled
    priority: Priority = Priority.MEDIUM
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    related_to: Optional[str] = None  # نوع الكيان المرتبط
    location: Optional[str] = None
    attendees: List[str] = field(default_factory=list)  # للمكالمات والاجتماعات
    attachments: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def complete(self) -> None:
        """إكمال النشاط"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def cancel(self, reason: str = "") -> None:
        """إلغاء النشاط"""
        self.status = "cancelled"
        if reason:
            self.description += f"\n[ألغي: {reason}]"
        self.updated_at = datetime.utcnow()
    
    def is_overdue(self) -> bool:
        """التحقق من تجاوز الموعد النهائي"""
        if self.due_date and self.status == "pending":
            return datetime.utcnow() > self.due_date
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الكيان إلى قاموس"""
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "opportunity_id": self.opportunity_id,
            "customer_id": self.customer_id,
            "activity_type": self.activity_type.value,
            "subject": self.subject,
            "description": self.description,
            "status": self.status,
            "priority": self.priority.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "assigned_to": self.assigned_to,
            "related_to": self.related_to,
            "location": self.location,
            "attendees": self.attendees,
            "attachments": self.attachments,
            "is_overdue": self.is_overdue(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class Task:
    """
    مهمة (Task)
    
    مهمة لفريق المبيعات مرتبطة بعميل محتمل أو فرصة.
    """
    id: str
    title: str
    description: str = ""
    lead_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    customer_id: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, cancelled
    priority: Priority = Priority.MEDIUM
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None
    created_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    completion_notes: str = ""
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def start(self) -> None:
        """بدء المهمة"""
        self.status = "in_progress"
        self.updated_at = datetime.utcnow()
    
    def complete(self, completed_by: str, notes: str = "") -> None:
        """إكمال المهمة"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.completed_by = completed_by
        self.completion_notes = notes
        self.updated_at = datetime.utcnow()
    
    def cancel(self, reason: str = "") -> None:
        """إلغاء المهمة"""
        self.status = "cancelled"
        if reason:
            self.description += f"\n[ألغيت: {reason}]"
        self.updated_at = datetime.utcnow()
    
    def is_overdue(self) -> bool:
        """التحقق من تجاوز الموعد النهائي"""
        if self.due_date and self.status in ["pending", "in_progress"]:
            return date.today() > self.due_date
        return False
    
    def days_until_due(self) -> Optional[int]:
        """عدد الأيام المتبقية للاستحقاق"""
        if self.due_date:
            delta = self.due_date - date.today()
            return delta.days
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الكيان إلى قاموس"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "lead_id": self.lead_id,
            "opportunity_id": self.opportunity_id,
            "customer_id": self.customer_id,
            "status": self.status,
            "priority": self.priority.value,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "assigned_to": self.assigned_to,
            "created_by": self.created_by,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "completed_by": self.completed_by,
            "completion_notes": self.completion_notes,
            "tags": self.tags,
            "custom_fields": self.custom_fields,
            "is_overdue": self.is_overdue(),
            "days_until_due": self.days_until_due(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


# ============================================================================
# Aggregate Root for Pipeline Management
# ============================================================================

@dataclass
class SalesPipeline:
    """
    خط أنابيب المبيعات (Sales Pipeline)
    
    يمثل رؤية شاملة لجميع الفرص البيعية ومراحلها.
    """
    id: str
    name: str
    description: Optional[str] = None
    stages: List[Dict[str, Any]] = field(default_factory=list)
    owner_id: Optional[str] = None
    team_ids: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_total_value(self, opportunities: List[Opportunity]) -> Money:
        """حساب القيمة الإجمالية للفرص في الخط"""
        total = Money(0.0)
        for opp in opportunities:
            total = total + opp.expected_value
        return total
    
    def get_weighted_value(self, opportunities: List[Opportunity]) -> float:
        """حساب القيمة المرجحة للفرص"""
        return sum(opp.weighted_value for opp in opportunities)
    
    def get_conversion_rate(self, opportunities: List[Opportunity]) -> float:
        """حساب معدل التحويل"""
        if not opportunities:
            return 0.0
        won = sum(1 for opp in opportunities if opp.stage == OpportunityStage.CLOSED_WON)
        total_closed = sum(1 for opp in opportunities if opp.stage in [OpportunityStage.CLOSED_WON, OpportunityStage.CLOSED_LOST])
        if total_closed == 0:
            return 0.0
        return won / total_closed
    
    def get_stage_summary(self, opportunities: List[Opportunity]) -> Dict[str, Any]:
        """ملخص لكل مرحلة"""
        summary = {}
        for stage in OpportunityStage:
            stage_opps = [opp for opp in opportunities if opp.stage == stage]
            summary[stage.value] = {
                "count": len(stage_opps),
                "total_value": sum(opp.expected_value.amount for opp in stage_opps),
                "weighted_value": sum(opp.weighted_value for opp in stage_opps),
                "avg_value": sum(opp.expected_value.amount for opp in stage_opps) / len(stage_opps) if stage_opps else 0
            }
        return summary
    
    def to_dict(self, opportunities: Optional[List[Opportunity]] = None) -> Dict[str, Any]:
        """تحويل الكيان إلى قاموس"""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "stages": self.stages,
            "owner_id": self.owner_id,
            "team_ids": self.team_ids,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
        
        if opportunities:
            result["summary"] = {
                "total_opportunities": len(opportunities),
                "total_value": self.get_total_value(opportunities).to_dict(),
                "weighted_value": self.get_weighted_value(opportunities),
                "conversion_rate": self.get_conversion_rate(opportunities),
                "stage_summary": self.get_stage_summary(opportunities)
            }
        
        return result
