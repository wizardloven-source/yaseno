# core/domain/payments/entities.py
"""
Payment Aggregate Root - كيان الدفع الأساسي
✅ محدث: إضافة دعم فروع العملاء (Customer Branches)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Any, Dict
from uuid import uuid4

from .value_objects import (
    PaymentId,
    PaymentCode,
    PaymentType,
    PaymentMethod,
    PaymentStatus,
    PaymentReference,
    Money,
)
from .exceptions import (
    PaymentAlreadyCompletedError,
    PaymentAlreadyCancelledError,
    InvalidPaymentStatusTransitionError,
    PaymentAmountError,
    InsufficientBalanceError,
)
from .events import (
    PaymentCreatedEvent,
    PaymentUpdatedEvent,
    PaymentApprovedEvent,
    PaymentRejectedEvent,
    PaymentCompletedEvent,
    PaymentCancelledEvent,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PaymentLine:
    """سطر دفع (مثل دفع جزء من فاتورة)"""
    line_id: str = field(default_factory=lambda: str(uuid4())[:8])
    reference_type: str = ""  # invoice, purchase_order, etc.
    reference_id: str = ""
    amount: Money = field(default_factory=lambda: Money.zero())
    notes: str = ""

    @property
    def total(self) -> Money:
        return self.amount


@dataclass
class Payment:
    """
    AGGREGATE ROOT - عملية الدفع/القبض
    ✅ محدث: إضافة دعم فروع العملاء
    """

    # ========== معلومات أساسية ==========
    id: PaymentId = field(default_factory=PaymentId.generate)
    code: PaymentCode = field(default_factory=lambda: PaymentCode(""))
    date: datetime = field(default_factory=utc_now)

    # ========== نوع العملية ==========
    payment_type: PaymentType = PaymentType.RECEIVE
    payment_method: PaymentMethod = PaymentMethod.CASH

    # ========== المبالغ ==========
    amount: Money = field(default_factory=lambda: Money.zero())
    currency: str = "USD"

    # ========== الأطراف ==========
    # العميل
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    
    # ✅ فروع العميل (جديد)
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    customer_branch_code: Optional[str] = None
    
    # المورد
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None

    # ========== المراجع ==========
    reference: Optional[PaymentReference] = None

    # ========== الصندوق ==========
    fund_id: Optional[str] = None
    fund_code: Optional[str] = None

    # ========== الحالة ==========
    status: PaymentStatus = PaymentStatus.DRAFT

    # ========== البنود ==========
    lines: List[PaymentLine] = field(default_factory=list)

    # ========== معلومات إضافية ==========
    notes: str = ""
    submitted_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    completed_at: Optional[datetime] = None

    # ========== بيانات التدقيق ==========
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = ""
    version: int = 1

    # ========== أحداث المجال ==========
    _events: List[Any] = field(default_factory=list, repr=False)

    # =========================================================================
    # ✅ خصائص فروع العملاء (جديدة)
    # =========================================================================
    
    @property
    def has_customer_branch(self) -> bool:
        """هل الدفعة تحدد فرع عميل؟"""
        return bool(self.customer_branch_id)
    
    @property
    def customer_branch_display(self) -> str:
        """الاسم المعروض لفرع العميل"""
        if self.customer_branch_name:
            return self.customer_branch_name
        if self.customer_branch_code:
            return self.customer_branch_code
        return "بدون فرع"

    # =========================================================================
    # خصائص محسوبة (موجودة)
    # =========================================================================

    @property
    def is_completed(self) -> bool:
        return self.status == PaymentStatus.COMPLETED

    @property
    def is_cancelled(self) -> bool:
        return self.status == PaymentStatus.CANCELLED

    @property
    def is_pending(self) -> bool:
        return self.status == PaymentStatus.PENDING

    @property
    def is_approved(self) -> bool:
        return self.status == PaymentStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.status == PaymentStatus.REJECTED

    @property
    def is_draft(self) -> bool:
        return self.status == PaymentStatus.DRAFT

    @property
    def total_amount(self) -> Money:
        """إجمالي المبلغ (من البنود أو المبلغ الرئيسي)"""
        if self.lines:
            total = Money.zero(self.currency)
            for line in self.lines:
                total += line.amount
            return total
        return self.amount

    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        branch_info = f" ({self.customer_branch_name or self.customer_branch_code})" if self.customer_branch_id else ""
        if self.customer_name:
            return f"{self.code} - {self.customer_name}{branch_info}"
        if self.supplier_name:
            return f"{self.code} - {self.supplier_name}"
        return str(self.code)

    @property
    def type_display(self) -> str:
        """نوع العملية المعروض"""
        from core.i18n.translator import tr
        if self.payment_type == PaymentType.RECEIVE:
            return tr("payments.receive")
        elif self.payment_type == PaymentType.PAY:
            return tr("payments.pay")
        return tr("payments.transfer")

    @property
    def method_display(self) -> str:
        """طريقة الدفع المعروضة"""
        from core.i18n.translator import tr
        mapping = {
            PaymentMethod.CASH: "payment.cash",
            PaymentMethod.CHECK: "payment.check",
            PaymentMethod.TRANSFER: "payment.transfer",
            PaymentMethod.CREDIT: "payment.credit",
            PaymentMethod.CARD: "payment.card",
        }
        return tr(mapping.get(self.payment_method, "common.unknown"))

    @property
    def status_display(self) -> str:
        """الحالة المعروضة"""
        return PaymentStatus.get_display_name(self.status.value)

    @property
    def status_color(self) -> str:
        """لون الحالة"""
        return PaymentStatus.get_color(self.status.value)

    @property
    def status_icon(self) -> str:
        """أيقونة الحالة"""
        return PaymentStatus.get_icon(self.status.value)

    # =========================================================================
    # ✅ تعيين فرع العميل (جديد)
    # =========================================================================
    
    def set_customer_branch(
        self,
        branch_id: str,
        branch_name: Optional[str] = None,
        branch_code: Optional[str] = None,
        updated_by: str = ""
    ) -> None:
        """
        تعيين فرع العميل للدفعة
        
        Args:
            branch_id: معرف فرع العميل
            branch_name: اسم فرع العميل (اختياري)
            branch_code: كود فرع العميل (اختياري)
            updated_by: من قام بالتحديث
        """
        if self.is_completed:
            raise PaymentAlreadyCompletedError(str(self.id))
        if self.is_cancelled:
            raise PaymentAlreadyCancelledError(str(self.id))
        
        self.customer_branch_id = branch_id
        
        if branch_name:
            self.customer_branch_name = branch_name
        
        if branch_code:
            self.customer_branch_code = branch_code
        
        self._update_timestamp()
        self.updated_by = updated_by
        self.version += 1
    
    def clear_customer_branch(self, updated_by: str = "") -> None:
        """
        إزالة فرع العميل من الدفعة
        
        Args:
            updated_by: من قام بالتحديث
        """
        if self.is_completed:
            raise PaymentAlreadyCompletedError(str(self.id))
        if self.is_cancelled:
            raise PaymentAlreadyCancelledError(str(self.id))
        
        self.customer_branch_id = None
        self.customer_branch_name = None
        self.customer_branch_code = None
        
        self._update_timestamp()
        self.updated_by = updated_by
        self.version += 1

    # =========================================================================
    # دالة المصنع (محدثة)
    # =========================================================================

    @classmethod
    def create(
        cls,
        payment_type: PaymentType,
        amount: Money,
        payment_method: PaymentMethod = PaymentMethod.CASH,
        customer_id: Optional[str] = None,
        customer_name: Optional[str] = None,
        # ✅ إضافة معاملات فرع العميل
        customer_branch_id: Optional[str] = None,
        customer_branch_name: Optional[str] = None,
        customer_branch_code: Optional[str] = None,
        supplier_id: Optional[str] = None,
        supplier_name: Optional[str] = None,
        fund_id: Optional[str] = None,
        reference: Optional[PaymentReference] = None,
        notes: str = "",
        created_by: str = "system",
    ) -> 'Payment':
        """
        إنشاء عملية دفع جديدة مع دعم فروع العملاء
        """
        payment = cls(
            code=PaymentCode(cls._generate_code()),
            payment_type=payment_type,
            amount=amount,
            currency=amount.currency,
            payment_method=payment_method,
            customer_id=customer_id,
            customer_name=customer_name,
            # ✅ تعيين فروع العملاء
            customer_branch_id=customer_branch_id,
            customer_branch_name=customer_branch_name,
            customer_branch_code=customer_branch_code,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            fund_id=fund_id,
            reference=reference,
            notes=notes,
            created_by=created_by,
            updated_by=created_by,
            version=1,
        )

        # إضافة حدث الإنشاء (محدث)
        payment._events.append(PaymentCreatedEvent(
            payment_id=payment.id,
            payment_code=payment.code,
            payment_type=payment.payment_type,
            amount=payment.amount,
            customer_id=payment.customer_id,
            customer_name=payment.customer_name,
            customer_branch_id=payment.customer_branch_id,  # ✅ إضافة
            customer_branch_name=payment.customer_branch_name,  # ✅ إضافة
            created_by=created_by,
        ))

        return payment

    @classmethod
    def _generate_code(cls) -> str:
        """توليد كود تلقائي"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d")
        import random
        seq = str(random.randint(1, 9999)).zfill(4)
        return f"PAY-{timestamp}-{seq}"

    # =========================================================================
    # العمليات الأساسية (موجودة)
    # =========================================================================

    def add_line(
        self,
        reference_type: str,
        reference_id: str,
        amount: Money,
        notes: str = "",
    ) -> None:
        """إضافة سطر دفع"""
        if self.is_completed:
            raise PaymentAlreadyCompletedError(str(self.id))
        if self.is_cancelled:
            raise PaymentAlreadyCancelledError(str(self.id))

        if amount.amount <= 0:
            raise PaymentAmountError("Amount must be greater than zero")

        line = PaymentLine(
            reference_type=reference_type,
            reference_id=reference_id,
            amount=amount,
            notes=notes,
        )
        self.lines.append(line)
        self._update_amounts()
        self._update_timestamp()

    def remove_line(self, line_id: str) -> bool:
        """حذف سطر دفع"""
        if self.is_completed:
            raise PaymentAlreadyCompletedError(str(self.id))
        if self.is_cancelled:
            raise PaymentAlreadyCancelledError(str(self.id))

        for i, line in enumerate(self.lines):
            if line.line_id == line_id:
                self.lines.pop(i)
                self._update_amounts()
                self._update_timestamp()
                return True
        return False

    def _update_amounts(self) -> None:
        """تحديث المبالغ من البنود"""
        if self.lines:
            total = Money.zero(self.currency)
            for line in self.lines:
                total += line.amount
            self.amount = total

    def _update_timestamp(self) -> None:
        """تحديث الطابع الزمني"""
        self.updated_at = utc_now()

    # =========================================================================
    # تغيير الحالة (موجودة)
    # =========================================================================

    def submit(self, submitted_by: str) -> None:
        """إرسال الدفع للاعتماد (Draft -> Pending)"""
        if not self.status.can_transition_to(PaymentStatus.PENDING):
            raise InvalidPaymentStatusTransitionError(
                self.status.value, PaymentStatus.PENDING.value
            )

        self.status = PaymentStatus.PENDING
        self.submitted_by = submitted_by
        self.submitted_at = utc_now()
        self._update_timestamp()
        self.version += 1

    def approve(self, approved_by: str) -> None:
        """اعتماد الدفع"""
        if not self.status.can_transition_to(PaymentStatus.APPROVED):
            raise InvalidPaymentStatusTransitionError(
                self.status.value, PaymentStatus.APPROVED.value
            )

        self.status = PaymentStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = utc_now()
        self._update_timestamp()
        self.version += 1

        self._events.append(PaymentApprovedEvent(
            payment_id=self.id,
            payment_code=self.code,
            approved_by=approved_by,
            amount=self.amount,
        ))

    def reject(self, rejected_by: str, reason: str = "") -> None:
        """رفض الدفع"""
        if not self.status.can_transition_to(PaymentStatus.REJECTED):
            raise InvalidPaymentStatusTransitionError(
                self.status.value, PaymentStatus.REJECTED.value
            )

        self.status = PaymentStatus.REJECTED
        self._update_timestamp()
        self.version += 1

        self._events.append(PaymentRejectedEvent(
            payment_id=self.id,
            payment_code=self.code,
            rejected_by=rejected_by,
            reason=reason,
        ))

    def complete(self, completed_by: str) -> None:
        """إكمال الدفع (تنفيذ العملية)"""
        if not self.status.can_transition_to(PaymentStatus.COMPLETED):
            raise InvalidPaymentStatusTransitionError(
                self.status.value, PaymentStatus.COMPLETED.value
            )

        # التحقق من وجود صندوق للدفع النقدي
        if self.payment_method == PaymentMethod.CASH and not self.fund_id:
            raise ValueError("Fund required for cash payment")

        self.status = PaymentStatus.COMPLETED
        self.completed_by = completed_by
        self.completed_at = utc_now()
        self._update_timestamp()
        self.version += 1

        self._events.append(PaymentCompletedEvent(
            payment_id=self.id,
            payment_code=self.code,
            completed_by=completed_by,
            amount=self.amount,
            fund_id=self.fund_id,
            customer_branch_id=self.customer_branch_id,  # ✅ إضافة
            customer_branch_name=self.customer_branch_name,  # ✅ إضافة
        ))

    def cancel(self, cancelled_by: str, reason: str = "") -> None:
        """إلغاء الدفع"""
        if self.is_completed:
            raise PaymentAlreadyCompletedError(str(self.id))

        if not self.status.can_transition_to(PaymentStatus.CANCELLED):
            raise InvalidPaymentStatusTransitionError(
                self.status.value, PaymentStatus.CANCELLED.value
            )

        self.status = PaymentStatus.CANCELLED
        self._update_timestamp()
        self.version += 1

        self._events.append(PaymentCancelledEvent(
            payment_id=self.id,
            payment_code=self.code,
            cancelled_by=cancelled_by,
            reason=reason,
        ))

    def update(
        self,
        notes: Optional[str] = None,
        payment_method: Optional[PaymentMethod] = None,
        fund_id: Optional[str] = None,
        # ✅ إضافة معاملات فرع العميل
        customer_branch_id: Optional[str] = None,
        customer_branch_name: Optional[str] = None,
        customer_branch_code: Optional[str] = None,
        updated_by: str = "",
    ) -> None:
        """تحديث بيانات الدفع"""
        if self.is_completed:
            raise PaymentAlreadyCompletedError(str(self.id))
        if self.is_cancelled:
            raise PaymentAlreadyCancelledError(str(self.id))

        changed = False

        if notes is not None and notes != self.notes:
            self.notes = notes
            changed = True

        if payment_method is not None and payment_method != self.payment_method:
            self.payment_method = payment_method
            changed = True

        if fund_id is not None and fund_id != self.fund_id:
            self.fund_id = fund_id
            changed = True

        # ✅ تحديث فرع العميل
        if customer_branch_id is not None and customer_branch_id != self.customer_branch_id:
            self.customer_branch_id = customer_branch_id
            changed = True
        
        if customer_branch_name is not None and customer_branch_name != self.customer_branch_name:
            self.customer_branch_name = customer_branch_name
            changed = True
        
        if customer_branch_code is not None and customer_branch_code != self.customer_branch_code:
            self.customer_branch_code = customer_branch_code
            changed = True

        if changed:
            self._update_timestamp()
            self.updated_by = updated_by
            self.version += 1

            self._events.append(PaymentUpdatedEvent(
                payment_id=self.id,
                payment_code=self.code,
                updated_by=updated_by,
            ))

    # =========================================================================
    # التحقق (موجود)
    # =========================================================================

    def can_complete(self) -> tuple:
        """التحقق من إمكانية الإكمال"""
        errors = []

        if self.is_completed:
            errors.append("Payment already completed")
        if self.is_cancelled:
            errors.append("Payment is cancelled")

        if self.payment_method == PaymentMethod.CASH and not self.fund_id:
            errors.append("Fund required for cash payment")

        if self.amount.is_zero():
            errors.append("Payment amount cannot be zero")

        return len(errors) == 0, errors

    # =========================================================================
    # أحداث المجال (موجودة)
    # =========================================================================

    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events

    # =========================================================================
    # التمثيل النصي (محدث)
    # =========================================================================

    def __repr__(self) -> str:
        branch_info = f", branch={self.customer_branch_name or self.customer_branch_id}" if self.customer_branch_id else ""
        return f"Payment(id={self.id}, code={self.code}, type={self.payment_type}, customer={self.customer_name}{branch_info}, amount={self.amount}, status={self.status})"