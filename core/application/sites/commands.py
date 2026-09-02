# core/application/sites/commands.py
"""
Commands and Queries for Sites Module
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from datetime import date  # ✅ إضافة للاستعلامات التي تحتاج تاريخ


# ========== COMMANDS (أوامر - عمليات الكتابة) ==========

@dataclass(frozen=True)
class CreateSiteCommand:
    """أمر إنشاء موقع جديد"""
    code: str
    name: str
    site_type: str = "general"
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    notes: Optional[str] = None
    is_default: bool = False
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateSiteCommand:
    """أمر تحديث موقع موجود"""
    site_id: UUID
    name: Optional[str] = None
    site_type: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    contact_person: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    updated_by: str = "system"
    version: int = 1


@dataclass(frozen=True)
class DeleteSiteCommand:
    """أمر حذف موقع"""
    site_id: UUID
    deleted_by: str = "system"


@dataclass(frozen=True)
class SetDefaultSiteCommand:
    """
    أمر تعيين موقع كافتراضي
    
    يقوم بتعيين موقع محدد كموقع افتراضي للنظام،
    مع إلغاء تعيين أي موقع افتراضي آخر.
    """
    site_id: UUID
    set_by: str = "system"


# ========== QUERIES (استعلامات - عمليات القراءة) ==========

@dataclass(frozen=True)
class GetSiteQuery:
    """استعلام لجلب موقع بواسطة المعرف"""
    site_id: UUID


@dataclass(frozen=True)
class GetSiteByCodeQuery:
    """استعلام لجلب موقع بواسطة الكود"""
    code: str


@dataclass(frozen=True)
class ListSitesQuery:
    """استعلام لجلب قائمة المواقع"""
    site_type: Optional[str] = None
    include_inactive: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetDefaultSiteQuery:
    """
    استعلام لجلب الموقع الافتراضي للنظام
    
    يعيد الموقع الذي تم تعيينه كافتراضي، أو None إذا لم يكن هناك موقع افتراضي.
    """
    pass


@dataclass(frozen=True)
class GetSiteStatisticsQuery:
    """
    استعلام لجلب إحصائيات موقع معين
    
    يقوم بجلب إحصائيات الموقع مثل عدد الفواتير، المبيعات، وأوامر الشراء.
    """
    site_id: UUID
    from_date: Optional[date] = None
    to_date: Optional[date] = None


@dataclass(frozen=True)
class SearchSitesQuery:
    """
    استعلام للبحث عن المواقع
    
    يقوم بالبحث عن المواقع باستخدام النص المدخل في الكود أو الاسم أو المدينة.
    """
    search_text: str
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetSitesForComboQuery:
    """
    استعلام لجلب المواقع للقوائم المنسدلة (Combo Boxes)
    
    يقوم بجلب المواقع بتنسيق مناسب للقوائم المنسدلة،
    مع إمكانية تضمين المواقع غير النشطة.
    """
    include_inactive: bool = False
    limit: int = 1000


__all__ = [
    # Commands
    "CreateSiteCommand",
    "UpdateSiteCommand",
    "DeleteSiteCommand",
    "SetDefaultSiteCommand",  # ✅ جديد
    
    # Queries
    "GetSiteQuery",
    "GetSiteByCodeQuery",  # ✅ جديد
    "ListSitesQuery",
    "GetDefaultSiteQuery",  # ✅ جديد
    "GetSiteStatisticsQuery",  # ✅ جديد
    "SearchSitesQuery",  # ✅ جديد
    "GetSitesForComboQuery",  # ✅ جديد
]