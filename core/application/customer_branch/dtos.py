# core/application/customer_branch/dtos.py
"""
Customer Branch DTOs - كائنات نقل البيانات
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass(frozen=True)
class BranchAddressDTO:
    """عنوان فرع العميل - DTO"""
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    postal_code: Optional[str] = None
    
    @property
    def full_address(self) -> str:
        parts = [self.street, self.city, self.country]
        return ", ".join([p for p in parts if p])


@dataclass(frozen=True)
class BranchContactDTO:
    """معلومات الاتصال - DTO"""
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None


@dataclass(frozen=True)
class BranchGeoLocationDTO:
    """الموقع الجغرافي - DTO"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass(frozen=True)
class CustomerBranchDTO:
    """فرع عميل - DTO كامل"""
    id: str
    code: str
    name: str
    status: str
    customer_id: str
    customer_name: str
    customer_code: str
    
    address: BranchAddressDTO
    contact: BranchContactDTO
    geo_location: BranchGeoLocationDTO
    
    tax_number: Optional[str]
    is_default: bool
    notes: Optional[str]
    working_hours: Optional[str]
    branch_type: str
    
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    version: int
    
    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"
    
    @property
    def full_address(self) -> str:
        return self.address.full_address
    
    @property
    def is_active(self) -> bool:
        return self.status == "active"


@dataclass(frozen=True)
class CreateBranchDTO:
    """بيانات إنشاء فرع جديد"""
    code: str
    name: str
    customer_id: str
    customer_name: str
    customer_code: str = ""
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    is_default: bool = False
    notes: Optional[str] = None
    working_hours: Optional[str] = None
    branch_type: str = "store"
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateBranchDTO:
    """بيانات تحديث فرع"""
    branch_id: str
    name: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = None
    working_hours: Optional[str] = None
    branch_type: Optional[str] = None
    status: Optional[str] = None
    updated_by: str = "system"
    version: int = 1


@dataclass(frozen=True)
class BranchListDTO:
    """قائمة فروع العملاء"""
    branches: List[CustomerBranchDTO]
    total_count: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        return (self.total_count + self.page_size - 1) // self.page_size if self.page_size > 0 else 1
    
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        return self.page > 1