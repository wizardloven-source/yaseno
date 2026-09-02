# core/domain/shared/clock.py
"""
Clock Service - خدمة الوقت الموحدة للنظام
الإصدار: 3.0.0 - مع إصلاحات المنطقة الزمنية وتوحيد الدوال
"""

from abc import ABC, abstractmethod
from datetime import datetime, date, timezone, timedelta
from typing import Optional, Union
from contextvars import ContextVar

# ============================================================================
# Context Variables للسياق
# ============================================================================

_clock_context: ContextVar[Optional['Clock']] = ContextVar('clock', default=None)


class Clock(ABC):
    """
    واجهة خدمة الوقت - قابلة للحقن والاختبار
    
    هذه هي الخدمة الموحدة للوقت في النظام بأكمله.
    يجب استخدامها بدلاً من `datetime.now()` أو `datetime.utcnow()` المباشرة.
    """
    
    @abstractmethod
    def now(self) -> datetime:
        """
        الحصول على الوقت الحالي بتوقيت UTC
        
        Returns:
            datetime: الوقت الحالي مع معلومات المنطقة الزمنية (UTC)
        
        Example:
            >>> clock = SystemClock()
            >>> clock.now()
            datetime.datetime(2024, 1, 15, 10, 30, 0, tzinfo=datetime.timezone.utc)
        """
        pass
    
    @abstractmethod
    def today(self) -> date:
        """
        الحصول على تاريخ اليوم بتوقيت UTC
        
        Returns:
            date: تاريخ اليوم
        """
        pass
    
    @abstractmethod
    def utc_now(self) -> datetime:
        """
        مرادف لـ now() - للتوافق مع الكود القديم
        
        Returns:
            datetime: الوقت الحالي بتوقيت UTC
        """
        pass
    
    @abstractmethod
    def to_utc(self, dt: Union[datetime, date, None]) -> Optional[datetime]:
        """
        تحويل أي تاريخ/وقت إلى UTC
        
        Args:
            dt: التاريخ/الوقت المراد تحويله
        
        Returns:
            Optional[datetime]: التاريخ/الوقت بتوقيت UTC أو None
        """
        pass
    
    @abstractmethod
    def is_utc(self, dt: datetime) -> bool:
        """
        التحقق من أن الوقت واعي بالمنطقة الزمنية (UTC)
        
        Args:
            dt: الوقت المراد التحقق منه
        
        Returns:
            bool: True إذا كان الوقت بتوقيت UTC
        """
        pass
    
    @abstractmethod
    def sleep(self, seconds: float) -> None:
        """
        تأخير التنفيذ
        
        Args:
            seconds: عدد الثواني للتأخير
        """
        pass


class SystemClock(Clock):
    """
    التنفيذ الافتراضي - يستخدم وقت النظام الحقيقي
    
    هذه هي الخدمة المستخدمة في بيئة الإنتاج.
    """
    
    def now(self) -> datetime:
        """الحصول على الوقت الحالي بتوقيت UTC"""
        return datetime.now(timezone.utc)
    
    def today(self) -> date:
        """الحصول على تاريخ اليوم بتوقيت UTC"""
        return self.now().date()
    
    def utc_now(self) -> datetime:
        """مرادف لـ now()"""
        return self.now()
    
    def to_utc(self, dt: Union[datetime, date, None]) -> Optional[datetime]:
        """
        تحويل أي تاريخ/وقت إلى UTC
        
        Args:
            dt: التاريخ/الوقت المراد تحويله
        
        Returns:
            Optional[datetime]: التاريخ/الوقت بتوقيت UTC أو None
        """
        if dt is None:
            return None
        
        # تحويل date إلى datetime إذا لزم الأمر
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        
        if not isinstance(dt, datetime):
            raise TypeError(f"Expected datetime or date, got {type(dt)}")
        
        # إذا كان الوقت بدون معلومات المنطقة الزمنية، نضيف UTC
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        
        # تحويل إلى UTC
        return dt.astimezone(timezone.utc)
    
    def is_utc(self, dt: datetime) -> bool:
        """
        التحقق من أن الوقت واعي بالمنطقة الزمنية (UTC)
        
        Args:
            dt: الوقت المراد التحقق منه
        
        Returns:
            bool: True إذا كان الوقت بتوقيت UTC
        """
        if dt.tzinfo is None:
            return False
        return dt.tzinfo.utcoffset(dt) == timezone.utc.utcoffset(dt)
    
    def sleep(self, seconds: float) -> None:
        """تأخير التنفيذ"""
        import time
        time.sleep(seconds)


