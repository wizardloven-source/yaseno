# core/application/fixed_assets/converters.py
"""
Fixed Assets Converters - محولات الأصول الثابتة
الإصدار: 1.0.0

تحويل بين Domain Entities و DTOs
"""

from typing import List, Optional
from decimal import Decimal

from core.domain.fixed_assets.entities import FixedAsset
from core.domain.fixed_assets.value_objects import (
    AssetId, AssetCode, AssetType, AssetStatus, AssetCategory,
    DepreciationScheduleEntry, DisposalRecord
)

from .dtos import (
    FixedAssetDTO,
    FixedAssetSummaryDTO,
    DepreciationScheduleEntryDTO,
    DepreciationScheduleDTO,
    DisposalRecordDTO,
    CreateFixedAssetDTO,
    UpdateFixedAssetDTO,
    DisposeFixedAssetDTO,
)


# =============================================================================
# دوال مساعدة للتحويل الآمن
# =============================================================================

def _safe_str(value) -> str:
    """تحويل آمن إلى str"""
    if value is None:
        return ""
    if hasattr(value, 'value'):
        return str(value.value)
    return str(value)


def _safe_decimal(value) -> Decimal:
    """تحويل آمن إلى Decimal"""
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    return Decimal(str(value))


def _safe_date(value):
    """تحويل آمن إلى date"""
    if value is None:
        return None
    if hasattr(value, 'date'):
        return value.date() if hasattr(value, 'date') else value
    return value


def _safe_datetime(value):
    """تحويل آمن إلى datetime"""
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value
    return value


# =============================================================================
# تحويل جدول الإهلاك
# =============================================================================

def schedule_entry_to_dto(entry: DepreciationScheduleEntry) -> DepreciationScheduleEntryDTO:
    """تحويل سطر جدول إهلاك إلى DTO"""
    if not entry:
        return None
    
    return DepreciationScheduleEntryDTO(
        period=entry.period,
        year=entry.year,
        month=entry.month,
        start_date=entry.start_date,
        end_date=entry.end_date,
        depreciation_amount=_safe_decimal(entry.depreciation_amount),
        accumulated_depreciation=_safe_decimal(entry.accumulated_depreciation),
        net_book_value=_safe_decimal(entry.net_book_value),
        is_posted=entry.is_posted,
        posted_at=_safe_datetime(entry.posted_at),
        journal_entry_id=entry.journal_entry_id
    )


def schedule_to_dto(asset: FixedAsset) -> DepreciationScheduleDTO:
    """تحويل جدول إهلاك كامل إلى DTO"""
    if not asset:
        return None
    
    entries = [schedule_entry_to_dto(e) for e in asset.schedule]
    
    return DepreciationScheduleDTO(
        asset_id=_safe_str(asset.id),
        asset_code=_safe_str(asset.code),
        asset_name=asset.name,
        entries=entries,
        total_depreciation=asset.accumulated_depreciation,
        net_book_value=asset.net_book_value,
        remaining_life=int(asset.remaining_life_years)
    )


# =============================================================================
# تحويل سجل التصرف
# =============================================================================

def disposal_to_dto(record: DisposalRecord) -> Optional[DisposalRecordDTO]:
    """تحويل سجل التصرف إلى DTO"""
    if not record:
        return None
    
    return DisposalRecordDTO(
        disposal_date=record.disposal_date,
        disposal_method=record.disposal_method.value if hasattr(record.disposal_method, 'value') else str(record.disposal_method),
        sale_amount=_safe_decimal(record.sale_amount),
        scrap_value=_safe_decimal(record.scrap_value),
        reason=record.reason,
        reference_type=record.reference_type,
        reference_id=record.reference_id,
        journal_entry_id=record.journal_entry_id,
        gain_loss_amount=_safe_decimal(record.gain_loss_amount),
        gain_loss_account=record.gain_loss_account
    )


# =============================================================================
# تحويل الأصول الثابتة
# =============================================================================

