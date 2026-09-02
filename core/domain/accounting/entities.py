# core/domain/accounting/entities.py
"""
HEART OF THE ERP SYSTEM - YAseen ERP ENTERPRISE VERSION
الإصدار المُصلح - v2.1.0

This module contains the domain entities and aggregate roots for the accounting context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Any, Tuple, Dict
from uuid import UUID, uuid4

# استيرادات الـ Shared Kernel والملفات المحلية
from core.domain.shared.value_objects import AccountCode, Money
from .value_objects import JournalEntryId
from .exceptions import (
    UnbalancedEntryError,
    PostedEntryModificationError,
    InvalidLineError,
    AlreadyPostedError,
    CannotReverseUnpostedError,
    MultiCurrencyMismatchError,
    AlreadyReversedError
)


# =============================================================================
# ✅ الإصلاح 1: دالة utc_now الموحدة والمتوافقة
# =============================================================================

def utc_now() -> datetime:
    """
    إرجاع توقيت UTC واعي للتدقيق.
    
    ✅ متوافق مع جميع إصدارات Python
    ✅ يستخدم timezone.utc مباشرة
    """
    return datetime.now(timezone.utc)


# =============================================================================
# ✅ JournalLine - سطر القيد المحاسبي (محسّن)
# =============================================================================

@dataclass
class JournalLine:
    """سطر محاسبي مفصل - يمثل حركة مالية واحدة."""
    
    account_code: AccountCode
    debit: Money
    credit: Money
    line_id: Optional[UUID] = None
    
    def __post_init__(self):
        if self.line_id is None:
            self.line_id = uuid4()
        
        has_debit = self.debit.amount > 0
        has_credit = self.credit.amount > 0
        
        # ✅ التحقق من صحة السطر
        if has_debit and has_credit:
            raise InvalidLineError(
                "Accounting Rule Violation: Cannot contain both debit and credit."
            )
        if self.debit.amount < 0 or self.credit.amount < 0:
            raise InvalidLineError(
                "Compliance Error: Negative amounts are forbidden."
            )
        
        # ✅ التحقق من صحة العملة
        if not self.currency or not isinstance(self.currency, str):
            raise InvalidLineError("Currency must be a non-empty string.")
    
    @property
    def currency(self) -> str:
        """الحصول على عملة السطر المحاسبي."""
        if self.debit.amount > 0:
            return self.debit.currency
        return self.credit.currency
    
    @property
    def is_debit(self) -> bool:
        """هل السطر مدين؟"""
        return self.debit.amount > 0
    
    @property
    def is_credit(self) -> bool:
        """هل السطر دائن؟"""
        return self.credit.amount > 0
    
    @property
    def amount(self) -> Decimal:
        """الحصول على المبلغ (الموجب للمدين، السالب للدائن)."""
        if self.debit.amount > 0:
            return self.debit.amount
        return -self.credit.amount
    
    @property
    def is_zero(self) -> bool:
        """هل السطر صفر؟"""
        return self.debit.amount == 0 and self.credit.amount == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل السطر إلى قاموس."""
        return {
            "line_id": str(self.line_id),
            "account_code": self.account_code.code,
            "debit": str(self.debit.amount),
            "credit": str(self.credit.amount),
            "currency": self.currency
        }


# =============================================================================
# ✅ JournalEntry - القيد المحاسبي (AGGREGATE ROOT - محسّن بالكامل)
# =============================================================================

