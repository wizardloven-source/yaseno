# core/application/handlers/fixed_assets/create_asset_handler.py
"""
Create Fixed Asset Handler - معالج إنشاء أصل ثابت جديد
"""

import logging

from core.domain.fixed_assets.services import FixedAssetService
from core.domain.fixed_assets.value_objects import AssetType, DepreciationMethod
from core.domain.accounting.interfaces import IUnitOfWork

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.fixed_assets.commands import CreateFixedAssetCommand
from core.application.fixed_assets.dtos import FixedAssetDTO
from core.application.fixed_assets.converters import asset_to_dto

logger = logging.getLogger(__name__)


class CreateFixedAssetHandler(BaseHandler[CreateFixedAssetCommand, FixedAssetDTO]):
    """
    معالج إنشاء أصل ثابت جديد
    
    يقوم بإنشاء أصل ثابت جديد مع:
        1. التحقق من عدم وجود كود مكرر
        2. التحقق من صحة البيانات المدخلة
        3. إنشاء جدول الإهلاك تلقائياً
        4. حفظ الأصل في قاعدة البيانات
    """
    
    def __init__(self, uow: IUnitOfWork, asset_service: FixedAssetService):
        super().__init__(uow)
        self._asset_service = asset_service
    
    @require_permission(Permission.CREATE_DRAFT)
    def handle(self, command: CreateFixedAssetCommand, user_context: UserContext) -> FixedAssetDTO:
        """
        تنفيذ إنشاء أصل ثابت جديد
        
        Args:
            command: أمر إنشاء الأصل
            user_context: سياق المستخدم
        
        Returns:
            FixedAssetDTO: بيانات الأصل الجديد
        """
        logger.info(f"Creating fixed asset: {command.code} - {command.name}")
        
        # التحقق من صحة طريقة الإهلاك
        try:
            depreciation_method = DepreciationMethod(command.depreciation_method)
        except ValueError:
            depreciation_method = DepreciationMethod.STRAIGHT_LINE
            logger.warning(f"Invalid depreciation method '{command.depreciation_method}', using STRAIGHT_LINE")
        
        # التحقق من صحة نوع الأصل
        try:
            asset_type = AssetType(command.asset_type)
        except ValueError:
            asset_type = AssetType.OTHER
            logger.warning(f"Invalid asset type '{command.asset_type}', using OTHER")
        
        # إنشاء الأصل
        asset = self._asset_service.create_asset(
            code=command.code,
            name=command.name,
            acquisition_cost=command.acquisition_cost,
            acquisition_date=command.acquisition_date,
            asset_type=asset_type,
            useful_life_years=command.useful_life_years,
            salvage_value=command.salvage_value,
            depreciation_method=depreciation_method,
            currency=command.currency,
            category=command.category,
            location=command.location,
            responsible_person=command.responsible_person,
            supplier_id=command.supplier_id,
            supplier_name=command.supplier_name,
            serial_number=command.serial_number,
            notes=command.notes,
            created_by=user_context.user_id
        )
        
        logger.info(f"Fixed asset created: {asset.code} - {asset.name} (ID: {asset.id})")
        
        return asset_to_dto(asset)