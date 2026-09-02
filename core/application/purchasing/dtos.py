# core/application/purchasing/dtos.py
"""Data Transfer Objects for Purchasing Module"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from decimal import Decimal


@dataclass(frozen=True)
class PurchaseLineDTO:
    """سطر أمر شراء - DTO"""
    line_id: str
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    currency: str
    notes: str = ""
    received_quantity: Decimal = Decimal('0')
    
    @property
    def total_formatted(self) -> str:
        return f"{self.total:,.2f}"
    
    @property
    def unit_price_formatted(self) -> str:
        return f"{self.unit_price:,.2f}"
    
    @property
    def is_fully_received(self) -> bool:
        return self.received_quantity >= self.quantity
    
    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.received_quantity


@dataclass(frozen=True)
class PurchaseOrderDTO:
    """أمر شراء - DTO كامل"""
    id: str
    number: Optional[str]
    date: datetime
    expected_delivery_date: Optional[datetime]
    supplier_id: str
    supplier_name: str
    site_id: Optional[str]
    site_name: Optional[str]
    currency: str
    payment_terms: str
    notes: str
    lines: List[PurchaseLineDTO]
    journal_entry_id: Optional[str]
    created_at: datetime
    created_by: str
    posted_at: Optional[datetime]
    posted_by: Optional[str]
    received_at: Optional[datetime]
    received_by: Optional[str]
    status: str
    stock_movements: List[dict] = field(default_factory=list)
    
    @property
    def subtotal_formatted(self) -> str:
        return f"{self.subtotal:,.2f}"
    
    @property
    def total_formatted(self) -> str:
        return f"{self.total:,.2f}"
    
    @property
    def is_posted(self) -> bool:
        return self.status == "posted"
    
    @property
    def is_fully_received(self) -> bool:
        return all(line.is_fully_received for line in self.lines)
    
    @property
    def subtotal(self) -> Decimal:
        return sum(line.total for line in self.lines)
    
    @property
    def total(self) -> Decimal:
        return self.subtotal


@dataclass(frozen=True)
class CreatePurchaseOrderDTO:
    """بيانات إنشاء أمر شراء جديد"""
    supplier_id: str
    supplier_name: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    currency: str = "USD"
    payment_terms: str = "net_30"
    expected_delivery_date: Optional[datetime] = None
    notes: str = ""
    created_by: str = "system"


# ✅ إضافة UpdatePurchaseOrderDTO للتحديث
@dataclass(frozen=True)
class UpdatePurchaseOrderDTO:
    """بيانات تحديث أمر شراء"""
    order_id: str
    notes: Optional[str] = None
    payment_terms: Optional[str] = None
    expected_delivery_date: Optional[datetime] = None
    updated_by: str = "system"
    version: int = 1


__all__ = [
    "PurchaseOrderDTO",
    "PurchaseLineDTO",
    "CreatePurchaseOrderDTO",
    "UpdatePurchaseOrderDTO",
]