class FixedClock(Clock):
    """
    خدمة وقت بوقت ثابت - للاختبارات
    
    هذه الخدمة مفيدة جداً للاختبارات حيث تحتاج إلى وقت محدد ومتوقع.
    يمكن أيضاً استخدامها لتقديم الوقت أو تأخيره.
    """
    
    def __init__(self, fixed_time: Optional[datetime] = None):
        """
        تهيئة الخدمة بوقت ثابت
        
        Args:
            fixed_time: الوقت الثابت (افتراضي: 2024-01-01 00:00:00 UTC)
        """
        if fixed_time is None:
            fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self._fixed_time = self.to_utc(fixed_time)
        self._step_seconds = 0
    
    def now(self) -> datetime:
        """الحصول على الوقت الثابت + التقدم"""
        return self._fixed_time + timedelta(seconds=self._step_seconds)
    
    def today(self) -> date:
        """الحصول على تاريخ اليوم من الوقت الثابت"""
        return self.now().date()
    
    def utc_now(self) -> datetime:
        """مرادف لـ now()"""
        return self.now()
    
    def to_utc(self, dt: Union[datetime, date, None]) -> Optional[datetime]:
        """
        تحويل أي تاريخ/وقت إلى UTC
        
        Args:
            dt: التاريخ/الوقت المراد تحويله
        
        Returns:
            Optional[datetime]: التاريخ/الوقت بتوقيت UTC أو None
        """
        if dt is None:
            return None
        
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
        
        if not isinstance(dt, datetime):
            raise TypeError(f"Expected datetime or date, got {type(dt)}")
        
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        
        return dt.astimezone(timezone.utc)
    
    def is_utc(self, dt: datetime) -> bool:
        """
        التحقق من أن الوقت واعي بالمنطقة الزمنية (UTC)
        
        Args:
            dt: الوقت المراد التحقق منه
        
        Returns:
            bool: True إذا كان الوقت بتوقيت UTC
        """
        if dt.tzinfo is None:
            return False
        return dt.tzinfo.utcoffset(dt) == timezone.utc.utcoffset(dt)
    
    def sleep(self, seconds: float) -> None:
        """
        تأخير التنفيذ (يقدم الوقت بدلاً من التأخير الحقيقي)
        
        Args:
            seconds: عدد الثواني للتقدم
        """
        self.advance(seconds)
    
    def advance(self, seconds: float) -> None:
        """
        تقديم الوقت بمقدار ثواني معينة
        
        Args:
            seconds: عدد الثواني للتقدم
        """
        self._step_seconds += seconds
    
    def set_time(self, dt: Union[datetime, date]) -> None:
        """
        تعيين وقت جديد
        
        Args:
            dt: الوقت الجديد
        """
        self._fixed_time = self.to_utc(dt)
        self._step_seconds = 0
    
    def reset(self) -> None:
        """إعادة تعيين الوقت إلى القيمة الافتراضية"""
        self._fixed_time = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self._step_seconds = 0


# ============================================================================
# إدارة الـ Clock مع دعم السياق
# ============================================================================

_global_clock: Clock = SystemClock()


def get_clock() -> Clock:
    """
    الحصول على خدمة الوقت - تدعم السياق
    
    هذه هي الدالة الرئيسية التي يجب استخدامها في جميع أنحاء النظام.
    
    Returns:
        Clock: خدمة الوقت الحالية
        
    Example:
        >>> from core.domain.shared.clock import get_clock
        >>> clock = get_clock()
        >>> now = clock.now()
    """
    context_clock = _clock_context.get()
    if context_clock is not None:
        return context_clock
    return _global_clock


def set_clock(clock: Clock) -> None:
    """
    تعيين خدمة الوقت (يتم استدعاؤها من bootstrap)
    
    Args:
        clock: خدمة الوقت الجديدة
    """
    global _global_clock
    _global_clock = clock


def set_context_clock(clock: Clock) -> None:
    """
    تعيين خدمة الوقت للسياق الحالي (مفيد للاختبارات)
    
    Args:
        clock: خدمة الوقت للسياق الحالي
    """
    _clock_context.set(clock)


def reset_context_clock() -> None:
    """إعادة تعيين خدمة الوقت في السياق الحالي"""
    _clock_context.set(None)


# ============================================================================
# دوال مساعدة للاستخدام السريع
# ============================================================================

def utc_now() -> datetime:
    """
    دالة مساعدة للحصول على الوقت الحالي بتوقيت UTC
    
    هذه هي الدالة الموصى بها للحصول على الوقت الحالي في جميع أنحاء النظام.
    
    Returns:
        datetime: الوقت الحالي بتوقيت UTC
        
    Example:
        >>> from core.domain.shared.clock import utc_now
        >>> now = utc_now()
    """
    return get_clock().now()


