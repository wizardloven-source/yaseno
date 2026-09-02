# core/domain/settings/interfaces.py
"""Repository Interfaces for Settings"""

from abc import ABC, abstractmethod
from typing import Optional

from .entities import Settings


class ISettingsRepository(ABC):
    """واجهة مستودع الإعدادات"""
    
    @abstractmethod
    def get(self) -> Optional[Settings]:
        """الحصول على إعدادات النظام"""
        pass
    
    @abstractmethod
    def save(self, settings: Settings) -> None:
        """حفظ إعدادات النظام"""
        pass
    
    @abstractmethod
    def get_by_version(self, version: int) -> Optional[Settings]:
        """الحصول على إعدادات بإصدار معين (للتراجع)"""
        pass