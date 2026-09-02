from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date

from .value_objects import PurchaseOrderId, PurchaseOrderNumber, PurchaseOrderStatus
from .entities import PurchaseOrder


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