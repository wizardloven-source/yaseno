"""
Sales Order Commands
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Dict, Any


@dataclass
class OrderItemCommand:
    """عنصر في أمر البيع"""
    product_id: str
    product_name: str
    quantity: float
    unit_price: float
    discount_percent: float = 0.0
    tax_percent: float = 15.0
    unit: str = "pcs"
    warehouse_id: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class CreateSalesOrderCommand:
    """إنشاء أمر بيع جديد"""
    customer_id: str
    customer_name: str
    currency: str = "SAR"
    order_date: date = field(default_factory=date.today)
    expected_delivery_date: Optional[date] = None
    
    # المصدر
    source_type: Optional[str] = None  # quotation, web, pos, manual
    source_id: Optional[str] = None
    quotation_id: Optional[str] = None
    
    # العناوين
    billing_address: Optional[dict] = None
    shipping_address: Optional[dict] = None
    
    # العناصر
    items: List[OrderItemCommand] = field(default_factory=list)
    
    # الخصومات
    global_discount_percent: float = 0.0
    global_discount_amount: float = 0.0
    
    # الشحن
    shipping_method: Optional[str] = None
    shipping_cost: float = 0.0
    shipping_tax_percent: float = 15.0
    
    # الدفع
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None
    
    # الملاحظات
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    # بيانات النظام
    priority: str = "normal"
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    branch_id: Optional[str] = None
    company_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateSalesOrderCommand:
    """تحديث أمر بيع موجود"""
    order_id: str
    
    # الحقول القابلة للتحديث
    customer_name: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    
    billing_address: Optional[dict] = None
    shipping_address: Optional[dict] = None
    
    items: Optional[List[OrderItemCommand]] = None
    
    global_discount_percent: Optional[float] = None
    global_discount_amount: Optional[float] = None
    
    shipping_method: Optional[str] = None
    shipping_cost: Optional[float] = None
    
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None
    
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    priority: Optional[str] = None
    
    custom_fields: Optional[Dict[str, Any]] = None


@dataclass
class ConfirmSalesOrderCommand:
    """تأكيد أمر البيع"""
    order_id: str
    confirmed_by: Optional[str] = None
    confirmation_notes: Optional[str] = None


@dataclass
class CancelSalesOrderCommand:
    """إلغاء أمر البيع"""
    order_id: str
    reason: str
    cancelled_by: Optional[str] = None


@dataclass
class ShipOrderCommand:
    """شحن الطلبية"""
    order_id: str
    tracking_number: str
    carrier: str
    shipped_by: Optional[str] = None


@dataclass
class DeliverOrderCommand:
    """تسليم الطلبية"""
    order_id: str
    delivery_date: date = field(default_factory=date.today)
    received_by: Optional[str] = None
    received_by_title: Optional[str] = None
    delivered_by: Optional[str] = None
