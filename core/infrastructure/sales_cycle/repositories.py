"""
Repositories for Sales Cycle
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import date

from core.domain.sales_cycle.entities import SalesQuotation, SalesOrder, DeliveryNote


class IQuotationRepository(ABC):
    """مستودع عروض الأسعار"""
    
    @abstractmethod
    async def create(self, quotation: SalesQuotation) -> SalesQuotation:
        """إنشاء عرض سعر جديد"""
        pass
    
    @abstractmethod
    async def get_by_id(self, quotation_id: str) -> Optional[SalesQuotation]:
        """الحصول على عرض سعر بالمعرف"""
        pass
    
    @abstractmethod
    async def get_by_number(self, number: str) -> Optional[SalesQuotation]:
        """الحصول على عرض سعر بالرقم"""
        pass
    
    @abstractmethod
    async def update(self, quotation: SalesQuotation) -> SalesQuotation:
        """تحديث عرض سعر"""
        pass
    
    @abstractmethod
    async def delete(self, quotation_id: str) -> bool:
        """حذف عرض سعر"""
        pass
    
    @abstractmethod
    async def list(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SalesQuotation]:
        """قائمة عروض الأسعار مع الفلترة"""
        pass
    
    @abstractmethod
    async def count(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> int:
        """عدد عروض الأسعار"""
        pass


class ISalesOrderRepository(ABC):
    """مستودع أوامر البيع"""
    
    @abstractmethod
    async def create(self, order: SalesOrder) -> SalesOrder:
        pass
    
    @abstractmethod
    async def get_by_id(self, order_id: str) -> Optional[SalesOrder]:
        pass
    
    @abstractmethod
    async def get_by_number(self, number: str) -> Optional[SalesOrder]:
        pass
    
    @abstractmethod
    async def update(self, order: SalesOrder) -> SalesOrder:
        pass
    
    @abstractmethod
    async def delete(self, order_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list(
        self,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SalesOrder]:
        pass


class IDeliveryNoteRepository(ABC):
    """مستودع إشعارات التسليم"""
    
    @abstractmethod
    async def create(self, delivery: DeliveryNote) -> DeliveryNote:
        pass
    
    @abstractmethod
    async def get_by_id(self, delivery_id: str) -> Optional[DeliveryNote]:
        pass
    
    @abstractmethod
    async def get_by_number(self, number: str) -> Optional[DeliveryNote]:
        pass
    
    @abstractmethod
    async def update(self, delivery: DeliveryNote) -> DeliveryNote:
        pass
    
    @abstractmethod
    async def delete(self, delivery_id: str) -> bool:
        pass
    
    @abstractmethod
    async def list(
        self,
        order_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DeliveryNote]:
        pass
