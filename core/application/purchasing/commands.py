from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Dict, Any  # ✅ أضف Dict, Any هنا
from decimal import Decimal


@dataclass(frozen=True)
class CreatePurchaseOrderCommand:
    supplier_id: str
    supplier_name: str
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    currency: str = "USD"
    payment_terms: str = "net_30"
    expected_delivery_date: Optional[datetime] = None
    notes: str = ""
    created_by: str = "system"


@dataclass(frozen=True)
class AddPurchaseLineCommand:
    order_id: str
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    currency: str
    notes: str = ""


@dataclass(frozen=True)
class PostPurchaseOrderCommand:
    order_id: str
    posted_by: str


@dataclass(frozen=True)
class UpdatePurchaseLineCommand:
    order_id: str
    line_id: str
    quantity: Decimal
    unit_price: Decimal
    notes: str = ""


@dataclass(frozen=True)
class RemovePurchaseLineCommand:
    order_id: str
    line_id: str


@dataclass(frozen=True)
class ClearPurchaseLinesCommand:
    order_id: str


@dataclass(frozen=True)
class DeleteDraftPurchaseOrderCommand:
    order_id: str
    deleted_by: str = "system"


@dataclass(frozen=True)
class ReceivePurchaseLineCommand:
    order_id: str
    line_id: str
    quantity: Decimal
    received_by: str = "system"


# ========== QUERIES ==========

@dataclass(frozen=True)
class GetPurchaseOrderQuery:
    order_id: str


@dataclass(frozen=True)
class ListPurchaseOrdersQuery:
    status: Optional[str] = None
    supplier_id: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


# ✅ إضافة استعلام جلب أوامر شراء مورد معين
@dataclass(frozen=True)
class GetSupplierOrdersQuery:
    """استعلام لجلب أوامر شراء مورد معين"""
    supplier_id: str
    status: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    limit: int = 100
    offset: int = 0


# ✅ إضافة استعلام البحث في أوامر الشراء
@dataclass(frozen=True)
class SearchPurchaseOrdersQuery:
    """استعلام للبحث في أوامر الشراء"""
    search_text: str
    status: Optional[str] = None
    supplier_id: Optional[str] = None
    limit: int = 50
    offset: int = 0


# ✅ أمر استلام جميع بنود أمر الشراء دفعة واحدة
@dataclass(frozen=True)
class ReceivePurchaseOrderCommand:
    """أمر استلام جميع بنود أمر الشراء دفعة واحدة"""
    order_id: str
    received_by: str = "system"
    batch_numbers: Optional[Dict[str, str]] = None  # line_id -> batch_number
    serial_numbers: Optional[Dict[str, List[str]]] = None  # line_id -> [serial_numbers]
    expiry_dates: Optional[Dict[str, datetime]] = None  # line_id -> expiry_date
    locations: Optional[Dict[str, str]] = None  # line_id -> location


# ========== EXPORTS ==========

__all__ = [
    # Commands
    "CreatePurchaseOrderCommand",
    "AddPurchaseLineCommand",
    "PostPurchaseOrderCommand",
    "UpdatePurchaseLineCommand",
    "RemovePurchaseLineCommand",
    "ClearPurchaseLinesCommand",
    "DeleteDraftPurchaseOrderCommand",
    "ReceivePurchaseLineCommand",
    "ReceivePurchaseOrderCommand",  # ✅ إضافة الأمر الجديد
    
    # Queries
    "GetPurchaseOrderQuery",
    "ListPurchaseOrdersQuery",
    "GetSupplierOrdersQuery",
    "SearchPurchaseOrdersQuery",
]