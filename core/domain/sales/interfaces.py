# core/domain/sales/interfaces.py
"""
Sales Repository Interfaces - واجهات المستودعات لوحدة المبيعات
✅ IQuotationRepository
✅ IOrderRepository
✅ IDeliveryRepository
✅ IReturnRepository (NEW - PHASE 1)
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .entities import SalesQuotation, SalesOrder, DeliveryNote, SalesReturn
from .value_objects import QuotationId, OrderId, DeliveryId, ReturnId, QuotationStatus, OrderStatus, DeliveryStatus, ReturnStatus


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


class IReturnRepository(ABC):
    """واجهة مستودع إرجاعات المبيعات (NEW - PHASE 1)"""
    
    @abstractmethod
    async def get_by_id(self, return_id: ReturnId) -> Optional[SalesReturn]:
        """الحصول على إرجاع مبيعات بالمعرف"""
        pass
    
    @abstractmethod
    async def get_by_number(self, return_number: str) -> Optional[SalesReturn]:
        """الحصول على إرجاع المبيعات بالرقم"""
        pass
    
    @abstractmethod
    async def get_all(
        self,
        status: Optional[ReturnStatus] = None,
        customer_id: Optional[str] = None,
        original_invoice_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SalesReturn]:
        """الحصول على جميع إرجاعات المبيعات مع الفلترة"""
        pass
    
    @abstractmethod
    async def save(self, return_entity: SalesReturn) -> SalesReturn:
        """حفظ إرجاع مبيعات"""
        pass
    
    @abstractmethod
    async def delete(self, return_id: ReturnId) -> bool:
        """حذف إرجاع مبيعات"""
        pass
    
    @abstractmethod
    async def count(
        self,
        status: Optional[ReturnStatus] = None,
        customer_id: Optional[str] = None
    ) -> int:
        """عد إرجاعات المبيعات"""
        pass
    
    @abstractmethod
    async def get_next_sequence(self) -> int:
        """الحصول على الرقم التسلسلي التالي"""
        pass


class ReturnFilter:
    """كائن فلتر لإرجاعات المبيعات"""
    
    def __init__(
        self,
        status: Optional[ReturnStatus] = None,
        customer_id: Optional[str] = None,
        original_invoice_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ):
        self.status = status
        self.customer_id = customer_id
        self.original_invoice_id = original_invoice_id
        self.date_from = date_from
        self.date_to = date_to


class ReturnStatistics:
    """كائن إحصائيات إرجاعات المبيعات"""
    
    def __init__(
        self,
        total_returns: int,
        total_amount: float,
        completed_returns: int,
        cancelled_returns: int,
        pending_returns: int,
        average_processing_days: float
    ):
        self.total_returns = total_returns
        self.total_amount = total_amount
        self.completed_returns = completed_returns
        self.cancelled_returns = cancelled_returns
        self.pending_returns = pending_returns
        self.average_processing_days = average_processing_days
