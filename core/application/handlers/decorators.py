# core/application/handlers/decorators.py
"""
Handlers Decorators - ديكوراتورات موحدة للمعالجات
الإصدار: 1.0.0

الميزات:
    1. معالجة استثناءات التعديل المتزامن (ConcurrentModificationError)
    2. تسجيل تنفيذ المعالجات
    3. قياس وقت التنفيذ
    4. معالجة الأخطاء الموحدة
"""

from functools import wraps
from typing import Callable, TypeVar, Any, Optional
import logging
import time
from datetime import datetime

from core.shared.exceptions import ConcurrentModificationError
from core.application.security.authorization import UserContext

logger = logging.getLogger(__name__)

T = TypeVar('T')


def handle_concurrent_modification(func: Callable) -> Callable:
    """
    Decorator لالتقاط ConcurrentModificationError وإعادة رفعه مع رسالة واضحة
    
    الاستخدام:
        @handle_concurrent_modification
        def handle(self, command, user_context):
            # منطق التحديث
            pass
    
    Args:
        func: الدالة المراد تزيينها
    
    Returns:
        Callable: الدالة المزينة
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConcurrentModificationError as e:
            # ✅ تسجيل الخطأ
            logger.warning(
                f"Concurrent modification detected: {e.entity_type} {e.entity_id} "
                f"(expected: {e.expected_version}, actual: {e.actual_version})"
            )
            # ✅ إعادة رفع الاستثناء مع رسالة مفهومة
            raise ConcurrentModificationError(
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                expected_version=e.expected_version,
                actual_version=e.actual_version
            ) from e
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise
    
    return wrapper


def log_handler_execution(func: Callable) -> Callable:
    """
    Decorator لتسجيل تنفيذ المعالج
    
    الاستخدام:
        @log_handler_execution
        def handle(self, command, user_context):
            pass
    
    Args:
        func: الدالة المراد تزيينها
    
    Returns:
        Callable: الدالة المزينة
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        handler_name = func.__name__
        command_name = None
        
        # محاولة استخراج اسم الأمر من المعاملات
        for arg in args:
            if hasattr(arg, '__class__'):
                class_name = arg.__class__.__name__
                if class_name.endswith('Command') or class_name.endswith('Query'):
                    command_name = class_name
                    break
        
        if not command_name:
            for key, val in kwargs.items():
                if hasattr(val, '__class__'):
                    class_name = val.__class__.__name__
                    if class_name.endswith('Command') or class_name.endswith('Query'):
                        command_name = class_name
                        break
        
        # تسجيل بداية التنفيذ
        logger.info(f"🔄 Executing {handler_name} for {command_name or 'unknown'}")
        
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # تسجيل نجاح التنفيذ
            elapsed = (time.time() - start_time) * 1000
            logger.info(f"✅ {handler_name} completed in {elapsed:.2f}ms")
            
            return result
            
        except Exception as e:
            # تسجيل فشل التنفيذ
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"❌ {handler_name} failed after {elapsed:.2f}ms: {e}")
            raise
    
    return wrapper


def timing_middleware(func: Callable) -> Callable:
    """
    Decorator لقياس وقت تنفيذ الدالة (مشابه لـ log_handler_execution ولكن بدون تسجيل)
    
    الاستخدام:
        @timing_middleware
        def expensive_operation():
            pass
    
    Args:
        func: الدالة المراد تزيينها
    
    Returns:
        Callable: الدالة المزينة
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"⏱️ {func.__name__} took {elapsed:.2f}ms")
            return result
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.debug(f"⏱️ {func.__name__} failed after {elapsed:.2f}ms")
            raise
    
    return wrapper


def handle_exceptions(
    error_map: Optional[dict] = None,
    default_error: str = "An unexpected error occurred"
) -> Callable:
    """
    Decorator لمعالجة الاستثناءات بشكل موحد
    
    الاستخدام:
        @handle_exceptions({
            ValueError: "Invalid data provided",
            PermissionError: "You don't have permission",
        })
        def handle(self, command):
            pass
    
    Args:
        error_map: قاموس يربط نوع الاستثناء برسالة خطأ
        default_error: الرسالة الافتراضية للاستثناءات غير المتوقعة
    
    Returns:
        Callable: الدالة المزينة
    """
    error_map = error_map or {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # البحث عن رسالة مخصصة لنوع الاستثناء
                for exc_type, message in error_map.items():
                    if isinstance(e, exc_type):
                        logger.warning(f"{func.__name__}: {message} - {e}")
                        raise exc_type(message) from e
                
                # استثناء غير متوقع
                logger.error(f"{func.__name__}: {default_error} - {e}", exc_info=True)
                raise RuntimeError(default_error) from e
        
        return wrapper
    
    return decorator


def require_transaction(func: Callable) -> Callable:
    """
    Decorator للتأكد من أن الدالة تعمل ضمن معاملة (Transaction)
    
    الاستخدام:
        @require_transaction
        def handle(self, command, user_context):
            # يجب أن يكون هناك UoW نشط
            pass
    
    Args:
        func: الدالة المراد تزيينها
    
    Returns:
        Callable: الدالة المزينة
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # البحث عن UoW في المعاملات
        uow = None
        for arg in args:
            if hasattr(arg, 'commit') and hasattr(arg, 'rollback'):
                uow = arg
                break
        
        if not uow:
            for key, val in kwargs.items():
                if hasattr(val, 'commit') and hasattr(val, 'rollback'):
                    uow = val
                    break
        
        if not uow:
            logger.warning(f"{func.__name__} called without UoW, transaction may not be guaranteed")
        
        return func(*args, **kwargs)
    
    return wrapper


# =============================================================================
# ديكوراتور مركب (Combined Decorator)
# =============================================================================

def handler_decorator(func: Callable) -> Callable:
    """
    ديكوراتور مركب يجمع بين جميع الديكوراتورات السابقة
    
    الاستخدام:
        @handler_decorator
        def handle(self, command, user_context):
            pass
    
    يوفر:
        1. تسجيل التنفيذ (log_handler_execution)
        2. معالجة التعديل المتزامن (handle_concurrent_modification)
        3. قياس وقت التنفيذ (timing_middleware)
    
    Args:
        func: الدالة المراد تزيينها
    
    Returns:
        Callable: الدالة المزينة بجميع الديكوراتورات
    """
    @log_handler_execution
    @handle_concurrent_modification
    @timing_middleware
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    
    return wrapper


# =============================================================================
# اختبار سريع
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Handlers Decorators")
    print("=" * 60)
    
    # اختبار handler_decorator
    @handler_decorator
    def test_handler(command, user_context=None):
        print(f"   Executing test_handler with command: {command}")
        return "Success"
    
    print("\n1. Testing handler_decorator:")
    result = test_handler("TestCommand")
    print(f"   Result: {result}")
    
    # اختبار handle_concurrent_modification
    print("\n2. Testing handle_concurrent_modification:")
    
    @handle_concurrent_modification
    def test_update_handler(entity_id, version):
        # محاكاة تحديث يتعارض
        raise ConcurrentModificationError(
            entity_type="Test",
            entity_id=entity_id,
            expected_version=version,
            actual_version=version + 1
        )
    
    try:
        test_update_handler("test-123", 1)
    except ConcurrentModificationError as e:
        print(f"   Caught expected error: {e}")
    
    print("\n✅ All tests passed!")