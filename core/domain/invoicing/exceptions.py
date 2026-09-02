# core/domain/invoicing/exceptions.py
"""
Domain Exceptions for Invoicing Context
✅ محدث: دعم استثناءات الضرائب
✅ محدث: دعم استثناءات سير العمل
✅ محدث: دعم استثناءات التعديل المتزامن
"""
from typing import Optional  # ✅ أضف هذا السطر


class InvoicingError(Exception):
    """Base exception for invoicing domain"""
    pass


# =============================================================================
# استثناءات الفاتورة الأساسية
# =============================================================================

class InvoiceNotFoundError(InvoicingError):
    """يُرفع عندما لا يتم العثور على الفاتورة"""
    def __init__(self, invoice_id: str):
        super().__init__(f"Invoice not found: {invoice_id}")
        self.invoice_id = invoice_id


class InvoiceAlreadyExistsError(InvoicingError):
    """يُرفع عند محاولة إنشاء فاتورة برقم موجود مسبقاً"""
    def __init__(self, invoice_number: str):
        super().__init__(f"Invoice already exists: {invoice_number}")
        self.invoice_number = invoice_number


class CannotModifyPostedInvoiceError(InvoicingError):
    """يُرفع عند محاولة تعديل فاتورة مرحّلة"""
    def __init__(self, invoice_id: str):
        super().__init__(f"Cannot modify posted invoice: {invoice_id}")
        self.invoice_id = invoice_id


class InvoiceAlreadyPostedError(InvoicingError):
    """يُرفع عند محاولة ترحيل فاتورة مرحّلة مسبقاً"""
    def __init__(self, invoice_id: str):
        super().__init__(f"Invoice already posted: {invoice_id}")
        self.invoice_id = invoice_id


class CannotCancelPostedInvoiceError(InvoicingError):
    """يُرفع عند محاولة إلغاء فاتورة مرحّلة"""
    def __init__(self, invoice_id: str, reason: str):
        super().__init__(f"Cannot cancel posted invoice {invoice_id}: {reason}")
        self.invoice_id = invoice_id


class InvoiceAlreadyCancelledError(InvoicingError):
    """يُرفع عند محاولة إلغاء فاتورة ملغاة مسبقاً"""
    def __init__(self, invoice_id: str):
        super().__init__(f"Invoice already cancelled: {invoice_id}")
        self.invoice_id = invoice_id


class CannotRestoreCancelledInvoiceError(InvoicingError):
    """يُرفع عند محاولة استعادة فاتورة ملغاة"""
    def __init__(self, invoice_id: str, reason: str):
        super().__init__(f"Cannot restore cancelled invoice {invoice_id}: {reason}")
        self.invoice_id = invoice_id


# =============================================================================
# استثناءات الضرائب
# =============================================================================

class InvoiceTaxCalculationError(InvoicingError):
    """يُرفع عند فشل حساب الضريبة"""
    def __init__(self, invoice_id: str, reason: str):
        super().__init__(f"Tax calculation failed for invoice {invoice_id}: {reason}")
        self.invoice_id = invoice_id
        self.reason = reason


class InvoiceTaxRuleNotFoundError(InvoicingError):
    """يُرفع عند عدم العثور على قاعدة ضريبية مناسبة"""
    def __init__(self, product_code: str, customer_id: Optional[str] = None):
        message = f"No tax rule found for product {product_code}"
        if customer_id:
            message += f" and customer {customer_id}"
        super().__init__(message)
        self.product_code = product_code
        self.customer_id = customer_id


class InvoiceTaxExemptionInvalidError(InvoicingError):
    """يُرفع عند محاولة تطبيق إعفاء ضريبي غير صالح"""
    def __init__(self, invoice_id: str, reason: str):
        super().__init__(f"Invalid tax exemption for invoice {invoice_id}: {reason}")
        self.invoice_id = invoice_id
        self.reason = reason


class InvoiceTaxRateInvalidError(InvoicingError):
    """يُرفع عند استخدام نسبة ضريبة غير صالحة"""
    def __init__(self, tax_rate: float, invoice_id: Optional[str] = None):
        message = f"Invalid tax rate: {tax_rate}%"
        if invoice_id:
            message += f" for invoice {invoice_id}"
        super().__init__(message)
        self.tax_rate = tax_rate
        self.invoice_id = invoice_id


