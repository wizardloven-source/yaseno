from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date

from .value_objects import (
    PurchaseOrderId, PurchaseOrderNumber, PurchaseOrderStatus,
    PurchaseReturnId, PurchaseReturnNumber, PurchaseReturnStatus
)
from .entities import PurchaseOrder, PurchaseReturn


class IPurchaseOrderRepository(ABC):
    """Repository Interface for PurchaseOrder Aggregate"""
    
    @abstractmethod
    def save(self, order: PurchaseOrder) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, order_id: PurchaseOrderId) -> Optional[PurchaseOrder]:
        pass
    
    @abstractmethod
    def get_by_number(self, number: PurchaseOrderNumber) -> Optional[PurchaseOrder]:
        pass
    
    @abstractmethod
    def get_by_journal_entry_id(self, journal_entry_id: str) -> Optional[PurchaseOrder]:
        pass
    
    @abstractmethod
    def list_by_supplier(self, supplier_id: str, limit: int = 100) -> List[PurchaseOrder]:
        pass
    
    @abstractmethod
    def list_by_status(self, status: PurchaseOrderStatus, limit: int = 100) -> List[PurchaseOrder]:
        pass
    
    @abstractmethod
    def list_by_date_range(self, from_date: date, to_date: date, limit: int = 100) -> List[PurchaseOrder]:
        pass
    
    @abstractmethod
    def get_next_number(self) -> PurchaseOrderNumber:
        pass
    
    @abstractmethod
    def delete_draft(self, order_id: PurchaseOrderId) -> bool:
        pass


class IPurchaseReturnRepository(ABC):
    """
    Repository Interface for PurchaseReturn Aggregate
    
    ✅ مسؤول عن:
    - حفظ واسترجاع إرجاعات المشتريات
    - البحث حسب المورد، أمر الشراء، الحالة
    - توليد الأرقام التسلسلية
    """
    
    @abstractmethod
    def save(self, return_obj: PurchaseReturn) -> None:
        """حفظ إرجاع مشتريات"""
        pass
    
    @abstractmethod
    def get_by_id(self, return_id: PurchaseReturnId) -> Optional[PurchaseReturn]:
        """الاسترجاع بالمعرف"""
        pass
    
    @abstractmethod
    def get_by_number(self, number: PurchaseReturnNumber) -> Optional[PurchaseReturn]:
        """الاسترجاع بالرقم"""
        pass
    
    @abstractmethod
    def list_by_supplier(self, supplier_id: str, limit: int = 100) -> List[PurchaseReturn]:
        """قائمة الإرجاعات حسب المورد"""
        pass
    
    @abstractmethod
    def list_by_purchase_order(self, purchase_order_id: str, limit: int = 100) -> List[PurchaseReturn]:
        """قائمة الإرجاعات حسب أمر الشراء"""
        pass
    
    @abstractmethod
    def list_by_status(self, status: PurchaseReturnStatus, limit: int = 100) -> List[PurchaseReturn]:
        """قائمة الإرجاعات حسب الحالة"""
        pass
    
    @abstractmethod
    def get_next_number(self) -> PurchaseReturnNumber:
        """الحصول على الرقم التالي"""
        pass
    
    @abstractmethod
    def delete_draft(self, return_id: PurchaseReturnId) -> bool:
        """حذف إرجاع في حالة المسودة"""
        pass