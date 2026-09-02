# core/bootstrap/middleware/registry.py
"""
Middleware Registry - تسجيل وتنظيم الـ Middleware
"""

from typing import Any, Dict, List, Optional, Callable
import logging

from .base import Middleware, MiddlewareChain
from .logging import LoggingMiddleware
from .timing import TimingMiddleware
from .transaction import TransactionMiddleware
from .authorization import AuthorizationMiddleware
from .validation import ValidationMiddleware
from .cache import CacheMiddleware
from .error_handling import ErrorHandlingMiddleware

logger = logging.getLogger(__name__)


class MiddlewareRegistry:
    """
    سجل مركزي لتسجيل وإدارة الـ Middleware
    
    الميزات:
        1. تسجيل Middleware مدمجة ومخصصة
        2. إنشاء سلاسل Middleware للـ Command Bus و Query Bus
        3. تمكين/تعطيل Middleware محددة
        4. ترتيب Middleware حسب الأولوية
    """
    
    def __init__(self):
        self._middleware: Dict[str, Middleware] = {}
        self._enabled: Dict[str, bool] = {}
        self._command_chain = MiddlewareChain()
        self._query_chain = MiddlewareChain()
    
    # =========================================================================
    # تسجيل Middleware
    # =========================================================================
    
    def register(self, middleware: Middleware, enabled: bool = True) -> 'MiddlewareRegistry':
        """تسجيل Middleware في السجل"""
        self._middleware[middleware.name] = middleware
        self._enabled[middleware.name] = enabled
        logger.debug(f"📋 Middleware registered: {middleware.name}")
        return self
    
    def register_defaults(self, **kwargs) -> 'MiddlewareRegistry':
        """تسجيل الـ Middleware الافتراضية"""
        # Logging
        self.register(LoggingMiddleware(
            log_level=kwargs.get('log_level', logging.INFO),
            log_payload=kwargs.get('log_payload', True)
        ))
        
        # Timing
        self.register(TimingMiddleware(
            log_slow_queries=kwargs.get('log_slow_queries', True),
            slow_threshold_ms=kwargs.get('slow_threshold_ms', 1000)
        ))
        
        # Cache
        self.register(CacheMiddleware(
            ttl_seconds=kwargs.get('cache_ttl', 300)
        ))
        
        # Error Handling
        self.register(ErrorHandlingMiddleware(
            default_error_message=kwargs.get('default_error_message', 'حدث خطأ غير متوقع'),
            retry_count=kwargs.get('retry_count', 0),
            log_exceptions=kwargs.get('log_exceptions', True)
        ))
        
        # Validation
        self.register(ValidationMiddleware(
            strict_mode=kwargs.get('strict_validation', True)
        ))
        
        return self
    
    def register_authorization(self, user_context_provider: Callable) -> 'MiddlewareRegistry':
        """تسجيل Middleware الصلاحيات"""
        self.register(AuthorizationMiddleware(user_context_provider))
        return self
    
    def register_transaction(self, uow_provider: Callable) -> 'MiddlewareRegistry':
        """تسجيل Middleware المعاملات"""
        self.register(TransactionMiddleware(uow_provider))
        return self
    
    # =========================================================================
    # إدارة Middleware
    # =========================================================================
    
    def enable(self, name: str) -> 'MiddlewareRegistry':
        """تفعيل Middleware"""
        if name in self._enabled:
            self._enabled[name] = True
            logger.debug(f"✅ Middleware enabled: {name}")
        return self
    
    def disable(self, name: str) -> 'MiddlewareRegistry':
        """تعطيل Middleware"""
        if name in self._enabled:
            self._enabled[name] = False
            logger.debug(f"❌ Middleware disabled: {name}")
        return self
    
    def is_enabled(self, name: str) -> bool:
        """التحقق من تفعيل Middleware"""
        return self._enabled.get(name, False)
    
    def get_middleware(self, name: str) -> Optional[Middleware]:
        """الحصول على Middleware بواسطة الاسم"""
        return self._middleware.get(name)
    
    def get_all_middleware(self) -> List[Middleware]:
        """الحصول على جميع الـ Middleware"""
        return list(self._middleware.values())
    
    def get_enabled_middleware(self) -> List[Middleware]:
        """الحصول على الـ Middleware المفعلة"""
        return [m for m in self._middleware.values() if self.is_enabled(m.name)]
    
    # =========================================================================
    # بناء السلاسل
    # =========================================================================
    
    def build_command_chain(self) -> MiddlewareChain:
        """بناء سلسلة Middleware للأوامر"""
        self._command_chain.clear()
        
        # إضافة الـ Middleware حسب الأولوية
        for middleware in sorted(self.get_enabled_middleware(), key=lambda m: m.priority):
            self._command_chain.add(middleware)
        
        logger.debug(f"📋 Command chain built with {self._command_chain.count} middleware")
        return self._command_chain
    
    def build_query_chain(self) -> MiddlewareChain:
        """بناء سلسلة Middleware للاستعلامات"""
        self._query_chain.clear()
        
        # إضافة الـ Middleware للاستعلامات (بدون Transaction)
        for middleware in sorted(self.get_enabled_middleware(), key=lambda m: m.priority):
            if middleware.name != 'transaction':  # Transaction لا يحتاج للاستعلامات
                self._query_chain.add(middleware)
        
        logger.debug(f"📋 Query chain built with {self._query_chain.count} middleware")
        return self._query_chain
    
    @property
    def command_chain(self) -> MiddlewareChain:
        """الحصول على سلسلة الأوامر"""
        return self._command_chain
    
    @property
    def query_chain(self) -> MiddlewareChain:
        """الحصول على سلسلة الاستعلامات"""
        return self._query_chain


# =========================================================================
# دالة مساعدة لإنشاء سلسلة Middleware افتراضية
# =========================================================================

def create_default_middleware_chain(
    user_context_provider: Optional[Callable] = None,
    uow_provider: Optional[Callable] = None,
    **kwargs
) -> MiddlewareChain:
    """
    إنشاء سلسلة Middleware افتراضية كاملة
    
    Args:
        user_context_provider: دالة تعيد سياق المستخدم
        uow_provider: دالة تعيد Unit of Work
        **kwargs: إعدادات إضافية
    
    Returns:
        MiddlewareChain: سلسلة الـ Middleware
    """
    registry = MiddlewareRegistry()
    
    # تسجيل الـ Middleware الافتراضية
    registry.register_defaults(**kwargs)
    
    # تسجيل Authorization إذا تم توفير provider
    if user_context_provider:
        registry.register_authorization(user_context_provider)
    
    # تسجيل Transaction إذا تم توفير provider
    if uow_provider:
        registry.register_transaction(uow_provider)
    
    # بناء السلسلة
    return registry.build_command_chain()