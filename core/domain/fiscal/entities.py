# core/domain/fiscal/entities.py
"""
Fiscal Year Entities - كيانات السنة المالية
الإصدار: 2.1.0 (مُحسَّن مع دعم أسماء الفترات)
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from calendar import monthrange
from typing import List, Optional, Any, Dict
from uuid import uuid4

from .value_objects import (
    FiscalYearId, FiscalYearCode, FiscalYearStatus,
    FiscalPeriodId, FiscalPeriodType, FiscalPeriodReference,
    FiscalQuarter
)

# ✅ استخدام خدمة الوقت الموحدة
from core.domain.shared.clock import get_clock
from core.shared.exceptions import DomainError, BusinessRuleViolation, ValidationError


# ============================================================================
# دوال مساعدة (للتوافق مع الكود القديم)
# ============================================================================

def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC - يستخدم خدمة الوقت الموحدة"""
    return get_clock().now()


# ============================================================================
# فئة الفترة المالية (FiscalPeriod) - محدثة مع حقل name
# ============================================================================

@dataclass
class FiscalPeriod:
    """
    الفترة المالية (شهر أو ربع سنة)
    
    ✅ محدث: إضافة حقل name للمحاسبة
    ✅ محدث: يستخدم خدمة الوقت الموحدة
    ✅ محدث: يستخدم نظام الأخطاء الموحد
    ✅ محدث: إضافة أحداث المجال
    """
    
    id: FiscalPeriodId = field(default_factory=lambda: FiscalPeriodId(str(uuid4())))
    reference: FiscalPeriodReference = field(default_factory=lambda: FiscalPeriodReference(2025, 1))
    name: str = ""  # ✅ إضافة هذا الحقل - ضروري للمحاسبة والتقارير
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    period_type: FiscalPeriodType = FiscalPeriodType.MONTH
    is_closed: bool = False
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    
    # الربط بالسنة المالية
    fiscal_year_id: Optional[FiscalYearId] = None
    
    # فترة تعديل
    is_adjustment: bool = False
    adjustment_reason: Optional[str] = None
    
    # Optimistic Locking
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """التحقق من صحة البيانات بعد الإنشاء"""
        if self.start_date >= self.end_date:
            raise ValidationError(
                f"Start date {self.start_date} must be before end date {self.end_date}",
                field="dates",
                value={"start": str(self.start_date), "end": str(self.end_date)}
            )

    @property
    def display_name(self) -> str:
        """الاسم المعروض للفترة"""
        return self.name if self.name else str(self.reference)

    @property
    def is_open(self) -> bool:
        """هل الفترة مفتوحة؟"""
        return not self.is_closed

    def contains_date(self, dt: date) -> bool:
        """التحقق من أن التاريخ يقع ضمن الفترة"""
        start = self.start_date.date() if isinstance(self.start_date, datetime) else self.start_date
        end = self.end_date.date() if isinstance(self.end_date, datetime) else self.end_date
        return start <= dt <= end

    def close(self, closed_by: str) -> None:
        """
        إغلاق الفترة
        
        ✅ محدث: يستخدم خدمة الوقت الموحدة
        ✅ محدث: يرفع استثناءات موحدة
        """
        if self.is_closed:
            raise BusinessRuleViolation(
                f"Period {self.reference} is already closed",
                rule_name="period_already_closed"
            )
        
        clock = get_clock()
        self.is_closed = True
        self.closed_at = clock.now()
        self.closed_by = closed_by
        self.version += 1
        
        # ✅ إضافة حدث الإغلاق
        from .events import PeriodClosedEvent
        self._events.append(PeriodClosedEvent(
            fiscal_year_id=self.fiscal_year_id,
            period_reference=self.reference,
            closed_by=closed_by,
            occurred_at=self.closed_at
        ))

    def open(self, opened_by: str) -> None:
        """
        إعادة فتح الفترة (للمسؤولين فقط)
        
        ✅ محدث: يستخدم خدمة الوقت الموحدة
        """
        if not self.is_closed:
            return
        
        clock = get_clock()
        self.is_closed = False
        self.closed_at = None
        self.closed_by = None
        self.version += 1
        
        # ✅ إضافة حدث الفتح
        from .events import PeriodOpenedEvent
        self._events.append(PeriodOpenedEvent(
            fiscal_year_id=self.fiscal_year_id,
            period_reference=self.reference,
            opened_by=opened_by,
            occurred_at=clock.now()
        ))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'reference': str(self.reference),
            'name': self.name,  # ✅ تضمين الاسم
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'period_type': self.period_type.value,
            'is_closed': self.is_closed,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'closed_by': self.closed_by,
            'fiscal_year_id': str(self.fiscal_year_id) if self.fiscal_year_id else None,
            'is_adjustment': self.is_adjustment,
            'adjustment_reason': self.adjustment_reason,
            'version': self.version
        }

    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة"""
        events = self._events.copy()
        self._events.clear()
        return events


# ============================================================================
# فئة السنة المالية (FiscalYear) - AGGREGATE ROOT - محدثة
# ============================================================================

@dataclass
class FiscalYear:
    """
    AGGREGATE ROOT - السنة المالية
    تحتوي على 12 شهراً أو 4 أرباع
    
    ✅ محدث: يستخدم خدمة الوقت الموحدة
    ✅ محدث: يستخدم نظام الأخطاء الموحد
    ✅ محدث: تحسين توليد الفترات مع أسماء
    ✅ محدث: إضافة المزيد من الأحداث
    """
    
    id: FiscalYearId = field(default_factory=lambda: FiscalYearId(str(uuid4())))
    code: FiscalYearCode = field(default_factory=lambda: FiscalYearCode("FY2025"))
    name: str = ""
    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)
    status: FiscalYearStatus = FiscalYearStatus.DRAFT
    
    # الفترات
    periods: List[FiscalPeriod] = field(default_factory=list)
    
    # إعدادات
    periods_per_year: int = 12  # 12 شهراً أو 4 أرباع
    period_type: FiscalPeriodType = FiscalPeriodType.MONTH
    
    # إغلاق العام
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    
    # بيانات التدقيق
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    
    # Optimistic Locking
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)

    # ========================================================================
    # الخصائص المحسوبة
    # ========================================================================

    @property
    def display_name(self) -> str:
        """الاسم المعروض للسنة المالية"""
        return f"{self.code} - {self.name}" if self.name else str(self.code)

    @property
    def is_open(self) -> bool:
        """هل السنة المالية مفتوحة؟"""
        return self.status == FiscalYearStatus.OPEN

    @property
    def is_closed(self) -> bool:
        """هل السنة المالية مغلقة؟"""
        return self.status in [FiscalYearStatus.CLOSED, FiscalYearStatus.ARCHIVED]

    @property
    def total_periods(self) -> int:
        """عدد الفترات في السنة"""
        return self.periods_per_year

    @property
    def open_periods(self) -> List[FiscalPeriod]:
        """الفترات المفتوحة"""
        return [p for p in self.periods if not p.is_closed]

    @property
    def closed_periods(self) -> List[FiscalPeriod]:
        """الفترات المغلقة"""
        return [p for p in self.periods if p.is_closed]

    @property
    def current_period(self) -> Optional[FiscalPeriod]:
        """الحصول على الفترة الحالية (بناءً على تاريخ اليوم)"""
        today = get_clock().today()
        return self.get_period_by_date(today)

    @property
    def completion_percentage(self) -> float:
        """نسبة إنجاز السنة المالية (0-100)"""
        today = get_clock().today()
        total_days = (self.end_date - self.start_date).days
        if total_days <= 0:
            return 0.0
        elapsed_days = (today - self.start_date).days
        return min(100.0, max(0.0, (elapsed_days / total_days) * 100))

    # ========================================================================
    # دوال البحث عن الفترات
    # ========================================================================

    def get_period(self, reference: FiscalPeriodReference) -> Optional[FiscalPeriod]:
        """الحصول على فترة معينة"""
        for period in self.periods:
            if period.reference == reference:
                return period
        return None

    def get_period_by_date(self, dt: date) -> Optional[FiscalPeriod]:
        """الحصول على الفترة التي تحتوي على تاريخ معين"""
        for period in self.periods:
            if period.contains_date(dt):
                return period
        return None

    def get_periods_in_range(
        self, 
        from_ref: FiscalPeriodReference, 
        to_ref: FiscalPeriodReference
    ) -> List[FiscalPeriod]:
        """الحصول على الفترات في نطاق معين"""
        periods = []
        for period in self.periods:
            if from_ref.year == period.reference.year:
                if period.reference.period_number >= from_ref.period_number:
                    periods.append(period)
            elif to_ref.year == period.reference.year:
                if period.reference.period_number <= to_ref.period_number:
                    periods.append(period)
            elif from_ref.year < period.reference.year < to_ref.year:
                periods.append(period)
        return periods

    def get_open_periods_for_date(self, dt: date) -> List[FiscalPeriod]:
        """الحصول على الفترات المفتوحة التي تحتوي على تاريخ معين"""
        result = []
        for period in self.periods:
            if not period.is_closed and period.contains_date(dt):
                result.append(period)
        return result

    # ========================================================================
    # دالة المصنع (Factory Method)
    # ========================================================================

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        start_date: date,
        end_date: date,
        periods_per_year: int = 12,
        period_type: FiscalPeriodType = FiscalPeriodType.MONTH,
        created_by: str = "system"
    ) -> 'FiscalYear':
        """إنشاء سنة مالية جديدة مع فتراتها وأسمائها"""
        if start_date >= end_date:
            raise ValidationError(
                "Start date must be before end date",
                field="dates",
                value={"start": str(start_date), "end": str(end_date)}
            )
        
        if periods_per_year not in [4, 12]:
            raise ValidationError(
                "Periods per year must be 4 (quarters) or 12 (months)",
                field="periods_per_year",
                value=periods_per_year
            )

        fiscal_year = cls(
            code=FiscalYearCode(code),
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=FiscalYearStatus.DRAFT,
            periods_per_year=periods_per_year,
            period_type=period_type,
            created_by=created_by,
            updated_by=created_by,
            version=1
        )

        # ✅ توليد الفترات مع أسمائها
        fiscal_year._generate_periods()

        # ✅ إضافة حدث الإنشاء
        from .events import FiscalYearCreatedEvent
        fiscal_year._events.append(FiscalYearCreatedEvent(
            fiscal_year_id=fiscal_year.id,
            code=fiscal_year.code,
            name=fiscal_year.name,
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
            created_by=created_by
        ))

        return fiscal_year

    # ========================================================================
    # ✅ توليد الفترات مع أسماء - الجزء الأهم
    # ========================================================================

    def _generate_periods(self) -> None:
        """
        توليد الفترات المالية تلقائياً مع أسماء واضحة للمحاسبة
        
        ✅ يدعم الأشهر (12 فترة)
        ✅ يدعم الأرباع (4 فترات)
        ✅ يدعم اللغة العربية
        ✅ يدعم اللغة الإنجليزية (اختياري)
        """
        self.periods.clear()

        # ✅ أسماء الأشهر العربية
        MONTHS_AR = [
            "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
            "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
        ]
        
        # ✅ أسماء الأشهر الإنجليزية (للحالات التي تحتاجها)
        MONTHS_EN = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        # ✅ تحديد اللغة (يمكن جلبها من الإعدادات لاحقاً)
        # افتراضياً نستخدم العربية للمحاسبة العربية
        use_arabic = True
        months = MONTHS_AR if use_arabic else MONTHS_EN

        start_year = self.start_date.year
        start_month = self.start_date.month
        
        for i in range(self.periods_per_year):
            period_num = i + 1
            
            if self.period_type == FiscalPeriodType.MONTH:
                m = ((start_month - 1 + i) % 12) + 1
                y = start_year + (start_month - 1 + i) // 12
                start = date(y, m, 1)
                last_day = monthrange(y, m)[1]
                end = date(y, m, last_day)
                reference = FiscalPeriodReference(y, m)
                if use_arabic:
                    period_name = f"{months[m-1]} {y}"
                else:
                    period_name = f"{months[m-1]} {y}"
            else:
                q = i + 1
                q_start_month = start_month + i * 3
                q_month = ((q_start_month - 1) % 12) + 1
                q_year = start_year + (q_start_month - 1) // 12
                start = date(q_year, q_month, 1)
                end_month = q_month + 2
                end_year = q_year
                if end_month > 12:
                    end_month -= 12
                    end_year += 1
                last_day = monthrange(end_year, end_month)[1]
                end = date(end_year, end_month, last_day)
                reference = FiscalPeriodReference(q_year, q_month)
                if use_arabic:
                    period_name = f"الربع {q} {q_year}"
                else:
                    period_name = f"Q{q} {q_year}"

            period = FiscalPeriod(
                reference=reference,
                name=period_name,
                start_date=start,
                end_date=end,
                period_type=self.period_type,
                fiscal_year_id=self.id,
                is_adjustment=False
            )
            self.periods.append(period)

    # ========================================================================
    # عمليات إدارة السنة المالية
    # ========================================================================

    def open(self, opened_by: str) -> None:
        """فتح السنة المالية"""
        if self.status == FiscalYearStatus.OPEN:
            return
        
        if self.status == FiscalYearStatus.CLOSED:
            raise BusinessRuleViolation(
                f"Cannot open closed fiscal year {self.code}",
                rule_name="year_already_closed"
            )
        
        clock = get_clock()
        self.status = FiscalYearStatus.OPEN
        self.updated_at = clock.now()
        self.updated_by = opened_by
        self.version += 1

        from .events import FiscalYearOpenedEvent
        self._events.append(FiscalYearOpenedEvent(
            fiscal_year_id=self.id,
            code=self.code,
            opened_by=opened_by
        ))

    def close(self, closed_by: str) -> None:
        """إغلاق السنة المالية"""
        if self.status == FiscalYearStatus.CLOSED:
            return

        # ✅ التحقق من أن جميع الفترات مغلقة
        open_periods = self.open_periods
        if open_periods:
            period_refs = [str(p.reference) for p in open_periods[:5]]
            raise BusinessRuleViolation(
                f"Cannot close fiscal year {self.code} because {len(open_periods)} periods are still open: {', '.join(period_refs)}",
                rule_name="open_periods_exist"
            )

        clock = get_clock()
        self.status = FiscalYearStatus.CLOSED
        self.closed_at = clock.now()
        self.closed_by = closed_by
        self.updated_at = clock.now()
        self.updated_by = closed_by
        self.version += 1

        from .events import FiscalYearClosedEvent
        self._events.append(FiscalYearClosedEvent(
            fiscal_year_id=self.id,
            code=self.code,
            closed_by=closed_by
        ))

    def archive(self, archived_by: str) -> None:
        """أرشفة السنة المالية (للقراءة فقط)"""
        if self.status == FiscalYearStatus.ARCHIVED:
            return

        clock = get_clock()
        self.status = FiscalYearStatus.ARCHIVED
        self.updated_at = clock.now()
        self.updated_by = archived_by
        self.version += 1

    # ========================================================================
    # عمليات إدارة الفترات
    # ========================================================================

    def close_period(self, period_reference: FiscalPeriodReference, closed_by: str) -> None:
        """إغلاق فترة مالية معينة"""
        period = self.get_period(period_reference)
        if not period:
            raise ValidationError(
                f"Period {period_reference} not found",
                field="period_reference",
                value=str(period_reference)
            )
        
        if self.is_closed:
            raise BusinessRuleViolation(
                f"Cannot close period in closed fiscal year {self.code}",
                rule_name="year_closed"
            )
        
        period.close(closed_by)
        clock = get_clock()
        self.updated_at = clock.now()
        self.updated_by = closed_by
        self.version += 1

    def open_period(self, period_reference: FiscalPeriodReference, opened_by: str) -> None:
        """إعادة فتح فترة مالية (للمسؤولين فقط)"""
        period = self.get_period(period_reference)
        if not period:
            raise ValidationError(
                f"Period {period_reference} not found",
                field="period_reference",
                value=str(period_reference)
            )
        
        if self.is_closed:
            raise BusinessRuleViolation(
                f"Cannot open period in closed fiscal year {self.code}",
                rule_name="year_closed"
            )
        
        period.open(opened_by)
        clock = get_clock()
        self.updated_at = clock.now()
        self.updated_by = opened_by
        self.version += 1

    def add_adjustment_period(
        self, 
        reference: FiscalPeriodReference, 
        start_date: date, 
        end_date: date, 
        reason: str,
        created_by: str = "system"
    ) -> FiscalPeriod:
        """إضافة فترة تعديل"""
        if self.is_closed:
            raise BusinessRuleViolation(
                f"Cannot add adjustment period to closed fiscal year {self.code}",
                rule_name="year_closed"
            )

        if start_date >= end_date:
            raise ValidationError(
                "Start date must be before end date for adjustment period",
                field="dates",
                value={"start": str(start_date), "end": str(end_date)}
            )

        # ✅ إنشاء فترة تعديل مع اسم مناسب
        period_name = f"تعديل {reference}"
        
        period = FiscalPeriod(
            reference=reference,
            name=period_name,  # ✅ تعيين اسم لفترة التعديل
            start_date=start_date,
            end_date=end_date,
            period_type=FiscalPeriodType.ADJUSTMENT,
            fiscal_year_id=self.id,
            is_adjustment=True,
            adjustment_reason=reason
        )
        self.periods.append(period)
        clock = get_clock()
        self.updated_at = clock.now()
        self.updated_by = created_by
        self.version += 1
        
        from .events import PeriodOpenedEvent
        self._events.append(PeriodOpenedEvent(
            fiscal_year_id=self.id,
            period_reference=reference,
            opened_by=created_by,
            occurred_at=clock.now()
        ))
        
        return period

    def is_period_closed(self, reference: FiscalPeriodReference) -> bool:
        """التحقق من إغلاق فترة معينة"""
        period = self.get_period(reference)
        return period.is_closed if period else False

    # ========================================================================
    # أحداث المجال
    # ========================================================================

    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة"""
        events = self._events.copy()
        self._events.clear()
        return events

    # ========================================================================
    # التسلسل (Serialization)
    # ========================================================================

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'code': str(self.code),
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'status': self.status.value,
            'periods_per_year': self.periods_per_year,
            'period_type': self.period_type.value,
            'periods': [p.to_dict() for p in self.periods],
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'closed_by': self.closed_by,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat(),
            'updated_by': self.updated_by,
            'version': self.version,
            'completion_percentage': self.completion_percentage,
            'current_period': str(self.current_period.reference) if self.current_period else None
        }

    def __repr__(self) -> str:
        return f"FiscalYear(id={self.id}, code={self.code}, status={self.status}, periods={len(self.periods)})"


