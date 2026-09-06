"""
Delivery Note Entity - إشعار تسليم
Represents a delivery note for shipping products to customer
"""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from enum import Enum

from app.core.domain.base_entity import BaseEntity


class DeliveryStatus(str, Enum):
    """حالات إشعار التسليم"""
    DRAFT = "draft"  # مسودة
    PENDING = "pending"  # قيد الانتظار
    IN_TRANSIT = "in_transit"  # أثناء النقل
    DELIVERED = "delivered"  # تم التسليم
    PARTIALLY_DELIVERED = "partially_delivered"  # تم التسليم جزئياً
    RETURNED = "returned"  # مرتجع
    CANCELLED = "cancelled"  # ملغى


class DeliveryNote(BaseEntity):
    """
    كيان إشعار التسليم
    
    Attributes:
        delivery_number: رقم إشعار التسليم
        sales_order_id: معرف أمر البيع
        customer_id: معرف العميل
        customer_name: اسم العميل
        warehouse_id: معرف المستودع
        delivery_date: تاريخ التسليم
        expected_delivery_date: تاريخ التسليم المتوقع
        status: حالة التسليم
        items: عناصر التسليم
        shipping_address: عنوان الشحن
        driver_name: اسم السائق
        vehicle_number: رقم المركبة
        notes: ملاحظات
        created_by: معرف من أنشأ الإشعار
    """
    
    def __init__(
        self,
        delivery_number: str,
        sales_order_id: str,
        customer_id: str,
        customer_name: str,
        warehouse_id: str,
        delivery_date: date,
        status: DeliveryStatus = DeliveryStatus.DRAFT,
        expected_delivery_date: Optional[date] = None,
        items: Optional[List['DeliveryItem']] = None,
        shipping_address: Optional[dict] = None,
        driver_name: Optional[str] = None,
        vehicle_number: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.delivery_number = delivery_number
        self.sales_order_id = sales_order_id
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.warehouse_id = warehouse_id
        self.delivery_date = delivery_date
        self.expected_delivery_date = expected_delivery_date
        self.status = status
        self.items = items or []
        self.shipping_address = shipping_address or {}
        self.driver_name = driver_name
        self.vehicle_number = vehicle_number
        self.notes = notes
        self.created_by = created_by
    
    def add_item(self, item: 'DeliveryItem') -> None:
        """إضافة عنصر للتسليم"""
        self.items.append(item)
    
    def remove_item(self, item_id: str) -> bool:
        """إزالة عنصر من التسليم"""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                return True
        return False
    
    def start_delivery(self) -> None:
        """بدء عملية التسليم"""
        if self.status == DeliveryStatus.PENDING:
            self.status = DeliveryStatus.IN_TRANSIT
            self.add_event('delivery_started', {
                'delivery_id': self.id,
                'started_at': datetime.utcnow().isoformat()
            })
    
    def deliver_items(self, delivered_quantities: dict) -> None:
        """
        تسليم العناصر
        
        Args:
            delivered_quantities: قاموس {item_id: quantity}
        """
        if self.status not in [DeliveryStatus.IN_TRANSIT, DeliveryStatus.PARTIALLY_DELIVERED]:
            raise ValueError("Delivery must be in transit to deliver items")
        
        all_delivered = True
        partially_delivered = False
        
        for item in self.items:
            delivered_qty = delivered_quantities.get(item.id, Decimal('0'))
            if delivered_qty > 0:
                item.delivered_quantity = delivered_qty
                if delivered_qty < item.quantity:
                    partially_delivered = True
                    all_delivered = False
            else:
                all_delivered = False
        
        if all_delivered:
            self.status = DeliveryStatus.DELIVERED
        elif partially_delivered:
            self.status = DeliveryStatus.PARTIALLY_DELIVERED
        
        self.add_event('delivery_completed', {
            'delivery_id': self.id,
            'delivered_quantities': {k: str(v) for k, v in delivered_quantities.items()},
            'delivered_at': datetime.utcnow().isoformat()
        })
    
    def return_items(self, returned_quantities: dict, reason: str) -> None:
        """
        إرجاع العناصر
        
        Args:
            returned_quantities: قاموس {item_id: quantity}
            reason: سبب الإرجاع
        """
        for item in self.items:
            returned_qty = returned_quantities.get(item.id, Decimal('0'))
            if returned_qty > 0:
                item.returned_quantity = returned_qty
        
        self.status = DeliveryStatus.RETURNED
        self.add_event('delivery_returned', {
            'delivery_id': self.id,
            'returned_quantities': {k: str(v) for k, v in returned_quantities.items()},
            'reason': reason,
            'returned_at': datetime.utcnow().isoformat()
        })
    
    def cancel(self, reason: str) -> None:
        """إلغاء إشعار التسليم"""
        if self.status not in [DeliveryStatus.DELIVERED, DeliveryStatus.PARTIALLY_DELIVERED]:
            self.status = DeliveryStatus.CANCELLED
            self.add_event('delivery_cancelled', {
                'delivery_id': self.id,
                'reason': reason,
                'cancelled_at': datetime.utcnow().isoformat()
            })
    
    def to_dict(self) -> dict:
        """تحويل الكيان إلى قاموس"""
        return {
            'id': self.id,
            'delivery_number': self.delivery_number,
            'sales_order_id': self.sales_order_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'warehouse_id': self.warehouse_id,
            'delivery_date': self.delivery_date.isoformat(),
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'status': self.status.value,
            'items': [item.to_dict() for item in self.items],
            'shipping_address': self.shipping_address,
            'driver_name': self.driver_name,
            'vehicle_number': self.vehicle_number,
            'notes': self.notes,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class DeliveryItem:
    """
    عنصر في إشعار التسليم
    """
    
    def __init__(
        self,
        product_id: str,
        product_name: str,
        quantity: Decimal,
        unit_of_measure: str = 'PCS',
        batch_number: Optional[str] = None,
        serial_numbers: Optional[List[str]] = None,
        id: Optional[str] = None,
    ):
        import uuid
        self.id = id or str(uuid.uuid4())
        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity
        self.unit_of_measure = unit_of_measure
        self.batch_number = batch_number
        self.serial_numbers = serial_numbers or []
        self.delivered_quantity = Decimal('0')
        self.returned_quantity = Decimal('0')
    
    def to_dict(self) -> dict:
        """تحويل العنصر إلى قاموس"""
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'quantity': str(self.quantity),
            'unit_of_measure': self.unit_of_measure,
            'batch_number': self.batch_number,
            'serial_numbers': self.serial_numbers,
            'delivered_quantity': str(self.delivered_quantity),
            'returned_quantity': str(self.returned_quantity),
        }
