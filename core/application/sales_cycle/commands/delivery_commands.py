"""
Delivery Note Commands
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List, Optional, Dict, Any


@dataclass
class DeliveryItemCommand:
    """عنصر في إشعار التسليم"""
    product_id: str
    product_name: str
    ordered_quantity: float
    delivered_quantity: float
    unit: str = "pcs"
    warehouse_id: Optional[str] = None
    batch_number: Optional[str] = None
    serial_numbers: List[str] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class CreateDeliveryNoteCommand:
    """إنشاء إشعار تسليم جديد"""
    order_id: str
    order_number: str
    customer_id: str
    customer_name: str
    
    delivery_date: date = field(default_factory=date.today)
    scheduled_date: Optional[date] = None
    
    # العنوان
    delivery_address: Optional[dict] = None
    
    # العناصر
    items: List[DeliveryItemCommand] = field(default_factory=list)
    
    # معلومات الشحن
    carrier: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    
    # الملاحظات
    notes: Optional[str] = None
    delivery_notes: Optional[str] = None
    
    # بيانات النظام
    warehouse_id: Optional[str] = None
    branch_id: Optional[str] = None
    company_id: Optional[str] = None
    created_by: Optional[str] = None
    delivered_by: Optional[str] = None
    
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateDeliveryNoteCommand:
    """تحديث إشعار تسليم موجود"""
    delivery_id: str
    
    # الحقول القابلة للتحديث
    delivery_date: Optional[date] = None
    scheduled_date: Optional[date] = None
    
    delivery_address: Optional[dict] = None
    items: Optional[List[DeliveryItemCommand]] = None
    
    carrier: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    
    notes: Optional[str] = None
    delivery_notes: Optional[str] = None
    
    delivered_by: Optional[str] = None
    
    custom_fields: Optional[Dict[str, Any]] = None


@dataclass
class CompleteDeliveryCommand:
    """اكتمال التسليم"""
    delivery_id: str
    received_by: str
    received_by_title: Optional[str] = None
    signature_url: Optional[str] = None
    completed_by: Optional[str] = None


@dataclass
class FailDeliveryCommand:
    """فشل التسليم"""
    delivery_id: str
    reason: str
    failed_by: Optional[str] = None
    failure_notes: Optional[str] = None
