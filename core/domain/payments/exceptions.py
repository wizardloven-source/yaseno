"""
Domain Exceptions for Payments Context
استثناءات مجال الدفعات
✅ محدث: إضافة استثناءات جديدة للمعالجات المتقدمة
"""


class PaymentError(Exception):
    """الاستثناء الأساسي لجميع أخطاء الدفعات"""
    pass


class PaymentNotFoundError(PaymentError):
    """يُرفع عندما لا يتم العثور على الدفعة"""
    def __init__(self, payment_id: str):
        self.payment_id = payment_id
        super().__init__(f"Payment not found: {payment_id}")


class DuplicatePaymentCodeError(PaymentError):
    """يُرفع عند محاولة إنشاء دفعة بكود مكرر"""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Payment code already exists: {code}")


class PaymentAlreadyCompletedError(PaymentError):
    """يُرفع عند محاولة تعديل دفعة مكتملة"""
    def __init__(self, payment_id: str):
        self.payment_id = payment_id
        super().__init__(f"Payment already completed: {payment_id}")


class PaymentAlreadyCancelledError(PaymentError):
    """يُرفع عند محاولة تعديل دفعة ملغية"""
    def __init__(self, payment_id: str):
        self.payment_id = payment_id
        super().__init__(f"Payment already cancelled: {payment_id}")


class InvalidPaymentStatusTransitionError(PaymentError):
    """يُرفع عند محاولة تغيير الحالة بشكل غير صحيح"""
    def __init__(self, current_status: str, new_status: str):
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(f"Cannot transition from {current_status} to {new_status}")


class InsufficientBalanceError(PaymentError):
    """يُرفع عند عدم كفاية الرصيد"""
    def __init__(self, available: float, requested: float):
        self.available = available
        self.requested = requested
        super().__init__(f"Insufficient balance: {available} < {requested}")


class PaymentAmountError(PaymentError):
    """يُرفع عند وجود خطأ في المبلغ"""
    def __init__(self, message: str):
        super().__init__(f"Payment amount error: {message}")


# =============================================================================
# ✅ استثناءات جديدة للمعالجات المتقدمة
# =============================================================================

class CannotCompletePaymentError(PaymentError):
    """يُرفع عند عدم إمكانية إكمال الدفعة"""
    def __init__(self, payment_id: str, reason: str):
        self.payment_id = payment_id
        self.reason = reason
        super().__init__(f"Cannot complete payment {payment_id}: {reason}")


class CannotCancelPaymentError(PaymentError):
    """يُرفع عند عدم إمكانية إلغاء الدفعة"""
    def __init__(self, payment_id: str, reason: str):
        self.payment_id = payment_id
        self.reason = reason
        super().__init__(f"Cannot cancel payment {payment_id}: {reason}")


class CannotApprovePaymentError(PaymentError):
    """يُرفع عند عدم إمكانية اعتماد الدفعة"""
    def __init__(self, payment_id: str, reason: str):
        self.payment_id = payment_id
        self.reason = reason
        super().__init__(f"Cannot approve payment {payment_id}: {reason}")


class CannotRejectPaymentError(PaymentError):
    """يُرفع عند عدم إمكانية رفض الدفعة"""
    def __init__(self, payment_id: str, reason: str):
        self.payment_id = payment_id
        self.reason = reason
        super().__init__(f"Cannot reject payment {payment_id}: {reason}")


class PaymentLineNotFoundError(PaymentError):
    """يُرفع عند عدم العثور على سطر الدفعة"""
    def __init__(self, line_id: str):
        self.line_id = line_id
        super().__init__(f"Payment line not found: {line_id}")


class PaymentLineAlreadyExistsError(PaymentError):
    """يُرفع عند محاولة إضافة سطر مكرر"""
    def __init__(self, reference_type: str, reference_id: str):
        self.reference_type = reference_type
        self.reference_id = reference_id
        super().__init__(f"Payment line already exists for {reference_type}: {reference_id}")


class FundNotFoundError(PaymentError):
    """يُرفع عند عدم العثور على الصندوق"""
    def __init__(self, fund_id: str):
        self.fund_id = fund_id
        super().__init__(f"Fund not found: {fund_id}")


class InsufficientFundBalanceError(PaymentError):
    """يُرفع عند عدم كفاية رصيد الصندوق"""
    def __init__(self, fund_id: str, balance: float, required: float):
        self.fund_id = fund_id
        self.balance = balance
        self.required = required
        super().__init__(
            f"Insufficient balance in fund {fund_id}. "
            f"Balance: {balance}, Required: {required}"
        )


class FundCurrencyMismatchError(PaymentError):
    """يُرفع عند عدم تطابق عملة الصندوق مع عملة الدفعة"""
    def __init__(self, fund_currency: str, payment_currency: str):
        self.fund_currency = fund_currency
        self.payment_currency = payment_currency
        super().__init__(
            f"Fund currency {fund_currency} does not match payment currency {payment_currency}"
        )


class PaymentReferenceNotFoundError(PaymentError):
    """يُرفع عند عدم العثور على المرجع (فاتورة، أمر شراء)"""
    def __init__(self, reference_type: str, reference_id: str):
        self.reference_type = reference_type
        self.reference_id = reference_id
        super().__init__(f"Reference not found: {reference_type} {reference_id}")


class PaymentReferenceAlreadyUsedError(PaymentError):
    """يُرفع عند استخدام المرجع في دفعة أخرى"""
    def __init__(self, reference_type: str, reference_id: str, payment_id: str):
        self.reference_type = reference_type
        self.reference_id = reference_id
        self.payment_id = payment_id
        super().__init__(
            f"Reference {reference_type}:{reference_id} already used in payment {payment_id}"
        )


class PaymentValidationError(PaymentError):
    """يُرفع عند فشل التحقق من صحة الدفعة"""
    def __init__(self, errors: list):
        self.errors = errors
        super().__init__(f"Payment validation failed: {', '.join(errors)}")


class PaymentNotDraftError(PaymentError):
    """يُرفع عند محاولة تعديل دفعة ليست مسودة"""
    def __init__(self, payment_id: str, status: str):
        self.payment_id = payment_id
        self.status = status
        super().__init__(f"Cannot modify payment {payment_id} in status: {status}")


# =============================================================================
# ✅ تصدير جميع الاستثناءات
# =============================================================================

__all__ = [
    # الاستثناءات الأساسية
    "PaymentError",
    "PaymentNotFoundError",
    "DuplicatePaymentCodeError",
    "PaymentAlreadyCompletedError",
    "PaymentAlreadyCancelledError",
    "InvalidPaymentStatusTransitionError",
    "InsufficientBalanceError",
    "PaymentAmountError",
    
    # الاستثناءات الجديدة
    "CannotCompletePaymentError",
    "CannotCancelPaymentError",
    "CannotApprovePaymentError",
    "CannotRejectPaymentError",
    "PaymentLineNotFoundError",
    "PaymentLineAlreadyExistsError",
    "FundNotFoundError",
    "InsufficientFundBalanceError",
    "FundCurrencyMismatchError",
    "PaymentReferenceNotFoundError",
    "PaymentReferenceAlreadyUsedError",
    "PaymentValidationError",
    "PaymentNotDraftError",
]