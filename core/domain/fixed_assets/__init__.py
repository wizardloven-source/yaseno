# core/domain/fixed_assets/__init__.py
"""
Fixed Assets Domain - الأصول الثابتة والإهلاك
الإصدار: 1.0.0
"""

from .entities import FixedAsset
from .value_objects import (
    AssetId,
    AssetCode,
    AssetType,
    AssetStatus,
    AssetCategory,
    DepreciationMethod,
    DepreciationRate,
    DepreciationScheduleEntry,
    DisposalRecord,
    DisposalMethod,
    AssetDepreciationSummary,
)
from .events import (
    AssetCreatedEvent,
    AssetUpdatedEvent,
    DepreciationPostedEvent,
    AssetDisposedEvent,
    AssetFullyDepreciatedEvent,
)
from .services import FixedAssetService, DepreciationResult

__all__ = [
    # Entities
    'FixedAsset',
    
    # Value Objects
    'AssetId',
    'AssetCode',
    'AssetType',
    'AssetStatus',
    'AssetCategory',
    'DepreciationMethod',
    'DepreciationRate',
    'DepreciationScheduleEntry',
    'DisposalRecord',
    'DisposalMethod',
    'AssetDepreciationSummary',
    
    # Events
    'AssetCreatedEvent',
    'AssetUpdatedEvent',
    'DepreciationPostedEvent',
    'AssetDisposedEvent',
    'AssetFullyDepreciatedEvent',
    
    # Services
    'FixedAssetService',
    'DepreciationResult',
]