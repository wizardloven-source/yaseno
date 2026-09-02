# core/application/fixed_assets/dtos.py
"""
Fixed Assets DTOs - كائنات نقل البيانات للأصول الثابتة
الإصدار: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List


@dataclass(frozen=True)
class DepreciationScheduleEntryDTO:
    """
    سطر في جدول الإهلاك - DTO
    
    Attributes:
        period: رقم الفترة
        year: السنة
        month: الشهر (اختياري)
        start_date: تاريخ بداية الفترة
        end_date: تاريخ نهاية الفترة
        depreciation_amount: مبلغ الإهلاك
        accumulated_depreciation: الإهلاك المتراكم
        net_book_value: القيمة الدفترية الصافية
        is_posted: هل تم ترحيله محاسبياً؟
        posted_at: تاريخ الترحيل (اختياري)
        journal_entry_id: معرف القيد المحاسبي (اختياري)
    """
    period: int
    year: int
    month: Optional[int] = None
    start_date: date = None
    end_date: date = None
    depreciation_amount: Decimal = Decimal('0')
    accumulated_depreciation: Decimal = Decimal('0')
    net_book_value: Decimal = Decimal('0')
    is_posted: bool = False
    posted_at: Optional[datetime] = None
    journal_entry_id: Optional[str] = None

    @property
    def depreciation_amount_formatted(self) -> str:
        return f"{self.depreciation_amount:,.2f}"

    @property
    def net_book_value_formatted(self) -> str:
        return f"{self.net_book_value:,.2f}"

    @property
    def period_display(self) -> str:
        if self.month:
            return f"{self.year}-{self.month:02d}"
        return f"{self.year}"


@dataclass(frozen=True)
class DepreciationScheduleDTO:
    """
    جدول الإهلاك الكامل - DTO
    
    Attributes:
        asset_id: معرف الأصل
        asset_code: كود الأصل
        asset_name: اسم الأصل
        entries: قائمة أسطر جدول الإهلاك
        total_depreciation: إجمالي الإهلاك
        net_book_value: القيمة الدفترية الحالية
        remaining_life: العمر المتبقي
    """
    asset_id: str
    asset_code: str
    asset_name: str
    entries: List[DepreciationScheduleEntryDTO] = field(default_factory=list)
    total_depreciation: Decimal = Decimal('0')
    net_book_value: Decimal = Decimal('0')
    remaining_life: int = 0

    @property
    def total_depreciation_formatted(self) -> str:
        return f"{self.total_depreciation:,.2f}"

    @property
    def net_book_value_formatted(self) -> str:
        return f"{self.net_book_value:,.2f}"

    @property
    def posted_entries_count(self) -> int:
        return len([e for e in self.entries if e.is_posted])

    @property
    def pending_entries_count(self) -> int:
        return len([e for e in self.entries if not e.is_posted])


@dataclass(frozen=True)
class DisposalRecordDTO:
    """
    سجل التصرف في الأصل - DTO
    
    Attributes:
        disposal_date: تاريخ التصرف
        disposal_method: طريقة التصرف
        sale_amount: مبلغ البيع (إن وجد)
        scrap_value: قيمة الخردة (إن وجد)
        reason: سبب التصرف
        reference_type: نوع المرجع
        reference_id: معرف المرجع
        journal_entry_id: معرف القيد المحاسبي
        gain_loss_amount: مبلغ الربح/الخسارة
        gain_loss_account: حساب الربح/الخسارة
    """
    disposal_date: date
    disposal_method: str
    sale_amount: Optional[Decimal] = None
    scrap_value: Optional[Decimal] = None
    reason: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    journal_entry_id: Optional[str] = None
    gain_loss_amount: Optional[Decimal] = None
    gain_loss_account: Optional[str] = None

    @property
    def sale_amount_formatted(self) -> str:
        return f"{self.sale_amount:,.2f}" if self.sale_amount else "-"

    @property
    def gain_loss_formatted(self) -> str:
        if self.gain_loss_amount is None:
            return "-"
        sign = "+" if self.gain_loss_amount > 0 else ""
        return f"{sign}{self.gain_loss_amount:,.2f}"

    @property
    def is_profit(self) -> bool:
        return self.gain_loss_amount is not None and self.gain_loss_amount > 0

    @property
    def is_loss(self) -> bool:
        return self.gain_loss_amount is not None and self.gain_loss_amount < 0


@dataclass(frozen=True)
class FixedAssetDTO:
    """
    أصل ثابت - DTO كامل
    
    Attributes:
        id: معرف الأصل
        code: كود الأصل
        name: اسم الأصل
        description: وصف الأصل
        asset_type: نوع الأصل
        category: تصنيف الأصل
        status: حالة الأصل
        
        acquisition_date: تاريخ الشراء
        acquisition_cost: تكلفة الشراء
        currency: العملة
        
        salvage_value: القيمة المتبقية
        useful_life_years: العمر الإنتاجي
        depreciation_method: طريقة الإهلاك
        depreciation_rate: نسبة الإهلاك (اختياري)
        
        location: موقع الأصل
        responsible_person: الشخص المسؤول
        supplier_id: معرف المورد
        supplier_name: اسم المورد
        serial_number: الرقم التسلسلي
        barcode: الباركود
        
        is_active: نشط
        is_fully_depreciated: مكتمل الإهلاك
        
        depreciated_amount: المبلغ المكتهل
        accumulated_depreciation: الإهلاك المتراكم
        net_book_value: القيمة الدفترية الصافية
        
        last_depreciation_date: آخر تاريخ إهلاك
        next_depreciation_date: تاريخ الإهلاك التالي
        
        notes: ملاحظات
        schedule: جدول الإهلاك (اختياري)
        disposal_record: سجل التصرف (اختياري)
        
        created_at: تاريخ الإنشاء
        created_by: من قام بالإنشاء
        updated_at: تاريخ التحديث
        updated_by: من قام بالتحديث
        version: رقم الإصدار
    """
    # معلومات أساسية
    id: str
    code: str
    name: str
    description: Optional[str] = None
    asset_type: str = "other"
    category: Optional[str] = None
    status: str = "active"
    
    # معلومات الشراء
    acquisition_date: date = None
    acquisition_cost: Decimal = Decimal('0')
    currency: str = "USD"
    
    # معلومات الإهلاك
    salvage_value: Decimal = Decimal('0')
    useful_life_years: int = 5
    depreciation_method: str = "straight_line"
    depreciation_rate: Optional[Decimal] = None
    
    # معلومات الموقع والمسؤول
    location: Optional[str] = None
    responsible_person: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    
    # الحالة والإهلاك
    is_active: bool = True
    is_fully_depreciated: bool = False
    depreciated_amount: Decimal = Decimal('0')
    accumulated_depreciation: Decimal = Decimal('0')
    net_book_value: Decimal = Decimal('0')
    last_depreciation_date: Optional[date] = None
    next_depreciation_date: Optional[date] = None
    
    # معلومات إضافية
    notes: Optional[str] = None
    
    # الجداول والسجلات
    schedule: List[DepreciationScheduleEntryDTO] = field(default_factory=list)
    disposal_record: Optional[DisposalRecordDTO] = None
    
    # بيانات التدقيق
    created_at: datetime = None
    created_by: str = "system"
    updated_at: datetime = None
    updated_by: str = "system"
    version: int = 1

    # ========== الخصائص المساعدة ==========
    
    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"
    
    @property
    def acquisition_cost_formatted(self) -> str:
        return f"{self.acquisition_cost:,.2f} {self.currency}"
    
    @property
    def net_book_value_formatted(self) -> str:
        return f"{self.net_book_value:,.2f} {self.currency}"
    
    @property
    def accumulated_depreciation_formatted(self) -> str:
        return f"{self.accumulated_depreciation:,.2f} {self.currency}"
    
    @property
    def depreciable_amount(self) -> Decimal:
        return self.acquisition_cost - self.salvage_value
    
    @property
    def depreciable_amount_formatted(self) -> str:
        return f"{self.depreciable_amount:,.2f} {self.currency}"
    
    @property
    def depreciation_percentage(self) -> Decimal:
        if self.depreciation_rate:
            return self.depreciation_rate
        if self.useful_life_years > 0:
            return Decimal('100') / Decimal(str(self.useful_life_years))
        return Decimal('0')
    
    @property
    def depreciation_percentage_formatted(self) -> str:
        return f"{self.depreciation_percentage:.2f}%"
    
    @property
    def annual_depreciation(self) -> Decimal:
        if self.depreciation_method == "straight_line":
            return self.depreciable_amount / Decimal(str(self.useful_life_years))
        return Decimal('0')
    
    @property
    def annual_depreciation_formatted(self) -> str:
        return f"{self.annual_depreciation:,.2f} {self.currency}"
    
    @property
    def remaining_life_years(self) -> Decimal:
        if self.is_fully_depreciated:
            return Decimal('0')
        remaining = self.depreciable_amount - self.accumulated_depreciation
        if remaining <= 0:
            return Decimal('0')
        if self.annual_depreciation > 0:
            return remaining / self.annual_depreciation
        return Decimal(str(self.useful_life_years))

    @property
    def status_display(self) -> str:
        statuses = {
            "draft": "مسودة",
            "active": "نشط",
            "depreciating": "قيد الإهلاك",
            "fully_depreciated": "مكتمل الإهلاك",
            "disposed": "تم التصرف",
            "sold": "مباع",
            "scrapped": "خردة",
        }
        return statuses.get(self.status, self.status)

    @property
    def type_display(self) -> str:
        types = {
            "building": "مبنى",
            "land": "أرض",
            "machinery": "آلات ومعدات",
            "vehicle": "مركبات",
            "furniture": "أثاث",
            "computer": "أجهزة كمبيوتر",
            "software": "برمجيات",
            "intangible": "أصول غير ملموسة",
            "other": "أخرى",
        }
        return types.get(self.asset_type, self.asset_type)

    @property
    def method_display(self) -> str:
        methods = {
            "straight_line": "القسط الثابت",
            "declining_balance": "القسط المتناقص",
            "double_declining": "القسط المتناقص المزدوج",
            "sum_of_years": "مجموع أرقام السنوات",
            "units_of_production": "وحدات الإنتاج",
            "none": "بدون إهلاك",
        }
        return methods.get(self.depreciation_method, self.depreciation_method)

    @property
    def utilization_percentage(self) -> Decimal:
        if self.depreciable_amount == 0:
            return Decimal('0')
        return (self.accumulated_depreciation / self.depreciable_amount) * 100


@dataclass(frozen=True)
class FixedAssetSummaryDTO:
    """
    ملخص أصل ثابت - DTO
    
    Attributes:
        id: معرف الأصل
        code: كود الأصل
        name: اسم الأصل
        asset_type: نوع الأصل
        status: حالة الأصل
        acquisition_cost: تكلفة الشراء
        net_book_value: القيمة الدفترية الصافية
        accumulated_depreciation: الإهلاك المتراكم
        depreciation_percentage: نسبة الإهلاك
        is_fully_depreciated: مكتمل الإهلاك
        is_active: نشط
        remaining_life_years: العمر المتبقي
    """
    id: str
    code: str
    name: str
    asset_type: str
    status: str
    acquisition_cost: Decimal
    net_book_value: Decimal
    accumulated_depreciation: Decimal
    depreciation_percentage: Decimal
    is_fully_depreciated: bool
    is_active: bool
    remaining_life_years: Decimal

    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"

    @property
    def acquisition_cost_formatted(self) -> str:
        return f"{self.acquisition_cost:,.2f}"

    @property
    def net_book_value_formatted(self) -> str:
        return f"{self.net_book_value:,.2f}"

    @property
    def depreciation_percentage_formatted(self) -> str:
        return f"{self.depreciation_percentage:.2f}%"


@dataclass(frozen=True)
class CreateFixedAssetDTO:
    """
    بيانات إنشاء أصل ثابت جديد - DTO
    
    Attributes:
        code: كود الأصل
        name: اسم الأصل
        acquisition_cost: تكلفة الشراء
        acquisition_date: تاريخ الشراء
        asset_type: نوع الأصل
        useful_life_years: العمر الإنتاجي بالسنوات
        salvage_value: القيمة المتبقية
        depreciation_method: طريقة الإهلاك
        currency: العملة
        category: تصنيف الأصل (اختياري)
        location: موقع الأصل (اختياري)
        responsible_person: الشخص المسؤول (اختياري)
        supplier_id: معرف المورد (اختياري)
        supplier_name: اسم المورد (اختياري)
        serial_number: الرقم التسلسلي (اختياري)
        barcode: الباركود (اختياري)
        notes: ملاحظات (اختياري)
        created_by: من قام بالإنشاء
    """
    code: str
    name: str
    acquisition_cost: Decimal
    acquisition_date: date
    asset_type: str = "other"
    useful_life_years: int = 5
    salvage_value: Decimal = Decimal('0')
    depreciation_method: str = "straight_line"
    currency: str = "USD"
    category: Optional[str] = None
    location: Optional[str] = None
    responsible_person: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    notes: Optional[str] = None
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateFixedAssetDTO:
    """
    بيانات تحديث أصل ثابت - DTO
    
    Attributes:
        asset_id: معرف الأصل
        version: رقم الإصدار
        name: اسم الأصل (اختياري)
        description: وصف الأصل (اختياري)
        location: موقع الأصل (اختياري)
        responsible_person: الشخص المسؤول (اختياري)
        notes: ملاحظات (اختياري)
        is_active: حالة النشاط (اختياري)
        updated_by: من قام بالتحديث
    """
    asset_id: str
    version: int
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    responsible_person: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    updated_by: str = "system"


@dataclass(frozen=True)
class DisposeFixedAssetDTO:
    """
    بيانات التصرف في أصل ثابت - DTO
    
    Attributes:
        asset_id: معرف الأصل
        disposal_date: تاريخ التصرف
        disposal_method: طريقة التصرف
        sale_amount: مبلغ البيع (إن وجد)
        scrap_value: قيمة الخردة (إن وجد)
        reason: سبب التصرف (اختياري)
        reference_type: نوع المرجع (اختياري)
        reference_id: معرف المرجع (اختياري)
        disposed_by: من قام بالتصرف
    """
    asset_id: str
    disposal_date: date
    disposal_method: str
    sale_amount: Optional[Decimal] = None
    scrap_value: Optional[Decimal] = None
    reason: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    disposed_by: str = "system"


__all__ = [
    "DepreciationScheduleEntryDTO",
    "DepreciationScheduleDTO",
    "DisposalRecordDTO",
    "FixedAssetDTO",
    "FixedAssetSummaryDTO",
    "CreateFixedAssetDTO",
    "UpdateFixedAssetDTO",
    "DisposeFixedAssetDTO",
]