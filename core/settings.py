# core/settings.py
"""
Application settings and configuration with .env support
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()


@dataclass(frozen=True)
class DatabaseSettings:
    """Database configuration settings."""
    
    host: str = "localhost"
    port: int = 5432
    database: str = "erpya"
    username: str = "postgres"
    password: str = "postgres"
    
    @property
    def connection_string(self) -> str:
        """Get SQLAlchemy connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        """Create settings from environment variables."""
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "erpya"),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
        )


@dataclass(frozen=True)
class AppSettings:
    """Application configuration."""
    
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    echo_sql: bool = False
    pool_size: int = 5
    max_overflow: int = 10
    debug: bool = False
    secret_key: str = "change-me-in-production"
    
    @classmethod
    def from_env(cls) -> "AppSettings":
        """Create settings from environment variables."""
        return cls(
            database=DatabaseSettings.from_env(),
            echo_sql=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            secret_key=os.getenv("SECRET_KEY", "change-me-in-production"),
        )


# =========================================
# إعدادات المستخدم القابلة للتخصيص
# =========================================

from core.config.settings_manager import settings_manager

def get_user_settings():
    """الحصول على إعدادات المستخدم القابلة للتخصيص"""
    return settings_manager.get()


def save_user_settings(section: str, values: dict):
    """حفظ إعدادات المستخدم"""
    settings_manager.update_section(section, values)


def reset_user_settings():
    """إعادة تعيين إعدادات المستخدم"""
    settings_manager.reset_to_defaults()


# Default settings instance (لإعدادات النظام الأساسية)
settings = AppSettings.from_env()

# إعدادات المستخدم (قابلة للتخصيص)
user_settings = get_user_settings()


__all__ = [
    "DatabaseSettings", 
    "AppSettings", 
    "settings",
    "user_settings",
    "get_user_settings",
    "save_user_settings",
    "reset_user_settings"
]