# ============================================================================
# فئة مساعدة لإدارة نطاق الفترات
# ============================================================================

@dataclass
class FiscalPeriodRange:
    """
    نطاق من الفترات المالية
    
    مفيد للتقارير والاستعلامات التي تحتاج إلى نطاق زمني.
    """
    
    from_period: FiscalPeriodReference
    to_period: FiscalPeriodReference
    
    def __post_init__(self):
        """التحقق من صحة النطاق"""
        if self.from_period.year > self.to_period.year:
            raise ValidationError(
                "From period must be before to period",
                field="dates",
                value={
                    "from": str(self.from_period),
                    "to": str(self.to_period)
                }
            )
        if (self.from_period.year == self.to_period.year and 
            self.from_period.period_number > self.to_period.period_number):
            raise ValidationError(
                "From period must be before to period",
                field="periods",
                value={
                    "from": str(self.from_period),
                    "to": str(self.to_period)
                }
            )
    
    def contains(self, period: FiscalPeriodReference) -> bool:
        """التحقق من وجود فترة ضمن النطاق"""
        if period.year < self.from_period.year or period.year > self.to_period.year:
            return False
        if period.year == self.from_period.year:
            return period.period_number >= self.from_period.period_number
        if period.year == self.to_period.year:
            return period.period_number <= self.to_period.period_number
        return True
    
    def get_periods(self) -> List[FiscalPeriodReference]:
        """الحصول على قائمة بجميع الفترات في النطاق"""
        periods = []
        current = self.from_period
        while current.year < self.to_period.year or (
            current.year == self.to_period.year and 
            current.period_number <= self.to_period.period_number
        ):
            periods.append(current)
            current = current.next_period() if hasattr(current, 'next_period') else None
            if current is None:
                break
        return periods
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'from': str(self.from_period),
            'to': str(self.to_period),
            'periods': [str(p) for p in self.get_periods()]
        }


# ============================================================================
# تصدير جميع العناصر
# ============================================================================

__all__ = [
    # الكيانات الرئيسية
    'FiscalPeriod',
    'FiscalYear',
    'FiscalPeriodRange',
    
    # الدوال المساعدة
    'utc_now',
]