# core/application/handlers/fixed_assets/__init__.py
"""
Fixed Assets Handlers - معالجات الأصول الثابتة
"""

from .create_asset_handler import CreateFixedAssetHandler
from .post_depreciation_handler import PostDepreciationHandler
from .run_monthly_depreciation_handler import RunMonthlyDepreciationHandler
from .dispose_asset_handler import DisposeFixedAssetHandler

from .get_asset_query_handler import GetFixedAssetQueryHandler
from .list_assets_query_handler import ListFixedAssetsQueryHandler

__all__ = [
    "CreateFixedAssetHandler",
    "PostDepreciationHandler",
    "RunMonthlyDepreciationHandler",
    "DisposeFixedAssetHandler",
    "GetFixedAssetQueryHandler",
    "ListFixedAssetsQueryHandler",
]