# core/bootstrap/middleware/logging.py
"""
Logging Middleware - تسجيل تنفيذ الأوامر والاستعلامات
مستخرج من bootstrap.py و infrastructure/messaging/middleware.py
"""

import logging
from typing import Any, Dict, Optional
from datetime import datetime
import json

from .base import Middleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(Middleware):
    """
    Middleware لتسجيل تنفيذ الأوامر والاستعلامات
    
    يقوم بتسجيل:
        1. بداية تنفيذ الأمر
        2. نهاية تنفيذ الأمر مع النتيجة
        3. الأخطاء التي تحدث
    """
    
    def __init__(self, log_level: int = logging.INFO, log_payload: bool = True):
        self._log_level = log_level
        self._log_payload = log_payload
        self._logger = logging.getLogger("core.middleware.logging")
    
    def before(self, command: Any, context: Dict) -> Dict:
        """تسجيل بداية تنفيذ الأمر"""
        command_name = self._get_command_name(command)
        user_id = context.get('user_id', 'unknown')
        
        # إضافة وقت البداية إلى السياق
        context['_start_time'] = datetime.now()
        context['_command_name'] = command_name
        
        log_data = {
            'command': command_name,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'action': 'start'
        }
        
        if self._log_payload:
            log_data['payload'] = self._safe_serialize(command)
        
        self._logger.log(self._log_level, f"▶️ Executing command: {command_name}", extra=log_data)
        
        return context
    
    def after(self, command: Any, result: Any, context: Dict) -> Any:
        """تسجيل انتهاء تنفيذ الأمر"""
        command_name = context.get('_command_name', self._get_command_name(command))
        start_time = context.get('_start_time')
        
        elapsed_ms = 0
        if start_time:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        log_data = {
            'command': command_name,
            'user_id': context.get('user_id', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'elapsed_ms': round(elapsed_ms, 2),
            'action': 'end',
            'success': True
        }
        
        if self._log_payload and result is not None:
            log_data['result'] = self._safe_serialize(result)
        
        self._logger.log(
            self._log_level,
            f"✅ Command completed: {command_name} ({elapsed_ms:.2f}ms)",
            extra=log_data
        )
        
        return result
    
    def handle_error(self, command: Any, error: Exception, context: Dict) -> Optional[Any]:
        """تسجيل الأخطاء"""
        command_name = context.get('_command_name', self._get_command_name(command))
        start_time = context.get('_start_time')
        
        elapsed_ms = 0
        if start_time:
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        log_data = {
            'command': command_name,
            'user_id': context.get('user_id', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'elapsed_ms': round(elapsed_ms, 2),
            'action': 'error',
            'error': str(error),
            'error_type': type(error).__name__
        }
        
        self._logger.error(
            f"❌ Command failed: {command_name} ({elapsed_ms:.2f}ms) - {error}",
            extra=log_data,
            exc_info=True
        )
        
        return None
    
    def _get_command_name(self, command: Any) -> str:
        """الحصول على اسم الأمر"""
        if hasattr(command, '__class__'):
            return command.__class__.__name__
        return str(command)
    
    def _safe_serialize(self, obj: Any) -> Any:
        """تسلسل آمن للكائنات"""
        try:
            if hasattr(obj, 'to_dict'):
                return obj.to_dict()
            if hasattr(obj, '__dict__'):
                return str(obj)
            return str(obj)
        except Exception:
            return str(obj)
    
    @property
    def priority(self) -> int:
        # أولوية عالية جداً (ينفذ أولاً)
        return 10
    
    @property
    def name(self) -> str:
        return "logging"