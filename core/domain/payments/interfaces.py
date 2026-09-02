# core/domain/payments/interfaces.py
"""
Repository Interfaces for Payments Context
واجهات مستودع الدفعات
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date, datetime

from .entities import Payment
from .value_objects import PaymentId, PaymentCode, PaymentType, PaymentStatus


class IPaymentRepository(ABC):
    """واجهة مستودع الدفعات"""

    @abstractmethod
    def save(self, payment: Payment) -> None:
        """حفظ الدفعة (جديدة أو محدثة)"""
        pass

    @abstractmethod
    def get_by_id(self, payment_id: PaymentId) -> Optional[Payment]:
        """الحصول على دفعة بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_code(self, code: PaymentCode) -> Optional[Payment]:
        """الحصول على دفعة بواسطة الكود"""
        pass

    @abstractmethod
    def get_by_reference(self, reference_type: str, reference_id: str) -> List[Payment]:
        """الحصول على دفعات بواسطة المرجع"""
        pass

    @abstractmethod
    def list_by_customer(self, customer_id: str, limit: int = 100) -> List[Payment]:
        """قائمة دفعات العميل"""
        pass

    @abstractmethod
    def list_by_supplier(self, supplier_id: str, limit: int = 100) -> List[Payment]:
        """قائمة دفعات المورد"""
        pass

    @abstractmethod
    def list_by_type(self, payment_type: PaymentType, limit: int = 100) -> List[Payment]:
        """قائمة دفعات حسب النوع"""
        pass

    @abstractmethod
    def list_by_status(self, status: PaymentStatus, limit: int = 100) -> List[Payment]:
        """قائمة دفعات حسب الحالة"""
        pass

    @abstractmethod
    def list_by_date_range(
        self,
        from_date: date,
        to_date: date,
        payment_type: Optional[PaymentType] = None,
        limit: int = 100,
    ) -> List[Payment]:
        """قائمة دفعات في نطاق زمني"""
        pass

    @abstractmethod
    def get_next_code(self) -> PaymentCode:
        """الحصول على الكود التالي"""
        pass

    @abstractmethod
    def delete_draft(self, payment_id: PaymentId) -> bool:
        """حذف دفعة مسودة"""
        pass

    @abstractmethod
    def get_summary(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> dict:
        """الحصول على ملخص الدفعات"""
        pass