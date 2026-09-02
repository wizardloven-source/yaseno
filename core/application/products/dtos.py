# core/application/products/dtos.py
"""Data Transfer Objects for Products Module"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


@dataclass(frozen=True)
class ProductDTO:
    """منتج - DTO كامل"""
    id: str
    code: str
    name: str
    description: Optional[str]
    category: Optional[str]
    unit_price: Decimal
    currency: str
    tax_rate: Decimal
    stock_quantity: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime
    version: int
    
    @property
    def unit_price_formatted(self) -> str:
        return f"{self.unit_price:,.2f}"
    
    @property
    def stock_quantity_formatted(self) -> str:
        return f"{self.stock_quantity:,.2f}"
    
    @property
    def is_low_stock(self, threshold: Decimal = Decimal('10')) -> bool:
        return self.stock_quantity <= threshold and self.stock_quantity > 0
    
    @property
    def is_out_of_stock(self) -> bool:
        return self.stock_quantity <= 0


@dataclass(frozen=True)
class CreateProductDTO:
    """بيانات إنشاء منتج جديد"""
    code: str
    name: str
    unit_price: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    category: Optional[str] = None
    tax_rate: Decimal = Decimal('0')
    stock_quantity: Decimal = Decimal('0')
    is_active: bool = True


@dataclass(frozen=True)
class UpdateProductDTO:
    """بيانات تحديث منتج"""
    product_id: str
    code: str
    name: str
    unit_price: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    category: Optional[str] = None
    tax_rate: Decimal = Decimal('0')
    stock_quantity: Decimal = Decimal('0')
    is_active: bool = True
    version: int = 1


@dataclass(frozen=True)
class ProductListDTO:
    """قائمة المنتجات مع معلومات التصفح"""
    products: List[ProductDTO]
    total_count: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        return (self.total_count + self.page_size - 1) // self.page_size


@dataclass(frozen=True)
class ProductSummaryDTO:
    """ملخص منتج للاستخدام في القوائم المنسدلة"""
    id: str
    code: str
    name: str
    unit_price: Decimal
    currency: str
    stock_quantity: Decimal
    
    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name} ({self.unit_price:,.2f} {self.currency})"