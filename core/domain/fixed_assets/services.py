# core/domain/fixed_assets/services.py
"""
Fixed Assets Services - خدمات الأصول الثابتة والإهلاك
الإصدار: 1.0.0

الميزات:
    1. إدارة دورة حياة الأصول الثابتة
    2. حساب الإهلاك بطرق متعددة
    3. إنشاء جداول الإهلاك
    4. ترحيل الإهلاك إلى المحاسبة
    5. التعامل مع بيع وتصرف الأصول
    6. تقارير الأصول الثابتة
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging

from .entities import FixedAsset
from .value_objects import (
    AssetId,
    AssetCode,
    AssetType,
    AssetStatus,
    DepreciationMethod,
    DisposalMethod,
    DepreciationScheduleEntry,
    DisposalRecord,
    AssetDepreciationSummary,
)
from .events import (
    AssetCreatedEvent,
    DepreciationPostedEvent,
    AssetDisposedEvent,
    AssetFullyDepreciatedEvent,
)
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.services import PostingEngine
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.shared.clock import get_clock

logger = logging.getLogger(__name__)


@dataclass
class DepreciationResult:
    """نتيجة عملية الإهلاك"""
    success: bool
    message: str
    asset_id: Optional[str] = None
    asset_code: Optional[str] = None
    period: Optional[int] = None
    depreciation_amount: Decimal = Decimal('0')
    accumulated_depreciation: Decimal = Decimal('0')
    net_book_value: Decimal = Decimal('0')
    journal_entry_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message': self.message,
            'asset_id': self.asset_id,
            'asset_code': self.asset_code,
            'period': self.period,
            'depreciation_amount': float(self.depreciation_amount),
            'accumulated_depreciation': float(self.accumulated_depreciation),
            'net_book_value': float(self.net_book_value),
            'journal_entry_id': self.journal_entry_id,
            'errors': self.errors
        }


class FixedAssetService:
    """
    خدمة الأصول الثابتة - تدير دورة حياة الأصول
    
    الميزات:
        1. إنشاء وتحديث الأصول
        2. حساب الإهلاك بطرق متعددة
        3. إنشاء جداول الإهلاك
        4. ترحيل الإهلاك إلى المحاسبة
        5. بيع وتصرف الأصول
        6. تقارير الأصول
    """
    
    def __init__(
        self,
        uow: IUnitOfWork,
        posting_engine: PostingEngine,
        depreciation_account: AccountCode = AccountCode("5070"),  # مصروف الإهلاك
        accumulated_depreciation_account: AccountCode = AccountCode("1060"),  # الإهلاك المتراكم
        gain_loss_account: AccountCode = AccountCode("5990"),  # أرباح/خسائر بيع الأصول
        asset_account: AccountCode = AccountCode("1050"),  # الأصول الثابتة
    ):
        self._uow = uow
        self._posting_engine = posting_engine
        self._clock = get_clock()
        
        self._depreciation_account = depreciation_account
        self._accumulated_depreciation_account = accumulated_depreciation_account
        self._gain_loss_account = gain_loss_account
        self._asset_account = asset_account
        
        self._logger = logging.getLogger(__name__)
    
    # =========================================================================
    # إدارة الأصول
    # =========================================================================
    
    def create_asset(
        self,
        code: str,
        name: str,
        acquisition_cost: Decimal,
        acquisition_date: date,
        asset_type: AssetType = AssetType.OTHER,
        useful_life_years: int = 5,
        salvage_value: Decimal = Decimal('0'),
        depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE,
        currency: str = "USD",
        category: Optional[str] = None,
        location: Optional[str] = None,
        responsible_person: Optional[str] = None,
        supplier_id: Optional[str] = None,
        supplier_name: Optional[str] = None,
        serial_number: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: str = "system"
    ) -> FixedAsset:
        """
        إنشاء أصل ثابت جديد
        
        Args:
            code: كود الأصل
            name: اسم الأصل
            acquisition_cost: تكلفة الشراء
            acquisition_date: تاريخ الشراء
            asset_type: نوع الأصل
            useful_life_years: العمر الإنتاجي
            salvage_value: القيمة المتبقية
            depreciation_method: طريقة الإهلاك
            currency: العملة
            category: التصنيف
            location: الموقع
            responsible_person: الشخص المسؤول
            supplier_id: معرف المورد
            supplier_name: اسم المورد
            serial_number: الرقم التسلسلي
            notes: ملاحظات
            created_by: من قام بالإنشاء
        
        Returns:
            FixedAsset: الأصل المنشأ
        """
        self._logger.info(f"Creating asset: {code} - {name}")
        
        # التحقق من عدم وجود كود مكرر
        with self._uow:
            existing = self._uow.assets.get_by_code(AssetCode(code))
            if existing:
                raise ValueError(f"Asset code already exists: {code}")
        
        asset = FixedAsset.create(
            code=code,
            name=name,
            acquisition_cost=acquisition_cost,
            acquisition_date=acquisition_date,
            asset_type=asset_type,
            useful_life_years=useful_life_years,
            salvage_value=salvage_value,
            depreciation_method=depreciation_method,
            currency=currency,
            category=category,
            location=location,
            responsible_person=responsible_person,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            serial_number=serial_number,
            notes=notes,
            created_by=created_by
        )
        
        with self._uow:
            self._uow.assets.save(asset)
            self._uow.commit()
        
        self._logger.info(f"Asset created: {asset.code} - {asset.name}")
        return asset
    
    def get_asset(self, asset_id: str) -> Optional[FixedAsset]:
        """الحصول على أصل بواسطة المعرف"""
        with self._uow:
            return self._uow.assets.get_by_id(AssetId.from_string(asset_id))
    
    def get_asset_by_code(self, code: str) -> Optional[FixedAsset]:
        """الحصول على أصل بواسطة الكود"""
        with self._uow:
            return self._uow.assets.get_by_code(AssetCode(code))
    
    def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        status: Optional[AssetStatus] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[FixedAsset]:
        """قائمة الأصول"""
        with self._uow:
            return self._uow.assets.list_all(
                asset_type=asset_type,
                status=status,
                include_inactive=include_inactive,
                limit=limit,
                offset=offset
            )
    
    def update_asset(
        self,
        asset_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        responsible_person: Optional[str] = None,
        notes: Optional[str] = None,
        updated_by: str = "system"
    ) -> FixedAsset:
        """تحديث بيانات الأصل"""
        with self._uow:
            asset = self._uow.assets.get_by_id(AssetId.from_string(asset_id))
            if not asset:
                raise ValueError(f"Asset not found: {asset_id}")
            
            asset.update(
                name=name,
                description=description,
                location=location,
                responsible_person=responsible_person,
                notes=notes,
                updated_by=updated_by
            )
            
            self._uow.assets.save(asset)
            self._uow.commit()
        
        self._logger.info(f"Asset updated: {asset.code} - {asset.name}")
        return asset
    
    def delete_asset(self, asset_id: str, permanent: bool = False) -> bool:
        """حذف أصل"""
        with self._uow:
            asset = self._uow.assets.get_by_id(AssetId.from_string(asset_id))
            if not asset:
                return False
            
            if asset.is_disposed:
                raise ValueError(f"Cannot delete disposed asset: {asset.code}")
            
            result = self._uow.assets.delete(asset.id, permanent=permanent)
            self._uow.commit()
            
            if result:
                self._logger.info(f"Asset deleted: {asset.code}")
            return result
    
    # =========================================================================
    # عمليات الإهلاك
    # =========================================================================
    
    def calculate_depreciation_for_period(
        self,
        asset_id: str,
        period: int
    ) -> DepreciationResult:
        """
        حساب إهلاك فترة محددة لأصل
        
        Args:
            asset_id: معرف الأصل
            period: رقم الفترة (1-based)
        
        Returns:
            DepreciationResult: نتيجة الحساب
        """
        with self._uow:
            asset = self._uow.assets.get_by_id(AssetId.from_string(asset_id))
            if not asset:
                return DepreciationResult(
                    success=False,
                    message=f"Asset not found: {asset_id}",
                    errors=[f"Asset not found: {asset_id}"]
                )
            
            if period < 1 or period > len(asset.schedule):
                return DepreciationResult(
                    success=False,
                    message=f"Invalid period: {period}",
                    errors=[f"Period {period} out of range (1-{len(asset.schedule)})"]
                )
            
            entry = asset.schedule[period - 1]
            if entry.is_posted:
                return DepreciationResult(
                    success=False,
                    message=f"Period {period} already posted",
                    errors=[f"Period {period} already posted"]
                )
            
            return DepreciationResult(
                success=True,
                message="Depreciation calculated successfully",
                asset_id=str(asset.id.value),
                asset_code=str(asset.code),
                period=period,
                depreciation_amount=entry.depreciation_amount,
                accumulated_depreciation=entry.accumulated_depreciation,
                net_book_value=entry.net_book_value
            )
    
    def post_depreciation(
        self,
        asset_id: str,
        period: int,
        posted_by: str = "system"
    ) -> DepreciationResult:
        """
        ترحيل إهلاك فترة محددة إلى المحاسبة
        
        Args:
            asset_id: معرف الأصل
            period: رقم الفترة
            posted_by: من قام بالترحيل
        
        Returns:
            DepreciationResult: نتيجة الترحيل
        """
        self._logger.info(f"Posting depreciation for asset {asset_id}, period {period}")
        
        with self._uow:
            asset = self._uow.assets.get_by_id(AssetId.from_string(asset_id))
            if not asset:
                return DepreciationResult(
                    success=False,
                    message=f"Asset not found: {asset_id}",
                    errors=[f"Asset not found: {asset_id}"]
                )
            
            if period < 1 or period > len(asset.schedule):
                return DepreciationResult(
                    success=False,
                    message=f"Invalid period: {period}",
                    errors=[f"Period {period} out of range"]
                )
            
            entry = asset.schedule[period - 1]
            if entry.is_posted:
                return DepreciationResult(
                    success=False,
                    message=f"Period {period} already posted",
                    errors=[f"Period {period} already posted"]
                )
            
            # إنشاء القيد المحاسبي
            journal_entry = self._create_depreciation_journal_entry(
                asset=asset,
                entry=entry,
                posted_by=posted_by
            )
            
            # ترحيل القيد
            post_result = self._posting_engine.post(
                journal_entry,
                posted_by,
                skip_save=False
            )
            
            if not post_result.success:
                return DepreciationResult(
                    success=False,
                    message=f"Posting failed: {post_result.message}",
                    errors=post_result.errors
                )
            
            # تحديث حالة الأصل
            asset.post_depreciation(period, post_result.journal_entry_id, posted_by)
            self._uow.assets.save(asset)
            
            # التحقق من اكتمال الإهلاك
            if asset.is_fully_depreciated:
                from .events import AssetFullyDepreciatedEvent
                asset.add_event(AssetFullyDepreciatedEvent(
                    asset_id=asset.id,
                    asset_code=asset.code,
                    asset_name=asset.name,
                    net_book_value=asset.net_book_value,
                    total_depreciation=asset.depreciated_amount
                ))
            
            self._uow.commit()
            
            self._logger.info(
                f"Depreciation posted: {asset.code} - Period {period}, "
                f"Amount: {entry.depreciation_amount}"
            )
            
            return DepreciationResult(
                success=True,
                message="Depreciation posted successfully",
                asset_id=str(asset.id.value),
                asset_code=str(asset.code),
                period=period,
                depreciation_amount=entry.depreciation_amount,
                accumulated_depreciation=entry.accumulated_depreciation,
                net_book_value=entry.net_book_value,
                journal_entry_id=post_result.journal_entry_id
            )
    
    def post_all_depreciation(
        self,
        asset_id: str,
        posted_by: str = "system"
    ) -> List[DepreciationResult]:
        """
        ترحيل جميع فترات الإهلاك غير المرحلة
        
        Args:
            asset_id: معرف الأصل
            posted_by: من قام بالترحيل
        
        Returns:
            List[DepreciationResult]: نتائج الترحيل
        """
        results = []
        
        with self._uow:
            asset = self._uow.assets.get_by_id(AssetId.from_string(asset_id))
            if not asset:
                return [DepreciationResult(
                    success=False,
                    message=f"Asset not found: {asset_id}",
                    errors=[f"Asset not found: {asset_id}"]
                )]
            
            for period, entry in enumerate(asset.schedule, 1):
                if not entry.is_posted:
                    result = self.post_depreciation(asset_id, period, posted_by)
                    results.append(result)
                    
                    if not result.success:
                        self._logger.warning(
                            f"Failed to post period {period} for asset {asset.code}: {result.message}"
                        )
            
            return results
    
    def run_monthly_depreciation(
        self,
        as_of_date: Optional[date] = None,
        posted_by: str = "system"
    ) -> List[DepreciationResult]:
        """
        تشغيل الإهلاك الشهري لجميع الأصول
        
        Args:
            as_of_date: تاريخ الإهلاك (اليوم إذا لم يحدد)
            posted_by: من قام بالترحيل
        
        Returns:
            List[DepreciationResult]: نتائج الترحيل
        """
        if as_of_date is None:
            as_of_date = self._clock.today()
        
        self._logger.info(f"Running monthly depreciation as of {as_of_date}")
        
        results = []
        
        with self._uow:
            # جلب جميع الأصول النشطة
            assets = self._uow.assets.list_all(
                status=[AssetStatus.ACTIVE, AssetStatus.DEPRECIATING],
                include_inactive=False,
                limit=10000
            )
            
            for asset in assets:
                if asset.is_fully_depreciated or asset.is_disposed:
                    continue
                
                # البحث عن الفترة التالية غير المرحلة
                for period, entry in enumerate(asset.schedule, 1):
                    if not entry.is_posted:
                        # التحقق من أن الفترة قد حان وقتها
                        if entry.start_date <= as_of_date:
                            result = self.post_depreciation(
                                str(asset.id.value),
                                period,
                                posted_by
                            )
                            results.append(result)
                        break
            
            self._uow.commit()
        
        self._logger.info(f"Monthly depreciation completed: {len(results)} entries posted")
        return results
    
    def _create_depreciation_journal_entry(
        self,
        asset: FixedAsset,
        entry: DepreciationScheduleEntry,
        posted_by: str
    ) -> JournalEntry:
        """إنشاء قيد محاسبي للإهلاك"""
        lines = [
            JournalLine(
                account_code=self._depreciation_account,
                debit=Money(entry.depreciation_amount, asset.currency),
                credit=Money(Decimal('0'), asset.currency)
            ),
            JournalLine(
                account_code=self._accumulated_depreciation_account,
                debit=Money(Decimal('0'), asset.currency),
                credit=Money(entry.depreciation_amount, asset.currency)
            )
        ]
        
        return JournalEntry(
            date=self._clock.now(),
            description=(
                f"إهلاك {asset.name} - الفترة {entry.period} "
                f"({entry.start_date} - {entry.end_date})"
            ),
            lines=lines
        )
    
    # =========================================================================
    # بيع وتصرف الأصول
    # =========================================================================
    
    def dispose_asset(
        self,
        asset_id: str,
        disposal_date: date,
        disposal_method: DisposalMethod,
        sale_amount: Optional[Decimal] = None,
        scrap_value: Optional[Decimal] = None,
        reason: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        posted_by: str = "system"
    ) -> Dict[str, Any]:
        """
        التصرف في الأصل (بيع، خردة، إلخ)
        
        Args:
            asset_id: معرف الأصل
            disposal_date: تاريخ التصرف
            disposal_method: طريقة التصرف
            sale_amount: مبلغ البيع (إن وجد)
            scrap_value: قيمة الخردة (إن وجد)
            reason: سبب التصرف
            reference_type: نوع المرجع
            reference_id: معرف المرجع
            posted_by: من قام بالتصرف
        
        Returns:
            Dict[str, Any]: نتيجة التصرف
        """
        self._logger.info(f"Disposing asset {asset_id} via {disposal_method.value}")
        
        with self._uow:
            asset = self._uow.assets.get_by_id(AssetId.from_string(asset_id))
            if not asset:
                return {
                    'success': False,
                    'message': f"Asset not found: {asset_id}",
                    'errors': [f"Asset not found: {asset_id}"]
                }
            
            if asset.is_disposed:
                return {
                    'success': False,
                    'message': f"Asset already disposed: {asset.code}",
                    'errors': [f"Asset already disposed: {asset.code}"]
                }
            
            # تسجيل التصرف
            record = asset.dispose(
                disposal_date=disposal_date,
                disposal_method=disposal_method,
                sale_amount=sale_amount,
                scrap_value=scrap_value,
                reason=reason,
                reference_type=reference_type,
                reference_id=reference_id,
                disposed_by=posted_by
            )
            
            # إنشاء قيد محاسبي
            journal_entry = self._create_disposal_journal_entry(
                asset=asset,
                record=record,
                posted_by=posted_by
            )
            
            if journal_entry:
                post_result = self._posting_engine.post(
                    journal_entry,
                    posted_by,
                    skip_save=False
                )
                
                if not post_result.success:
                    return {
                        'success': False,
                        'message': f"Disposal journal entry failed: {post_result.message}",
                        'errors': post_result.errors
                    }
                
                record = replace(record, journal_entry_id=post_result.journal_entry_id)
                asset.disposal_record = record
            
            self._uow.assets.save(asset)
            self._uow.commit()
            
            self._logger.info(f"Asset disposed: {asset.code} - {disposal_method.value}")
            
            return {
                'success': True,
                'message': f"Asset disposed successfully via {disposal_method.value}",
                'asset_id': str(asset.id.value),
                'asset_code': str(asset.code),
                'asset_name': asset.name,
                'disposal_method': disposal_method.value,
                'gain_loss_amount': float(record.gain_loss_amount) if record.gain_loss_amount else None,
                'journal_entry_id': record.journal_entry_id,
                'net_book_value': float(asset.net_book_value)
            }
    
    def _create_disposal_journal_entry(
        self,
        asset: FixedAsset,
        record: DisposalRecord,
        posted_by: str
    ) -> Optional[JournalEntry]:
        """إنشاء قيد محاسبي للتصرف في الأصل"""
        lines = []
        
        # 1. إزالة الأصل من حساب الأصول الثابتة
        lines.append(JournalLine(
            account_code=self._asset_account,
            debit=Money(Decimal('0'), asset.currency),
            credit=Money(asset.acquisition_cost, asset.currency)
        ))
        
        # 2. إزالة الإهلاك المتراكم
        lines.append(JournalLine(
            account_code=self._accumulated_depreciation_account,
            debit=Money(asset.accumulated_depreciation, asset.currency),
            credit=Money(Decimal('0'), asset.currency)
        ))
        
        # 3. تسجيل قيمة البيع (إن وجدت)
        if record.sale_amount and record.sale_amount > 0:
            lines.append(JournalLine(
                account_code=AccountCode("1010"),  # الصندوق
                debit=Money(record.sale_amount, asset.currency),
                credit=Money(Decimal('0'), asset.currency)
            ))
        
        # 4. تسجيل الربح/الخسارة
        if record.gain_loss_amount:
            if record.gain_loss_amount > 0:
                # ربح
                lines.append(JournalLine(
                    account_code=self._gain_loss_account,
                    debit=Money(Decimal('0'), asset.currency),
                    credit=Money(record.gain_loss_amount, asset.currency)
                ))
            else:
                # خسارة
                lines.append(JournalLine(
                    account_code=self._gain_loss_account,
                    debit=Money(abs(record.gain_loss_amount), asset.currency),
                    credit=Money(Decimal('0'), asset.currency)
                ))
        
        if not lines:
            return None
        
        return JournalEntry(
            date=self._clock.now(),
            description=(
                f"تصرف في {asset.name} - {record.disposal_method.value} "
                f"({record.reason or 'بدون سبب'})"
            ),
            lines=lines
        )
    
    # =========================================================================
    # التقارير
    # =========================================================================
    
    def get_asset_summary(self, asset_id: str) -> Optional[AssetDepreciationSummary]:
        """الحصول على ملخص إهلاك الأصل"""
        with self._uow:
            asset = self._uow.assets.get_by_id(AssetId.from_string(asset_id))
            if not asset:
                return None
            
            total_depreciation = asset.depreciated_amount
            remaining = asset.depreciable_amount - total_depreciation
            
            return AssetDepreciationSummary(
                asset_id=str(asset.id.value),
                asset_code=str(asset.code),
                asset_name=asset.name,
                acquisition_cost=asset.acquisition_cost,
                salvage_value=asset.salvage_value,
                depreciable_amount=asset.depreciable_amount,
                total_depreciation=total_depreciation,
                accumulated_depreciation=asset.accumulated_depreciation,
                net_book_value=asset.net_book_value,
                depreciation_percentage=asset.depreciation_percentage,
                useful_life_years=asset.useful_life_years,
                remaining_life_years=float(asset.remaining_life_years),
                current_period_depreciation=asset.monthly_depreciation,
                next_depreciation_date=asset.next_depreciation_date,
                is_fully_depreciated=asset.is_fully_depreciated
            )
    
    def get_depreciation_report(
        self,
        from_date: date,
        to_date: date,
        asset_type: Optional[AssetType] = None
    ) -> Dict[str, Any]:
        """
        تقرير الإهلاك لفترة معينة
        
        Args:
            from_date: بداية الفترة
            to_date: نهاية الفترة
            asset_type: نوع الأصل (اختياري)
        
        Returns:
            Dict[str, Any]: تقرير الإهلاك
        """
        with self._uow:
            assets = self._uow.assets.list_all(
                asset_type=asset_type,
                include_inactive=True,
                limit=10000
            )
            
            report = {
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
                'total_assets': len(assets),
                'total_cost': Decimal('0'),
                'total_accumulated_depreciation': Decimal('0'),
                'total_net_book_value': Decimal('0'),
                'total_monthly_depreciation': Decimal('0'),
                'assets': []
            }
            
            for asset in assets:
                # حساب الإهلاك للفترة
                period_depreciation = Decimal('0')
                for entry in asset.schedule:
                    if entry.start_date and entry.end_date:
                        if entry.start_date <= to_date and entry.end_date >= from_date:
                            period_depreciation += entry.depreciation_amount
                
                asset_data = {
                    'id': str(asset.id.value),
                    'code': str(asset.code),
                    'name': asset.name,
                    'type': asset.asset_type.value,
                    'status': asset.status.value,
                    'acquisition_cost': float(asset.acquisition_cost),
                    'accumulated_depreciation': float(asset.accumulated_depreciation),
                    'net_book_value': float(asset.net_book_value),
                    'period_depreciation': float(period_depreciation),
                    'depreciation_percentage': float(asset.depreciation_percentage),
                    'useful_life_years': asset.useful_life_years,
                    'remaining_life': float(asset.remaining_life_years),
                    'is_fully_depreciated': asset.is_fully_depreciated,
                    'is_disposed': asset.is_disposed
                }
                
                report['assets'].append(asset_data)
                report['total_cost'] += asset.acquisition_cost
                report['total_accumulated_depreciation'] += asset.accumulated_depreciation
                report['total_net_book_value'] += asset.net_book_value
                report['total_monthly_depreciation'] += period_depreciation
            
            # ترتيب الأصول حسب القيمة الدفترية (تنازلي)
            report['assets'].sort(key=lambda x: x['net_book_value'], reverse=True)
            
            return report
    
    def get_assets_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """تجميع الأصول حسب التصنيف"""
        with self._uow:
            assets = self._uow.assets.list_all(limit=10000)
            
            categories = {}
            for asset in assets:
                category = str(asset.category) if asset.category else "غير مصنف"
                if category not in categories:
                    categories[category] = []
                
                categories[category].append({
                    'id': str(asset.id.value),
                    'code': str(asset.code),
                    'name': asset.name,
                    'acquisition_cost': float(asset.acquisition_cost),
                    'net_book_value': float(asset.net_book_value),
                    'status': asset.status.value
                })
            
            return categories
    
    # =========================================================================
    # إحصائيات
    # =========================================================================
    
    def get_asset_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الأصول"""
        with self._uow:
            assets = self._uow.assets.list_all(limit=10000)
            
            stats = {
                'total_assets': len(assets),
                'active_assets': 0,
                'fully_depreciated': 0,
                'disposed': 0,
                'total_cost': Decimal('0'),
                'total_accumulated_depreciation': Decimal('0'),
                'total_net_book_value': Decimal('0'),
                'by_type': {},
                'by_status': {}
            }
            
            for asset in assets:
                stats['total_cost'] += asset.acquisition_cost
                stats['total_accumulated_depreciation'] += asset.accumulated_depreciation
                stats['total_net_book_value'] += asset.net_book_value
                
                if asset.is_active_status:
                    stats['active_assets'] += 1
                
                if asset.is_fully_depreciated:
                    stats['fully_depreciated'] += 1
                
                if asset.is_disposed:
                    stats['disposed'] += 1
                
                # حسب النوع
                key = asset.asset_type.value
                stats['by_type'][key] = stats['by_type'].get(key, 0) + 1
                
                # حسب الحالة
                key = asset.status.value
                stats['by_status'][key] = stats['by_status'].get(key, 0) + 1
            
            return stats


__all__ = [
    'FixedAssetService',
    'DepreciationResult',
]