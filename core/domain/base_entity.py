"""
Base Entity - الكيان الأساسي
يستخدم كفئة أساسية لجميع الكيانات في النظام
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional


def utc_now() -> datetime:
    """الحصول على الوقت الحالي بالتوقيت العالمي"""
    return datetime.now(timezone.utc)


@dataclass
class BaseEntity(ABC):
    """
    فئة أساسية لجميع الكيانات
    
    تحتوي على الحقول المشتركة:
    - id: المعرف الفريد
    - created_at: تاريخ الإنشاء
    - updated_at: تاريخ آخر تحديث
    - created_by: معرف من أنشأ الكيان
    - updated_by: معرف من عدل الكيان
    """
    
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    def update_timestamp(self, user_id: Optional[str] = None):
        """تحديث وقت التعديل الأخير"""
        self.updated_at = utc_now()
        if user_id:
            self.updated_by = user_id
    
    def __eq__(self, other):
        """مقارنة الكيانات بناءً على المعرف"""
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id
    
    def __hash__(self):
        """Hash بناءً على المعرف"""
        return hash(self.id)
