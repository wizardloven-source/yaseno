# core/application/fixed_assets/commands.py
"""
Fixed Assets Commands - أوامر الأصول الثابتة
الإصدار: 1.0.0

تحتوي على جميع أوامر الكتابة (Commands) الخاصة بالأصول الثابتة
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any


# =============================================================================
# أوامر إدارة الأصول
# =============================================================================

@dataclass(frozen=True)
class CreateFixedAssetCommand:
    """
    أمر إنشاء أصل ثابت جديد
    
    Attributes:
        code: كود الأصل
        name: اسم الأصل
        acquisition_cost: تكلفة الشراء
        acquisition_date: تاريخ الشراء
        asset_type: نوع الأصل (building, machinery, vehicle, etc.)
        useful_life_years: العمر الإنتاجي بالسنوات
        salvage_value: القيمة المتبقية (الخردة)
        depreciation_method: طريقة الإهلاك (straight_line, declining_balance, etc.)
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
    asset_type: str
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
class UpdateFixedAssetCommand:
    """
    أمر تحديث أصل ثابت موجود
    
    Attributes:
        asset_id: معرف الأصل
        version: رقم الإصدار (للتحقق من التزامن)
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
class DeleteFixedAssetCommand:
    """
    أمر حذف أصل ثابت
    
    Attributes:
        asset_id: معرف الأصل
        permanent: حذف دائم (True) أم ناعم (False)
        deleted_by: من قام بالحذف
    """
    asset_id: str
    permanent: bool = False
    deleted_by: str = "system"


@dataclass(frozen=True)
class ActivateFixedAssetCommand:
    """
    أمر تنشيط أصل ثابت
    
    Attributes:
        asset_id: معرف الأصل
        activated_by: من قام بالتنشيط
    """
    asset_id: str
    activated_by: str = "system"


@dataclass(frozen=True)
class DeactivateFixedAssetCommand:
    """
    أمر تعطيل أصل ثابت
    
    Attributes:
        asset_id: معرف الأصل
        reason: سبب التعطيل (اختياري)
        deactivated_by: من قام بالتعطيل
    """
    asset_id: str
    reason: Optional[str] = None
    deactivated_by: str = "system"


# =============================================================================
# أوامر الإهلاك
# =============================================================================

@dataclass(frozen=True)
class CalculateDepreciationCommand:
    """
    أمر حساب إهلاك أصل ثابت
    
    Attributes:
        asset_id: معرف الأصل
        as_of_date: تاريخ الحساب
        posted_by: من قام بالحساب
    """
    asset_id: str
    as_of_date: date
    posted_by: str = "system"


@dataclass(frozen=True)
class PostDepreciationCommand:
    """
    أمر ترحيل إهلاك فترة محددة
    
    Attributes:
        asset_id: معرف الأصل
        period: رقم الفترة (1-based)
        posted_by: من قام بالترحيل
    """
    asset_id: str
    period: int
    posted_by: str = "system"


@dataclass(frozen=True)
class PostAllDepreciationCommand:
    """
    أمر ترحيل جميع فترات الإهلاك غير المرحلة
    
    Attributes:
        asset_id: معرف الأصل
        posted_by: من قام بالترحيل
    """
    asset_id: str
    posted_by: str = "system"


@dataclass(frozen=True)
class RunMonthlyDepreciationCommand:
    """
    أمر تشغيل الإهلاك الشهري لجميع الأصول
    
    Attributes:
        as_of_date: تاريخ الإهلاك (اليوم إذا لم يحدد)
        posted_by: من قام بالترحيل
    """
    as_of_date: Optional[date] = None
    posted_by: str = "system"


# =============================================================================
# أوامر التصرف
# =============================================================================

@dataclass(frozen=True)
class DisposeFixedAssetCommand:
    """
    أمر التصرف في أصل ثابت
    
    Attributes:
        asset_id: معرف الأصل
        disposal_date: تاريخ التصرف
        disposal_method: طريقة التصرف (sale, scrap, donation, trade_in, loss)
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


@dataclass(frozen=True)
class SellFixedAssetCommand:
    """
    أمر بيع أصل ثابت (اختصار لـ DisposeFixedAssetCommand مع method=sale)
    
    Attributes:
        asset_id: معرف الأصل
        sale_date: تاريخ البيع
        sale_amount: مبلغ البيع
        buyer_name: اسم المشتري (اختياري)
        reason: سبب البيع (اختياري)
        sold_by: من قام بالبيع
    """
    asset_id: str
    sale_date: date
    sale_amount: Decimal
    buyer_name: Optional[str] = None
    reason: Optional[str] = None
    sold_by: str = "system"


@dataclass(frozen=True)
class ScrapFixedAssetCommand:
    """
    أمر خردة أصل ثابت (اختصار لـ DisposeFixedAssetCommand مع method=scrap)
    
    Attributes:
        asset_id: معرف الأصل
        scrap_date: تاريخ الخردة
        scrap_value: قيمة الخردة (اختياري)
        reason: سبب الخردة (اختياري)
        scrapped_by: من قام بالخردة
    """
    asset_id: str
    scrap_date: date
    scrap_value: Optional[Decimal] = None
    reason: Optional[str] = None
    scrapped_by: str = "system"


__all__ = [
    # إدارة الأصول
    "CreateFixedAssetCommand",
    "UpdateFixedAssetCommand",
    "DeleteFixedAssetCommand",
    "ActivateFixedAssetCommand",
    "DeactivateFixedAssetCommand",
    
    # الإهلاك
    "CalculateDepreciationCommand",
    "PostDepreciationCommand",
    "PostAllDepreciationCommand",
    "RunMonthlyDepreciationCommand",
    
    # التصرف
    "DisposeFixedAssetCommand",
    "SellFixedAssetCommand",
    "ScrapFixedAssetCommand",
]