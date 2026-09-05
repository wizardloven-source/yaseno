# core/shared/error_handler.py

"""
Unified Error Handler - Centralized error handling for the entire application
"""

import logging
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime
from dataclasses import dataclass, field

from .exceptions import (
    DomainError, ApplicationError, InfrastructureError,
    ValidationError, BusinessRuleViolation, NotFoundError,
    ConcurrentModificationError, PermissionDeniedError
)

logger = logging.getLogger(__name__)


@dataclass
class ErrorDetails:
    """هيكل بيانات تفاصيل الخطأ"""
    code: str
    message: str
    user_message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ErrorCodes:
    """رموز الخطأ الموحدة"""
    VALIDATION_FAILED = "ERR-001"
    ENTITY_NOT_FOUND = "ERR-002"
    UNBALANCED_ENTRY = "ERR-003"
    PERMISSION_DENIED = "ERR-401"
    CONCURRENT_MODIFICATION = "ERR-004"
    DATABASE_ERROR = "ERR-500"
    INTERNAL_ERROR = "ERR-500"
    NOT_FOUND = "ERR-404"


class ErrorHandler:
    """
    Centralized error handling with:
        1. Structured error responses
        2. Logging
        3. User-friendly messages
        4. Error recovery strategies
    """
    
    def __init__(self):
        self._handlers: Dict[type, Callable] = {}
        self._default_handler = self._default_error_handler
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default error handlers"""
        self.register(ValidationError, self._handle_validation_error)
        self.register(BusinessRuleViolation, self._handle_business_rule_error)
        self.register(NotFoundError, self._handle_not_found_error)
        self.register(ConcurrentModificationError, self._handle_concurrency_error)
        self.register(PermissionDeniedError, self._handle_permission_error)
        self.register(DomainError, self._handle_domain_error)
        self.register(ApplicationError, self._handle_application_error)
        self.register(InfrastructureError, self._handle_infrastructure_error)
        self.register(Exception, self._handle_unknown_error)
    
    def register(self, error_type: type, handler: Callable):
        """Register a custom error handler"""
        self._handlers[error_type] = handler
    
    def handle(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorDetails:
        """
        Handle an exception and return structured error details
        
        Args:
            error: The exception to handle
            context: Additional context (user_id, request_id, etc.)
        
        Returns:
            Structured error details
        """
        # Find handler for this error type
        handler = self._find_handler(type(error))
        
        # Handle the error
        error_details = handler(error, context or {})
        
        # Log the error
        self._log_error(error, error_details, context)
        
        return error_details
    
    def _find_handler(self, error_type: type) -> Callable:
        """Find the appropriate handler for an error type"""
        # Check exact match
        if error_type in self._handlers:
            return self._handlers[error_type]
        
        # Check parent classes
        for handler_type, handler in self._handlers.items():
            if issubclass(error_type, handler_type):
                return handler
        
        return self._default_handler
    
    def _log_error(self, error: Exception, details: ErrorDetails, context: Optional[Dict]):
        """Log error with full context"""
        log_data = {
            "error_code": details.code,
            "error_type": type(error).__name__,
            "message": details.message,
            "timestamp": details.timestamp,
        }
        if context:
            log_data["context"] = context
        
        # Log at appropriate level
        if details.code.startswith("ERR-4"):  # Permission errors
            logger.warning(log_data)
        elif details.code.startswith("ERR-3"):  # Not found errors
            logger.info(log_data)
        else:
            logger.error(log_data, exc_info=True)
    
    def _default_error_handler(self, error: Exception, context: Dict) -> ErrorDetails:
        """Default error handler for unregistered errors"""
        return ErrorDetails(
            code=ErrorCodes.INTERNAL_ERROR,
            message=str(error),
            user_message="حدث خطأ داخلي. الرجاء المحاولة مرة أخرى أو الاتصال بالدعم.",
            details={"original_error": str(error)}
        )
    
    def _handle_validation_error(self, error: ValidationError, context: Dict) -> ErrorDetails:
        """Handle validation errors"""
        return ErrorDetails(
            code=ErrorCodes.VALIDATION_FAILED,
            message=str(error),
            user_message="البيانات المدخلة غير صحيحة. الرجاء التحقق والمحاولة مرة أخرى.",
            details={"validation_errors": str(error)}
        )
    
    def _handle_business_rule_error(self, error: BusinessRuleViolation, context: Dict) -> ErrorDetails:
        """Handle business rule violations"""
        return ErrorDetails(
            code=ErrorCodes.UNBALANCED_ENTRY if "unbalanced" in str(error).lower() else ErrorCodes.VALIDATION_FAILED,
            message=str(error),
            user_message=str(error),
            details={"rule": str(error)}
        )
    
    def _handle_not_found_error(self, error: NotFoundError, context: Dict) -> ErrorDetails:
        """Handle entity not found errors"""
        entity_type = getattr(error, 'entity_type', 'العنصر')
        entity_id = getattr(error, 'entity_id', '')
        return ErrorDetails(
            code=ErrorCodes.NOT_FOUND,
            message=str(error),
            user_message=f"العنصر {entity_type} غير موجود.",
            details={"entity_type": entity_type, "entity_id": str(entity_id)}
        )
    
    def _handle_concurrency_error(self, error: ConcurrentModificationError, context: Dict) -> ErrorDetails:
        """Handle optimistic locking errors"""
        return ErrorDetails(
            code=ErrorCodes.CONCURRENT_MODIFICATION,
            message=str(error),
            user_message="تم تعديل هذا العنصر بواسطة مستخدم آخر. الرجاء تحديث الصفحة والمحاولة مرة أخرى.",
            details={
                "entity_type": getattr(error, 'entity_type', ''),
                "entity_id": str(getattr(error, 'entity_id', '')),
                "expected_version": getattr(error, 'expected_version', None),
                "actual_version": getattr(error, 'actual_version', None)
            }
        )
    
    def _handle_permission_error(self, error: PermissionDeniedError, context: Dict) -> ErrorDetails:
        """Handle permission denied errors"""
        return ErrorDetails(
            code=ErrorCodes.PERMISSION_DENIED,
            message=str(error),
            user_message="ليس لديك صلاحية للقيام بهذه العملية.",
            details={"permission": getattr(error, 'permission', ''), "user_id": getattr(error, 'user_id', '')}
        )
    
    def _handle_domain_error(self, error: DomainError, context: Dict) -> ErrorDetails:
        """Handle domain errors"""
        return ErrorDetails(
            code=ErrorCodes.VALIDATION_FAILED,
            message=str(error),
            user_message=str(error),
            details={"domain_error": str(error)}
        )
    
    def _handle_application_error(self, error: ApplicationError, context: Dict) -> ErrorDetails:
        """Handle application layer errors"""
        return ErrorDetails(
            code=ErrorCodes.INTERNAL_ERROR,
            message=str(error),
            user_message="حدث خطأ في التطبيق. الرجاء المحاولة مرة أخرى.",
            details={"app_error": str(error)}
        )
    
    def _handle_infrastructure_error(self, error: InfrastructureError, context: Dict) -> ErrorDetails:
        """Handle infrastructure errors (database, network, etc.)"""
        return ErrorDetails(
            code=ErrorCodes.DATABASE_ERROR,
            message=str(error),
            user_message="حدث خطأ في الاتصال بقاعدة البيانات. الرجاء المحاولة مرة أخرى.",
            details={"infra_error": str(error)}
        )
    
    def _handle_unknown_error(self, error: Exception, context: Dict) -> ErrorDetails:
        """Handle unknown errors"""
        return ErrorDetails(
            code=ErrorCodes.INTERNAL_ERROR,
            message=str(error),
            user_message="حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى.",
            details={"unknown_error": str(error)}
        )


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get global error handler instance"""
    return _error_handler


def handle_errors(func: Callable) -> Callable:
    """
    Decorator to automatically handle errors in handlers and views
    
    Usage:
        @handle_errors
        def my_handler(command):
            # code that might raise exceptions
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_details = _error_handler.handle(e)
            # Re-raise as appropriate or return error DTO
            raise type(e)(error_details.user_message) from e
    return wrapper