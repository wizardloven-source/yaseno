# core/shared/exceptions.py
"""
Shared Exceptions - نظام استثناءات موحد للنظام
الإصدار: 2.0.0

هذا الملف يحتوي على جميع الاستثناءات المستخدمة في النظام،
مرتبة حسب طبقات الهندسة المعمارية.
"""
from decimal import Decimal

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# استثناءات أساسية
# ============================================================================

class BaseError(Exception):
    """
    الاستثناء الأساسي لجميع أخطاء النظام
    
    يحتوي على:
        - message: رسالة الخطأ
        - code: رمز الخطأ (فريد)
        - details: تفاصيل إضافية (اختياري)
        - timestamp: وقت حدوث الخطأ
    """
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now()
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الاستثناء إلى قاموس للتسلسل"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code}, message={self.message})"


class DomainError(BaseError):
    """الاستثناء الأساسي لجميع أخطاء مجال الأعمال"""
    pass


class ApplicationError(BaseError):
    """الاستثناء الأساسي لجميع أخطاء طبقة التطبيق"""
    pass


class InfrastructureError(BaseError):
    """الاستثناء الأساسي لجميع أخطاء البنية التحتية"""
    pass


class PresentationError(BaseError):
    """الاستثناء الأساسي لجميع أخطاء طبقة العرض"""
    pass


# ============================================================================
# استثناءات مجال الأعمال (Domain)
# ============================================================================

class ValidationError(DomainError):
    """
    خطأ في التحقق من صحة البيانات
    
    يُستخدم عندما تفشل البيانات في اجتياز قواعد التحقق.
    """
    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
        super().__init__(message, code="ERR_VALIDATION", details=details)
        self.field = field
        self.value = value


class BusinessRuleViolation(DomainError):
    """
    انتهاك قاعدة عمل
    
    يُستخدم عندما يحاول المستخدم تنفيذ عملية تخالف قواعد العمل.
    """
    def __init__(self, message: str, rule_name: Optional[str] = None):
        details = {}
        if rule_name:
            details["rule_name"] = rule_name
        super().__init__(message, code="ERR_BUSINESS_RULE", details=details)
        self.rule_name = rule_name


class NotFoundError(DomainError):
    """
    الكيان غير موجود
    
    يُستخدم عندما لا يتم العثور على كيان مطلوب.
    """
    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} with id '{entity_id}' not found",
            code="ERR_NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": entity_id}
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class ConcurrentModificationError(DomainError):
    """
    تعديل متزامن - فشل القفل التفاؤلي
    
    يُستخدم عندما يحاول مستخدمان تعديل نفس الكيان في نفس الوقت.
    """
    def __init__(
        self,
        entity_type: str,
        entity_id: str,
        expected_version: int,
        actual_version: int
    ):
        super().__init__(
            message=f"{entity_type} '{entity_id}' was modified concurrently. "
                    f"Expected version {expected_version}, got {actual_version}",
            code="ERR_CONCURRENT_MODIFICATION",
            details={
                "entity_type": entity_type,
                "entity_id": entity_id,
                "expected_version": expected_version,
                "actual_version": actual_version
            }
        )
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.expected_version = expected_version
        self.actual_version = actual_version


class DuplicateError(DomainError):
    """
    عنصر مكرر
    
    يُستخدم عند محاولة إنشاء عنصر يوجد بالفعل.
    """
    def __init__(self, entity_type: str, field: str, value: str):
        super().__init__(
            message=f"{entity_type} with {field} '{value}' already exists",
            code="ERR_DUPLICATE",
            details={"entity_type": entity_type, "field": field, "value": value}
        )
        self.entity_type = entity_type
        self.field = field
        self.value = value


# ============================================================================
# استثناءات المحاسبة (Accounting)
# ============================================================================

class AccountingError(DomainError):
    """استثناء أساسي لأخطاء المحاسبة"""
    pass


class UnbalancedEntryError(AccountingError):
    """القيد المحاسبي غير متوازن"""
    def __init__(self, debit_total: Decimal, credit_total: Decimal, entry_id: Optional[str] = None):
        details = {
            "debit_total": str(debit_total),
            "credit_total": str(credit_total),
            "difference": str(abs(debit_total - credit_total))
        }
        if entry_id:
            details["entry_id"] = entry_id
        super().__init__(
            message=f"Journal entry is unbalanced: debit {debit_total} != credit {credit_total}",
            code="ERR_UNBALANCED_ENTRY",
            details=details
        )
        self.debit_total = debit_total
        self.credit_total = credit_total
        self.difference = abs(debit_total - credit_total)


