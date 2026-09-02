# core/domain/inventory/interfaces.py
"""
Inventory Repository Interfaces - واجهات مستودع المخزون
"""
from decimal import Decimal  # ✅ أضف هذا الاستيراد

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from .entities import StockMovement, StockBatch, StockTransfer
from .value_objects import (
    StockMovementId,
    StockBatchId,
    StockTransferId,
    EntityId,
    StockMovementType,
    StockBatchStatus,
    BatchNumber,
    StockLocation,
    Money,
)


# =============================================================================
# IStockMovementRepository - مستودع حركات المخزون
# =============================================================================

class IStockMovementRepository(ABC):
    """واجهة مستودع حركات المخزون"""
    
    @abstractmethod
    def save(self, movement: StockMovement) -> None:
        """حفظ حركة مخزون"""
        pass
    
    @abstractmethod
    def get_by_id(self, movement_id: StockMovementId) -> Optional[StockMovement]:
        """الحصول على حركة بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_entity(
        self,
        entity: EntityId,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockMovement]:
        """الحصول على حركات كيان معين"""
        pass
    
    @abstractmethod
    def get_by_reference(
        self,
        reference_type: str,
        reference_id: str
    ) -> List[StockMovement]:
        """الحصول على حركات مرجع معين"""
        pass
    
    @abstractmethod
    def get_by_date_range(
        self,
        entity: EntityId,
        from_date: datetime,
        to_date: datetime,
        movement_type: Optional[StockMovementType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockMovement]:
        """الحصول على حركات في نطاق زمني"""
        pass
    
    @abstractmethod
    def get_current_quantity(self, entity: EntityId) -> Decimal:
        """الحصول على الكمية الحالية لكيان"""
        pass
    
    @abstractmethod
    def get_quantity_at_date(
        self,
        entity: EntityId,
        as_of_date: date
    ) -> Decimal:
        """الحصول على الكمية في تاريخ معين"""
        pass
    
    @abstractmethod
    def get_layers_for_fifo(
        self,
        entity: EntityId,
        as_of_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """الحصول على طبقات المخزون لـ FIFO"""
        pass
    
    @abstractmethod
    def delete(self, movement_id: StockMovementId) -> bool:
        """حذف حركة مخزون"""
        pass


# =============================================================================
# IStockBatchRepository - مستودع دفعات المخزون
# =============================================================================

class IStockBatchRepository(ABC):
    """واجهة مستودع دفعات المخزون"""
    
    @abstractmethod
    def save(self, batch: StockBatch) -> None:
        """حفظ دفعة مخزون"""
        pass
    
    @abstractmethod
    def get_by_id(self, batch_id: StockBatchId) -> Optional[StockBatch]:
        """الحصول على دفعة بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_batch_number(
        self,
        batch_number: BatchNumber,
        entity: Optional[EntityId] = None
    ) -> Optional[StockBatch]:
        """الحصول على دفعة برقم الدفعة"""
        pass
    
    @abstractmethod
    def get_by_entity(
        self,
        entity: EntityId,
        status: Optional[StockBatchStatus] = None,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockBatch]:
        """الحصول على دفعات كيان معين"""
        pass
    
    @abstractmethod
    def get_expiring_batches(
        self,
        days_threshold: int = 30,
        limit: int = 100
    ) -> List[StockBatch]:
        """الحصول على الدفعات التي تنتهي قريباً"""
        pass
    
    @abstractmethod
    def get_expired_batches(self, limit: int = 100) -> List[StockBatch]:
        """الحصول على الدفعات المنتهية الصلاحية"""
        pass
    
    @abstractmethod
    def delete(self, batch_id: StockBatchId) -> bool:
        """حذف دفعة مخزون"""
        pass


# =============================================================================
# IStockTransferRepository - مستودع عمليات التحويل
# =============================================================================

class IStockTransferRepository(ABC):
    """واجهة مستودع عمليات التحويل"""
    
    @abstractmethod
    def save(self, transfer: StockTransfer) -> None:
        """حفظ عملية تحويل"""
        pass
    
    @abstractmethod
    def get_by_id(self, transfer_id: StockTransferId) -> Optional[StockTransfer]:
        """الحصول على تحويل بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_entity(
        self,
        entity: EntityId,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockTransfer]:
        """الحصول على تحويلات كيان معين"""
        pass
    
    @abstractmethod
    def get_by_location(
        self,
        location: StockLocation,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[StockTransfer]:
        """الحصول على تحويلات موقع معين"""
        pass
    
    @abstractmethod
    def get_pending_transfers(
        self,
        entity: Optional[EntityId] = None,
        limit: int = 100
    ) -> List[StockTransfer]:
        """الحصول على التحويلات المعلقة"""
        pass
    
    @abstractmethod
    def update_status(
        self,
        transfer_id: StockTransferId,
        status: str,
        updated_by: str
    ) -> bool:
        """تحديث حالة التحويل"""
        pass
    
    @abstractmethod
    def delete(self, transfer_id: StockTransferId) -> bool:
        """حذف عملية تحويل"""
        pass


# =============================================================================
# IInventoryReportService - خدمة تقارير المخزون
# =============================================================================

class IInventoryReportService(ABC):
    """واجهة خدمة تقارير المخزون"""
    
    @abstractmethod
    def get_stock_valuation(
        self,
        entity: EntityId,
        as_of_date: date,
        method: str = "fifo"
    ) -> Dict[str, Any]:
        """تقييم المخزون لكيان"""
        pass
    
    @abstractmethod
    def get_stock_movement_summary(
        self,
        entity: EntityId,
        from_date: date,
        to_date: date
    ) -> Dict[str, Any]:
        """ملخص حركات المخزون"""
        pass
    
    @abstractmethod
    def get_low_stock_items(
        self,
        threshold: Decimal,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """الحصول على العناصر منخفضة المخزون"""
        pass


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "IStockMovementRepository",
    "IStockBatchRepository",
    "IStockTransferRepository",
    "IInventoryReportService",
]