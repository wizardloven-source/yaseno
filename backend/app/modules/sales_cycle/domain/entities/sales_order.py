"""
Sales Order Entity - أمر بيع
Represents a confirmed customer order for products/services
"""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from enum import Enum

from app.core.domain.base_entity import BaseEntity


class SalesOrderStatus(str, Enum):
    """حالات أمر البيع"""
    DRAFT = "draft"  # مسودة
    PENDING = "pending"  # قيد الانتظار (بانتظار الموافقة)
    APPROVED = "approved"  # معتمد
    CONFIRMED = "confirmed"  # مؤكد
    PROCESSING = "processing"  # قيد المعالجة
    PARTIALLY_PICKED = "partially_picked"  # تم التحضير جزئياً
    PICKED = "picked"  # تم التحضير
    PARTIALLY_PACKED = "partially_packed"  # تم التغليف جزئياً
    PACKED = "packed"  # تم التغليف
    READY_FOR_SHIPMENT = "ready_for_shipment"  # جاهز للشحن
    PARTIALLY_SHIPPED = "partially_shipped"  # تم الشحن جزئياً
    SHIPPED = "shipped"  # تم الشحن
    PARTIALLY_DELIVERED = "partially_delivered"  # تم التسليم جزئياً
    DELIVERED = "delivered"  # تم التسليم
    INVOICED = "invoiced"  # تمت الفوترة
    COMPLETED = "completed"  # مكتمل
    CANCELLED = "cancelled"  # ملغى


