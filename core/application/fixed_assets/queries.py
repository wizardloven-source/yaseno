# core/application/fixed_assets/queries.py
"""
Fixed Assets Queries - استعلامات الأصول الثابتة
الإصدار: 1.0.0

تحتوي على جميع استعلامات القراءة (Queries) الخاصة بالأصول الثابتة
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional, List


# =============================================================================
# استعلامات الأصول
# =============================================================================

@dataclass(frozen=True)
class GetFixedAssetQuery:
    """
    استعلام لجلب أصل ثابت بواسطة المعرف
    
    Attributes:
        asset_id: معرف الأصل
    """
    asset_id: str


@dataclass(frozen=True)
class GetFixedAssetByCodeQuery:
    """
    استعلام لجلب أصل ثابت بواسطة الكود
    
    Attributes:
        code: كود الأصل
    """
    code: str


@dataclass(frozen=True)
class ListFixedAssetsQuery:
    """
    استعلام لقائمة الأصول الثابتة مع خيارات التصفية والترقيم
    
    Attributes:
        asset_type: نوع الأصل (اختياري)
        status: حالة الأصل (اختياري)
        include_inactive: تضمين الأصول غير النشطة
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات
    """
    asset_type: Optional[str] = None
    status: Optional[str] = None
    include_inactive: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class SearchFixedAssetsQuery:
    """
    استعلام للبحث عن الأصول الثابتة
    
    Attributes:
        search_text: نص البحث
        asset_type: نوع الأصل (اختياري)
        include_inactive: تضمين الأصول غير النشطة
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات
    """
    search_text: str
    asset_type: Optional[str] = None
    include_inactive: bool = False
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetFixedAssetStatisticsQuery:
    """
    استعلام لإحصائيات الأصول الثابتة
    
    Attributes:
        include_disposed: تضمين الأصول الم disposed
    """
    include_disposed: bool = False


# =============================================================================
# استعلامات الإهلاك
# =============================================================================

@dataclass(frozen=True)
class GetDepreciationScheduleQuery:
    """
    استعلام لجلب جدول إهلاك أصل ثابت
    
    Attributes:
        asset_id: معرف الأصل
    """
    asset_id: str


@dataclass(frozen=True)
class GetDepreciationReportQuery:
    """
    استعلام لتقرير الإهلاك لفترة معينة
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        asset_type: نوع الأصل (اختياري)
    """
    from_date: date
    to_date: date
    asset_type: Optional[str] = None


@dataclass(frozen=True)
class GetAssetsForDepreciationQuery:
    """
    استعلام لجلب الأصول التي تحتاج إلى إهلاك في تاريخ معين
    
    Attributes:
        as_of_date: تاريخ الإهلاك
        limit: الحد الأقصى للنتائج
    """
    as_of_date: date
    limit: int = 100


# =============================================================================
# استعلامات التقارير
# =============================================================================

@dataclass(frozen=True)
class GetFixedAssetSummaryQuery:
    """
    استعلام لملخص أصل ثابت معين
    
    Attributes:
        asset_id: معرف الأصل
    """
    asset_id: str


@dataclass(frozen=True)
class GetAssetsByCategoryQuery:
    """
    استعلام لتجميع الأصول حسب التصنيف
    
    Attributes:
        include_inactive: تضمين الأصول غير النشطة
    """
    include_inactive: bool = False


@dataclass(frozen=True)
class GetAssetValuationQuery:
    """
    استعلام لتقييم الأصول في تاريخ معين
    
    Attributes:
        as_of_date: تاريخ التقييم
        asset_type: نوع الأصل (اختياري)
        include_disposed: تضمين الأصول الم disposed
    """
    as_of_date: date
    asset_type: Optional[str] = None
    include_disposed: bool = False


__all__ = [
    "GetFixedAssetQuery",
    "GetFixedAssetByCodeQuery",
    "ListFixedAssetsQuery",
    "SearchFixedAssetsQuery",
    "GetFixedAssetStatisticsQuery",
    "GetDepreciationScheduleQuery",
    "GetDepreciationReportQuery",
    "GetAssetsForDepreciationQuery",
    "GetFixedAssetSummaryQuery",
    "GetAssetsByCategoryQuery",
    "GetAssetValuationQuery",
]