def asset_to_dto(asset: FixedAsset) -> FixedAssetDTO:
    """
    تحويل كيان أصل ثابت (Domain) إلى DTO
    
    Args:
        asset: كيان الأصل من Domain Layer
    
    Returns:
        FixedAssetDTO: كائن نقل البيانات
    """
    if not asset:
        return None
    
    return FixedAssetDTO(
        # معلومات أساسية
        id=_safe_str(asset.id),
        code=_safe_str(asset.code),
        name=asset.name,
        description=asset.description,
        asset_type=asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type),
        category=_safe_str(asset.category) if asset.category else None,
        status=asset.status.value if hasattr(asset.status, 'value') else str(asset.status),
        
        # معلومات الشراء
        acquisition_date=asset.acquisition_date,
        acquisition_cost=_safe_decimal(asset.acquisition_cost),
        currency=asset.currency,
        
        # معلومات الإهلاك
        salvage_value=_safe_decimal(asset.salvage_value),
        useful_life_years=asset.useful_life_years,
        depreciation_method=asset.depreciation_method.value if hasattr(asset.depreciation_method, 'value') else str(asset.depreciation_method),
        depreciation_rate=_safe_decimal(asset.depreciation_rate.rate) if asset.depreciation_rate else None,
        
        # معلومات الموقع والمسؤول
        location=asset.location,
        responsible_person=asset.responsible_person,
        supplier_id=asset.supplier_id,
        supplier_name=asset.supplier_name,
        serial_number=asset.serial_number,
        barcode=asset.barcode,
        
        # الحالة والإهلاك
        is_active=asset.is_active,
        is_fully_depreciated=asset.is_fully_depreciated,
        depreciated_amount=_safe_decimal(asset.depreciated_amount),
        accumulated_depreciation=_safe_decimal(asset.accumulated_depreciation),
        net_book_value=_safe_decimal(asset.net_book_value),
        last_depreciation_date=asset.last_depreciation_date,
        next_depreciation_date=asset.next_depreciation_date,
        
        # معلومات إضافية
        notes=asset.notes,
        
        # الجداول والسجلات
        schedule=[schedule_entry_to_dto(e) for e in asset.schedule],
        disposal_record=disposal_to_dto(asset.disposal_record) if asset.disposal_record else None,
        
        # بيانات التدقيق
        created_at=asset.created_at,
        created_by=asset.created_by,
        updated_at=asset.updated_at,
        updated_by=asset.updated_by,
        version=asset.version
    )


def asset_to_summary_dto(asset: FixedAsset) -> FixedAssetSummaryDTO:
    """
    تحويل كيان أصل ثابت (Domain) إلى Summary DTO
    
    Args:
        asset: كيان الأصل من Domain Layer
    
    Returns:
        FixedAssetSummaryDTO: ملخص الأصل
    """
    if not asset:
        return None
    
    return FixedAssetSummaryDTO(
        id=_safe_str(asset.id),
        code=_safe_str(asset.code),
        name=asset.name,
        asset_type=asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type),
        status=asset.status.value if hasattr(asset.status, 'value') else str(asset.status),
        acquisition_cost=_safe_decimal(asset.acquisition_cost),
        net_book_value=_safe_decimal(asset.net_book_value),
        accumulated_depreciation=_safe_decimal(asset.accumulated_depreciation),
        depreciation_percentage=asset.depreciation_percentage,
        is_fully_depreciated=asset.is_fully_depreciated,
        is_active=asset.is_active,
        remaining_life_years=asset.remaining_life_years
    )


def assets_to_dto_list(assets: List[FixedAsset]) -> List[FixedAssetDTO]:
    """
    تحويل قائمة أصول إلى قائمة DTOs
    
    Args:
        assets: قائمة كيانات الأصول
    
    Returns:
        List[FixedAssetDTO]: قائمة DTOs
    """
    if not assets:
        return []
    return [asset_to_dto(a) for a in assets if a]


def assets_to_summary_list(assets: List[FixedAsset]) -> List[FixedAssetSummaryDTO]:
    """
    تحويل قائمة أصول إلى قائمة Summary DTOs
    
    Args:
        assets: قائمة كيانات الأصول
    
    Returns:
        List[FixedAssetSummaryDTO]: قائمة ملخصات الأصول
    """
    if not assets:
        return []
    return [asset_to_summary_dto(a) for a in assets if a]


def dto_to_asset(dto: CreateFixedAssetDTO) -> FixedAsset:
    """
    تحويل DTO إلى كيان أصل ثابت
    
    Args:
        dto: كائن نقل البيانات للإنشاء
    
    Returns:
        FixedAsset: كيان الأصل
    """
    if not dto:
        return None
    
    from core.domain.fixed_assets.entities import FixedAsset
    from core.domain.fixed_assets.value_objects import AssetType, DepreciationMethod
    
    return FixedAsset.create(
        code=dto.code,
        name=dto.name,
        acquisition_cost=dto.acquisition_cost,
        acquisition_date=dto.acquisition_date,
        asset_type=AssetType(dto.asset_type),
        useful_life_years=dto.useful_life_years,
        salvage_value=dto.salvage_value,
        depreciation_method=DepreciationMethod(dto.depreciation_method),
        currency=dto.currency,
        category=dto.category,
        location=dto.location,
        responsible_person=dto.responsible_person,
        supplier_id=dto.supplier_id,
        supplier_name=dto.supplier_name,
        serial_number=dto.serial_number,
        notes=dto.notes,
        created_by=dto.created_by
    )


# =============================================================================
# تصدير جميع الدوال
# =============================================================================

__all__ = [
    "schedule_entry_to_dto",
    "schedule_to_dto",
    "disposal_to_dto",
    "asset_to_dto",
    "asset_to_summary_dto",
    "assets_to_dto_list",
    "assets_to_summary_list",
    "dto_to_asset",
]