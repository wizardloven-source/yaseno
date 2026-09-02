# core/application/products/commands.py
"""Commands and Queries for Products Module"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


# ========== COMMANDS (عمليات الكتابة) ==========

@dataclass(frozen=True)
class CreateProductCommand:
    """أمر إنشاء منتج جديد"""
    code: str
    name: str
    unit_price: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    category: Optional[str] = None
    tax_rate: Decimal = Decimal('0')
    stock_quantity: Decimal = Decimal('0')
    is_active: bool = True
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateProductCommand:
    """أمر تحديث منتج موجود"""
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
    updated_by: str = "system"
    version: int = 1  # للتحقق من التزامن


@dataclass(frozen=True)
class DeleteProductCommand:
    """أمر حذف منتج (Soft Delete)"""
    product_id: str
    deleted_by: str = "system"


@dataclass(frozen=True)
class UpdateStockCommand:
    """أمر تحديث كمية المخزون"""
    product_id: str
    quantity_change: Decimal  # موجب للإضافة، سالب للخصم
    reason: str = ""
    updated_by: str = "system"


# ========== QUERIES (عمليات القراءة) ==========

@dataclass(frozen=True)
class GetProductQuery:
    """استعلام لجلب منتج بواسطة المعرف"""
    product_id: str


@dataclass(frozen=True)
class GetProductByCodeQuery:
    """استعلام لجلب منتج بواسطة الكود"""
    code: str


@dataclass(frozen=True)
class ListProductsQuery:
    """استعلام لجلب قائمة المنتجات"""
    include_inactive: bool = False
    category: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class SearchProductsQuery:
    """استعلام للبحث عن المنتجات"""
    search_text: str
    category: Optional[str] = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class GetLowStockProductsQuery:
    """استعلام لجلب المنتجات ذات المخزون المنخفض"""
    threshold: Decimal = Decimal('10')
    limit: int = 50