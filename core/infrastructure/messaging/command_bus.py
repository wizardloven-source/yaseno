# core/infrastructure/messaging/command_bus.py

from typing import Dict, Type, Any, Callable, Optional, List, Union
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class CommandBus:
    """
    ناقل الأوامر (Command Bus) - لتوزيع الأوامر إلى معالجاتها
    
    الميزات:
        1. تسجيل المعالجات لكل أمر
        2. دعم الـ Middleware (للتحقق من الصلاحيات، التسجيل، إلخ)
        3. معالجة الأخطاء الموحدة
        4. دعم التنفيذ غير المتزامن (اختياري)
    """
    
    def __init__(self):
        self._handlers: Dict[str, Any] = {}  # ✅ تغيير المفتاح إلى str
        self._middleware: List[Callable] = []
        self._is_async: bool = False
        self._handler_resolver: Optional[Callable[[str], Any]] = None
    
    def set_handler_resolver(self, resolver: Callable[[str], Any]) -> None:
        """
        تعيين دالة تحل المعالج من اسم الخدمة في نطاق جديد (لكل طلب).
        
        Args:
            resolver: دالة تأخذ اسم الخدمة (str) وتعيد نسخة معالجة جديدة.
        """
        self._handler_resolver = resolver
    
    def register(self, command_cls: Union[Type, str], handler: Any) -> None:
        """
        تسجيل المعالج المسؤول عن كل أمر
        
        Args:
            command_cls: نوع الأمر (كلاس أو اسم الكلاس كسلسلة نصية)
            handler: نسخة من المعالج (يجب أن يحتوي على طريقة handle)
                     أو اسم خدمة المعالج في الحاوية (يُحل في نطاق جديد عند الإرسال)
        """
        # ✅ إذا كان handler نصاً (اسم خدمة)، فسيُحل لكل إرسال في نطاق جديد
        if not isinstance(handler, str) and not hasattr(handler, 'handle'):
            raise ValueError(f"Handler {handler} must have a 'handle' method")
        
        # ✅ استخراج اسم الأمر
        if isinstance(command_cls, str):
            command_name = command_cls
        else:
            command_name = command_cls.__name__
        
        self._handlers[command_name] = handler
        logger.debug(f"Command registered: {command_name} -> {handler}")
    
    def register_middleware(self, middleware: Callable) -> None:
        """
        تسجيل Middleware للتنفيذ قبل وبعد معالجة الأمر
        
        Args:
            middleware: دالة تأخذ (command, next_handler) وتعيد النتيجة
            
        مثال:
            def logging_middleware(command, next_handler):
                print(f"Executing: {command}")
                result = next_handler(command)
                print(f"Result: {result}")
                return result
        """
        self._middleware.append(middleware)
        logger.debug(f"Middleware registered: {middleware.__name__}")
    
    def set_async(self, is_async: bool = True) -> None:
        """تعيين وضع التنفيذ غير المتزامن"""
        self._is_async = is_async
    
    def dispatch(self, command: Any) -> Any:
        """
        إرسال الأمر للمعالج الصحيح مع تطبيق الـ Middleware
        
        Args:
            command: الأمر المراد إرساله
        
        Returns:
            نتيجة معالجة الأمر
        
        Raises:
            Exception: إذا لم يتم العثور على معالج للأمر
        """
        command_name = type(command).__name__
        registered = self._handlers.get(command_name)
        
        if not registered:
            error_msg = f"لا يوجد معالج مسجل للأمر: {command_name}"
            logger.error(error_msg)
            raise Exception(error_msg)
        
        # ✅ إذا كان المعالج مسجلاً باسم خدمة، نحصل على دالة تنفذه
        # في نطاق جديد (جلسة جديدة لكل طلب) وتبقي النطاق مفتوحاً أثناء التنفيذ
        if isinstance(registered, str):
            if not self._handler_resolver:
                raise RuntimeError(
                    f"Handler '{registered}' is registered as a service name but "
                    "no handler resolver is installed on the CommandBus"
                )
            execute_handler = self._handler_resolver(registered)
        else:
            handler = registered

            def execute_handler(cmd):
                return handler.handle(cmd)
        
        # بناء سلسلة الـ Middleware
        chain = execute_handler
        for middleware in self._middleware:
            chain = self._wrap_middleware(middleware, chain)
        
        # تنفيذ السلسلة
        try:
            return chain(command)
        except Exception as e:
            logger.error(f"Command {command_name} failed: {e}")
            raise
    
    def _wrap_middleware(self, middleware: Callable, next_handler: Callable) -> Callable:
        """تغليف Middleware حول المعالج التالي"""
        @wraps(next_handler)
        def wrapper(command):
            return middleware(command, next_handler)
        return wrapper
    
    def has_handler(self, command_cls: Union[Type, str]) -> bool:
        """التحقق من وجود معالج لأمر معين"""
        if isinstance(command_cls, str):
            command_name = command_cls
        else:
            command_name = command_cls.__name__
        return command_name in self._handlers
    
    def get_handler(self, command_cls: Union[Type, str]) -> Optional[Any]:
        """الحصول على المعالج لأمر معين"""
        if isinstance(command_cls, str):
            command_name = command_cls
        else:
            command_name = command_cls.__name__
        return self._handlers.get(command_name)
    
    def clear_handlers(self) -> None:
        """مسح جميع المعالجات"""
        self._handlers.clear()
        logger.debug("All handlers cleared")
    
    def clear_middleware(self) -> None:
        """مسح جميع الـ Middleware"""
        self._middleware.clear()
        logger.debug("All middleware cleared")
    
    def get_registered_commands(self) -> List[str]:
        """الحصول على قائمة الأوامر المسجلة"""
        return list(self._handlers.keys())


# =============================================================================
# Middleware مدمجة
# =============================================================================

def logging_middleware(command, next_handler):
    """Middleware لتسجيل تنفيذ الأوامر"""
    command_name = type(command).__name__
    logger.info(f"🔵 Executing command: {command_name}")
    
    try:
        result = next_handler(command)
        logger.info(f"✅ Command {command_name} completed successfully")
        return result
    except Exception as e:
        logger.error(f"❌ Command {command_name} failed: {e}")
        raise


def timing_middleware(command, next_handler):
    """Middleware لقياس وقت تنفيذ الأمر"""
    import time
    command_name = type(command).__name__
    
    start_time = time.time()
    try:
        result = next_handler(command)
        elapsed = (time.time() - start_time) * 1000
        logger.debug(f"⏱️ Command {command_name} took {elapsed:.2f}ms")
        return result
    except Exception as e:
        elapsed = (time.time() - start_time) * 1000
        logger.debug(f"⏱️ Command {command_name} failed after {elapsed:.2f}ms")
        raise


def validation_middleware(command, next_handler):
    """Middleware للتحقق من صحة الأمر قبل التنفيذ"""
    command_name = type(command).__name__
    
    # إذا كان الأمر يحتوي على طريقة validate، قم بتنفيذها
    if hasattr(command, 'validate'):
        try:
            is_valid, errors = command.validate()
            if not is_valid:
                error_msg = f"Command {command_name} validation failed: {', '.join(errors)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            logger.error(f"Validation error for {command_name}: {e}")
            raise
    
    return next_handler(command)