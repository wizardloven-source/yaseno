# core/infrastructure/messaging/middleware.py

from typing import Any, Callable
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def authorization_middleware(user_context_provider):
    """
    Middleware للتحقق من صلاحيات المستخدم
    
    Args:
        user_context_provider: دالة ترجع سياق المستخدم الحالي
    
    مثال:
        def get_user_context():
            return current_user_context
        
        command_bus.register_middleware(
            authorization_middleware(get_user_context)
        )
    """
    def middleware(command, next_handler):
        # الحصول على سياق المستخدم
        user_context = user_context_provider()
        
        # إذا كان الأمر يحتوي على متطلب صلاحيات، تحقق منه
        if hasattr(command, 'required_permission'):
            if not user_context or not user_context.has_permission(command.required_permission):
                from core.application.security.authorization import PermissionDeniedError
                raise PermissionDeniedError(
                    permission=command.required_permission,
                    user_id=user_context.user_id if user_context else "unknown"
                )
        
        return next_handler(command)
    return middleware


def transaction_middleware(uow_provider):
    """
    Middleware لإدارة المعاملات (Unit of Work)
    
    Args:
        uow_provider: دالة ترجع نسخة من Unit of Work
    
    مثال:
        def get_uow():
            return PostgresUnitOfWork(session_factory)
        
        command_bus.register_middleware(
            transaction_middleware(get_uow)
        )
    """
    def middleware(command, next_handler):
        uow = uow_provider()
        
        with uow:
            try:
                result = next_handler(command)
                uow.commit()
                return result
            except Exception as e:
                uow.rollback()
                raise
    
    return middleware


def cache_middleware(cache_service, ttl_seconds=300):
    """
    Middleware للتخزين المؤقت للاستعلامات
    
    Args:
        cache_service: خدمة التخزين المؤقت
        ttl_seconds: مدة صلاحية الكاش
    
    مثال:
        command_bus.register_middleware(
            cache_middleware(get_cache_service(), ttl_seconds=60)
        )
    """
    def middleware(query, next_handler):
        # فقط للاستعلامات التي تطلب التخزين المؤقت
        if not hasattr(query, 'cacheable') or not query.cacheable:
            return next_handler(query)
        
        # توليد مفتاح الكاش
        cache_key = f"query:{type(query).__name__}:{hash(str(query))}"
        
        # محاولة القراءة من الكاش
        cached_result = cache_service.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {type(query).__name__}")
            return cached_result
        
        # تنفيذ الاستعلام
        result = next_handler(query)
        
        # حفظ في الكاش
        cache_service.set(cache_key, result, ttl_seconds)
        logger.debug(f"Cache miss for query: {type(query).__name__}")
        
        return result
    return middleware