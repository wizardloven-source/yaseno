# core/application/inventory/commands.py

"""
Inventory Commands - أوامر المخزون
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal

# ✅ استيراد EntityId من shared
from core.domain.shared.value_objects import EntityId
from core.domain.inventory.value_objects import StockMovementType


# =============================================================================
# حركات المخزون
# =============================================================================

@dataclass(frozen=True)
class CreateStockMovementCommand:
    """أمر إنشاء حركة مخزون"""
    entity_type: str  # product, raw_material, asset, etc.
    entity_id: str
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    currency: str = "USD"
    reference_type: str = ""
    reference_id: str = ""
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""
    created_by: str = "system"
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)


@dataclass(frozen=True)
class CreatePurchaseMovementCommand:
    """أمر إنشاء حركة شراء"""
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    purchase_order_id: str  # ✅ نقل إلى قبل المعاملات ذات القيم الافتراضية
    currency: str = "USD"
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""
    created_by: str = "system"
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)


@dataclass(frozen=True)
class CreateSaleMovementCommand:
    """أمر إنشاء حركة بيع"""
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal  # محسوبة من FIFO
    invoice_id: str  # ✅ نقل إلى قبل المعاملات ذات القيم الافتراضية
    currency: str = "USD"
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    location: Optional[str] = None
    notes: str = ""
    created_by: str = "system"
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)


@dataclass(frozen=True)
class CreateAdjustmentMovementCommand:
    """أمر إنشاء حركة تعديل"""
    entity_type: str
    entity_id: str
    old_quantity: Decimal
    new_quantity: Decimal
    unit_cost: Decimal
    reason: str  # ✅ نقل إلى قبل المعاملات ذات القيم الافتراضية
    currency: str = "USD"
    location: Optional[str] = None
    notes: str = ""
    created_by: str = "system"
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)
    
    @property
    def quantity_change(self) -> Decimal:
        return self.new_quantity - self.old_quantity
    
    @property
    def movement_type(self) -> str:
        return "adjustment_in" if self.quantity_change > 0 else "adjustment_out"


# =============================================================================
# دفعات المخزون
# =============================================================================

@dataclass(frozen=True)
class CreateStockBatchCommand:
    """أمر إنشاء دفعة مخزون"""
    entity_type: str
    entity_id: str
    batch_number: str  # ✅ نقل إلى قبل المعاملات ذات القيم الافتراضية
    quantity: Decimal
    unit_cost: Decimal
    currency: str = "USD"
    production_date: Optional[date] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    notes: str = ""
    created_by: str = "system"
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)


@dataclass(frozen=True)
class ConsumeStockBatchCommand:
    """أمر استهلاك دفعة مخزون"""
    batch_id: str
    quantity: Decimal
    reference_type: str
    reference_id: str
    consumed_by: str = "system"


# =============================================================================
# تحويلات المخزون
# =============================================================================

@dataclass(frozen=True)
class CreateStockTransferCommand:
    """أمر إنشاء تحويل مخزون"""
    entity_type: str
    entity_id: str
    quantity: Decimal
    unit_cost: Decimal
    from_location: str  # ✅ نقل إلى قبل المعاملات ذات القيم الافتراضية
    to_location: str    # ✅ نقل إلى قبل المعاملات ذات القيم الافتراضية
    currency: str = "USD"
    reference_id: str = ""
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    notes: str = ""
    created_by: str = "system"
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)


@dataclass(frozen=True)
class CompleteStockTransferCommand:
    """أمر إكمال تحويل مخزون"""
    transfer_id: str
    completed_by: str = "system"


# =============================================================================
# استعلامات المخزون
# =============================================================================

@dataclass(frozen=True)
class GetStockQuantityQuery:
    """استعلام للحصول على كمية المخزون"""
    entity_type: str
    entity_id: str
    as_of_date: Optional[date] = None
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)


@dataclass(frozen=True)
class GetStockMovementsQuery:
    """استعلام للحصول على حركات المخزون"""
    entity_type: str
    entity_id: str
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    movement_type: Optional[str] = None
    limit: int = 100
    offset: int = 0
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)


@dataclass(frozen=True)
class GetStockValuationQuery:
    """استعلام لتقييم المخزون"""
    entity_type: str
    entity_id: str
    as_of_date: date
    method: str = "fifo"
    
    @property
    def entity(self) -> EntityId:
        return EntityId(self.entity_type, self.entity_id)


# ✅ ✅ ✅ الكلاس المفقود - تم إضافته
@dataclass(frozen=True)
class GetLowStockQuery:
    """
    استعلام للحصول على المنتجات منخفضة المخزون
    
    Attributes:
        threshold: الحد الأدنى للمخزون (المنتجات التي تقل عن هذا الحد)
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات (اختياري)
    """
    threshold: int = 10
    limit: int = 50
    offset: int = 0


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Movements
    "CreateStockMovementCommand",
    "CreatePurchaseMovementCommand",
    "CreateSaleMovementCommand",
    "CreateAdjustmentMovementCommand",
    
    # Batches
    "CreateStockBatchCommand",
    "ConsumeStockBatchCommand",
    
    # Transfers
    "CreateStockTransferCommand",
    "CompleteStockTransferCommand",
    
    # Queries
    "GetStockQuantityQuery",
    "GetStockMovementsQuery",
    "GetStockValuationQuery",
    "GetLowStockQuery",  # ✅ تمت الإضافة
]