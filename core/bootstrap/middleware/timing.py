# core/bootstrap/middleware/timing.py
"""
Timing Middleware - قياس وقت تنفيذ الأوامر والاستعلامات
مستخرج من bootstrap.py و infrastructure/messaging/middleware.py
"""

import time
import logging
from typing import Any, Dict, Optional

from .base import Middleware

logger = logging.getLogger(__name__)


class TimingMiddleware(Middleware):
    """
    Middleware لقياس وقت تنفيذ الأوامر والاستعلامات
    
    يقوم بحساب:
        1. وقت التنفيذ الكلي
        2. تسجيل الأداء في السجلات
    """
    
    def __init__(self, log_slow_queries: bool = True, slow_threshold_ms: int = 1000):
        self._log_slow_queries = log_slow_queries
        self._slow_threshold_ms = slow_threshold_ms
    
    def before(self, command: Any, context: Dict) -> Dict:
        """بدء قياس الوقت"""
        context['_timing_start'] = time.perf_counter()
        return context
    
    def after(self, command: Any, result: Any, context: Dict) -> Any:
        """حساب وقت التنفيذ"""
        start_time = context.get('_timing_start')
        if not start_time:
            return result
        
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        command_name = self._get_command_name(command)
        
        # تسجيل الوقت
        logger.debug(f"⏱️ {command_name} took {elapsed_ms:.2f}ms")
        
        # تنبيه للاستعلامات البطيئة
        if self._log_slow_queries and elapsed_ms > self._slow_threshold_ms:
            logger.warning(
                f"🐌 Slow query detected: {command_name} took {elapsed_ms:.2f}ms "
                f"(threshold: {self._slow_threshold_ms}ms)"
            )
        
        # إضافة الوقت إلى النتيجة إذا كانت قاموساً
        if isinstance(result, dict):
            result['_execution_time_ms'] = round(elapsed_ms, 2)
        
        return result
    
    def handle_error(self, command: Any, error: Exception, context: Dict) -> Optional[Any]:
        """تسجيل وقت الفشل"""
        start_time = context.get('_timing_start')
        if start_time:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.debug(f"⏱️ {self._get_command_name(command)} failed after {elapsed_ms:.2f}ms")
        return None
    
    def _get_command_name(self, command: Any) -> str:
        if hasattr(command, '__class__'):
            return command.__class__.__name__
        return str(command)
    
    @property
    def priority(self) -> int:
        # ينفذ بعد الـ Logging
        return 20
    
    @property
    def name(self) -> str:
        return "timing"