class SalesOrder(BaseEntity):
    """
    كيان أمر البيع
    
    Attributes:
        order_number: رقم أمر البيع الفريد
        customer_id: معرف العميل
        customer_name: اسم العميل
        branch_id: معرف الفرع
        issue_date: تاريخ إنشاء الأمر
        expected_delivery_date: تاريخ التسليم المتوقع
        status: حالة أمر البيع
        items: عناصر أمر البيع
        subtotal: المجموع الجزئي
        discount_amount: قيمة الخصم
        discount_percentage: نسبة الخصم
        tax_amount: قيمة الضريبة
        total_amount: المبلغ الإجمالي
        currency_code: رمز العملة
        exchange_rate: سعر الصرف
        notes: ملاحظات
        sales_person_id: معرف موظف المبيعات
        warehouse_id: معرف المستودع
        shipping_address: عنوان الشحن
        source_quotation_id: معرف عرض السعر المصدر
        payment_terms: شروط الدفع
        created_by: معرف من أنشأ الأمر
    """
    
    def __init__(
        self,
        order_number: str,
        customer_id: str,
        customer_name: str,
        issue_date: date,
        status: SalesOrderStatus = SalesOrderStatus.DRAFT,
        branch_id: Optional[str] = None,
        expected_delivery_date: Optional[date] = None,
        items: Optional[List['SalesOrderItem']] = None,
        discount_amount: Decimal = Decimal('0'),
        discount_percentage: Decimal = Decimal('0'),
        tax_amount: Decimal = Decimal('0'),
        total_amount: Decimal = Decimal('0'),
        currency_code: str = 'SAR',
        exchange_rate: Decimal = Decimal('1'),
        notes: Optional[str] = None,
        sales_person_id: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        shipping_address: Optional[dict] = None,
        source_quotation_id: Optional[str] = None,
        payment_terms: Optional[str] = None,
        created_by: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.order_number = order_number
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.branch_id = branch_id
        self.issue_date = issue_date
        self.expected_delivery_date = expected_delivery_date
        self.status = status
        self.items = items or []
        self.discount_amount = discount_amount
        self.discount_percentage = discount_percentage
        self.tax_amount = tax_amount
        self.total_amount = total_amount
        self.currency_code = currency_code
        self.exchange_rate = exchange_rate
        self.notes = notes
        self.sales_person_id = sales_person_id
        self.warehouse_id = warehouse_id
        self.shipping_address = shipping_address or {}
        self.source_quotation_id = source_quotation_id
        self.payment_terms = payment_terms
        self.created_by = created_by
        
        if self.items:
            self._calculate_totals()
    
    def _calculate_totals(self) -> None:
        """إعادة حساب المجاميع"""
        self.subtotal = sum(
            item.line_total for item in self.items
        )
        
        # تطبيق الخصم
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / Decimal('100'))
        
        amount_after_discount = self.subtotal - self.discount_amount
        
        # حساب الضريبة
        self.tax_amount = amount_after_discount * (Decimal('15') / Decimal('100'))
        
        # المجموع الإجمالي
        self.total_amount = amount_after_discount + self.tax_amount
    
    def add_item(self, item: 'SalesOrderItem') -> None:
        """إضافة عنصر لأمر البيع"""
        self.items.append(item)
        self._calculate_totals()
    
    def remove_item(self, item_id: str) -> bool:
        """إزالة عنصر من أمر البيع"""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                self._calculate_totals()
                return True
        return False
    
    def update_quantity(self, item_id: str, quantity: Decimal) -> bool:
        """تحديث كمية عنصر"""
        for item in self.items:
            if item.id == item_id:
                item.quantity = quantity
                self._calculate_totals()
                return True
        return False
    
    def submit_for_approval(self) -> None:
        """إرسال الأمر للموافقة"""
        if self.status == SalesOrderStatus.DRAFT:
            self.status = SalesOrderStatus.PENDING
            self.add_event('sales_order_submitted', {
                'order_id': self.id,
                'submitted_at': datetime.utcnow().isoformat()
            })
    
    def approve(self, approved_by: str) -> None:
        """الموافقة على أمر البيع"""
        if self.status == SalesOrderStatus.PENDING:
            self.status = SalesOrderStatus.APPROVED
            self.add_event('sales_order_approved', {
                'order_id': self.id,
                'approved_by': approved_by,
                'approved_at': datetime.utcnow().isoformat()
            })
    
    def reject(self, reason: str, rejected_by: str) -> None:
        """رفض أمر البيع"""
        if self.status == SalesOrderStatus.PENDING:
            self.status = SalesOrderStatus.CANCELLED
            self.add_event('sales_order_rejected', {
                'order_id': self.id,
                'reason': reason,
                'rejected_by': rejected_by,
                'rejected_at': datetime.utcnow().isoformat()
            })
    
    def confirm(self) -> None:
        """تأكيد أمر البيع"""
        if self.status == SalesOrderStatus.APPROVED:
            self.status = SalesOrderStatus.CONFIRMED
            self.add_event('sales_order_confirmed', {
                'order_id': self.id,
                'confirmed_at': datetime.utcnow().isoformat()
            })
    
    def start_processing(self) -> None:
        """بدء معالجة الأمر"""
        if self.status in [SalesOrderStatus.CONFIRMED, SalesOrderStatus.APPROVED]:
            self.status = SalesOrderStatus.PROCESSING
            self.add_event('sales_order_processing', {
                'order_id': self.id,
                'started_at': datetime.utcnow().isoformat()
            })
    
    def pick_items(self, picked_quantities: dict) -> None:
        """
        تحضير العناصر من المستودع
        
        Args:
            picked_quantities: قاموس {item_id: quantity}
        """
        if self.status not in [SalesOrderStatus.PROCESSING, SalesOrderStatus.PARTIALLY_PICKED]:
            raise ValueError("Order must be in processing state to pick items")
        
        all_picked = True
        partially_picked = False
        
        for item in self.items:
            picked_qty = picked_quantities.get(item.id, Decimal('0'))
            if picked_qty > 0:
                item.picked_quantity = picked_qty
                if picked_qty < item.quantity:
                    partially_picked = True
                    all_picked = False
                elif picked_qty > item.quantity:
                    raise ValueError(f"Picked quantity exceeds ordered quantity for item {item.product_id}")
            else:
                all_picked = False
        
        if all_picked:
            self.status = SalesOrderStatus.PICKED
        elif partially_picked:
            self.status = SalesOrderStatus.PARTIALLY_PICKED
        
        self.add_event('sales_order_picked', {
            'order_id': self.id,
            'picked_quantities': {k: str(v) for k, v in picked_quantities.items()},
            'picked_at': datetime.utcnow().isoformat()
        })
    
    def pack_items(self, packed_quantities: dict) -> None:
        """
        تغليف العناصر
        
        Args:
            packed_quantities: قاموس {item_id: quantity}
        """
        if self.status not in [SalesOrderStatus.PICKED, SalesOrderStatus.PARTIALLY_PICKED, SalesOrderStatus.PARTIALLY_PACKED]:
            raise ValueError("Order must be picked before packing")
        
        all_packed = True
        partially_packed = False
        
        for item in self.items:
            packed_qty = packed_quantities.get(item.id, Decimal('0'))
            if packed_qty > 0:
                item.packed_quantity = packed_qty
                if packed_qty < item.picked_quantity:
                    partially_packed = True
                    all_packed = False
            else:
                all_packed = False
        
        if all_packed:
            self.status = SalesOrderStatus.PACKED
        elif partially_packed:
            self.status = SalesOrderStatus.PARTIALLY_PACKED
        
        self.add_event('sales_order_packed', {
            'order_id': self.id,
            'packed_quantities': {k: str(v) for k, v in packed_quantities.items()},
            'packed_at': datetime.utcnow().isoformat()
        })
    
    def mark_ready_for_shipment(self) -> None:
        """وضع علامة كجاهز للشحن"""
        if self.status == SalesOrderStatus.PACKED:
            self.status = SalesOrderStatus.READY_FOR_SHIPMENT
            self.add_event('sales_order_ready_for_shipment', {
                'order_id': self.id,
                'ready_at': datetime.utcnow().isoformat()
            })
    
    def ship_items(self, shipped_quantities: dict, tracking_number: str = None) -> None:
        """
        شحن العناصر
        
        Args:
            shipped_quantities: قاموس {item_id: quantity}
            tracking_number: رقم التتبع
        """
        if self.status not in [SalesOrderStatus.PACKED, SalesOrderStatus.READY_FOR_SHIPMENT, SalesOrderStatus.PARTIALLY_PACKED]:
            raise ValueError("Order must be packed before shipping")
        
        all_shipped = True
        partially_shipped = False
        
        for item in self.items:
            shipped_qty = shipped_quantities.get(item.id, Decimal('0'))
            if shipped_qty > 0:
                item.shipped_quantity = shipped_qty
                if shipped_qty < item.packed_quantity:
                    partially_shipped = True
                    all_shipped = False
            else:
                all_shipped = False
        
        if all_shipped:
            self.status = SalesOrderStatus.SHIPPED
        elif partially_shipped:
            self.status = SalesOrderStatus.PARTIALLY_SHIPPED
        
        self.add_event('sales_order_shipped', {
            'order_id': self.id,
            'shipped_quantities': {k: str(v) for k, v in shipped_quantities.items()},
            'tracking_number': tracking_number,
            'shipped_at': datetime.utcnow().isoformat()
        })
    
    def deliver_items(self, delivered_quantities: dict) -> None:
        """
        تسليم العناصر
        
        Args:
            delivered_quantities: قاموس {item_id: quantity}
        """
        if self.status not in [SalesOrderStatus.SHIPPED, SalesOrderStatus.PARTIALLY_SHIPPED]:
            raise ValueError("Order must be shipped before delivery")
        
        all_delivered = True
        partially_delivered = False
        
        for item in self.items:
            delivered_qty = delivered_quantities.get(item.id, Decimal('0'))
            if delivered_qty > 0:
                item.delivered_quantity = delivered_qty
                if delivered_qty < item.shipped_quantity:
                    partially_delivered = True
                    all_delivered = False
            else:
                all_delivered = False
        
        if all_delivered:
            self.status = SalesOrderStatus.DELIVERED
        elif partially_delivered:
            self.status = SalesOrderStatus.PARTIALLY_DELIVERED
        
        self.add_event('sales_order_delivered', {
            'order_id': self.id,
            'delivered_quantities': {k: str(v) for k, v in delivered_quantities.items()},
            'delivered_at': datetime.utcnow().isoformat()
        })
    
    def create_invoice(self, invoice_id: str) -> None:
        """إنشاء فاتورة من أمر البيع"""
        if self.status in [SalesOrderStatus.DELIVERED, SalesOrderStatus.PARTIALLY_DELIVERED]:
            self.status = SalesOrderStatus.INVOICED
            self.add_event('sales_order_invoiced', {
                'order_id': self.id,
                'invoice_id': invoice_id,
                'invoiced_at': datetime.utcnow().isoformat()
            })
    
    def complete(self) -> None:
        """إكمال أمر البيع"""
        if self.status == SalesOrderStatus.INVOICED:
            self.status = SalesOrderStatus.COMPLETED
            self.add_event('sales_order_completed', {
                'order_id': self.id,
                'completed_at': datetime.utcnow().isoformat()
            })
    
    def cancel(self, reason: str) -> None:
        """إلغاء أمر البيع"""
        if self.status not in [SalesOrderStatus.DELIVERED, SalesOrderStatus.INVOICED, SalesOrderStatus.COMPLETED]:
            self.status = SalesOrderStatus.CANCELLED
            self.add_event('sales_order_cancelled', {
                'order_id': self.id,
                'reason': reason,
                'cancelled_at': datetime.utcnow().isoformat()
            })
    
    def can_create_invoice(self) -> bool:
        """التحقق مما إذا كان يمكن إنشاء فاتورة"""
        return self.status in [
            SalesOrderStatus.DELIVERED,
            SalesOrderStatus.PARTIALLY_DELIVERED
        ]
    
    def get_pending_quantity(self, item_id: str) -> Decimal:
        """الحصول على الكمية المعلقة لعنصر"""
        for item in self.items:
            if item.id == item_id:
                return item.quantity - item.delivered_quantity
        return Decimal('0')
    
    def to_dict(self) -> dict:
        """تحويل الكيان إلى قاموس"""
        return {
            'id': self.id,
            'order_number': self.order_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'branch_id': self.branch_id,
            'issue_date': self.issue_date.isoformat(),
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'status': self.status.value,
            'items': [item.to_dict() for item in self.items],
            'subtotal': str(self.subtotal),
            'discount_amount': str(self.discount_amount),
            'discount_percentage': str(self.discount_percentage),
            'tax_amount': str(self.tax_amount),
            'total_amount': str(self.total_amount),
            'currency_code': self.currency_code,
            'exchange_rate': str(self.exchange_rate),
            'notes': self.notes,
            'sales_person_id': self.sales_person_id,
            'warehouse_id': self.warehouse_id,
            'shipping_address': self.shipping_address,
            'source_quotation_id': self.source_quotation_id,
            'payment_terms': self.payment_terms,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SalesOrderItem:
    """
    عنصر في أمر البيع
    
    Attributes:
        id: معرف العنصر
        line_number: رقم السطر
        product_id: معرف المنتج
        product_name: اسم المنتج
        description: الوصف
        quantity: الكمية المطلوبة
        picked_quantity: الكمية المحضرة
        packed_quantity: الكمية المغلفة
        shipped_quantity: الكمية المشحونة
        delivered_quantity: الكمية المسلمة
        invoiced_quantity: الكمية المفوترة
        unit_of_measure: وحدة القياس
        unit_price: سعر الوحدة
        discount_percentage: نسبة الخصم
        tax_percentage: نسبة الضريبة
        line_total: إجمالي السطر
    """
    
    def __init__(
        self,
        product_id: str,
        product_name: str,
        quantity: Decimal,
        unit_price: Decimal,
        description: Optional[str] = None,
        unit_of_measure: str = 'PCS',
        discount_percentage: Decimal = Decimal('0'),
        tax_percentage: Decimal = Decimal('15'),
        line_number: int = 1,
        id: Optional[str] = None,
    ):
        import uuid
        self.id = id or str(uuid.uuid4())
        self.line_number = line_number
        self.product_id = product_id
        self.product_name = product_name
        self.description = description
        self.quantity = quantity
        self.picked_quantity = Decimal('0')
        self.packed_quantity = Decimal('0')
        self.shipped_quantity = Decimal('0')
        self.delivered_quantity = Decimal('0')
        self.invoiced_quantity = Decimal('0')
        self.unit_of_measure = unit_of_measure
        self.unit_price = unit_price
        self.discount_percentage = discount_percentage
        self.tax_percentage = tax_percentage
        self.line_total = self._calculate_line_total()
    
    def _calculate_line_total(self) -> Decimal:
        """حساب إجمالي السطر"""
        base_amount = self.quantity * self.unit_price
        discount = base_amount * (self.discount_percentage / Decimal('100'))
        return base_amount - discount
    
    def get_pending_quantity(self) -> Decimal:
        """الحصول على الكمية المعلقة"""
        return self.quantity - self.delivered_quantity
    
    def to_dict(self) -> dict:
        """تحويل العنصر إلى قاموس"""
        return {
            'id': self.id,
            'line_number': self.line_number,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'description': self.description,
            'quantity': str(self.quantity),
            'picked_quantity': str(self.picked_quantity),
            'packed_quantity': str(self.packed_quantity),
            'shipped_quantity': str(self.shipped_quantity),
            'delivered_quantity': str(self.delivered_quantity),
            'invoiced_quantity': str(self.invoiced_quantity),
            'unit_of_measure': self.unit_of_measure,
            'unit_price': str(self.unit_price),
            'discount_percentage': str(self.discount_percentage),
            'tax_percentage': str(self.tax_percentage),
            'line_total': str(self.line_total),
        }
