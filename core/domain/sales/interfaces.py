# core/domain/sales/interfaces.py
"""
Sales Repository Interfaces - واجهات المستودعات لوحدة المبيعات
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .entities import SalesQuotation, SalesOrder, DeliveryNote
from .value_objects import QuotationId, OrderId, DeliveryId, QuotationStatus, OrderStatus, DeliveryStatus


class IQuotationRepository(ABC):
    """واجهة مستودع عروض الأسعار"""
    
    @abstractmethod
    async def get_by_id(self, quotation_id: QuotationId) -> Optional[SalesQuotation]:
        """الحصول على عرض سعر بالمعرف"""
        pass
    
    @abstractmethod
    async def get_by_number(self, quotation_number: str) -> Optional[SalesQuotation]:
        """الحصول على عرض السعر بالرقم"""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        status: Optional[QuotationStatus] = None,
        customer_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sales_person_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SalesQuotation]:
        """الحصول على جميع عروض الأسعار مع الفلترة"""
        pass
    
    @abstractmethod
    async def save(self, quotation: SalesQuotation) -> SalesQuotation:
        """حفظ عرض سعر"""
        pass
    
    @abstractmethod
    async def delete(self, quotation_id: QuotationId) -> bool:
        """حذف عرض سعر"""
        pass
    
    @abstractmethod
    async def count(
        self,
        status: Optional[QuotationStatus] = None,
        customer_id: Optional[str] = None
    ) -> int:
        """عد عروض الأسعار"""
        pass
    
    @abstractmethod
    async def get_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """الحصول على إحصائيات عروض الأسعار"""
        pass
    
    @abstractmethod
    async def get_next_sequence(self) -> int:
        """الحصول على الرقم التسلسلي التالي"""
        pass


class IOrderRepository(ABC):
    """واجهة مستودع أوامر البيع"""
    
    @abstractmethod
    async def get_by_id(self, order_id: OrderId) -> Optional[SalesOrder]:
        """الحصول على أمر بيع بالمعرف"""
        pass
    
    @abstractmethod
    async def get_by_number(self, order_number: str) -> Optional[SalesOrder]:
        """الحصول على أمر البيع بالرقم"""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        status: Optional[OrderStatus] = None,
        customer_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        sales_person_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SalesOrder]:
        """الحصول على جميع أوامر البيع مع الفلترة"""
        pass
    
    @abstractmethod
    async def save(self, order: SalesOrder) -> SalesOrder:
        """حفظ أمر بيع"""
        pass
    
    @abstractmethod
    async def delete(self, order_id: OrderId) -> bool:
        """حذف أمر بيع"""
        pass
    
    @abstractmethod
    async def count(
        self,
        status: Optional[OrderStatus] = None,
        customer_id: Optional[str] = None
    ) -> int:
        """عد أوامر البيع"""
        pass
    
    @abstractmethod
    async def get_next_sequence(self) -> int:
        """الحصول على الرقم التسلسلي التالي"""
        pass


class IDeliveryRepository(ABC):
    """واجهة مستودع إشعارات التسليم"""
    
    @abstractmethod
    async def get_by_id(self, delivery_id: DeliveryId) -> Optional[DeliveryNote]:
        """الحصول على إشعار تسليم بالمعرف"""
        pass
    
    @abstractmethod
    async def get_by_number(self, delivery_number: str) -> Optional[DeliveryNote]:
        """الحصول على إشعار التسليم بالرقم"""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        status: Optional[DeliveryStatus] = None,
        customer_id: Optional[str] = None,
        order_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DeliveryNote]:
        """الحصول على جميع إشعارات التسليم مع الفلترة"""
        pass
    
    @abstractmethod
    async def save(self, delivery: DeliveryNote) -> DeliveryNote:
        """حفظ إشعار تسليم"""
        pass
    
    @abstractmethod
    async def delete(self, delivery_id: DeliveryId) -> bool:
        """حذف إشعار تسليم"""
        pass
    
    @abstractmethod
    async def count(
        self,
        status: Optional[DeliveryStatus] = None,
        customer_id: Optional[str] = None
    ) -> int:
        """عد إشعارات التسليم"""
        pass
    
    @abstractmethod
    async def get_next_sequence(self) -> int:
        """الحصول على الرقم التسلسلي التالي"""
        pass