class AlreadyPostedError(AccountingError):
    """القيد مرحلة مسبقاً"""
    def __init__(self, entry_id: str):
        super().__init__(
            message=f"Journal entry {entry_id} is already posted",
            code="ERR_ALREADY_POSTED",
            details={"entry_id": entry_id}
        )
        self.entry_id = entry_id


class NotPostedError(AccountingError):
    """القيد غير مرحل"""
    def __init__(self, entry_id: str, operation: str = "reverse"):
        super().__init__(
            message=f"Cannot {operation} journal entry {entry_id} - it must be posted first",
            code="ERR_NOT_POSTED",
            details={"entry_id": entry_id, "operation": operation}
        )
        self.entry_id = entry_id
        self.operation = operation


class ClosedPeriodError(AccountingError):
    """الفترة المالية مغلقة"""
    def __init__(self, period_name: str, entry_date: Optional[str] = None):
        details = {"period_name": period_name}
        if entry_date:
            details["entry_date"] = entry_date
        super().__init__(
            message=f"Cannot post to closed fiscal period: '{period_name}'",
            code="ERR_CLOSED_PERIOD",
            details=details
        )
        self.period_name = period_name


# ============================================================================
# استثناءات طبقة التطبيق (Application)
# ============================================================================

class PermissionDeniedError(ApplicationError):
    """صلاحية مرفوضة"""
    def __init__(self, permission: str, user_id: str, resource: Optional[str] = None):
        details = {"permission": permission, "user_id": user_id}
        if resource:
            details["resource"] = resource
        super().__init__(
            message=f"User {user_id} does not have permission '{permission}'",
            code="ERR_PERMISSION_DENIED",
            details=details
        )
        self.permission = permission
        self.user_id = user_id
        self.resource = resource


class InvalidOperationError(ApplicationError):
    """عملية غير صالحة في السياق الحالي"""
    def __init__(self, message: str, operation: Optional[str] = None, state: Optional[str] = None):
        details = {}
        if operation:
            details["operation"] = operation
        if state:
            details["current_state"] = state
        super().__init__(message, code="ERR_INVALID_OPERATION", details=details)
        self.operation = operation
        self.state = state


class CommandNotFoundError(ApplicationError):
    """الأمر غير موجود"""
    def __init__(self, command_type: str):
        super().__init__(
            message=f"No handler registered for command: {command_type}",
            code="ERR_COMMAND_NOT_FOUND",
            details={"command_type": command_type}
        )
        self.command_type = command_type


class QueryNotFoundError(ApplicationError):
    """الاستعلام غير موجود"""
    def __init__(self, query_type: str):
        super().__init__(
            message=f"No handler registered for query: {query_type}",
            code="ERR_QUERY_NOT_FOUND",
            details={"query_type": query_type}
        )
        self.query_type = query_type


# ============================================================================
# استثناءات البنية التحتية (Infrastructure)
# ============================================================================

class DatabaseError(InfrastructureError):
    """خطأ في قاعدة البيانات"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(
            message=message,
            code="ERR_DATABASE",
            details=details,
            cause=original_error
        )


class ConnectionError(InfrastructureError):
    """خطأ في الاتصال"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(
            message=message,
            code="ERR_CONNECTION",
            details=details,
            cause=original_error
        )


# ============================================================================
# استثناءات أمنية (Security)
# ============================================================================

