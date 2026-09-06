"""
Repository Interface for Sales Quotations
Domain layer contract
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date

from app.modules.sales_cycle.domain.entities.quotation import SalesQuotation, QuotationStatus


class IQuotationRepository(ABC):
    """
    واجهة مستودع عروض الأسعار
    Contract for quotation repository
    """
    
    @abstractmethod
    async def add(self, quotation: SalesQuotation) -> SalesQuotation:
        """إضافة عرض سعر جديد"""
        pass
    
    @abstractmethod
    async def get_by_id(self, quotation_id: str) -> Optional[SalesQuotation]:
        """الحصول على عرض سعر بالمعرف"""
        pass
    
    @abstractmethod
    async def get_by_number(self, quotation_number: str) -> Optional[SalesQuotation]:
        """الحصول على عرض سعر بالرقم"""
        pass
    
    @abstractmethod
    async def update(self, quotation: SalesQuotation) -> SalesQuotation:
        """تحديث عرض سعر موجود"""
        pass
    
    @abstractmethod
    async def delete(self, quotation_id: str) -> bool:
        """حذف عرض سعر"""
        pass
    
    @abstractmethod
    async def list(
        self,
        customer_id: Optional[str] = None,
        status: Optional[QuotationStatus] = None,
        sales_person_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SalesQuotation]:
        """قائمة عروض الأسعار مع فلترة"""
        pass
    
    @abstractmethod
    async def count(
        self,
        customer_id: Optional[str] = None,
        status: Optional[QuotationStatus] = None,
        sales_person_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> int:
        """عدد عروض الأسعار"""
        pass
    
    @abstractmethod
    async def get_pending_quotations(self, days_threshold: int = 7) -> List[SalesQuotation]:
        """الحصول على عروض الأسعار المعلقة التي اقترب تاريخ انتهائها"""
        pass
    
    @abstractmethod
    async def expire_overdue_quotations(self) -> int:
        """إنهاء صلاحية عروض الأسعار منتهية الصلاحية"""
        pass
