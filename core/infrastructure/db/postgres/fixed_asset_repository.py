# core/infrastructure/db/postgres/fixed_asset_repository.py

"""
Fixed Asset Repository - PostgreSQL Implementation
مستودع الأصول الثابتة - تطبيق PostgreSQL
الإصدار: 1.0.0
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, delete

from core.domain.fixed_assets.entities import FixedAsset
from core.domain.fixed_assets.value_objects import (
    AssetId, AssetCode, AssetType, AssetStatus, AssetCategory, DepreciationMethod
)
from core.domain.fixed_assets.interfaces import IFixedAssetRepository
from core.infrastructure.db.models.fixed_asset_model import FixedAssetModel, DepreciationScheduleModel

logger = logging.getLogger(__name__)


class PostgresFixedAssetRepository(IFixedAssetRepository):
    """
    تطبيق PostgreSQL لمستودع الأصول الثابتة
    
    الميزات:
        1. دعم Optimistic Locking عبر حقل version
        2. دعم التحميل الكسول (Lazy Loading) للعلاقات
        3. دعم البحث المتقدم بالعديد من الفلاتر
        4. دعم Pagination
    """

    def __init__(self, session: Session):
        self._session = session

    # =========================================================================
    # العمليات الأساسية
    # =========================================================================

    def save(self, asset: FixedAsset) -> None:
        """
        حفظ أصل ثابت (جديد أو محدث) مع التحقق من الإصدار.
        """
        # البحث عن الأصل في قاعدة البيانات
        existing = self._session.execute(
            select(FixedAssetModel).where(FixedAssetModel.id == asset.id.value)
        ).scalar_one_or_none()

        if existing:
            # ✅ تحديث: التحقق من الإصدار (Optimistic Locking)
            # يسمح بمساواة النسخة (تعديل مباشر) أو بزيادة واحدة (دوال المجال التي تزيد النسخة)
            if existing.version != asset.version and existing.version != asset.version - 1:
                from core.shared.exceptions import ConcurrentModificationError
                raise ConcurrentModificationError(
                    entity_type="FixedAsset",
                    entity_id=str(asset.id.value),
                    expected_version=asset.version,
                    actual_version=existing.version
                )
            # تحديث الأصل الموجود
            self._update_model(existing, asset)
            self._sync_schedule(asset)
        else:
# إنشاء أصل جديد
            model = self._to_model(asset)
            self._session.add(model)
            self._sync_schedule(asset)

    def _sync_schedule(self, asset: FixedAsset) -> None:
        """
        مزامنة جدول الإهلاك للأصل مع جدول depreciation_schedule.
        """
        asset_id = asset.id.value
        self._session.flush()
        self._session.execute(
            delete(DepreciationScheduleModel).where(DepreciationScheduleModel.asset_id == asset_id)
        )
        for entry in asset.schedule:
            self._session.add(DepreciationScheduleModel(
                asset_id=asset_id,
                period=entry.period,
                year=entry.year,
                month=entry.month,
                start_date=entry.start_date,
                end_date=entry.end_date,
                depreciation_amount=entry.depreciation_amount,
                accumulated_depreciation=entry.accumulated_depreciation,
                net_book_value=entry.net_book_value,
                is_posted=entry.is_posted,
                posted_at=entry.posted_at,
            ))

    def get_by_id(self, asset_id: AssetId) -> Optional[FixedAsset]:
        """
        الحصول على أصل ثابت بواسطة المعرف مع تحميل جدول الإهلاك.
        """
        model = self._session.execute(
            select(FixedAssetModel)
            
            .where(FixedAssetModel.id == asset_id.value)
        ).scalar_one_or_none()

        if not model:
            return None

        return self._to_domain(model)

    def get_by_code(self, code: AssetCode) -> Optional[FixedAsset]:
        """
        الحصول على أصل ثابت بواسطة الكود.
        """
        model = self._session.execute(
            select(FixedAssetModel)
            
            .where(FixedAssetModel.code == code.value)
        ).scalar_one_or_none()

        if not model:
            return None

        return self._to_domain(model)

    def get_by_serial_number(self, serial_number: str) -> Optional[FixedAsset]:
        """
        الحصول على أصل ثابت بواسطة الرقم التسلسلي.
        """
        model = self._session.execute(
            select(FixedAssetModel)
            
            .where(FixedAssetModel.serial_number == serial_number)
        ).scalar_one_or_none()

        if not model:
            return None

        return self._to_domain(model)

    # =========================================================================
    # القوائم والبحث
    # =========================================================================

    def list_all(
        self,
        asset_type: Optional[AssetType] = None,
        status: Optional[AssetStatus] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[FixedAsset]:
        """
        قائمة جميع الأصول مع خيارات التصفية والترقيم.
        """
        query = select(FixedAssetModel)

        # تصفية حسب النوع
        if asset_type:
            query = query.where(FixedAssetModel.asset_type == asset_type.value)

        # تصفية حسب الحالة
        if status is not None:
            if isinstance(status, (list, tuple, set)):
                status_values = [s.value if hasattr(s, 'value') else s for s in status]
                query = query.where(FixedAssetModel.status.in_(status_values))
            else:
                status_value = status.value if hasattr(status, 'value') else status
                query = query.where(FixedAssetModel.status == status_value)

        # تضمين الأصول غير النشطة
        if not include_inactive:
            query = query.where(FixedAssetModel.is_active == True)

        # تنفيذ الاستعلام مع الترتيب والترقيم
        models = self._session.execute(
            query.order_by(FixedAssetModel.code).limit(limit).offset(offset)
        ).scalars().all()

        return [self._to_domain(model) for model in models]

    def list_by_status(
        self,
        statuses: List[AssetStatus],
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[FixedAsset]:
        """
        قائمة الأصول حسب الحالات المحددة.
        """
        status_values = [s.value for s in statuses]
        query = select(FixedAssetModel)

        query = query.where(FixedAssetModel.status.in_(status_values))

        if not include_inactive:
            query = query.where(FixedAssetModel.is_active == True)

        models = self._session.execute(
            query.order_by(FixedAssetModel.code).limit(limit).offset(offset)
        ).scalars().all()

        return [self._to_domain(model) for model in models]

    def list_by_category(self, category: str, limit: int = 100) -> List[FixedAsset]:
        """
        قائمة الأصول حسب التصنيف.
        """
        query = select(FixedAssetModel)
        query = query.where(FixedAssetModel.category == category)

        models = self._session.execute(
            query.order_by(FixedAssetModel.code).limit(limit)
        ).scalars().all()

        return [self._to_domain(model) for model in models]

    def list_by_asset_type(
        self,
        asset_type: Optional[AssetType] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[FixedAsset]:
        """
        قائمة الأصول حسب النوع.
        """
        query = select(FixedAssetModel)

        if asset_type is not None:
            query = query.where(FixedAssetModel.asset_type == asset_type.value)

        if not include_inactive:
            query = query.where(FixedAssetModel.is_active == True)

        models = self._session.execute(
            query.order_by(FixedAssetModel.code).limit(limit).offset(offset)
        ).scalars().all()

        return [self._to_domain(model) for model in models]

    def get_depreciable_assets(self, as_of_date: date, limit: int = 100) -> List[FixedAsset]:
        """
        الحصول على الأصول القابلة للإهلاك حتى تاريخ معين.
        """
        query = select(FixedAssetModel)

        # الأصول النشطة وغير المكتملة الإهلاك
        query = query.where(
            and_(
                FixedAssetModel.is_active == True,
                FixedAssetModel.is_fully_depreciated == False,
                FixedAssetModel.acquisition_date <= as_of_date,
                FixedAssetModel.status.in_([
                    AssetStatus.ACTIVE.value,
                    AssetStatus.DEPRECIATING.value
                ])
            )
        )

        models = self._session.execute(
            query.order_by(FixedAssetModel.code).limit(limit)
        ).scalars().all()

        return [self._to_domain(model) for model in models]

    def get_fully_depreciated_assets(self, limit: int = 100) -> List[FixedAsset]:
        """
        الحصول على الأصول المكتملة الإهلاك.
        """
        query = select(FixedAssetModel)
        query = query.where(FixedAssetModel.is_fully_depreciated == True)

        models = self._session.execute(
            query.order_by(FixedAssetModel.code).limit(limit)
        ).scalars().all()

        return [self._to_domain(model) for model in models]

    # =========================================================================
    # البحث
    # =========================================================================

    def search(
        self,
        search_text: str,
        asset_type: Optional[AssetType] = None,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[FixedAsset]:
        """
        البحث في الأصول بالكود أو الاسم أو الرقم التسلسلي.
        """
        search_pattern = f"%{search_text}%"
        query = select(FixedAssetModel)

        # شروط البحث
        search_conditions = or_(
            FixedAssetModel.code.ilike(search_pattern),
            FixedAssetModel.name.ilike(search_pattern),
            FixedAssetModel.serial_number.ilike(search_pattern),
            FixedAssetModel.barcode.ilike(search_pattern)
        )
        query = query.where(search_conditions)

        if asset_type:
            query = query.where(FixedAssetModel.asset_type == asset_type.value)

        if not include_inactive:
            query = query.where(FixedAssetModel.is_active == True)

        models = self._session.execute(
            query.order_by(FixedAssetModel.code).limit(limit).offset(offset)
        ).scalars().all()

        return [self._to_domain(model) for model in models]

    # =========================================================================
    # الحذف
    # =========================================================================

    def delete(self, asset_id: AssetId, permanent: bool = False) -> bool:
        """
        حذف أصل ثابت (ناعم أو دائم).
        """
        model = self._session.execute(
            select(FixedAssetModel).where(FixedAssetModel.id == asset_id.value)
        ).scalar_one_or_none()

        if not model:
            return False

        # منع حذف الأصل إذا كان مرتبطاً بحركات محاسبية (يتم التحقق في الخدمة)
        if permanent:
            self._session.delete(model)
        else:
            # حذف ناعم: تعطيل الأصل فقط
            model.is_active = False
            model.is_deleted = True
            model.deleted_at = date.today()

        self._session.flush()
        return True

    # =========================================================================
    # دوال مساعدة
    # =========================================================================

    def get_next_code(self, prefix: str = "A") -> str:
        """
        توليد كود أصل تلقائي.
        """
        # جلب آخر كود مستخدم
        result = self._session.execute(
            select(FixedAssetModel.code)
            .where(FixedAssetModel.code.startswith(prefix))
            .order_by(FixedAssetModel.code.desc())
            .limit(1)
        ).scalar_one_or_none()

        if result:
            # استخراج الرقم التسلسلي من الكود
            try:
                last_num = int(result.replace(prefix, ''))
                next_num = last_num + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        return f"{prefix}-{next_num:05d}"

    def count_all(self, asset_type: Optional[AssetType] = None, include_inactive: bool = False) -> int:
        """
        حساب عدد الأصول.
        """
        query = select(func.count()).select_from(FixedAssetModel)

        if asset_type:
            query = query.where(FixedAssetModel.asset_type == asset_type.value)

        if not include_inactive:
            query = query.where(FixedAssetModel.is_active == True)

        return self._session.execute(query).scalar_one()

    def exists_by_code(self, code: AssetCode) -> bool:
        """
        التحقق من وجود أصل بالكود.
        """
        result = self._session.execute(
            select(FixedAssetModel.id).where(FixedAssetModel.code == code.value).limit(1)
        ).scalar_one_or_none()

        return result is not None

    # =========================================================================
    # عمليات الإهلاك
    # =========================================================================

    def get_assets_for_depreciation(
        self,
        as_of_date: date,
        limit: int = 100
    ) -> List[FixedAsset]:
        """
        الحصول على الأصول التي تحتاج إلى إهلاك في تاريخ معين.
        """
        query = select(FixedAssetModel)

        query = query.where(
            and_(
                FixedAssetModel.is_active == True,
                FixedAssetModel.is_fully_depreciated == False,
                or_(
                    FixedAssetModel.next_depreciation_date <= as_of_date,
                    FixedAssetModel.next_depreciation_date.is_(None)
                ),
                FixedAssetModel.status.in_([
                    AssetStatus.ACTIVE.value,
                    AssetStatus.DEPRECIATING.value
                ])
            )
        )

        models = self._session.execute(
            query.order_by(FixedAssetModel.next_depreciation_date).limit(limit)
        ).scalars().all()

        return [self._to_domain(model) for model in models]

    def update_depreciation_schedule(
        self,
        asset_id: AssetId,
        schedule_entries: List[Dict[str, Any]]
    ) -> None:
        """
        تحديث جدول الإهلاك للأصل.
        """
        # حذف الجدول القديم
        self._session.execute(
            select(DepreciationScheduleModel)
            .where(DepreciationScheduleModel.asset_id == asset_id.value)
            .delete()
        )

        # إضافة الجدول الجديد
        for entry in schedule_entries:
            schedule_model = DepreciationScheduleModel(
                asset_id=asset_id.value,
                period=entry['period'],
                year=entry['year'],
                month=entry.get('month'),
                start_date=entry['start_date'],
                end_date=entry['end_date'],
                depreciation_amount=entry['depreciation_amount'],
                accumulated_depreciation=entry['accumulated_depreciation'],
                net_book_value=entry['net_book_value'],
                is_posted=entry.get('is_posted', False)
            )
            self._session.add(schedule_model)

    # =========================================================================
    # دوال التحويل (Model ↔ Domain)
    # =========================================================================

    def _to_model(self, asset: FixedAsset) -> FixedAssetModel:
        """
        تحويل كيان المجال (Domain) إلى نموذج SQLAlchemy.
        """
        return FixedAssetModel(
            id=asset.id.value,
            code=asset.code.value,
            name=asset.name,
            description=asset.description,
            asset_type=asset.asset_type.value,
            category=asset.category.value if asset.category else None,
            status=asset.status.value,
            acquisition_date=asset.acquisition_date,
            acquisition_cost=asset.acquisition_cost,
            currency=asset.currency,
            salvage_value=asset.salvage_value,
            useful_life_years=asset.useful_life_years,
            depreciation_method=asset.depreciation_method.value,
            depreciation_rate=asset.depreciation_rate.rate if asset.depreciation_rate else None,
            location=asset.location,
            responsible_person=asset.responsible_person,
            supplier_id=asset.supplier_id,
            supplier_name=asset.supplier_name,
            serial_number=asset.serial_number,
            barcode=asset.barcode,
            is_active=asset.is_active,
            is_fully_depreciated=asset.is_fully_depreciated,
            depreciated_amount=asset.depreciated_amount,
            accumulated_depreciation=asset.accumulated_depreciation,
            net_book_value=asset.net_book_value,
            last_depreciation_date=asset.last_depreciation_date,
            next_depreciation_date=asset.next_depreciation_date,
            notes=asset.notes,
            created_at=asset.created_at,
            created_by=asset.created_by,
            updated_at=asset.updated_at,
            updated_by=asset.updated_by,
            version=asset.version,
            # سيتم إضافة جدول الإهلاك بشكل منفصل
        )

    def _update_model(self, model: FixedAssetModel, asset: FixedAsset) -> None:
        """
        تحديث نموذج SQLAlchemy من كيان المجال.
        """
        model.code = asset.code.value
        model.name = asset.name
        model.description = asset.description
        model.asset_type = asset.asset_type.value
        model.category = asset.category.value if asset.category else None
        model.status = asset.status.value
        model.acquisition_date = asset.acquisition_date
        model.acquisition_cost = asset.acquisition_cost
        model.currency = asset.currency
        model.salvage_value = asset.salvage_value
        model.useful_life_years = asset.useful_life_years
        model.depreciation_method = asset.depreciation_method.value
        model.depreciation_rate = asset.depreciation_rate.rate if asset.depreciation_rate else None
        model.location = asset.location
        model.responsible_person = asset.responsible_person
        model.supplier_id = asset.supplier_id
        model.supplier_name = asset.supplier_name
        model.serial_number = asset.serial_number
        model.barcode = asset.barcode
        model.is_active = asset.is_active
        model.is_fully_depreciated = asset.is_fully_depreciated
        model.depreciated_amount = asset.depreciated_amount
        model.accumulated_depreciation = asset.accumulated_depreciation
        model.net_book_value = asset.net_book_value
        model.last_depreciation_date = asset.last_depreciation_date
        model.next_depreciation_date = asset.next_depreciation_date
        model.notes = asset.notes
        model.updated_at = asset.updated_at
        model.updated_by = asset.updated_by
        model.version = asset.version

    def _to_domain(self, model: FixedAssetModel) -> FixedAsset:
        """
        تحويل نموذج SQLAlchemy إلى كيان المجال (Domain).
        """
        from core.domain.fixed_assets.value_objects import DepreciationScheduleEntry

        # تحويل جدول الإهلاك من جدول depreciation_schedule
        schedule = []
        schedule_models = self._session.execute(
            select(DepreciationScheduleModel)
            .where(DepreciationScheduleModel.asset_id == model.id)
            .order_by(DepreciationScheduleModel.period)
        ).scalars().all()
        for entry in schedule_models:
            schedule.append(DepreciationScheduleEntry(
                period=entry.period,
                year=entry.year,
                month=entry.month,
                start_date=entry.start_date,
                end_date=entry.end_date,
                depreciation_amount=entry.depreciation_amount,
                accumulated_depreciation=entry.accumulated_depreciation,
                net_book_value=entry.net_book_value,
                is_posted=entry.is_posted,
                posted_at=entry.posted_at,
            ))

        # إنشاء كيان المجال
        asset = FixedAsset(
            id=AssetId(model.id),
            code=AssetCode(model.code),
            name=model.name,
            description=model.description,
            asset_type=AssetType(model.asset_type),
            category=AssetCategory(model.category) if model.category else None,
            status=AssetStatus(model.status),
            acquisition_date=model.acquisition_date,
            acquisition_cost=model.acquisition_cost,
            currency=model.currency,
            salvage_value=model.salvage_value,
            useful_life_years=model.useful_life_years,
            depreciation_method=DepreciationMethod(model.depreciation_method),
            location=model.location,
            responsible_person=model.responsible_person,
            supplier_id=model.supplier_id,
            supplier_name=model.supplier_name,
            serial_number=model.serial_number,
            barcode=model.barcode,
            is_active=model.is_active,
            is_fully_depreciated=model.is_fully_depreciated,
            depreciated_amount=model.depreciated_amount,
            accumulated_depreciation=model.accumulated_depreciation,
            net_book_value=model.net_book_value,
            last_depreciation_date=model.last_depreciation_date,
            next_depreciation_date=model.next_depreciation_date,
            notes=model.notes,
            created_at=model.created_at,
            created_by=model.created_by,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
            version=model.version,
            schedule=schedule,
            disposal_record=None  # سيتم تعيينه من نموذج منفصل إذا لزم الأمر
        )

        return asset