class AuthenticationError(ApplicationError):
    """خطأ في المصادقة"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, code="ERR_AUTHENTICATION")


class SessionExpiredError(ApplicationError):
    """انتهت صلاحية الجلسة"""
    def __init__(self, message: str = "Session has expired"):
        super().__init__(message, code="ERR_SESSION_EXPIRED")


# ============================================================================
# دوال مساعدة
# ============================================================================

def is_error_of_type(error: Exception, error_type: type) -> bool:
    """التحقق من أن الخطأ من نوع معين أو يرث منه"""
    return isinstance(error, error_type)


def get_error_code(error: Exception) -> str:
    """الحصول على رمز الخطأ من الاستثناء"""
    if hasattr(error, 'code'):
        return error.code
    return error.__class__.__name__


def get_error_details(error: Exception) -> Dict[str, Any]:
    """الحصول على تفاصيل الخطأ من الاستثناء"""
    if hasattr(error, 'details'):
        return error.details
    return {}


def error_to_dict(error: Exception) -> Dict[str, Any]:
    """تحويل أي استثناء إلى قاموس موحد"""
    if isinstance(error, BaseError):
        return error.to_dict()
    
    return {
        "code": error.__class__.__name__,
        "message": str(error),
        "details": {},
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# مدير الأخطاء المركزي (Error Handler)
# ============================================================================

class ErrorHandler:
    """
    مدير الأخطاء المركزي
    
    يوفر:
        - تسجيل الأخطاء
        - تحويل الاستثناءات إلى استجابات موحدة
        - تجميع الأخطاء المتعددة
    """
    
    def __init__(self):
        self._errors: List[BaseError] = []
    
    def add_error(self, error: BaseError) -> None:
        """إضافة خطأ إلى المجموعة"""
        self._errors.append(error)
    
    def add_errors(self, errors: List[BaseError]) -> None:
        """إضافة مجموعة أخطاء"""
        self._errors.extend(errors)
    
    def has_errors(self) -> bool:
        """التحقق من وجود أخطاء"""
        return len(self._errors) > 0
    
    def get_errors(self) -> List[BaseError]:
        """الحصول على جميع الأخطاء"""
        return self._errors.copy()
    
    def clear(self) -> None:
        """مسح جميع الأخطاء"""
        self._errors.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل جميع الأخطاء إلى قاموس"""
        return {
            "has_errors": self.has_errors(),
            "errors": [error.to_dict() for error in self._errors],
            "count": len(self._errors)
        }
    
    def raise_if_has_errors(self) -> None:
        """رفع استثناء إذا كان هناك أخطاء"""
        if self.has_errors():
            messages = [e.message for e in self._errors]
            raise ValidationError(
                f"Validation failed with {len(self._errors)} errors: {', '.join(messages)}",
                details={"errors": [e.to_dict() for e in self._errors]}
            )


# ============================================================================
# ديكوراتورات لمعالجة الأخطاء
# ============================================================================

def handle_errors(func):
    """
    ديكوراتور لمعالجة الأخطاء في الدوال
    
    يلتقط جميع الاستثناءات ويحولها إلى BaseError.
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseError:
            raise
        except Exception as e:
            raise InfrastructureError(
                f"Unexpected error in {func.__name__}: {str(e)}",
                cause=e
            ) from e
    return wrapper


def log_errors(func):
    """
    ديكوراتور لتسجيل الأخطاء
    
    يسجل جميع الاستثناءات قبل إعادة رفعها.
    """
    from functools import wraps
    import logging
    
    logger = logging.getLogger(func.__module__)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BaseError as e:
            logger.error(f"Error in {func.__name__}: {e.code} - {e.message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise
    return wrapper


# ============================================================================
# تصدير الكلاسات والدوال
# ============================================================================

__all__ = [
    # استثناءات أساسية
    "BaseError",
    "DomainError",
    "ApplicationError",
    "InfrastructureError",
    "PresentationError",
    
    # استثناءات مجال الأعمال
    "ValidationError",
    "BusinessRuleViolation",
    "NotFoundError",
    "ConcurrentModificationError",
    "DuplicateError",
    
    # استثناءات المحاسبة
    "AccountingError",
    "UnbalancedEntryError",
    "AlreadyPostedError",
    "NotPostedError",
    "ClosedPeriodError",
    
    # استثناءات التطبيق
    "PermissionDeniedError",
    "InvalidOperationError",
    "CommandNotFoundError",
    "QueryNotFoundError",
    
    # استثناءات البنية التحتية
    "DatabaseError",
    "ConnectionError",
    
    # استثناءات أمنية
    "AuthenticationError",
    "SessionExpiredError",
    
    # دوال مساعدة
    "is_error_of_type",
    "get_error_code",
    "get_error_details",
    "error_to_dict",
    
    # مدير الأخطاء
    "ErrorHandler",
    
    # ديكوراتورات
    "handle_errors",
    "log_errors",
]