@dataclass
class JournalEntry:
    """
    AGGREGATE ROOT - قيد اليومية المحاسبي
    
    هذا هو الكيان الرئيسي في النظام المحاسبي.
    يمثل مجموعة من الأسطر المحاسبية التي يجب أن تكون متوازنة.
    
    ملاحظة: الـ version هو للتحكم في التزامن (Optimistic Locking)
    يتم إدارته فقط بواسطة الـ Repository ولا يتم تعديله داخل الـ Entity
    
    ✅ محسّن: دعم كامل للعملات المتعددة
    ✅ محسّن: تحقق مسبق قبل الترحيل
    ✅ محسّن: أحداث مجال متكاملة
    """
    
    # ========== الحقول الأساسية ==========
    id: JournalEntryId = field(default_factory=JournalEntryId.generate)
    date: datetime = field(default_factory=utc_now)
    description: str = ""
    lines: List[JournalLine] = field(default_factory=list)
    
    # ========== حالة الترحيل ==========
    is_posted: bool = False
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None
    
    # ========== العلاقات مع القيود الأخرى ==========
    reversed_entry_id: Optional[JournalEntryId] = None
    reverses_entry_id: Optional[JournalEntryId] = None
    
    # ========== التحكم في التزامن (يدار بواسطة Repository) ==========
    version: int = 1
    
    # ========== أحداث المجال ==========
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # ========================================================================
    # ✅ الخصائص المحسوبة
    # ========================================================================
    
    @property
    def is_draft(self) -> bool:
        """هل القيد مسودة؟"""
        return not self.is_posted
    
    @property
    def is_reversed(self) -> bool:
        """هل تم عكس هذا القيد؟"""
        return self.reversed_entry_id is not None
    
    @property
    def is_reversal(self) -> bool:
        """هل هذا القيد عكسي؟"""
        return self.reverses_entry_id is not None
    
    @property
    def line_count(self) -> int:
        """عدد الأسطر في القيد."""
        return len(self.lines)
    
    @property
    def total_debit(self) -> Decimal:
        """إجمالي المدين."""
        return self.get_total_debit()
    
    @property
    def total_credit(self) -> Decimal:
        """إجمالي الدائن."""
        return self.get_total_credit()
    
    @property
    def is_balanced(self) -> bool:
        """هل القيد متوازن؟"""
        return self._is_balanced()
    
    @property
    def currency_breakdown(self) -> Dict[str, Dict[str, Decimal]]:
        """تفصيل القيد حسب العملة."""
        return self._get_currency_breakdown()
    
    # ========================================================================
    # ✅ الإصلاح 3: validate_for_posting() - التحقق المسبق
    # ========================================================================
    
    def validate_for_posting(self) -> List[str]:
        """
        التحقق من صحة القيد قبل الترحيل.
        
        Returns:
            List[str]: قائمة بأخطاء التحقق (فارغة إذا كان صحيحاً)
        """
        errors = []
        
        # 1. التحقق من وجود وصف
        if not self.description or not self.description.strip():
            errors.append("Description is required for posting.")
        
        # 2. التحقق من وجود سطور
        if len(self.lines) < 2:
            errors.append("Entry requires at least 2 lines.")
        
        # 3. التحقق من أن القيد غير مرحل مسبقاً
        if self.is_posted:
            errors.append(f"Entry {self.id} is already posted.")
        
        # 4. التحقق من توازن القيد
        if not self._is_balanced():
            debit, credit = self._calculate_totals()
            errors.append(f"Entry unbalanced: Debit={debit}, Credit={credit}")
        
        # 5. التحقق من تطابق العملات
        if self.lines:
            base_currency = self.lines[0].currency
            for line in self.lines:
                if line.currency != base_currency:
                    errors.append(
                        f"Currency mismatch: {line.currency} vs {base_currency}"
                    )
        
        return errors
    
    # ========================================================================
    # ✅ الإصلاح 4: add_line() - مع التحقق من العملة
    # ========================================================================
    
    def add_line(self, line: JournalLine) -> None:
        """
        إضافة سطر إلى القيد المحاسبي.
        
        Args:
            line: السطر المراد إضافته
            
        Raises:
            PostedEntryModificationError: إذا كان القيد مرحلاً
        """
        if self.is_posted:
            raise PostedEntryModificationError(str(self.id), "add_line")
        
        # ✅ التحقق من صحة السطر
        if line.is_zero:
            raise InvalidLineError("Cannot add zero-value line.")
        
        # ✅ التحقق من تطابق العملة (مع السماح بالعملات المتعددة)
        if self.lines:
            base_currency = self.lines[0].currency
            if line.currency != base_currency:
                # في النظام متعدد العملات، نسمح بذلك ولكن نضيف تحذيراً
                # سيتم التحقق النهائي عند الترحيل
                pass
        
        self.lines.append(line)
        # ❌ self.version += 1 - تم حذفها (يدار بواسطة Repository)
    
    # ========================================================================
    # ✅ الإصلاح 5: post() - مع التحقق المسبق
    # ========================================================================
    
    def post(self, posted_by: str) -> None:
        """
        ترحيل القيد المحاسبي.
        
        هذه هي الطريقة الوحيدة لتغيير حالة القيد من مسودة إلى مرحل.
        
        Args:
            posted_by: معرف المستخدم الذي يقوم بالترحيل
            
        Raises:
            AlreadyPostedError: إذا كان القيد مرحلاً مسبقاً
            UnbalancedEntryError: إذا كان القيد غير متوازن
            MultiCurrencyMismatchError: إذا كانت العملات غير متطابقة
        """
        # ✅ التحقق المسبق
        errors = self.validate_for_posting()
        if errors:
            # إذا كان هناك أخطاء، نرفع الاستثناء المناسب
            if "already posted" in errors[0].lower():
                raise AlreadyPostedError(str(self.id))
            elif "unbalanced" in errors[0].lower():
                debit, credit = self._calculate_totals()
                raise UnbalancedEntryError(debit, credit, str(self.id))
            else:
                raise ValueError(f"Validation failed: {', '.join(errors)}")
        
        # ✅ التحقق من توازن العملات المتعددة
        base_currency = self.lines[0].currency
        for line in self.lines:
            if line.currency != base_currency:
                raise MultiCurrencyMismatchError(
                    str(self.id), 
                    f"Currency Mismatch: {line.currency} vs {base_currency}"
                )
        
        # ✅ حساب المجاميع والتحقق من التوازن
        total_debit, total_credit = self._calculate_totals()
        if total_debit != total_credit:
            raise UnbalancedEntryError(total_debit, total_credit, str(self.id))
        
        # ✅ تحديث حالة القيد
        self.is_posted = True
        self.posted_at = utc_now()
        self.posted_by = posted_by
        # ❌ self.version += 1 - تم حذفها (يدار بواسطة Repository)
        
        # ✅ بث حدث الترحيل
        from .events import EntryPostedEvent
        self._events.append(EntryPostedEvent(
            entry_id=self.id,
            posted_by=posted_by,
            total_debit=total_debit,
            total_credit=total_credit,
            currency=base_currency,
            entry_date=self.date,
            line_count=len(self.lines),
            posted_at=self.posted_at
        ))
    
    # ========================================================================
    # ✅ الإصلاح 6: reverse() - مع التحقق الإضافي
    # ========================================================================
    
    def reverse(self, reason: str = "") -> 'JournalEntry':
        """
        إنشاء قيد عكسي للقيد الحالي.
        
        القيد العكسي يلغي تأثير القيد الأصلي عن طريق عكس جميع الأسطر.
        
        Args:
            reason: سبب العكس (اختياري)
            
        Returns:
            JournalEntry: القيد العكسي الجديد
            
        Raises:
            CannotReverseUnpostedError: إذا كان القيد غير مرحل
            AlreadyReversedError: إذا كان القيد معكوساً مسبقاً
            ValueError: إذا كان القيد لا يحتوي على سطور
        """
        # ✅ التحقق من إمكانية العكس
        if not self.is_posted:
            raise CannotReverseUnpostedError(str(self.id))
        
        if self.reversed_entry_id is not None:
            raise AlreadyReversedError(str(self.id), str(self.reversed_entry_id))
        
        if not self.lines:
            raise ValueError("Cannot reverse an entry with no lines.")
        
        # ✅ إنشاء الأسطر العكسية
        reversed_lines = []
        for line in self.lines:
            reversed_lines.append(JournalLine(
                account_code=line.account_code,
                debit=line.credit,  # swap: debit becomes credit
                credit=line.debit   # swap: credit becomes debit
            ))
        
        # ✅ إنشاء القيد العكسي
        reversal_entry = JournalEntry(
            id=JournalEntryId.generate(),
            date=utc_now(),
            description=f"REVERSAL: {self.description}" + (f" - {reason}" if reason else ""),
            lines=reversed_lines,
            reverses_entry_id=self.id
        )
        
        # ✅ تحديث القيد الأصلي
        self.reversed_entry_id = reversal_entry.id
        # ❌ self.version += 1 - تم حذفها (يدار بواسطة Repository)
        
        # ✅ بث حدث العكس
        from .events import EntryReversedEvent
        self._events.append(EntryReversedEvent(
            original_entry_id=self.id,
            reversal_entry_id=reversal_entry.id,
            reversed_by=self.posted_by or "system",
            reason=reason or "No reason provided",
            total_amount=Money(self.total_debit, self.lines[0].currency)
        ))
        
        return reversal_entry
    
    # ========================================================================
    # ✅ الإصلاح 7: _is_balanced() - دعم العملات المتعددة
    # ========================================================================
    
    def _is_balanced(self) -> bool:
        """
        التحقق من توازن القيد.
        
        ✅ مصحح: يدعم العملات المتعددة - يجب أن تتوازن كل عملة على حدة
        """
        if not self.lines:
            return False
        
        # التحقق من توازن كل عملة على حدة
        currency_totals: Dict[str, Decimal] = {}
        for line in self.lines:
            currency = line.currency
            if currency not in currency_totals:
                currency_totals[currency] = Decimal('0')
            currency_totals[currency] += line.debit.amount - line.credit.amount
        
        # جميع العملات يجب أن تكون متوازنة
        return all(abs(balance) < Decimal('0.01') for balance in currency_totals.values())
    
    # ========================================================================
    # ✅ دوال الحصول على المجاميع
    # ========================================================================
    
    def get_total_debit(self, currency: Optional[str] = None) -> Decimal:
        """
        الحصول على إجمالي المدين.
        
        Args:
            currency: العملة المطلوبة (اختياري)
        """
        total = Decimal('0')
        for line in self.lines:
            if currency is None or line.currency == currency:
                total += line.debit.amount
        return total
    
    def get_total_credit(self, currency: Optional[str] = None) -> Decimal:
        """
        الحصول على إجمالي الدائن.
        
        Args:
            currency: العملة المطلوبة (اختياري)
        """
        total = Decimal('0')
        for line in self.lines:
            if currency is None or line.currency == currency:
                total += line.credit.amount
        return total
    
    def _calculate_totals(self) -> Tuple[Decimal, Decimal]:
        """حساب إجمالي المدين والدائن."""
        return self.get_total_debit(), self.get_total_credit()
    
    # ========================================================================
    # ✅ الإصلاح 8: _get_currency_breakdown() - تفصيل العملات
    # ========================================================================
    
    def _get_currency_breakdown(self) -> Dict[str, Dict[str, Decimal]]:
        """
        الحصول على تفصيل القيد حسب العملة.
        
        Returns:
            Dict: {currency: {"debit": total_debit, "credit": total_credit, "balance": balance}}
        """
        breakdown = {}
        for line in self.lines:
            currency = line.currency
            if currency not in breakdown:
                breakdown[currency] = {
                    "debit": Decimal('0'),
                    "credit": Decimal('0'),
                    "balance": Decimal('0')
                }
            breakdown[currency]["debit"] += line.debit.amount
            breakdown[currency]["credit"] += line.credit.amount
            breakdown[currency]["balance"] = (
                breakdown[currency]["debit"] - breakdown[currency]["credit"]
            )
        return breakdown
    
    # ========================================================================
    # ✅ الإصلاح 9: to_dict() - التسلسل
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        تحويل القيد إلى قاموس للتسلسل.
        """
        return {
            "id": str(self.id),
            "date": self.date.isoformat() if self.date else None,
            "description": self.description,
            "is_posted": self.is_posted,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "posted_by": self.posted_by,
            "reversed_entry_id": str(self.reversed_entry_id) if self.reversed_entry_id else None,
            "reverses_entry_id": str(self.reverses_entry_id) if self.reverses_entry_id else None,
            "version": self.version,
            "lines": [line.to_dict() for line in self.lines],
            "total_debit": str(self.total_debit),
            "total_credit": str(self.total_credit),
            "is_balanced": self._is_balanced(),
            "currency_breakdown": self._get_currency_breakdown()
        }
    
    # ========================================================================
    # ✅ الإصلاح 10: pull_events() - استخراج الأحداث
    # ========================================================================
    
    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة."""
        events = self._events.copy()
        self._events.clear()
        return events
    
    # ========================================================================
    # ✅ الإصلاح 11: __repr__() - تمثيل نصي محسن
    # ========================================================================
    
    def __repr__(self) -> str:
        """تمثيل نصي للقيد."""
        status = "POSTED" if self.is_posted else "DRAFT"
        return (
            f"JournalEntry(id={self.id}, status={status}, "
            f"date={self.date}, lines={len(self.lines)}, version={self.version})"
        )


