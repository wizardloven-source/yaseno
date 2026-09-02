# core/bootstrap/modules/database.py
"""
وحدة قاعدة البيانات - تسجيل خدمات قاعدة البيانات
"""

from typing import TYPE_CHECKING, Dict, Any
import logging

if TYPE_CHECKING:
    from ..container import DependencyContainer

from ..container import ServiceLifetime
from .base import Module

logger = logging.getLogger(__name__)


class DatabaseModule(Module):
    """وحدة قاعدة البيانات - إدارة الاتصال بقاعدة البيانات"""
    
    name = "database"
    description = "إدارة اتصال قاعدة البيانات والجلسات"
    dependencies = []
    version = "2.0.0"
    order = 0  # أول وحدة يتم تحميلها
    
    def register(self, container: 'DependencyContainer') -> None:
        """تسجيل خدمات قاعدة البيانات"""
        
        # ========== Session Factory (Singleton) ==========
        container.register_singleton(
            "session_factory",
            "core.infrastructure.db.postgres.unit_of_work.SessionFactory",
            dependencies=["connection_string", "echo_sql", "pool_size", "max_overflow"]
        )
        
        # ========== Session (Scoped) ==========
        # ✅ session هي نفس جلسة الـ Unit of Work (جلسة واحدة موحّدة لكل نطاق)
        # هذا يضمن أن المستودعات والـ UoW يكتبان ويـ commit في نفس الجلسة،
        # مما يمنع فقدان الكتابات بسبب انقسام الجلسات.
        container.register_scoped(
            "session",
            "sqlalchemy.orm.Session",
            factory=lambda uow: uow.session,
            dependencies=["uow"]
        )
        
        # ========== Unit of Work (Scoped) ==========
        container.register_scoped(
            "uow",
            "core.infrastructure.db.postgres.unit_of_work.PostgresUnitOfWork",
            dependencies=["session_factory", "event_bus"]
        )
        
        # ========== Connection String (Singleton) ==========
        import os
        _db_url = os.getenv('DATABASE_URL')
        if not _db_url:
            raise RuntimeError("DATABASE_URL is required. Copy .env.example to .env and configure it.")
        
        container.register_singleton(
            "connection_string",
            str,
            factory=lambda: _db_url
        )
        container.register_singleton(
            "echo_sql",
            bool,
            factory=lambda: False
        )
        container.register_singleton(
            "pool_size",
            int,
            factory=lambda: 5
        )
        container.register_singleton(
            "max_overflow",
            int,
            factory=lambda: 10
        )
    
    def configure(self, container: 'DependencyContainer', config: Dict[str, Any]) -> None:
        """تكوين قاعدة البيانات"""
        # تحديث إعدادات الاتصال من config
        if config:
            try:
                # تحديث connection_string من config
                if 'database_url' in config:
                    container.register_instance("connection_string", config['database_url'])
                if 'echo_sql' in config:
                    container.register_instance("echo_sql", config['echo_sql'])
                if 'pool_size' in config:
                    container.register_instance("pool_size", config['pool_size'])
                if 'max_overflow' in config:
                    container.register_instance("max_overflow", config['max_overflow'])
                logger.info("✅ Database configuration updated from config")
            except Exception as e:
                logger.error(f"❌ Failed to update database config: {e}")