class InvoiceTaxAmountMismatchError(InvoicingError):
    """يُرفع عند عدم تطابق مبلغ الضريبة المحسوب مع المبلغ المتوقع"""
    def __init__(self, invoice_id: str, calculated: float, expected: float):
        super().__init__(
            f"Tax amount mismatch for invoice {invoice_id}: "
            f"calculated {calculated}, expected {expected}"
        )
        self.invoice_id = invoice_id
        self.calculated = calculated
        self.expected = expected


# =============================================================================
# استثناءات البنود (Lines)
# =============================================================================

class InvoiceLineNotFoundError(InvoicingError):
    """يُرفع عند عدم العثور على سطر في الفاتورة"""
    def __init__(self, line_id: str, invoice_id: Optional[str] = None):
        message = f"Invoice line not found: {line_id}"
        if invoice_id:
            message += f" in invoice {invoice_id}"
        super().__init__(message)
        self.line_id = line_id
        self.invoice_id = invoice_id


class InvoiceLineQuantityError(InvoicingError):
    """يُرفع عند استخدام كمية غير صالحة"""
    def __init__(self, quantity: float, reason: str):
        super().__init__(f"Invalid quantity {quantity}: {reason}")
        self.quantity = quantity
        self.reason = reason


class InvoiceLinePriceError(InvoicingError):
    """يُرفع عند استخدام سعر غير صالح"""
    def __init__(self, price: float, reason: str):
        super().__init__(f"Invalid price {price}: {reason}")
        self.price = price
        self.reason = reason


class InvoiceLineCurrencyMismatchError(InvoicingError):
    """يُرفع عند اختلاف عملة السطر عن عملة الفاتورة"""
    def __init__(self, line_currency: str, invoice_currency: str):
        super().__init__(
            f"Currency mismatch: line currency {line_currency} "
            f"does not match invoice currency {invoice_currency}"
        )
        self.line_currency = line_currency
        self.invoice_currency = invoice_currency


# =============================================================================
# استثناءات العميل والمورد
# =============================================================================

class InvoiceCustomerRequiredError(InvoicingError):
    """يُرفع عند محاولة إنشاء فاتورة بدون عميل"""
    def __init__(self):
        super().__init__("Customer is required for invoice")


class InvoiceCustomerInvalidError(InvoicingError):
    """يُرفع عند استخدام عميل غير صالح"""
    def __init__(self, customer_id: str, reason: str):
        super().__init__(f"Invalid customer {customer_id}: {reason}")
        self.customer_id = customer_id
        self.reason = reason


class InvoiceCustomerBlockedError(InvoicingError):
    """يُرفع عند محاولة إنشاء فاتورة لعميل محظور"""
    def __init__(self, customer_id: str, customer_name: str):
        super().__init__(f"Customer {customer_name} ({customer_id}) is blocked")
        self.customer_id = customer_id
        self.customer_name = customer_name


# =============================================================================
# استثناءات الموقع
# =============================================================================

class InvoiceSiteRequiredError(InvoicingError):
    """يُرفع عند محاولة إنشاء فاتورة بدون موقع (إذا كان مطلوباً)"""
    def __init__(self):
        super().__init__("Site is required for this invoice")


class InvoiceSiteInvalidError(InvoicingError):
    """يُرفع عند استخدام موقع غير صالح"""
    def __init__(self, site_id: str, reason: str):
        super().__init__(f"Invalid site {site_id}: {reason}")
        self.site_id = site_id
        self.reason = reason


# =============================================================================
# استثناءات التزامن (Concurrency)
# =============================================================================

class InvoiceConcurrentModificationError(InvoicingError):
    """يُرفع عند محاولة تعديل فاتورة تم تعديلها من قبل مستخدم آخر"""
    def __init__(self, invoice_id: str, expected_version: int, actual_version: int):
        super().__init__(
            f"Invoice {invoice_id} was modified concurrently. "
            f"Expected version {expected_version}, got {actual_version}"
        )
        self.invoice_id = invoice_id
        self.expected_version = expected_version
        self.actual_version = actual_version


# =============================================================================
# استثناءات الصندوق والدفع
# =============================================================================

class InvoiceFundRequiredError(InvoicingError):
    """يُرفع عند محاولة ترحيل فاتورة نقدية بدون صندوق"""
    def __init__(self):
        super().__init__("Fund is required for cash invoice")


