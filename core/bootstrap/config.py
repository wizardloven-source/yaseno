# core/bootstrap/config.py
"""
إعدادات Bootstrap - مستخرجة من bootstrap.py
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime


@dataclass
class BootstrapConfig:
    """إعدادات تشغيل التطبيق"""
    
    # قاعدة البيانات
    database_url: str
    echo_sql: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    
    # الأمان
    secret_key: str = "change-me-in-production"
    enable_auth: bool = True
    session_timeout: int = 3600  # ثواني
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    
    # الأداء
    enable_cache: bool = True
    cache_ttl: int = 300  # ثواني
    
    # الوقت (للاستخدام في الاختبارات)
    fixed_time: Optional[datetime] = None
    
    # إعدادات إضافية
    seed_data: bool = False
    debug: bool = False
    
    @classmethod
    def from_env(cls, **kwargs) -> 'BootstrapConfig':
        """إنشاء الإعدادات من متغيرات البيئة"""
        import os
        
        db_url = kwargs.get('database_url') or os.getenv('DATABASE_URL')
        if not db_url:
            raise RuntimeError("DATABASE_URL is required. Copy .env.example to .env and configure it.")
        
        return cls(
            database_url=db_url,
            echo_sql=kwargs.get('echo_sql', os.getenv('SQL_ECHO', 'false').lower() == 'true'),
            pool_size=kwargs.get('pool_size', int(os.getenv('DB_POOL_SIZE', '5'))),
            max_overflow=kwargs.get('max_overflow', int(os.getenv('DB_MAX_OVERFLOW', '10'))),
            secret_key=kwargs.get('secret_key', os.getenv('SECRET_KEY')),
            enable_auth=kwargs.get('enable_auth', os.getenv('ENABLE_AUTH', 'true').lower() == 'true'),
            session_timeout=kwargs.get('session_timeout', int(os.getenv('SESSION_TIMEOUT', '3600'))),
            max_login_attempts=kwargs.get('max_login_attempts', int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))),
            lockout_minutes=kwargs.get('lockout_minutes', int(os.getenv('LOCKOUT_MINUTES', '15'))),
            enable_cache=kwargs.get('enable_cache', os.getenv('ENABLE_CACHE', 'true').lower() == 'true'),
            cache_ttl=kwargs.get('cache_ttl', int(os.getenv('CACHE_TTL', '300'))),
            fixed_time=kwargs.get('fixed_time'),
            seed_data=kwargs.get('seed_data', os.getenv('SEED_DATA', 'false').lower() == 'true'),
            debug=kwargs.get('debug', os.getenv('DEBUG', 'false').lower() == 'true'),
        )