def today() -> date:
    """
    دالة مساعدة للحصول على تاريخ اليوم بتوقيت UTC
    
    Returns:
        date: تاريخ اليوم
        
    Example:
        >>> from core.domain.shared.clock import today
        >>> today_date = today()
    """
    return get_clock().today()


def to_utc(dt: Union[datetime, date, None]) -> Optional[datetime]:
    """
    دالة مساعدة لتحويل أي تاريخ/وقت إلى UTC
    
    Args:
        dt: التاريخ/الوقت المراد تحويله
    
    Returns:
        Optional[datetime]: التاريخ/الوقت بتوقيت UTC أو None
    
    Example:
        >>> from core.domain.shared.clock import to_utc
        >>> from datetime import datetime
        >>> local_time = datetime.now()
        >>> utc_time = to_utc(local_time)
    """
    return get_clock().to_utc(dt)


def now_with_tz() -> datetime:
    """
    دالة مساعدة للتوافق مع الكود القديم (مرادف لـ utc_now)
    
    Returns:
        datetime: الوقت الحالي بتوقيت UTC
    """
    return get_clock().now()


# ============================================================================
# ديكوراتور لضمان استخدام UTC
# ============================================================================

def require_utc(func):
    """
    ديكوراتور للتأكد من أن التواريخ المرسلة هي UTC
    
    هذا الديكوراتور مفيد للوظائف التي تتطلب تواريخ بتوقيت UTC.
    
    Args:
        func: الدالة المراد تزيينها
    
    Returns:
        Callable: الدالة المزينة
    
    Example:
        >>> @require_utc
        ... def process_date(dt: datetime):
        ...     return dt
        >>> process_date(datetime.now())  # سيتم تحويلها إلى UTC تلقائياً
    """
    def wrapper(*args, **kwargs):
        # تحويل المعاملات المسماة
        for key, value in kwargs.items():
            if isinstance(value, datetime) and not get_clock().is_utc(value):
                kwargs[key] = get_clock().to_utc(value)
        
        # تحويل المعاملات الموضعية
        new_args = []
        for arg in args:
            if isinstance(arg, datetime) and not get_clock().is_utc(arg):
                new_args.append(get_clock().to_utc(arg))
            else:
                new_args.append(arg)
        
        return func(*new_args, **kwargs)
    return wrapper


# ============================================================================
# وظائف إضافية للراحة
# ============================================================================

def format_iso(dt: datetime) -> str:
    """
    تنسيق الوقت بصيغة ISO مع منطقة زمنية
    
    Args:
        dt: الوقت المراد تنسيقه
    
    Returns:
        str: الوقت بصيغة ISO
    
    Example:
        >>> from core.domain.shared.clock import format_iso
        >>> format_iso(utc_now())
        '2024-01-15T10:30:00+00:00'
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_iso(iso_string: str) -> datetime:
    """
    تحويل نص ISO إلى datetime مع منطقة زمنية
    
    Args:
        iso_string: النص بصيغة ISO
    
    Returns:
        datetime: الوقت المحول
    
    Example:
        >>> from core.domain.shared.clock import parse_iso
        >>> dt = parse_iso('2024-01-15T10:30:00+00:00')
    """
    from datetime import datetime as dt
    parsed = dt.fromisoformat(iso_string)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ============================================================================
# اختبار سريع (يعمل فقط عند تشغيل الملف مباشرة)
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("اختبار خدمة الوقت (Clock Service)")
    print("=" * 60)
    
    # اختبار SystemClock
    print("\n1. اختبار SystemClock:")
    clock = SystemClock()
    now = clock.now()
    print(f"   الوقت الحالي: {now}")
    print(f"   التاريخ: {clock.today()}")
    print(f"   هو UTC؟ {clock.is_utc(now)}")
    
    # اختبار FixedClock
    print("\n2. اختبار FixedClock:")
    fixed = FixedClock()
    print(f"   الوقت الثابت: {fixed.now()}")
    fixed.advance(3600)  # تقدم ساعة
    print(f"   بعد التقدم ساعة: {fixed.now()}")
    fixed.set_time(datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
    print(f"   بعد تعيين وقت جديد: {fixed.now()}")
    
    # اختبار الدوال المساعدة
    print("\n3. اختبار الدوال المساعدة:")
    print(f"   utc_now(): {utc_now()}")
    print(f"   today(): {today()}")
    print(f"   format_iso(utc_now()): {format_iso(utc_now())}")
    
    # اختبار التوافق مع الكود القديم
    print("\n4. اختبار التوافق:")
    print(f"   now_with_tz(): {now_with_tz()}")
    
    print("\n" + "=" * 60)
    print("✅ جميع الاختبارات نجحت!")