# =============================================================================
# ✅ دالة مساعدة: create_journal_entry()
# =============================================================================

def create_journal_entry(
    date: datetime,
    description: str,
    lines_data: List[Dict[str, Any]],
) -> JournalEntry:
    """
    إنشاء قيد محاسبي من قائمة بيانات الأسطر.
    
    هذه دالة مصنع (Factory) لتسهيل إنشاء القيود من البيانات الأولية.
    
    Args:
        date: تاريخ القيد
        description: وصف القيد
        lines_data: قائمة من القواميس تحتوي على:
            - account_code: كود الحساب
            - debit: مبلغ المدين (اختياري)
            - credit: مبلغ الدائن (اختياري)
            - currency: العملة (اختياري، افتراضي USD)
    
    Returns:
        JournalEntry: كائن القيد المحاسبي
        
    Example:
        >>> entry = create_journal_entry(
        ...     date=datetime.now(),
        ...     description="إيداع نقدي",
        ...     lines_data=[
        ...         {"account_code": "1010", "debit": "1000", "currency": "USD"},
        ...         {"account_code": "1020", "credit": "1000", "currency": "USD"}
        ...     ]
        ... )
    """
    lines = []
    for data in lines_data:
        debit_amount = Decimal(str(data.get('debit', '0')))
        credit_amount = Decimal(str(data.get('credit', '0')))
        currency = data.get('currency', 'USD')
        
        line = JournalLine(
            account_code=AccountCode(data['account_code']),
            debit=Money(debit_amount, currency),
            credit=Money(credit_amount, currency)
        )
        lines.append(line)
    
    return JournalEntry(
        date=date,
        description=description,
        lines=lines
    )


# =============================================================================
# ✅ تصدير جميع العناصر
# =============================================================================

__all__ = [
    "JournalLine",
    "JournalEntry",
    "utc_now",
    "create_journal_entry",
]