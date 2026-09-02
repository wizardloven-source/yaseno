# core/application/sites/dtos.py

"""
Data Transfer Objects for Sites Module
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class SiteDTO:
    """الموقع - DTO كامل"""
    # ✅ الحقول الإجبارية أولاً (بدون قيم افتراضية)
    id: UUID
    code: str
    name: str
    site_type: str
    
    # ✅ الحقول الاختيارية (بقيم افتراضية)
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True
    is_default: bool = False
    is_deleted: bool = False
    
    # ✅ بيانات التدقيق - اجعلها اختيارية بقيم افتراضية
    created_at: Optional[datetime] = None
    created_by: str = "system"
    updated_at: Optional[datetime] = None
    updated_by: str = "system"
    version: int = 1
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        if self.city:
            return f"{self.code} - {self.name} ({self.city})"
        return f"{self.code} - {self.name}"
    
    @property
    def full_address(self) -> str:
        """العنوان الكامل"""
        parts = [self.street, self.city, self.country]
        return ", ".join([p for p in parts if p])
    
    @property
    def is_active_display(self) -> str:
        """نص الحالة للعرض"""
        return "نشط" if self.is_active else "غير نشط"