# core/application/customers/dtos.py
"""Data Transfer Objects for Customers Module"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass(frozen=True)
class CustomerDTO:
    """العميل - DTO كامل"""
    id: str
    code: str
    name: str
    status: str  # active, inactive, suspended, blocked
    
    # معلومات الاتصال (كحقول مسطحة بدلاً من كائن منفصل)
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    
    # العنوان (كحقول مسطحة بدلاً من كائن منفصل)
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    
    # المعلومات المالية
    tax_number: Optional[str] = None
    credit_limit: float = 0.0
    currency: str = "USD"
    notes: Optional[str] = None
    
    # بيانات التدقيق
    created_at: Optional[datetime] = None
    created_by: str = "system"
    updated_at: Optional[datetime] = None
    updated_by: str = "system"
    version: int = 1
    
    # الحذف الناعم
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    @property
    def is_active(self) -> bool:
        """هل العميل نشط؟"""
        return self.status == "active" and not self.is_deleted
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        return f"{self.code} - {self.name}"
    
    @property
    def full_address(self) -> str:
        """العنوان الكامل"""
        parts = [self.street, self.city, self.country]
        return ", ".join([p for p in parts if p])
    
    @property
    def contact_info_dict(self) -> dict:
        """معلومات الاتصال كقاموس"""
        return {
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile
        }


@dataclass(frozen=True)
class CustomerListDTO:
    """قائمة العملاء مع معلومات التصفح"""
    customers: List[CustomerDTO]
    total_count: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        """عدد الصفحات الإجمالي"""
        return (self.total_count + self.page_size - 1) // self.page_size if self.page_size > 0 else 1
    
    @property
    def has_next(self) -> bool:
        """هل توجد صفحة تالية؟"""
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        """هل توجد صفحة سابقة؟"""
        return self.page > 1


@dataclass(frozen=True)
class CreateCustomerDTO:
    """بيانات إنشاء عميل جديد"""
    code: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    tax_number: Optional[str] = None
    credit_limit: float = 0.0
    currency: str = "USD"
    notes: Optional[str] = None
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateCustomerDTO:
    """بيانات تحديث عميل"""
    customer_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    tax_number: Optional[str] = None
    credit_limit: Optional[float] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    updated_by: str = "system"
    version: int = 1


__all__ = [
    "CustomerDTO",
    "CustomerListDTO",
    "CreateCustomerDTO",
    "UpdateCustomerDTO",
]