# core/infrastructure/messaging/query_bus.py

from typing import Dict, Type, Any, Optional, Callable, List, Union
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class QueryBus:
    """
    ناقل الاستعلامات (Query Bus)

    المسؤوليات:
        1. تسجيل معالجات الاستعلامات
        2. تنفيذ الاستعلامات
        3. دعم Middleware
        4. معالجة الأخطاء الموحدة

    يدعم التسجيل بواسطة:
        - Query Class
        - اسم الـ Query كسلسلة نصية
    """

    def __init__(self):
        self._handlers: Dict[str, Any] = {}
        self._middleware: List[Callable] = []
        self._handler_resolver: Optional[Callable[[str], Any]] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def set_handler_resolver(self, resolver: Callable[[str], Any]) -> None:
        """تعيين دالة تحل المعالج من اسم الخدمة في نطاق جديد (لكل طلب)."""

        self._handler_resolver = resolver

    def register(self, query_cls: Union[Type, str], handler: Any) -> None:
        """
        تسجيل معالج للاستعلام.

        Args:
            query_cls:
                إما كلاس الاستعلام أو اسمه.
            handler:
                كائن يحتوي على handle() أو اسم خدمة المعالج (يُحل لكل إرسال).
        """

        if not isinstance(handler, str) and not hasattr(handler, "handle"):
            raise ValueError(
                f"Handler {handler} must have a 'handle' method"
            )

        if isinstance(query_cls, str):
            query_name = query_cls
        else:
            query_name = query_cls.__name__

        self._handlers[query_name] = handler

        logger.debug(
            f"Query registered: {query_name} -> {handler}"
        )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------

    def register_middleware(self, middleware: Callable) -> None:
        """تسجيل Middleware."""

        self._middleware.append(middleware)

        logger.debug(
            f"Middleware registered: {middleware.__name__}"
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, query: Any) -> Any:
        """
        تنفيذ الاستعلام.
        """

        query_name = type(query).__name__

        registered = self._handlers.get(query_name)

        if not registered:
            error_msg = (
                f"لا يوجد معالج مسجل للاستعلام: {query_name}"
            )

            logger.error(error_msg)
            raise Exception(error_msg)

        # ✅ إذا كان المعالج مسجلاً باسم خدمة، نحصل على دالة تنفذه
        # في نطاق جديد (جلسة جديدة لكل طلب) وتبقي النطاق مفتوحاً أثناء التنفيذ
        if isinstance(registered, str):
            if not self._handler_resolver:
                raise RuntimeError(
                    f"Handler '{registered}' is registered as a service name but "
                    "no handler resolver is installed on the QueryBus"
                )
            execute_handler = self._handler_resolver(registered)
        else:
            handler = registered

            def execute_handler(q):
                return handler.handle(q)

        chain = execute_handler

        for middleware in self._middleware:
            chain = self._wrap_middleware(
                middleware,
                chain
            )

        try:
            return chain(query)

        except Exception as e:
            logger.error(
                f"Query {query_name} failed: {e}"
            )
            raise

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _wrap_middleware(
        self,
        middleware: Callable,
        next_handler: Callable
    ) -> Callable:

        @wraps(next_handler)
        def wrapper(query):
            return middleware(query, next_handler)

        return wrapper

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def has_handler(
        self,
        query_cls: Union[Type, str]
    ) -> bool:

        if isinstance(query_cls, str):
            query_name = query_cls
        else:
            query_name = query_cls.__name__

        return query_name in self._handlers

    def get_handler(
        self,
        query_cls: Union[Type, str]
    ) -> Optional[Any]:

        if isinstance(query_cls, str):
            query_name = query_cls
        else:
            query_name = query_cls.__name__

        return self._handlers.get(query_name)

    def clear_handlers(self) -> None:
        """حذف جميع المعالجات."""

        self._handlers.clear()

        logger.debug("All query handlers cleared")

    def clear_middleware(self) -> None:
        """حذف جميع الـ Middleware."""

        self._middleware.clear()

        logger.debug("All query middleware cleared")

    def get_registered_queries(self) -> List[str]:
        """الحصول على جميع الاستعلامات المسجلة."""

        return list(self._handlers.keys())


# =============================================================================
# Built-in Middleware
# =============================================================================

def logging_middleware(query, next_handler):
    """تسجيل تنفيذ الاستعلام."""

    query_name = type(query).__name__

    logger.info(f"🔵 Executing query: {query_name}")

    try:
        result = next_handler(query)

        logger.info(
            f"✅ Query {query_name} completed successfully"
        )

        return result

    except Exception as e:
        logger.error(
            f"❌ Query {query_name} failed: {e}"
        )
        raise


def timing_middleware(query, next_handler):
    """قياس زمن تنفيذ الاستعلام."""

    import time

    query_name = type(query).__name__

    start_time = time.time()

    try:
        result = next_handler(query)

        elapsed = (time.time() - start_time) * 1000

        logger.debug(
            f"⏱️ Query {query_name} took {elapsed:.2f} ms"
        )

        return result

    except Exception:

        elapsed = (time.time() - start_time) * 1000

        logger.debug(
            f"⏱️ Query {query_name} failed after {elapsed:.2f} ms"
        )

        raise


def validation_middleware(query, next_handler):
    """التحقق من صحة الاستعلام إن كان يدعم validate()."""

    query_name = type(query).__name__

    if hasattr(query, "validate"):

        is_valid, errors = query.validate()

        if not is_valid:

            error_msg = (
                f"Query {query_name} validation failed: "
                f"{', '.join(errors)}"
            )

            logger.error(error_msg)

            raise ValueError(error_msg)

    return next_handler(query)