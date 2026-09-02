# C:\Users\MTC\Desktop\erpya\core\application\suppliers\dtos.py
"""Data Transfer Objects for Suppliers Module"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass(frozen=True)
class ContactInfoDTO:
    """معلومات الاتصال - DTO"""
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None


@dataclass(frozen=True)
class AddressDTO:
    """العنوان - DTO"""
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"


@dataclass(frozen=True)
class SupplierDTO:
    """المورد - DTO كامل"""
    id: str
    code: str
    name: str
    status: str  # active, inactive, suspended, blocked
    
    contact_info: ContactInfoDTO
    address: AddressDTO
    tax_number: Optional[str]
    credit_limit: float
    currency: str
    notes: Optional[str]
    
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    version: int
    
    @property
    def is_active(self) -> bool:
        """هل المورد نشط؟"""
        return self.status == "active"
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        return f"{self.code} - {self.name}"
    
    @property
    def formatted_credit_limit(self) -> str:
        """الحد الائتماني منسق"""
        return f"{self.credit_limit:,.2f} {self.currency}"


@dataclass(frozen=True)
class SupplierListDTO:
    """قائمة الموردين مع معلومات التصفح"""
    suppliers: List[SupplierDTO]
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


__all__ = [
    "ContactInfoDTO",
    "AddressDTO",
    "SupplierDTO",
    "SupplierListDTO",
]