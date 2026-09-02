# core/application/fixed_assets/__init__.py
"""
Fixed Assets Application Layer - طبقة تطبيق الأصول الثابتة
الإصدار: 1.0.0

تحتوي على:
    - الأوامر (Commands): عمليات الكتابة (إنشاء، تحديث، حذف، إهلاك، بيع)
    - الاستعلامات (Queries): عمليات القراءة (جلب، بحث، تقارير)
    - DTOs: كائنات نقل البيانات
    - المحولات (Converters): التحويل بين Domain Entities و DTOs
"""

from .commands import (
    # أوامر إدارة الأصول
    CreateFixedAssetCommand,
    UpdateFixedAssetCommand,
    DeleteFixedAssetCommand,
    ActivateFixedAssetCommand,
    DeactivateFixedAssetCommand,
    
    # أوامر الإهلاك
    CalculateDepreciationCommand,
    PostDepreciationCommand,
    PostAllDepreciationCommand,
    RunMonthlyDepreciationCommand,
    
    # أوامر التصرف
    DisposeFixedAssetCommand,
    SellFixedAssetCommand,
    ScrapFixedAssetCommand,
)

from .queries import (
    # استعلامات الأصول
    GetFixedAssetQuery,
    GetFixedAssetByCodeQuery,
    ListFixedAssetsQuery,
    SearchFixedAssetsQuery,
    GetFixedAssetStatisticsQuery,
    
    # استعلامات الإهلاك
    GetDepreciationScheduleQuery,
    GetDepreciationReportQuery,
    GetAssetsForDepreciationQuery,
    
    # استعلامات التقارير
    GetFixedAssetSummaryQuery,
    GetAssetsByCategoryQuery,
    GetAssetValuationQuery,
)

from .dtos import (
    # DTOs الأساسية
    FixedAssetDTO,
    FixedAssetSummaryDTO,
    DepreciationScheduleEntryDTO,
    DepreciationScheduleDTO,
    DisposalRecordDTO,
    
    # DTOs للإنشاء والتحديث
    CreateFixedAssetDTO,
    UpdateFixedAssetDTO,
    DisposeFixedAssetDTO,
)

from .converters import (
    # محولات التحويل
    asset_to_dto,
    asset_to_summary_dto,
    dto_to_asset,
    schedule_entry_to_dto,
    schedule_to_dto,
    disposal_to_dto,
)

__all__ = [
    # Commands
    "CreateFixedAssetCommand",
    "UpdateFixedAssetCommand",
    "DeleteFixedAssetCommand",
    "ActivateFixedAssetCommand",
    "DeactivateFixedAssetCommand",
    "CalculateDepreciationCommand",
    "PostDepreciationCommand",
    "PostAllDepreciationCommand",
    "RunMonthlyDepreciationCommand",
    "DisposeFixedAssetCommand",
    "SellFixedAssetCommand",
    "ScrapFixedAssetCommand",
    
    # Queries
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
    
    # DTOs
    "FixedAssetDTO",
    "FixedAssetSummaryDTO",
    "DepreciationScheduleEntryDTO",
    "DepreciationScheduleDTO",
    "DisposalRecordDTO",
    "CreateFixedAssetDTO",
    "UpdateFixedAssetDTO",
    "DisposeFixedAssetDTO",
    
    # Converters
    "asset_to_dto",
    "asset_to_summary_dto",
    "dto_to_asset",
    "schedule_entry_to_dto",
    "schedule_to_dto",
    "disposal_to_dto",
]