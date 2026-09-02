# core/bootstrap/middleware/cache.py
"""
Cache Middleware - التخزين المؤقت للاستعلامات
مستخرج من infrastructure/messaging/middleware.py
"""

from typing import Any, Dict, Optional, Callable
import logging
from functools import lru_cache
import hashlib
import json

from .base import Middleware

logger = logging.getLogger(__name__)


class CacheMiddleware(Middleware):
    """
    Middleware للتخزين المؤقت للاستعلامات
    
    الميزات:
        1. تخزين نتائج الاستعلامات
        2. تحديد مدة صلاحية الكاش
        3. إبطال الكاش عند التغيير
        4. دعم أنماط تخزين مختلفة (ذاكرة، Redis، إلخ)
    """
    
    def __init__(
        self,
        cache_service: Optional[Dict] = None,
        ttl_seconds: int = 300,
        cacheable_commands: Optional[List[str]] = None
    ):
        """
        Args:
            cache_service: خدمة التخزين المؤقت (قاموس بسيط أو Redis)
            ttl_seconds: مدة صلاحية الكاش بالثواني
            cacheable_commands: قائمة بأسماء الأوامر التي يمكن تخزينها مؤقتاً
        """
        self._cache = cache_service or {}
        self._ttl_seconds = ttl_seconds
        self._cacheable_commands = cacheable_commands or []
        self._cache_timestamps: Dict[str, float] = {}
    
    def before(self, command: Any, context: Dict) -> Dict:
        """التحقق من وجود نتيجة في الكاش"""
        # فقط للاستعلامات
        if not self._is_cacheable(command):
            return context
        
        cache_key = self._generate_cache_key(command, context)
        context['_cache_key'] = cache_key
        
        # التحقق من وجود النتيجة في الكاش
        if cache_key in self._cache:
            # التحقق من صلاحية الكاش
            if self._is_cache_valid(cache_key):
                logger.debug(f"📦 Cache hit for: {cache_key}")
                context['_cached_result'] = self._cache[cache_key]
                context['_cache_hit'] = True
            else:
                # الكاش منتهي الصلاحية
                del self._cache[cache_key]
                self._cache_timestamps.pop(cache_key, None)
                logger.debug(f"🗑️ Cache expired: {cache_key}")
        
        return context
    
    def after(self, command: Any, result: Any, context: Dict) -> Any:
        """تخزين النتيجة في الكاش"""
        # إذا كانت هناك نتيجة من الكاش، نعيدها مباشرة
        if context.get('_cache_hit', False):
            return context.get('_cached_result')
        
        # تخزين النتيجة في الكاش
        if self._is_cacheable(command):
            cache_key = context.get('_cache_key')
            if cache_key and result is not None:
                self._cache[cache_key] = result
                self._cache_timestamps[cache_key] = self._get_current_time()
                logger.debug(f"💾 Cache stored: {cache_key}")
        
        return result
    
    def handle_error(self, command: Any, error: Exception, context: Dict) -> Optional[Any]:
        """معالجة أخطاء الكاش"""
        return None
    
    def _is_cacheable(self, command: Any) -> bool:
        """التحقق مما إذا كان الأمر قابلاً للتخزين المؤقت"""
        command_name = self._get_command_name(command)
        
        # التحقق من وجود سمة cacheable
        if hasattr(command, 'cacheable'):
            return bool(command.cacheable)
        
        # التحقق من القائمة المخصصة
        if self._cacheable_commands:
            return command_name in self._cacheable_commands
        
        # بشكل افتراضي، نخزن فقط الاستعلامات (Queries)
        return 'Query' in command_name
    
    def _generate_cache_key(self, command: Any, context: Dict) -> str:
        """توليد مفتاح فريد للكاش"""
        command_name = self._get_command_name(command)
        
        # إنشاء تمثيل نصي للأمر
        command_repr = str(command)
        
        # إضافة سياق المستخدم
        user_id = context.get('user_id', 'anonymous')
        
        # إضافة معرف المستخدم إذا كان موجوداً
        if hasattr(command, 'user_id'):
            user_id = str(command.user_id)
        
        # توليد هاش
        key_string = f"{command_name}:{command_repr}:{user_id}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """التحقق من صلاحية الكاش"""
        if cache_key not in self._cache_timestamps:
            return False
        
        timestamp = self._cache_timestamps[cache_key]
        current_time = self._get_current_time()
        return (current_time - timestamp) < self._ttl_seconds
    
    def _get_current_time(self) -> float:
        """الحصول على الوقت الحالي"""
        import time
        return time.time()
    
    def _get_command_name(self, command: Any) -> str:
        if hasattr(command, '__class__'):
            return command.__class__.__name__
        return str(command)
    
    def invalidate(self, cache_key: str) -> None:
        """إبطال كاش محدد"""
        self._cache.pop(cache_key, None)
        self._cache_timestamps.pop(cache_key, None)
        logger.debug(f"🗑️ Cache invalidated: {cache_key}")
    
    def invalidate_all(self) -> None:
        """إبطال جميع الكاش"""
        self._cache.clear()
        self._cache_timestamps.clear()
        logger.debug("🗑️ All cache invalidated")
    
    def invalidate_by_command(self, command_name: str) -> None:
        """إبطال الكاش لأمر معين"""
        keys_to_remove = []
        for key in self._cache.keys():
            if key.startswith(command_name):
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            self.invalidate(key)
        
        logger.debug(f"🗑️ Cache invalidated for command: {command_name}")
    
    @property
    def priority(self) -> int:
        # ينفذ قبل الصلاحيات (للاستعلامات)
        return 15
    
    @property
    def name(self) -> str:
        return "cache"