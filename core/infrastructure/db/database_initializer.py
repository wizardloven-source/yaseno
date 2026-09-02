"""
Migration Manager - نظام إدارة ترحيلات قاعدة البيانات
الإصدار: 1.0.0
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import importlib
import os
import re

from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """ترحيلة قاعدة البيانات"""
    version: str
    name: str
    description: str
    up: str  # SQL للتطبيق
    down: str  # SQL للتراجع
    created_at: datetime = field(default_factory=datetime.now)
    applied_at: Optional[datetime] = None


class MigrationManager:
    """
    مدير الترحيلات - ينفذ الترحيلات بالترتيب الصحيح
    """
    
    def __init__(self, engine: Engine, migrations_dir: str = "core/infrastructure/db/migrations"):
        self._engine = engine
        self._migrations_dir = migrations_dir
        self._migrations: List[Migration] = []
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self) -> None:
        """إنشاء جدول تتبع الترحيلات"""
        with self._engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    up_sql TEXT,
                    down_sql TEXT
                )
            """))
            conn.commit()
    
    def load_migrations(self) -> None:
        """تحميل جميع الترحيلات من المجلد"""
        if not os.path.exists(self._migrations_dir):
            return
        
        for file in sorted(os.listdir(self._migrations_dir)):
            if not file.endswith('.sql'):
                continue
            
            # استخراج الإصدار والاسم من اسم الملف
            match = re.match(r'^(\d{4}_\d{2}_\d{2}_\d{6})_(.+)\.sql$', file)
            if not match:
                continue
            
            version = match.group(1)
            name = match.group(2)
            
            with open(os.path.join(self._migrations_dir, file), 'r', encoding='utf-8') as f:
                content = f.read()
            
            # استخراج UP و DOWN من المحتوى
            up_match = re.search(r'-- UP\s+(.*?)\s+-- DOWN', content, re.DOTALL)
            down_match = re.search(r'-- DOWN\s+(.*?)$', content, re.DOTALL)
            
            migration = Migration(
                version=version,
                name=name,
                description=f"Migration {version}: {name}",
                up=up_match.group(1).strip() if up_match else "",
                down=down_match.group(1).strip() if down_match else ""
            )
            self._migrations.append(migration)
        
        logger.info(f"📋 Loaded {len(self._migrations)} migrations")
    
    def get_applied_migrations(self) -> List[str]:
        """الحصول على قائمة الترحيلات المطبقة"""
        with self._engine.connect() as conn:
            result = conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
            return [row[0] for row in result]
    
    def get_pending_migrations(self) -> List[Migration]:
        """الحصول على الترحيلات غير المطبقة"""
        applied = set(self.get_applied_migrations())
        return [m for m in self._migrations if m.version not in applied]
    
    def apply_migration(self, migration: Migration) -> bool:
        """تطبيق ترحيلة واحدة"""
        try:
            with self._engine.connect() as conn:
                conn.execute(text("BEGIN"))
                
                # تطبيق SQL
                for statement in migration.up.split(';'):
                    statement = statement.strip()
                    if statement:
                        conn.execute(text(statement))
                
                # تسجيل التطبيق
                conn.execute(text("""
                    INSERT INTO schema_migrations (version, name, description, up_sql, down_sql)
                    VALUES (:version, :name, :description, :up_sql, :down_sql)
                """), {
                    "version": migration.version,
                    "name": migration.name,
                    "description": migration.description,
                    "up_sql": migration.up,
                    "down_sql": migration.down
                })
                
                conn.execute(text("COMMIT"))
                logger.info(f"✅ Migration applied: {migration.version} - {migration.name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Failed to apply migration {migration.version}: {e}")
            return False
    
    def migrate(self) -> Dict[str, Any]:
        """تطبيق جميع الترحيلات المعلقة"""
        self.load_migrations()
        pending = self.get_pending_migrations()
        
        result = {
            "success": True,
            "applied": [],
            "errors": []
        }
        
        if not pending:
            logger.info("✅ No pending migrations")
            return result
        
        logger.info(f"🔄 Applying {len(pending)} migrations...")
        
        for migration in pending:
            if self.apply_migration(migration):
                result["applied"].append(migration.version)
            else:
                result["errors"].append(migration.version)
                result["success"] = False
                break
        
        return result
    
    def rollback(self, version: str) -> bool:
        """التراجع عن ترحيلة"""
        with self._engine.connect() as conn:
            # الحصول على SQL للتراجع
            result = conn.execute(text("""
                SELECT down_sql FROM schema_migrations WHERE version = :version
            """), {"version": version})
            
            row = result.first()
            if not row:
                logger.error(f"❌ Migration {version} not found")
                return False
            
            try:
                conn.execute(text("BEGIN"))
                for statement in row[0].split(';'):
                    statement = statement.strip()
                    if statement:
                        conn.execute(text(statement))
                
                conn.execute(text("DELETE FROM schema_migrations WHERE version = :version"), {"version": version})
                conn.execute(text("COMMIT"))
                logger.info(f"✅ Migration rolled back: {version}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to rollback migration {version}: {e}")
                return False