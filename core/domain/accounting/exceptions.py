"""
ACCOUNTING DOMAIN EXCEPTIONS - YAseen ERP ENTERPRISE VERSION
الإصدار المُصحَّح - v2.0.0

All exceptions that can occur within the core accounting domain.
These exceptions are purely domain-driven, containing no web/HTTP framework context,
and are raised by domain aggregates, entities, and domain services to protect invariant rules.

RULES:
    1. All business rule violations must inherit from AccountingError.
    2. Exceptions must accept and capture raw identifiers for precise audit mapping.
    3. Error messages must be clean, deterministic, and safe for structured log capture.
    4. Each exception has a unique error code for easy identification.
"""

from typing import Optional, List, Dict, Any

# ✅ استيراد الاستثناءات المشتركة
from core.shared.exceptions import ConcurrentModificationError, ValidationError


# ==============================================================================
# ========== BASE EXCEPTION ===================================================
# ==============================================================================

class AccountingError(Exception):
    """
    الاستثناء الأساسي لجميع أخطاء وقواعد العمل في النظام المحاسبي.
    
    Attributes:
        code: كود الخطأ الفريد (مثل "ACC-001")
        details: تفاصيل إضافية للخطأ
        cause: الاستثناء المسبب (إن وجد)
    """
    code: str = "ACC-000"
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.details = details or {}
        self.cause = cause
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الاستثناء إلى قاموس للتسجيل والتصحيح"""
        result = {
            "code": self.code,
            "message": str(self),
            "details": self.details
        }
        if self.cause:
            result["cause"] = str(self.cause)
        return result


# ==============================================================================
# ========== ENTRY VALIDATION ERRORS (أخطاء التحقق من القيود) =================
# ==============================================================================

class UnbalancedEntryError(AccountingError):
    """
    يُرفع عندما لا يتساوى إجمالي الجانب المدين مع الجانب الدائن في القيد المحاسبي.
    """
    code = "ACC-001"
    
    def __init__(self, debit_total, credit_total, entry_id=None, details=None):
        self.debit_total = debit_total
        self.credit_total = credit_total
        self.difference = abs(debit_total - credit_total)
        self.entry_id = entry_id
        message = f"Accounting Violation: Entry unbalanced. Total Debits={debit_total}, Total Credits={credit_total}, Difference={self.difference}"
        if entry_id:
            message += f" (Entry ID: {entry_id})"
        super().__init__(message, details)


class MultiCurrencyMismatchError(AccountingError):
    """
    ✅ يُرفع عند وجود تعارض بين العملات في نفس القيد.
    مُحسَّن: يتضمن العملات المتضاربة للتصحيح السريع.
    """
    code = "ACC-002"
    
    def __init__(
        self, 
        entry_id: str, 
        from_currency: str, 
        to_currency: str, 
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.entry_id = entry_id
        self.from_currency = from_currency
        self.to_currency = to_currency
        if message is None:
            message = f"Cannot mix {from_currency} and {to_currency} in the same entry"
        super().__init__(f"{message} (Entry ID: {entry_id})", details)


class InvalidLineError(AccountingError):
    """يُرفع عند إدخال سطر محاسبي يحتوي على قيم غير صالحة أو صفرية."""
    code = "ACC-003"
    
    def __init__(self, message, line_id=None, details=None):
        self.line_id = line_id
        super().__init__(message, details)


class JournalEntryValidationError(AccountingError):
    """
    ✅ جديد: يُرفع عند فشل التحقق من صحة القيد المحاسبي.
    يحتوي على قائمة بجميع أخطاء التحقق.
    """
    code = "ACC-004"
    
    def __init__(self, entry_id: str, errors: List[str], details: Optional[Dict[str, Any]] = None):
        self.entry_id = entry_id
        self.errors = errors
        message = f"Journal entry {entry_id} validation failed: {', '.join(errors)}"
        super().__init__(message, details)


class InvalidEntryDateError(AccountingError):
    """
    ✅ جديد: يُرفع عند استخدام تاريخ غير صالح لقيد محاسبي.
    """
    code = "ACC-005"
    
    def __init__(self, entry_date, reason: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.entry_date = entry_date
        self.reason = reason
        message = f"Invalid entry date: {entry_date}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, details)


# ==============================================================================
# ========== POSTING ERRORS (أخطاء الترحيل والأقفال) ===========================
# ==============================================================================

class AlreadyPostedError(AccountingError):
    """
    يُرفع عند محاولة ترحيل قيد تم ترحيله مسبقاً لمنع التكرار الحسابي.
    """
    code = "ACC-010"
    
    def __init__(self, entry_id: str, details: Optional[Dict[str, Any]] = None):
        self.entry_id = entry_id
        super().__init__(f"Security Action Blocked: Journal entry {entry_id} is already posted.", details)


class NotPostedError(AccountingError):
    """
    يُرفع عند محاولة إجراء تعديل أو قيد عكسي على قيد لا يزال في حالة مسودة.
    """
    code = "ACC-011"
    
    def __init__(self, entry_id: str, operation: str = "reverse", details: Optional[Dict[str, Any]] = None):
        self.entry_id = entry_id
        self.operation = operation
        super().__init__(f"Operation Refused: Cannot {operation} journal entry {entry_id} - it must be posted first.", details)


class PostedEntryModificationError(AccountingError):
    """
    يُرفع لمنع تعديل أو حذف أي قيد بعد ترحيله حفاظاً على النزاهة المالية التاريخية.
    """
    code = "ACC-012"
    
    def __init__(self, entry_id: str, operation: str = "modify", details: Optional[Dict[str, Any]] = None):
        self.entry_id = entry_id
        self.operation = operation
        super().__init__(f"Immutable Data Error: Cannot {operation} posted journal entry {entry_id}. You must issue a Reversal Entry instead.", details)


class ClosedPeriodError(AccountingError):
    """
    يُرفع عند محاولة إدراج أو ترحيل قيد ينتمي لفترة مالية مغلقة دفترياً.
    """
    code = "ACC-013"
    
    def __init__(self, period_name: str, entry_date=None, details: Optional[Dict[str, Any]] = None):
        self.period_name = period_name
        self.entry_date = entry_date
        message = f"Compliance Blocked: Cannot post to closed fiscal period: '{period_name}'"
        if entry_date:
            message += f" (Target Date: {entry_date})"
        super().__init__(message, details)


# ==============================================================================
# ========== REVERSAL ERRORS (أخطاء القيود العكسية والتسويات) =================
# ==============================================================================

class CannotReverseUnpostedError(AccountingError):
    """
    يُرفع عند محاولة تسوية قيد لم يرحل بالأساس.
    """
    code = "ACC-020"
    
    def __init__(self, entry_id: str, details: Optional[Dict[str, Any]] = None):
        self.entry_id = entry_id
        super().__init__(f"Validation Error: Cannot reverse unposted journal entry {entry_id}.", details)


class AlreadyReversedError(AccountingError):
    """
    يُرفع عند محاولة عمل أكثر من قيد عكسي لنفس القيد الأصلي.
    """
    code = "ACC-021"
    
    def __init__(self, entry_id: str, reversal_id: str, details: Optional[Dict[str, Any]] = None):
        self.entry_id = entry_id
        self.reversal_id = reversal_id
        super().__init__(f"Accounting Block: Journal entry {entry_id} has already been reversed by Reversal Entry {reversal_id}.", details)


class ReversalAlreadyExistsError(AccountingError):
    """
    ✅ جديد: يُرفع عند محاولة إنشاء قيد عكسي لقيد تم عكسه مسبقاً.
    أكثر تحديداً من AlreadyReversedError.
    """
    code = "ACC-022"
    
    def __init__(self, original_entry_id: str, reversal_entry_id: str, details: Optional[Dict[str, Any]] = None):
        self.original_entry_id = original_entry_id
        self.reversal_entry_id = reversal_entry_id
        super().__init__(
            f"Reversal already exists: Entry {original_entry_id} was already reversed by {reversal_entry_id}",
            details
        )


# ==============================================================================
# ========== REPOSITORY & CONCURRENCY ERRORS (أخطاء المستودعات والتزامن) =======
# ==============================================================================

class EntryNotFoundError(AccountingError):
    """
    يُرفع عندما يكون قيد اليومية المطلوب غير موجود في قاعدة البيانات.
    """
    code = "ACC-030"
    
    def __init__(self, entry_id: str, details: Optional[Dict[str, Any]] = None):
        self.entry_id = entry_id
        super().__init__(f"Data Entity Error: Journal entry {entry_id} not found in repository.", details)


class InvalidAccountError(AccountingError):
    """
    يُرفع عند الإشارة إلى رمز حساب غير معرف أو غير موجود في الدليل المحاسبي.
    """
    code = "ACC-031"
    
    def __init__(self, account_code: str, reason: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.account_code = account_code
        message = f"Chart of Accounts Error: Invalid account code '{account_code}'"
        if reason:
            message += f" - Reason: {reason}"
        super().__init__(message, details)


class InvalidPeriodError(AccountingError):
    """
    يُرفع عند الإشارة إلى فترة مالية غير معرفة في النظام.
    """
    code = "ACC-032"
    
    def __init__(self, period_name: str, details: Optional[Dict[str, Any]] = None):
        self.period_name = period_name
        super().__init__(f"Fiscal Period Error: Invalid or non-existent fiscal period reference: '{period_name}'", details)


class AccountAlreadyExistsError(AccountingError):
    """
    يُرفع عند محاولة إنشاء حساب برمز مكرر.
    """
    code = "ACC-040"
    
    def __init__(self, account_code: str, details: Optional[Dict[str, Any]] = None):
        self.account_code = account_code
        super().__init__(f"Constraint Error: Account code '{account_code}' already exists in the ledger architecture.", details)


class AccountHasTransactionsError(AccountingError):
    """
    يُرفع لمنع حذف حساب يمتلك حركات مالية مسجلة تاريخياً.
    """
    code = "ACC-041"
    
    def __init__(self, account_code: str, transaction_count: int, details: Optional[Dict[str, Any]] = None):
        self.account_code = account_code
        self.transaction_count = transaction_count
        super().__init__(
            f"Integrity Lock: Cannot delete account '{account_code}' because it has {transaction_count} active general ledger transactions.",
            details
        )


class AccountStructureViolationError(AccountingError):
    """
    يُرفع عند محاولة ترحيل قيد مباشرة على حساب رئيسي (أب) غير تحليلي.
    """
    code = "ACC-042"
    
    def __init__(self, account_code: str, details: Optional[Dict[str, Any]] = None):
        self.account_code = account_code
        super().__init__(
            f"Structural Mismatch: Account '{account_code}' is a Parent/Summary node. Direct journal transactions can only target final Leaf accounts.",
            details
        )


# ==============================================================================
# ========== PERIOD STATE ERRORS (أخطاء حالات الفترات المالية) =================
# ==============================================================================

class PeriodAlreadyClosedError(AccountingError):
    """
    يُرفع عند محاولة إغلاق فترة تم إقفالها مسبقاً.
    """
    code = "ACC-050"
    
    def __init__(self, period_name: str, details: Optional[Dict[str, Any]] = None):
        self.period_name = period_name
        super().__init__(f"Workflow Violation: Fiscal period '{period_name}' is already closed and locked.", details)


class PeriodAlreadyOpenError(AccountingError):
    """
    ✅ مُحسَّن: يُرفع عند محاولة فتح فترة مالية وهي مفتوحة بالفعل.
    تم تغيير الاسم من PeriodNotClosedError ليكون أكثر دقة.
    """
    code = "ACC-051"
    
    def __init__(self, period_name: str, details: Optional[Dict[str, Any]] = None):
        self.period_name = period_name
        super().__init__(f"Workflow Violation: Fiscal period '{period_name}' is already open.", details)


# توفير اسم مستعار للتوافق مع الإصدارات السابقة
PeriodNotClosedError = PeriodAlreadyOpenError


class PeriodHasUnpostedEntriesError(AccountingError):
    """
    يُرفع لمنع إقفال الفترة المالية قبل ترحيل أو حذف كافة المسودات المعلقة.
    """
    code = "ACC-052"
    
    def __init__(self, period_name: str, unposted_count: int, details: Optional[Dict[str, Any]] = None):
        self.period_name = period_name
        self.unposted_count = unposted_count
        super().__init__(
            f"Compliance Failure: Cannot close fiscal period '{period_name}' - there are {unposted_count} unposted draft journal entries that must be posted or purged first.",
            details
        )


# ==============================================================================
# ========== FUND RELATED EXCEPTIONS (استثناءات الصناديق النقدية) ==============
# ==============================================================================

class InsufficientFundsError(AccountingError):
    """
    ✅ جديد: يُرفع عند محاولة سحب مبلغ أكبر من رصيد الصندوق.
    """
    code = "ACC-060"
    
    def __init__(self, fund_code: str, balance: float, requested: float, details: Optional[Dict[str, Any]] = None):
        self.fund_code = fund_code
        self.balance = balance
        self.requested = requested
        super().__init__(
            f"Insufficient balance in fund {fund_code}. Balance: {balance}, Requested: {requested}",
            details
        )


class FundNotFoundError(AccountingError):
    """
    ✅ جديد: يُرفع عند عدم العثور على الصندوق المطلوب.
    """
    code = "ACC-061"
    
    def __init__(self, fund_id: str, details: Optional[Dict[str, Any]] = None):
        self.fund_id = fund_id
        super().__init__(f"Fund not found: {fund_id}", details)


class FundCurrencyMismatchError(AccountingError):
    """
    ✅ جديد: يُرفع عند عدم تطابق عملة الصندوق مع عملة المعاملة.
    """
    code = "ACC-062"
    
    def __init__(self, fund_currency: str, transaction_currency: str, details: Optional[Dict[str, Any]] = None):
        self.fund_currency = fund_currency
        self.transaction_currency = transaction_currency
        super().__init__(
            f"Currency mismatch: Fund currency is {fund_currency}, but transaction currency is {transaction_currency}",
            details
        )


# ==============================================================================
# ========== EXPORTS ==========
# ==============================================================================

__all__ = [
    # Base
    "AccountingError",
    
    # Entry Validation
    "UnbalancedEntryError",
    "MultiCurrencyMismatchError",
    "InvalidLineError",
    "JournalEntryValidationError",
    "InvalidEntryDateError",
    
    # Posting
    "AlreadyPostedError",
    "NotPostedError",
    "PostedEntryModificationError",
    "ClosedPeriodError",
    
    # Reversal
    "CannotReverseUnpostedError",
    "AlreadyReversedError",
    "ReversalAlreadyExistsError",
    
    # Repository
    "EntryNotFoundError",
    "InvalidAccountError",
    "InvalidPeriodError",
    "AccountAlreadyExistsError",
    "AccountHasTransactionsError",
    "AccountStructureViolationError",
    
    # Period State
    "PeriodAlreadyClosedError",
    "PeriodAlreadyOpenError",
    "PeriodNotClosedError",  # Alias for compatibility
    "PeriodHasUnpostedEntriesError",
    
    # Funds
    "InsufficientFundsError",
    "FundNotFoundError",
    "FundCurrencyMismatchError",
    
    # Shared (re-exported)
    "ConcurrentModificationError",
    "ValidationError",
]