# core/bootstrap/middleware/error_handling.py
"""
Error Handling Middleware - معالجة الأخطاء الموحدة
"""

from typing import Any, Dict, Optional, Type
import logging
import traceback

from .base import Middleware

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(Middleware):
    """
    Middleware لمعالجة الأخطاء بشكل موحد
    
    الميزات:
        1. تحويل الاستثناءات إلى استجابات موحدة
        2. تسجيل الأخطاء بتفاصيل كاملة
        3. إعادة محاولة العمليات الفاشلة (اختياري)
        4. تحويل الأخطاء إلى رسائل مفهومة للمستخدم
    """
    
    def __init__(
        self,
        error_map: Optional[Dict[Type[Exception], str]] = None,
        default_error_message: str = "حدث خطأ غير متوقع",
        retry_count: int = 0,
        log_exceptions: bool = True
    ):
        """
        Args:
            error_map: خريطة تحويل الاستثناءات إلى رسائل
            default_error_message: الرسالة الافتراضية للاستثناءات غير المعروفة
            retry_count: عدد مرات إعادة المحاولة
            log_exceptions: تسجيل الاستثناءات
        """
        self._error_map = error_map or {}
        self._default_error_message = default_error_message
        self._retry_count = retry_count
        self._log_exceptions = log_exceptions
        
        # تسجيل الاستثناءات المدمجة
        self._register_builtin_errors()
    
    def _register_builtin_errors(self) -> None:
        """تسجيل الاستثناءات المدمجة"""
        # استثناءات الأعمال
        try:
            from core.shared.exceptions import (
                DomainError, ValidationError, NotFoundError,
                PermissionDeniedError, BusinessRuleViolation,
                ConcurrentModificationError
            )
            self._error_map[ValidationError] = "البيانات المدخلة غير صحيحة"
            self._error_map[NotFoundError] = "العنصر غير موجود"
            self._error_map[PermissionDeniedError] = "ليس لديك صلاحية لهذه العملية"
            self._error_map[BusinessRuleViolation] = "انتهاك قاعدة عمل"
            self._error_map[ConcurrentModificationError] = "تم تعديل العنصر بواسطة مستخدم آخر"
        except ImportError:
            pass
        
        # استثناءات المحاسبة
        try:
            from core.domain.accounting.exceptions import (
                UnbalancedEntryError, AlreadyPostedError,
                ClosedPeriodError, CannotReverseUnpostedError
            )
            self._error_map[UnbalancedEntryError] = "القيد المحاسبي غير متوازن"
            self._error_map[AlreadyPostedError] = "القيد مرحلة مسبقاً"
            self._error_map[ClosedPeriodError] = "الفترة المالية مغلقة"
            self._error_map[CannotReverseUnpostedError] = "لا يمكن عكس قيد غير مرحل"
        except ImportError:
            pass
    
    def before(self, command: Any, context: Dict) -> Dict:
        """إضافة معلومات إضافية للسياق"""
        context['_error_handling_attempts'] = 0
        return context
    
    def after(self, command: Any, result: Any, context: Dict) -> Any:
        """لا يوجد منطق بعد التنفيذ"""
        return result
    
    def handle_error(self, command: Any, error: Exception, context: Dict) -> Optional[Any]:
        """
        معالجة الأخطاء وتحويلها إلى استجابات موحدة
        
        الميزات:
            1. تسجيل الخطأ
            2. تحويل إلى رسالة مفهومة
            3. إعادة محاولة (إذا كان ذلك ممكناً)
            4. إرجاع استجابة خطأ موحدة
        """
        # تسجيل الخطأ
        if self._log_exceptions:
            self._log_error(command, error, context)
        
        # إعادة محاولة
        attempts = context.get('_error_handling_attempts', 0)
        if attempts < self._retry_count:
            context['_error_handling_attempts'] = attempts + 1
            logger.info(f"🔄 Retrying command (attempt {attempts + 1}/{self._retry_count})")
            # إعادة رفع الاستثناء لتنفيذ إعادة المحاولة
            raise error
        
        # تحويل الخطأ إلى استجابة موحدة
        error_response = self._create_error_response(error, context)
        
        # إرجاع استجابة الخطأ (بدلاً من رفع استثناء)
        return error_response
    
    def _log_error(self, command: Any, error: Exception, context: Dict) -> None:
        """تسجيل الخطأ بتفاصيل كاملة"""
        command_name = self._get_command_name(command)
        error_type = type(error).__name__
        error_message = str(error)
        
        log_data = {
            'command': command_name,
            'error_type': error_type,
            'error_message': error_message,
            'user_id': context.get('user_id', 'unknown'),
            'timestamp': self._get_current_time(),
        }
        
        # إضافة تتبع الاستثناء
        log_data['traceback'] = traceback.format_exc()
        
        # تسجيل حسب مستوى الخطأ
        if self._is_critical_error(error):
            logger.critical(f"💀 Critical error in {command_name}: {error_message}", extra=log_data)
        elif self._is_business_error(error):
            logger.warning(f"⚠️ Business error in {command_name}: {error_message}", extra=log_data)
        else:
            logger.error(f"❌ Error in {command_name}: {error_message}", extra=log_data, exc_info=True)
    
    def _create_error_response(self, error: Exception, context: Dict) -> Dict:
        """إنشاء استجابة خطأ موحدة"""
        # الحصول على رسالة الخطأ من الخريطة
        error_message = self._default_error_message
        error_code = "INTERNAL_ERROR"
        
        for exc_type, message in self._error_map.items():
            if isinstance(error, exc_type):
                error_message = message
                error_code = exc_type.__name__.upper()
                break
        
        # استثناءات محددة
        if hasattr(error, 'code'):
            error_code = error.code
        
        if hasattr(error, 'details'):
            details = error.details
        else:
            details = {'error': str(error)}
        
        # إنشاء الاستجابة
        response = {
            'success': False,
            'error': {
                'code': error_code,
                'message': error_message,
                'details': details,
                'timestamp': self._get_current_time(),
                'command': self._get_command_name(context.get('_command', 'unknown'))
            }
        }
        
        # إضافة معلومات إضافية في وضع التصحيح
        if context.get('debug', False):
            response['error']['traceback'] = traceback.format_exc()
            response['error']['error_type'] = type(error).__name__
        
        return response
    
    def _is_critical_error(self, error: Exception) -> bool:
        """التحقق مما إذا كان الخطأ حرجاً"""
        critical_types = [
            'SystemError', 'MemoryError', 'KeyboardInterrupt',
            'DatabaseError', 'ConnectionError'
        ]
        return type(error).__name__ in critical_types
    
    def _is_business_error(self, error: Exception) -> bool:
        """التحقق مما إذا كان الخطأ من نوع أخطاء الأعمال"""
        business_types = [
            'ValidationError', 'NotFoundError', 'PermissionDeniedError',
            'BusinessRuleViolation', 'DomainError'
        ]
        return type(error).__name__ in business_types
    
    def _get_command_name(self, command: Any) -> str:
        if hasattr(command, '__class__'):
            return command.__class__.__name__
        return str(command)
    
    def _get_current_time(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
    
    @property
    def priority(self) -> int:
        # ينفذ أخيراً (قبل التنفيذ الفعلي)
        return 90
    
    @property
    def name(self) -> str:
        return "error_handling"