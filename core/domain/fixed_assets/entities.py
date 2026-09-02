# core/domain/fixed_assets/entities.py
"""
Fixed Assets Entities - كيانات الأصول الثابتة
الإصدار: 1.0.0
"""

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Any, Dict
from uuid import uuid4

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
)
from core.domain.shared.value_objects import Money
from core.domain.shared.clock import get_clock


def utc_now() -> datetime:
    return get_clock().now()


@dataclass
class FixedAsset:
    """
    AGGREGATE ROOT - الأصل الثابت
    
    يمثل أصلاً ثابتاً مملوكاً للشركة مع جميع تفاصيله المحاسبية
    
    Attributes:
        id: معرف فريد للأصل
        code: كود الأصل
        name: اسم الأصل
        description: وصف الأصل
        asset_type: نوع الأصل
        category: تصنيف الأصل
        status: حالة الأصل
        
        acquisition_date: تاريخ الشراء
        acquisition_cost: تكلفة الشراء
        currency: العملة
        
        salvage_value: القيمة المتبقية (الخردة)
        useful_life_years: العمر الإنتاجي بالسنوات
        depreciation_method: طريقة الإهلاك
        depreciation_rate: نسبة الإهلاك السنوية (اختياري)
        
        location: موقع الأصل
        responsible_person: الشخص المسؤول
        supplier_id: معرف المورد
        supplier_name: اسم المورد
        serial_number: الرقم التسلسلي
        barcode: الباركود
        
        notes: ملاحظات
        is_active: هل الأصل نشط؟
        is_fully_depreciated: هل تم إهلاكه بالكامل؟
        
        schedule: جدول الإهلاك
        disposal_record: سجل التصرف (إذا تم التصرف)
        
        created_at: تاريخ الإنشاء
        created_by: من قام بالإنشاء
        updated_at: تاريخ آخر تحديث
        updated_by: من قام بآخر تحديث
        version: رقم الإصدار (للتحكم في التزامن)
    """
    
    # === معلومات أساسية ===
    id: AssetId = field(default_factory=AssetId.generate)
    code: AssetCode = field(default_factory=lambda: AssetCode(""))
    name: str = ""
    description: Optional[str] = None
    asset_type: AssetType = AssetType.OTHER
    category: Optional[AssetCategory] = None
    status: AssetStatus = AssetStatus.DRAFT
    
    # === معلومات الشراء ===
    acquisition_date: date = field(default_factory=date.today)
    acquisition_cost: Decimal = Decimal('0')
    currency: str = "USD"
    purchase_order_id: Optional[str] = None
    invoice_id: Optional[str] = None
    
    # === معلومات الإهلاك ===
    salvage_value: Decimal = Decimal('0')
    useful_life_years: int = 5
    depreciation_method: DepreciationMethod = DepreciationMethod.STRAIGHT_LINE
    depreciation_rate: Optional[DepreciationRate] = None
    
    # === معلومات الموقع والمسؤول ===
    location: Optional[str] = None
    responsible_person: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    
    # === الحالة والإهلاك ===
    notes: Optional[str] = None
    is_active: bool = True
    is_fully_depreciated: bool = False
    depreciated_amount: Decimal = Decimal('0')
    accumulated_depreciation: Decimal = Decimal('0')
    net_book_value: Decimal = Decimal('0')
    last_depreciation_date: Optional[date] = None
    next_depreciation_date: Optional[date] = None
    
    # === الجداول والسجلات ===
    schedule: List[DepreciationScheduleEntry] = field(default_factory=list)
    disposal_record: Optional[DisposalRecord] = None
    
    # === Optimistic Locking ===
    version: int = 1
    
    # === بيانات التدقيق ===
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # =========================================================================
    # الخصائص المحسوبة
    # =========================================================================
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        return f"{self.code} - {self.name}"
    
    @property
    def depreciable_amount(self) -> Decimal:
        """المبلغ القابل للإهلاك = التكلفة - القيمة المتبقية"""
        return self.acquisition_cost - self.salvage_value
    
    @property
    def depreciation_percentage(self) -> Decimal:
        """نسبة الإهلاك السنوية"""
        if self.depreciation_rate:
            return self.depreciation_rate.rate
        if self.useful_life_years > 0:
            return Decimal('100') / Decimal(str(self.useful_life_years))
        return Decimal('0')
    
    @property
    def annual_depreciation(self) -> Decimal:
        """مبلغ الإهلاك السنوي"""
        if self.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
            return self.depreciable_amount / Decimal(str(self.useful_life_years))
        elif self.depreciation_method == DepreciationMethod.NONE:
            return Decimal('0')
        return Decimal('0')
    
    @property
    def monthly_depreciation(self) -> Decimal:
        """مبلغ الإهلاك الشهري"""
        return self.annual_depreciation / Decimal('12')
    
    @property
    def remaining_life_years(self) -> Decimal:
        """العمر المتبقي بالسنوات"""
        if self.is_fully_depreciated:
            return Decimal('0')
        
        remaining = self.depreciable_amount - self.accumulated_depreciation
        if remaining <= 0:
            return Decimal('0')
        
        if self.annual_depreciation > 0:
            return remaining / self.annual_depreciation
        return Decimal(str(self.useful_life_years))
    
    @property
    def acquisition_cost_formatted(self) -> str:
        """تكلفة الشراء منسقة"""
        return f"{self.acquisition_cost:,.2f} {self.currency}"
    
    @property
    def net_book_value_formatted(self) -> str:
        """القيمة الدفترية منسقة"""
        return f"{self.net_book_value:,.2f} {self.currency}"
    
    @property
    def accumulated_depreciation_formatted(self) -> str:
        """الإهلاك المتراكم منسق"""
        return f"{self.accumulated_depreciation:,.2f} {self.currency}"
    
    @property
    def is_active_status(self) -> bool:
        """هل الأصل نشط؟"""
        return self.status in [AssetStatus.ACTIVE, AssetStatus.DEPRECIATING]
    
    @property
    def is_disposed(self) -> bool:
        """هل تم التصرف في الأصل؟"""
        return self.status in [AssetStatus.DISPOSED, AssetStatus.SOLD]
    
    # =========================================================================
    # دالة المصنع
    # =========================================================================
    
    @classmethod
    def create(
        cls,
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
    ) -> 'FixedAsset':
        """
        إنشاء أصل ثابت جديد
        
        Args:
            code: كود الأصل
            name: اسم الأصل
            acquisition_cost: تكلفة الشراء
            acquisition_date: تاريخ الشراء
            asset_type: نوع الأصل
            useful_life_years: العمر الإنتاجي بالسنوات
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
        asset = cls(
            code=AssetCode(code),
            name=name,
            acquisition_cost=acquisition_cost,
            acquisition_date=acquisition_date,
            asset_type=asset_type,
            useful_life_years=useful_life_years,
            salvage_value=salvage_value,
            depreciation_method=depreciation_method,
            currency=currency,
            category=AssetCategory(category) if category else None,
            location=location,
            responsible_person=responsible_person,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            serial_number=serial_number,
            notes=notes,
            created_by=created_by,
            updated_by=created_by,
            status=AssetStatus.ACTIVE,
            net_book_value=acquisition_cost,
            version=1
        )
        
        # إنشاء جدول الإهلاك
        asset._generate_depreciation_schedule()
        
        from .events import AssetCreatedEvent
        asset._events.append(AssetCreatedEvent(
            asset_id=asset.id,
            asset_code=asset.code,
            asset_name=asset.name,
            acquisition_cost=asset.acquisition_cost,
            acquisition_date=asset.acquisition_date,
            created_by=created_by
        ))
        
        return asset
    
    # =========================================================================
    # جدول الإهلاك
    # =========================================================================
    
    def _generate_depreciation_schedule(self) -> None:
        """إنشاء جدول الإهلاك للأصل"""
        if self.depreciation_method == DepreciationMethod.NONE:
            return
        
        self.schedule.clear()
        
        total_periods = self.useful_life_years * 12  # بالأشهر
        remaining_value = self.depreciable_amount
        accumulated = Decimal('0')
        
        for period in range(1, total_periods + 1):
            # حساب الإهلاك للفترة
            dep_amount = self._calculate_period_depreciation(period, remaining_value)
            accumulated += dep_amount
            remaining_value -= dep_amount
            
            # حساب التواريخ
            start_date = self.acquisition_date + timedelta(days=(period - 1) * 30)
            end_date = start_date + timedelta(days=30)
            year = start_date.year
            month = start_date.month
            
            entry = DepreciationScheduleEntry(
                period=period,
                year=year,
                month=month,
                start_date=start_date,
                end_date=end_date,
                depreciation_amount=dep_amount,
                accumulated_depreciation=accumulated,
                net_book_value=self.acquisition_cost - accumulated,
                is_posted=False
            )
            self.schedule.append(entry)
            
            if remaining_value <= 0:
                break
        
        # تحديث التواريخ
        if self.schedule:
            self.next_depreciation_date = self.schedule[0].start_date
    
    def _calculate_period_depreciation(
        self,
        period: int,
        remaining_value: Decimal
    ) -> Decimal:
        """
        حساب مبلغ الإهلاك لفترة معينة
        
        Args:
            period: رقم الفترة (1-based)
            remaining_value: القيمة المتبقية القابلة للإهلاك
        
        Returns:
            Decimal: مبلغ الإهلاك للفترة
        """
        if self.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
            return self.monthly_depreciation
        
        elif self.depreciation_method == DepreciationMethod.DECLINING_BALANCE:
            rate = self.depreciation_percentage / Decimal('100')
            monthly_rate = rate / Decimal('12')
            return remaining_value * monthly_rate
        
        elif self.depreciation_method == DepreciationMethod.DOUBLE_DECLINING:
            rate = (Decimal('2') / Decimal(str(self.useful_life_years)))
            monthly_rate = rate / Decimal('12')
            return remaining_value * monthly_rate
        
        elif self.depreciation_method == DepreciationMethod.SUM_OF_YEARS:
            total_years = self.useful_life_years
            remaining_years = total_years - (period - 1) // 12
            if remaining_years <= 0:
                return Decimal('0')
            sum_of_years = total_years * (total_years + 1) / 2
            annual_dep = self.depreciable_amount * (remaining_years / sum_of_years)
            return annual_dep / Decimal('12')
        
        else:
            return Decimal('0')
    
    # =========================================================================
    # عمليات الإهلاك
    # =========================================================================
    
    def calculate_depreciation(self, as_of_date: date) -> Decimal:
        """
        حساب الإهلاك المستحق حتى تاريخ معين
        
        Args:
            as_of_date: تاريخ الحساب
        
        Returns:
            Decimal: مبلغ الإهلاك المستحق
        """
        if self.is_fully_depreciated:
            return Decimal('0')
        
        if self.depreciation_method == DepreciationMethod.NONE:
            return Decimal('0')
        
        # حساب عدد الأشهر من تاريخ الشراء
        months_diff = (as_of_date.year - self.acquisition_date.year) * 12 + \
                     (as_of_date.month - self.acquisition_date.month)
        
        if months_diff <= 0:
            return Decimal('0')
        
        total_depreciation = Decimal('0')
        remaining_value = self.depreciable_amount
        
        for period in range(1, months_diff + 1):
            dep_amount = self._calculate_period_depreciation(period, remaining_value)
            if remaining_value - dep_amount < 0:
                dep_amount = remaining_value
            
            total_depreciation += dep_amount
            remaining_value -= dep_amount
            
            if remaining_value <= 0:
                break
        
        return total_depreciation
    
    def post_depreciation(
        self,
        period: int,
        journal_entry_id: str,
        posted_by: str
    ) -> None:
        """
        ترحيل إهلاك فترة محددة
        
        Args:
            period: رقم الفترة
            journal_entry_id: معرف القيد المحاسبي
            posted_by: من قام بالترحيل
        """
        if period < 1 or period > len(self.schedule):
            raise ValueError(f"Invalid period: {period}")
        
        entry = self.schedule[period - 1]
        if entry.is_posted:
            raise ValueError(f"Period {period} already posted")
        
        entry = replace(
            entry,
            is_posted=True,
            posted_at=utc_now(),
            journal_entry_id=journal_entry_id
        )
        self.schedule[period - 1] = entry
        
        # تحديث الأرصدة
        self.accumulated_depreciation = entry.accumulated_depreciation
        self.net_book_value = entry.net_book_value
        self.depreciated_amount += entry.depreciation_amount
        self.last_depreciation_date = entry.end_date
        
        # تحديث الحالة
        if self.net_book_value <= self.salvage_value or self.net_book_value <= 0:
            self.is_fully_depreciated = True
            self.status = AssetStatus.FULLY_DEPRECIATED
        
        self.updated_at = utc_now()
        self.updated_by = posted_by
        self.version += 1
        
        from .events import DepreciationPostedEvent
        self._events.append(DepreciationPostedEvent(
            asset_id=self.id,
            asset_code=self.code,
            asset_name=self.name,
            period=period,
            depreciation_amount=entry.depreciation_amount,
            accumulated_depreciation=self.accumulated_depreciation,
            net_book_value=self.net_book_value,
            journal_entry_id=journal_entry_id,
            posted_by=posted_by
        ))
    
    def post_all_depreciation(
        self,
        posted_by: str
    ) -> List[str]:
        """
        ترحيل جميع فترات الإهلاك غير المرحلة
        
        Args:
            posted_by: من قام بالترحيل
        
        Returns:
            List[str]: قائمة معرفات القيود المحاسبية (سيتم تعبئتها من الخارج)
        """
        posted_entries = []
        for period, entry in enumerate(self.schedule, 1):
            if not entry.is_posted:
                # سيتم إنشاء القيد المحاسبي من الخارج
                # هنا فقط نحدث الحالة
                self.schedule[period - 1] = replace(
                    entry,
                    is_posted=True,
                    posted_at=utc_now()
                )
                posted_entries.append(str(period))
        
        self.updated_at = utc_now()
        self.updated_by = posted_by
        self.version += 1
        
        return posted_entries
    
    # =========================================================================
    # عمليات التصرف
    # =========================================================================
    
    def dispose(
        self,
        disposal_date: date,
        disposal_method: DisposalMethod,
        sale_amount: Optional[Decimal] = None,
        scrap_value: Optional[Decimal] = None,
        reason: Optional[str] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        disposed_by: str = "system"
    ) -> DisposalRecord:
        """
        التصرف في الأصل (بيع، خردة، إلخ)
        
        Args:
            disposal_date: تاريخ التصرف
            disposal_method: طريقة التصرف
            sale_amount: مبلغ البيع (إن وجد)
            scrap_value: قيمة الخردة (إن وجد)
            reason: سبب التصرف
            reference_type: نوع المرجع
            reference_id: معرف المرجع
            disposed_by: من قام بالتصرف
        
        Returns:
            DisposalRecord: سجل التصرف
        """
        if self.is_disposed:
            raise ValueError(f"Asset already disposed: {self.code}")
        
        # حساب الربح/الخسارة
        gain_loss_amount = None
        if sale_amount is not None:
            gain_loss_amount = sale_amount - self.net_book_value
        
        record = DisposalRecord(
            disposal_date=disposal_date,
            disposal_method=disposal_method,
            sale_amount=sale_amount,
            scrap_value=scrap_value,
            reason=reason,
            reference_type=reference_type,
            reference_id=reference_id,
            gain_loss_amount=gain_loss_amount
        )
        
        self.disposal_record = record
        self.status = AssetStatus.DISPOSED if disposal_method == DisposalMethod.SCRAP else AssetStatus.SOLD
        self.is_active = False
        self.is_fully_depreciated = True
        self.updated_at = utc_now()
        self.updated_by = disposed_by
        self.version += 1
        
        from .events import AssetDisposedEvent
        self._events.append(AssetDisposedEvent(
            asset_id=self.id,
            asset_code=self.code,
            asset_name=self.name,
            disposal_method=disposal_method.value,
            disposal_date=disposal_date,
            sale_amount=sale_amount,
            gain_loss_amount=gain_loss_amount,
            disposed_by=disposed_by
        ))
        
        return record
    
    # =========================================================================
    # عمليات التحديث
    # =========================================================================
    
    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        responsible_person: Optional[str] = None,
        notes: Optional[str] = None,
        updated_by: str = "system"
    ) -> None:
        """تحديث بيانات الأصل"""
        changes = {}
        
        if name and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name
        
        if description is not None and description != self.description:
            changes['description'] = {'old': self.description, 'new': description}
            self.description = description
        
        if location is not None and location != self.location:
            changes['location'] = {'old': self.location, 'new': location}
            self.location = location
        
        if responsible_person is not None and responsible_person != self.responsible_person:
            changes['responsible_person'] = {'old': self.responsible_person, 'new': responsible_person}
            self.responsible_person = responsible_person
        
        if notes is not None and notes != self.notes:
            changes['notes'] = {'old': self.notes, 'new': notes}
            self.notes = notes
        
        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            self.version += 1
            
            from .events import AssetUpdatedEvent
            self._events.append(AssetUpdatedEvent(
                asset_id=self.id,
                asset_code=self.code,
                asset_name=self.name,
                changes=changes,
                updated_by=updated_by
            ))
    
    # =========================================================================
    # أحداث المجال
    # =========================================================================
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events
    
    def add_event(self, event: Any) -> None:
        self._events.append(event)
    
    # =========================================================================
    # التسلسل
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id.value),
            'code': str(self.code),
            'name': self.name,
            'description': self.description,
            'asset_type': self.asset_type.value,
            'category': str(self.category) if self.category else None,
            'status': self.status.value,
            'acquisition_date': self.acquisition_date.isoformat(),
            'acquisition_cost': float(self.acquisition_cost),
            'currency': self.currency,
            'salvage_value': float(self.salvage_value),
            'useful_life_years': self.useful_life_years,
            'depreciation_method': self.depreciation_method.value,
            'depreciation_rate': float(self.depreciation_rate.rate) if self.depreciation_rate else None,
            'location': self.location,
            'responsible_person': self.responsible_person,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier_name,
            'serial_number': self.serial_number,
            'barcode': self.barcode,
            'is_active': self.is_active,
            'is_fully_depreciated': self.is_fully_depreciated,
            'depreciated_amount': float(self.depreciated_amount),
            'accumulated_depreciation': float(self.accumulated_depreciation),
            'net_book_value': float(self.net_book_value),
            'depreciable_amount': float(self.depreciable_amount),
            'annual_depreciation': float(self.annual_depreciation),
            'monthly_depreciation': float(self.monthly_depreciation),
            'remaining_life_years': float(self.remaining_life_years),
            'last_depreciation_date': self.last_depreciation_date.isoformat() if self.last_depreciation_date else None,
            'next_depreciation_date': self.next_depreciation_date.isoformat() if self.next_depreciation_date else None,
            'schedule': [entry.to_dict() for entry in self.schedule],
            'disposal_record': self.disposal_record.to_dict() if self.disposal_record else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat(),
            'updated_by': self.updated_by,
            'version': self.version
        }
    
    def to_summary(self) -> Dict[str, Any]:
        """ملخص سريع للأصل"""
        return {
            'id': str(self.id.value),
            'code': str(self.code),
            'name': self.name,
            'asset_type': self.asset_type.value,
            'status': self.status.value,
            'acquisition_cost': float(self.acquisition_cost),
            'net_book_value': float(self.net_book_value),
            'accumulated_depreciation': float(self.accumulated_depreciation),
            'depreciation_percentage': float(self.depreciation_percentage),
            'is_fully_depreciated': self.is_fully_depreciated,
            'is_active': self.is_active
        }
    
    def __repr__(self) -> str:
        return f"FixedAsset(id={self.id}, code={self.code}, name={self.name}, status={self.status.value})"


__all__ = [
    'FixedAsset',
]