class InvoiceFundInvalidError(InvoicingError):
    """يُرفع عند استخدام صندوق غير صالح"""
    def __init__(self, fund_id: str, reason: str):
        super().__init__(f"Invalid fund {fund_id}: {reason}")
        self.fund_id = fund_id
        self.reason = reason


class InvoiceFundCurrencyMismatchError(InvoicingError):
    """يُرفع عند اختلاف عملة الصندوق عن عملة الفاتورة"""
    def __init__(self, fund_currency: str, invoice_currency: str):
        super().__init__(
            f"Fund currency {fund_currency} does not match invoice currency {invoice_currency}"
        )
        self.fund_currency = fund_currency
        self.invoice_currency = invoice_currency


# =============================================================================
# استثناءات التقارير والطباعة
# =============================================================================

class InvoicePrintError(InvoicingError):
    """يُرفع عند فشل طباعة الفاتورة"""
    def __init__(self, invoice_id: str, reason: str):
        super().__init__(f"Cannot print invoice {invoice_id}: {reason}")
        self.invoice_id = invoice_id
        self.reason = reason


class InvoiceExportError(InvoicingError):
    """يُرفع عند فشل تصدير الفاتورة"""
    def __init__(self, invoice_id: str, format: str, reason: str):
        super().__init__(f"Cannot export invoice {invoice_id} to {format}: {reason}")
        self.invoice_id = invoice_id
        self.format = format
        self.reason = reason


# =============================================================================
# استثناءات سير العمل (Workflow)
# =============================================================================

class InvoiceWorkflowError(InvoicingError):
    """يُرفع عند حدوث خطأ في سير عمل الفاتورة"""
    def __init__(self, invoice_id: str, current_status: str, action: str, reason: str):
        super().__init__(
            f"Cannot perform '{action}' on invoice {invoice_id} "
            f"in status '{current_status}': {reason}"
        )
        self.invoice_id = invoice_id
        self.current_status = current_status
        self.action = action
        self.reason = reason


class InvoiceApprovalRequiredError(InvoicingError):
    """يُرفع عند الحاجة إلى موافقة قبل تنفيذ إجراء"""
    def __init__(self, invoice_id: str, action: str):
        super().__init__(f"Approval required for '{action}' on invoice {invoice_id}")
        self.invoice_id = invoice_id
        self.action = action


class InvoiceApprovalRejectedError(InvoicingError):
    """يُرفع عند رفض الموافقة على الفاتورة"""
    def __init__(self, invoice_id: str, reason: str):
        super().__init__(f"Invoice {invoice_id} approval rejected: {reason}")
        self.invoice_id = invoice_id
        self.reason = reason


# =============================================================================
# تصدير جميع الاستثناءات
# =============================================================================

__all__ = [
    # الأساسية
    "InvoicingError",
    "InvoiceNotFoundError",
    "InvoiceAlreadyExistsError",
    "CannotModifyPostedInvoiceError",
    "InvoiceAlreadyPostedError",
    "CannotCancelPostedInvoiceError",
    "InvoiceAlreadyCancelledError",
    "CannotRestoreCancelledInvoiceError",
    
    # الضرائب
    "InvoiceTaxCalculationError",
    "InvoiceTaxRuleNotFoundError",
    "InvoiceTaxExemptionInvalidError",
    "InvoiceTaxRateInvalidError",
    "InvoiceTaxAmountMismatchError",
    
    # البنود
    "InvoiceLineNotFoundError",
    "InvoiceLineQuantityError",
    "InvoiceLinePriceError",
    "InvoiceLineCurrencyMismatchError",
    
    # العميل والمورد
    "InvoiceCustomerRequiredError",
    "InvoiceCustomerInvalidError",
    "InvoiceCustomerBlockedError",
    
    # الموقع
    "InvoiceSiteRequiredError",
    "InvoiceSiteInvalidError",
    
    # التزامن
    "InvoiceConcurrentModificationError",
    
    # الصندوق والدفع
    "InvoiceFundRequiredError",
    "InvoiceFundInvalidError",
    "InvoiceFundCurrencyMismatchError",
    
    # التقارير والطباعة
    "InvoicePrintError",
    "InvoiceExportError",
    
    # سير العمل
    "InvoiceWorkflowError",
    "InvoiceApprovalRequiredError",
    "InvoiceApprovalRejectedError",
]