# core/bootstrap/middleware/validation.py
"""
Validation Middleware - التحقق من صحة البيانات
مستخرج من infrastructure/messaging/middleware.py
"""

from typing import Any, Dict, Optional, List
import logging

from .base import Middleware

logger = logging.getLogger(__name__)


class ValidationMiddleware(Middleware):
    """
    Middleware للتحقق من صحة البيانات قبل تنفيذ الأمر
    
    الميزات:
        1. التحقق من الحقول المطلوبة
        2. التحقق من أنواع البيانات
        3. التحقق من القيم المسموحة
        4. دعم التحقق المخصص عبر دالة validate()
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Args:
            strict_mode: إذا كان True، يتم رفع استثناء عند أي خطأ في التحقق
        """
        self._strict_mode = strict_mode
    
    def before(self, command: Any, context: Dict) -> Dict:
        """التحقق من صحة الأمر قبل التنفيذ"""
        # إذا كان الأمر يحتوي على دالة validate
        if hasattr(command, 'validate'):
            try:
                is_valid, errors = command.validate()
                if not is_valid:
                    from core.shared.exceptions import ValidationError
                    raise ValidationError(
                        f"Validation failed: {', '.join(errors)}",
                        details={'errors': errors, 'command': self._get_command_name(command)}
                    )
            except Exception as e:
                if self._strict_mode:
                    raise
                logger.warning(f"Validation error: {e}")
        
        # التحقق من الحقول المطلوبة (إذا كان الأمر يحتوي على required_fields)
        if hasattr(command, 'required_fields'):
            required = getattr(command, 'required_fields')
            missing = []
            for field in required:
                if not hasattr(command, field) or getattr(command, field) is None:
                    missing.append(field)
            
            if missing:
                from core.shared.exceptions import ValidationError
                raise ValidationError(
                    f"Missing required fields: {', '.join(missing)}",
                    details={'missing_fields': missing, 'command': self._get_command_name(command)}
                )
        
        # التحقق من أنواع البيانات (إذا كان الأمر يحتوي على field_types)
        if hasattr(command, 'field_types'):
            field_types = getattr(command, 'field_types')
            for field, expected_type in field_types.items():
                if hasattr(command, field):
                    value = getattr(command, field)
                    if value is not None and not isinstance(value, expected_type):
                        from core.shared.exceptions import ValidationError
                        raise ValidationError(
                            f"Field '{field}' must be of type {expected_type.__name__}, got {type(value).__name__}",
                            details={'field': field, 'expected': str(expected_type), 'actual': str(type(value))}
                        )
        
        return context
    
    def after(self, command: Any, result: Any, context: Dict) -> Any:
        """التحقق من صحة النتيجة (اختياري)"""
        # إذا كانت النتيجة تحتوي على دالة validate_result
        if hasattr(result, 'validate_result'):
            try:
                is_valid, errors = result.validate_result()
                if not is_valid:
                    logger.warning(f"Result validation failed: {', '.join(errors)}")
            except Exception as e:
                logger.warning(f"Result validation error: {e}")
        
        return result
    
    def handle_error(self, command: Any, error: Exception, context: Dict) -> Optional[Any]:
        """معالجة أخطاء التحقق"""
        if isinstance(error, ValidationError):
            logger.warning(f"⚠️ Validation error: {error}")
        return None
    
    def _get_command_name(self, command: Any) -> str:
        if hasattr(command, '__class__'):
            return command.__class__.__name__
        return str(command)
    
    @property
    def priority(self) -> int:
        # ينفذ بعد الصلاحيات
        return 50
    
    @property
    def name(self) -> str:
        return "validation"


class ValidationError(Exception):
    """استثناء يحدث عند فشل التحقق من صحة البيانات"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        self.details = details or {}
        super().__init__(message)