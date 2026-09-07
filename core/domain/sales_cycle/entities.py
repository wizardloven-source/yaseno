"""
Entities for Sales Cycle Domain
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from uuid import uuid4

from core.domain.base_entity import BaseEntity
from .value_objects import (
    QuotationStatus, OrderStatus, DeliveryStatus,
    Money, Address
)


@dataclass
class QuotationItem:
    """عنصر في عرض السعر"""
    product_id: str
    product_name: str
    quantity: float
    unit_price: float
    discount_percent: float = 0.0
    tax_percent: float = 15.0
    unit: str = "pcs"
    notes: Optional[str] = None
    
    @property
    def subtotal(self) -> float:
        """المجموع قبل الخصم والضريبة"""
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self) -> float:
        """قيمة الخصم"""
        return self.subtotal * (self.discount_percent / 100)
    
    @property
    def amount_after_discount(self) -> float:
        """المبلغ بعد الخصم"""
        return self.subtotal - self.discount_amount
    
    @property
    def tax_amount(self) -> float:
        """قيمة الضريبة"""
        return self.amount_after_discount * (self.tax_percent / 100)
    
    @property
    def total(self) -> float:
        """الإجمالي مع الضريبة"""
        return self.amount_after_discount + self.tax_amount
    
    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "discount_percent": self.discount_percent,
            "tax_percent": self.tax_percent,
            "unit": self.unit,
            "notes": self.notes,
            "subtotal": self.subtotal,
            "discount_amount": self.discount_amount,
            "amount_after_discount": self.amount_after_discount,
            "tax_amount": self.tax_amount,
            "total": self.total,
        }


@dataclass
class SalesQuotation(BaseEntity):
    """
    كيان عرض السعر
    يمثل عرض سعر مقدم للعميل يمكن تحويله لأمر بيع
    """
    quotation_number: str
    customer_id: str
    customer_name: str
    currency: str = "SAR"
    
    # التواريخ
    issue_date: date
    expiry_date: date
    valid_until: Optional[datetime] = None
    
    # العناوين
    billing_address: Optional[Address] = None
    shipping_address: Optional[Address] = None
    
    # العناصر والمجاميع
    items: List[QuotationItem] = field(default_factory=list)
    
    # الخصومات والضرائب العامة
    global_discount_percent: float = 0.0
    global_discount_amount: float = 0.0
    
    # الحالة والملاحظات
    status: QuotationStatus = QuotationStatus.DRAFT
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    # معلومات الإرسال
    sent_date: Optional[datetime] = None
    viewed_date: Optional[datetime] = None
    accepted_date: Optional[datetime] = None
    rejected_date: Optional[datetime] = None
    converted_date: Optional[datetime] = None
    
    # بيانات النظام
    created_by: Optional[str] = None
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    branch_id: Optional[str] = None
    company_id: Optional[str] = None
    
    # حقول مخصصة
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
        if not self.created_at:
            self.created_at = datetime.now()
    
    @property
    def subtotal(self) -> float:
        """المجموع الكلي للعناصر قبل الخصم العام"""
        return sum(item.subtotal for item in self.items)
    
    @property
    def total_discount(self) -> float:
        """إجمالي الخصومات (عناصر + عام)"""
        items_discount = sum(item.discount_amount for item in self.items)
        return items_discount + self.global_discount_amount
    
    @property
    def amount_after_discount(self) -> float:
        """المبلغ بعد خصم جميع الخصومات"""
        return self.subtotal - self.total_discount
    
    @property
    def total_tax(self) -> float:
        """إجمالي الضريبة"""
        return sum(item.tax_amount for item in self.items)
    
    @property
    def grand_total(self) -> float:
        """الإجمالي النهائي"""
        return self.amount_after_discount + self.total_tax
    
    @property
    def is_expired(self) -> bool:
        """هل انتهى صلاحية العرض؟"""
        if self.expiry_date:
            return date.today() > self.expiry_date
        return False
    
    @property
    def days_until_expiry(self) -> int:
        """عدد الأيام المتبقية حتى انتهاء الصلاحية"""
        if self.expiry_date:
            delta = self.expiry_date - date.today()
            return max(0, delta.days)
        return 0
    
    def add_item(self, item: QuotationItem):
        """إضافة عنصر للعرض"""
        self.items.append(item)
        self.updated_at = datetime.now()
    
    def remove_item(self, product_id: str):
        """إزالة عنصر من العرض"""
        self.items = [i for i in self.items if i.product_id != product_id]
        self.updated_at = datetime.now()
    
    def update_item(self, product_id: str, **kwargs):
        """تحديث عنصر موجود"""
        for item in self.items:
            if item.product_id == product_id:
                for key, value in kwargs.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                self.updated_at = datetime.now()
                return
        raise ValueError(f"المنتج {product_id} غير موجود في العرض")
    
    def send_to_customer(self):
        """إرسال العرض للعميل"""
        if self.status != QuotationStatus.DRAFT:
            raise ValueError("يمكن إرسال فقط العروض في حالة المسودة")
        self.status = QuotationStatus.SENT
        self.sent_date = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_as_viewed(self):
        """تسجيل أن العميل شاهد العرض"""
        if self.status != QuotationStatus.SENT:
            raise ValueError("العرض لم يتم إرساله بعد")
        self.status = QuotationStatus.VIEWED
        self.viewed_date = datetime.now()
        self.updated_at = datetime.now()
    
    def accept(self):
        """قبول العرض"""
        if self.status not in [QuotationStatus.SENT, QuotationStatus.VIEWED]:
            raise ValueError("لا يمكن قبول هذا العرض")
        self.status = QuotationStatus.ACCEPTED
        self.accepted_date = datetime.now()
        self.updated_at = datetime.now()
    
    def reject(self, reason: Optional[str] = None):
        """رفض العرض"""
        if self.status not in [QuotationStatus.SENT, QuotationStatus.VIEWED]:
            raise ValueError("لا يمكن رفض هذا العرض")
        self.status = QuotationStatus.REJECTED
        self.rejected_date = datetime.now()
        if reason:
            self.internal_notes = f"سبب الرفض: {reason}\n{self.internal_notes or ''}"
        self.updated_at = datetime.now()
    
    def expire(self):
        """إنهاء صلاحية العرض"""
        if self.status not in [QuotationStatus.DRAFT, QuotationStatus.SENT, QuotationStatus.VIEWED]:
            raise ValueError("لا يمكن إنهاء صلاحية هذا العرض")
        self.status = QuotationStatus.EXPIRED
        self.updated_at = datetime.now()
    
    def can_convert_to_order(self) -> bool:
        """هل يمكن تحويل العرض لأمر بيع؟"""
        return self.status == QuotationStatus.ACCEPTED and not self.is_expired
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "quotation_number": self.quotation_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "currency": self.currency,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "status": self.status.value,
            "items": [item.to_dict() for item in self.items],
            "subtotal": self.subtotal,
            "total_discount": self.total_discount,
            "amount_after_discount": self.amount_after_discount,
            "total_tax": self.total_tax,
            "grand_total": self.grand_total,
            "is_expired": self.is_expired,
            "days_until_expiry": self.days_until_expiry,
            "billing_address": self.billing_address.to_dict() if self.billing_address else None,
            "shipping_address": self.shipping_address.to_dict() if self.shipping_address else None,
            "notes": self.notes,
            "internal_notes": self.internal_notes,
            "sent_date": self.sent_date.isoformat() if self.sent_date else None,
            "viewed_date": self.viewed_date.isoformat() if self.viewed_date else None,
            "accepted_date": self.accepted_date.isoformat() if self.accepted_date else None,
            "rejected_date": self.rejected_date.isoformat() if self.rejected_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class OrderItem:
    """عنصر في أمر البيع"""
    product_id: str
    product_name: str
    quantity: float
    unit_price: float
    discount_percent: float = 0.0
    tax_percent: float = 15.0
    unit: str = "pcs"
    
    # تتبع التنفيذ
    picked_quantity: float = 0.0
    packed_quantity: float = 0.0
    shipped_quantity: float = 0.0
    delivered_quantity: float = 0.0
    returned_quantity: float = 0.0
    
    warehouse_id: Optional[str] = None
    batch_number: Optional[str] = None
    serial_numbers: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    
    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price
    
    @property
    def discount_amount(self) -> float:
        return self.subtotal * (self.discount_percent / 100)
    
    @property
    def amount_after_discount(self) -> float:
        return self.subtotal - self.discount_amount
    
    @property
    def tax_amount(self) -> float:
        return self.amount_after_discount * (self.tax_percent / 100)
    
    @property
    def total(self) -> float:
        return self.amount_after_discount + self.tax_amount
    
    @property
    def pending_quantity(self) -> float:
        """الكمية المتبقية للتنفيذ"""
        return self.quantity - self.delivered_quantity
    
    @property
    def is_fully_delivered(self) -> bool:
        """هل تم تسليم الكمية كاملة؟"""
        return self.delivered_quantity >= self.quantity
    
    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "discount_percent": self.discount_percent,
            "tax_percent": self.tax_percent,
            "unit": self.unit,
            "picked_quantity": self.picked_quantity,
            "packed_quantity": self.packed_quantity,
            "shipped_quantity": self.shipped_quantity,
            "delivered_quantity": self.delivered_quantity,
            "returned_quantity": self.returned_quantity,
            "pending_quantity": self.pending_quantity,
            "is_fully_delivered": self.is_fully_delivered,
            "warehouse_id": self.warehouse_id,
            "batch_number": self.batch_number,
            "serial_numbers": self.serial_numbers,
            "notes": self.notes,
            "subtotal": self.subtotal,
            "discount_amount": self.discount_amount,
            "amount_after_discount": self.amount_after_discount,
            "tax_amount": self.tax_amount,
            "total": self.total,
        }


@dataclass
class SalesOrder(BaseEntity):
    """
    كيان أمر البيع
    يمثل طلب مؤكد من العميل يتم تنفيذه عبر مراحل متعددة
    """
    order_number: str
    customer_id: str
    customer_name: str
    currency: str = "SAR"
    
    # مصدر الأمر
    source_type: Optional[str] = None  # quotation, web, pos, manual
    source_id: Optional[str] = None  # ID of the source document
    quotation_id: Optional[str] = None
    
    # التواريخ
    order_date: date
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    
    # العناوين
    billing_address: Optional[Address] = None
    shipping_address: Optional[Address] = None
    
    # العناصر والمجاميع
    items: List[OrderItem] = field(default_factory=list)
    
    # الخصومات والضرائب
    global_discount_percent: float = 0.0
    global_discount_amount: float = 0.0
    
    # الشحن
    shipping_method: Optional[str] = None
    shipping_cost: float = 0.0
    shipping_tax_percent: float = 15.0
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    
    # الدفع
    payment_status: str = "pending"  # pending, partial, paid, refunded
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None
    
    # الحالة
    status: OrderStatus = OrderStatus.DRAFT
    priority: str = "normal"  # low, normal, high, urgent
    
    # الملاحظات
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    # الفوترة
    invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    invoiced_date: Optional[datetime] = None
    invoiced_amount: float = 0.0
    
    # بيانات النظام
    created_by: Optional[str] = None
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    branch_id: Optional[str] = None
    company_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    
    # حقول مخصصة
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
        if not self.created_at:
            self.created_at = datetime.now()
    
    @property
    def subtotal(self) -> float:
        return sum(item.subtotal for item in self.items)
    
    @property
    def total_discount(self) -> float:
        items_discount = sum(item.discount_amount for item in self.items)
        return items_discount + self.global_discount_amount
    
    @property
    def amount_after_discount(self) -> float:
        return self.subtotal - self.total_discount
    
    @property
    def total_tax(self) -> float:
        items_tax = sum(item.tax_amount for item in self.items)
        shipping_tax = self.shipping_cost * (self.shipping_tax_percent / 100)
        return items_tax + shipping_tax
    
    @property
    def grand_total(self) -> float:
        return self.amount_after_discount + self.total_tax + self.shipping_cost
    
    @property
    def paid_amount(self) -> float:
        """المبلغ المدفوع"""
        return self.invoiced_amount if self.payment_status == "paid" else 0.0
    
    @property
    def outstanding_amount(self) -> float:
        """المبلغ المستحق"""
        return self.grand_total - self.paid_amount
    
    @property
    def is_fully_delivered(self) -> bool:
        """هل تم تسليم جميع العناصر؟"""
        return all(item.is_fully_delivered for item in self.items)
    
    @property
    def delivery_progress(self) -> float:
        """نسبة التقدم في التسليم"""
        if not self.items:
            return 0.0
        total_qty = sum(item.quantity for item in self.items)
        delivered_qty = sum(item.delivered_quantity for item in self.items)
        return (delivered_qty / total_qty * 100) if total_qty > 0 else 0.0
    
    def confirm(self):
        """تأكيد أمر البيع"""
        if self.status != OrderStatus.DRAFT:
            raise ValueError("يمكن تأكيد فقط الأوامر في حالة المسودة")
        self.status = OrderStatus.CONFIRMED
        self.updated_at = datetime.now()
    
    def start_picking(self):
        """بدء تحضير الطلبية"""
        if self.status != OrderStatus.CONFIRMED:
            raise ValueError("الأمر يجب أن يكون مؤكداً لبدء التحضير")
        self.status = OrderStatus.PICKING
        self.updated_at = datetime.now()
    
    def complete_picking(self):
        """اكتمال التحضير"""
        if self.status != OrderStatus.PICKING:
            raise ValueError("الأمر ليس قيد التحضير")
        self.status = OrderStatus.PACKING
        self.updated_at = datetime.now()
    
    def complete_packing(self):
        """اكتمال التغليف"""
        if self.status != OrderStatus.PACKING:
            raise ValueError("الأمر ليس قيد التغليف")
        self.status = OrderStatus.READY_TO_SHIP
        self.updated_at = datetime.now()
    
    def ship(self, tracking_number: str, carrier: Optional[str] = None):
        """شحن الطلبية"""
        if self.status != OrderStatus.READY_TO_SHIP:
            raise ValueError("الأمر ليس جاهزاً للشحن")
        self.status = OrderStatus.SHIPPED
        self.tracking_number = tracking_number
        self.carrier = carrier
        self.updated_at = datetime.now()
    
    def mark_in_transit(self):
        """تسجيل أن الطلبية أثناء النقل"""
        if self.status != OrderStatus.SHIPPED:
            raise ValueError("الأمر لم يتم شحنه بعد")
        self.status = OrderStatus.IN_TRANSIT
        self.updated_at = datetime.now()
    
    def mark_out_for_delivery(self):
        """تسجيل أن الطلبية خارج للتسليم"""
        if self.status not in [OrderStatus.IN_TRANSIT, OrderStatus.SHIPPED]:
            raise ValueError("الأمر ليس أثناء النقل")
        self.status = OrderStatus.OUT_FOR_DELIVERY
        self.updated_at = datetime.now()
    
    def deliver(self, delivery_date: Optional[date] = None):
        """تسليم الطلبية"""
        self.status = OrderStatus.DELIVERED
        self.actual_delivery_date = delivery_date or date.today()
        self.updated_at = datetime.now()
    
    def cancel(self, reason: Optional[str] = None):
        """إلغاء أمر البيع"""
        if self.status in [OrderStatus.DELIVERED, OrderStatus.COMPLETED]:
            raise ValueError("لا يمكن إلغاء أمر تم تسليمه")
        self.status = OrderStatus.CANCELLED
        if reason:
            self.internal_notes = f"سبب الإلغاء: {reason}\n{self.internal_notes or ''}"
        self.updated_at = datetime.now()
    
    def put_on_hold(self, reason: str):
        """تعليق أمر البيع"""
        if self.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            raise ValueError("لا يمكن تعليق أمر تم تسليمه أو إلغاؤه")
        self.status = OrderStatus.ON_HOLD
        self.internal_notes = f"سبب التعليق: {reason}\n{self.internal_notes or ''}"
        self.updated_at = datetime.now()
    
    def resume(self):
        """استئناف أمر البيع المعلق"""
        if self.status != OrderStatus.ON_HOLD:
            raise ValueError("الأمر ليس معلقاً")
        self.status = OrderStatus.CONFIRMED
        self.updated_at = datetime.now()
    
    def create_invoice(self, invoice_id: str, invoice_number: str, amount: float):
        """إنشاء فاتورة للأمر"""
        self.invoice_id = invoice_id
        self.invoice_number = invoice_number
        self.invoiced_amount = amount
        self.invoiced_date = datetime.now()
        self.payment_status = "paid" if amount >= self.grand_total else "partial"
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "order_number": self.order_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "currency": self.currency,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "quotation_id": self.quotation_id,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "expected_delivery_date": self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            "actual_delivery_date": self.actual_delivery_date.isoformat() if self.actual_delivery_date else None,
            "status": self.status.value,
            "priority": self.priority,
            "items": [item.to_dict() for item in self.items],
            "subtotal": self.subtotal,
            "total_discount": self.total_discount,
            "amount_after_discount": self.amount_after_discount,
            "total_tax": self.total_tax,
            "shipping_cost": self.shipping_cost,
            "grand_total": self.grand_total,
            "payment_status": self.payment_status,
            "outstanding_amount": self.outstanding_amount,
            "is_fully_delivered": self.is_fully_delivered,
            "delivery_progress": self.delivery_progress,
            "tracking_number": self.tracking_number,
            "carrier": self.carrier,
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice_number,
            "notes": self.notes,
            "internal_notes": self.internal_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


@dataclass
class DeliveryItem:
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
    
    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "ordered_quantity": self.ordered_quantity,
            "delivered_quantity": self.delivered_quantity,
            "unit": self.unit,
            "warehouse_id": self.warehouse_id,
            "batch_number": self.batch_number,
            "serial_numbers": self.serial_numbers,
            "notes": self.notes,
        }


@dataclass
class DeliveryNote(BaseEntity):
    """
    كيان إشعار التسليم
    يوثق عملية تسليم البضائع للعميل
    """
    delivery_number: str
    order_id: str
    order_number: str
    customer_id: str
    customer_name: str
    
    # التواريخ
    delivery_date: date
    scheduled_date: Optional[date] = None
    actual_delivery_time: Optional[datetime] = None
    
    # العنوان
    delivery_address: Optional[Address] = None
    
    # العناصر
    items: List[DeliveryItem] = field(default_factory=list)
    
    # معلومات الشحن
    carrier: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    
    # الحالة
    status: DeliveryStatus = DeliveryStatus.DRAFT
    
    # التوقيع والاستلام
    received_by: Optional[str] = None
    received_by_title: Optional[str] = None
    received_date: Optional[datetime] = None
    signature_url: Optional[str] = None
    
    # الملاحظات
    notes: Optional[str] = None
    delivery_notes: Optional[str] = None
    failure_reason: Optional[str] = None
    
    # بيانات النظام
    warehouse_id: Optional[str] = None
    branch_id: Optional[str] = None
    company_id: Optional[str] = None
    created_by: Optional[str] = None
    delivered_by: Optional[str] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid4())
        if not self.created_at:
            self.created_at = datetime.now()
    
    @property
    def total_items(self) -> int:
        return len(self.items)
    
    @property
    def total_quantity(self) -> float:
        return sum(item.delivered_quantity for item in self.items)
    
    @property
    def is_fully_delivered(self) -> bool:
        return all(
            item.delivered_quantity >= item.ordered_quantity 
            for item in self.items
        )
    
    def schedule(self, scheduled_date: date):
        """جدولة التسليم"""
        if self.status != DeliveryStatus.DRAFT:
            raise ValueError("يمكن الجدولة فقط للمسودات")
        self.scheduled_date = scheduled_date
        self.status = DeliveryStatus.SCHEDULED
        self.updated_at = datetime.now()
    
    def start_delivery(self):
        """بدء عملية التسليم"""
        if self.status not in [DeliveryStatus.DRAFT, DeliveryStatus.SCHEDULED]:
            raise ValueError("لا يمكن بدء التسليم")
        self.status = DeliveryStatus.IN_TRANSIT
        self.updated_at = datetime.now()
    
    def complete_delivery(self, received_by: str, received_by_title: Optional[str] = None):
        """اكتمال التسليم"""
        self.status = DeliveryStatus.DELIVERED
        self.received_by = received_by
        self.received_by_title = received_by_title
        self.received_date = datetime.now()
        self.actual_delivery_time = datetime.now()
        self.updated_at = datetime.now()
    
    def fail_delivery(self, reason: str):
        """فشل التسليم"""
        self.status = DeliveryStatus.FAILED
        self.failure_reason = reason
        self.updated_at = datetime.now()
    
    def return_delivery(self):
        """إرجاع التسليم"""
        if self.status != DeliveryStatus.DELIVERED:
            raise ValueError("يمكن الإرجاع فقط للتسليمات المكتملة")
        self.status = DeliveryStatus.RETURNED
        self.updated_at = datetime.now()
    
    def cancel(self):
        """إلغاء إشعار التسليم"""
        if self.status in [DeliveryStatus.DELIVERED]:
            raise ValueError("لا يمكن إلغاء تسليم مكتمل")
        self.status = DeliveryStatus.CANCELLED
        self.updated_at = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "delivery_number": self.delivery_number,
            "order_id": self.order_id,
            "order_number": self.order_number,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "delivery_date": self.delivery_date.isoformat() if self.delivery_date else None,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "actual_delivery_time": self.actual_delivery_time.isoformat() if self.actual_delivery_time else None,
            "status": self.status.value,
            "items": [item.to_dict() for item in self.items],
            "total_items": self.total_items,
            "total_quantity": self.total_quantity,
            "is_fully_delivered": self.is_fully_delivered,
            "carrier": self.carrier,
            "vehicle_number": self.vehicle_number,
            "driver_name": self.driver_name,
            "driver_phone": self.driver_phone,
            "received_by": self.received_by,
            "received_by_title": self.received_by_title,
            "received_date": self.received_date.isoformat() if self.received_date else None,
            "signature_url": self.signature_url,
            "notes": self.notes,
            "delivery_notes": self.delivery_notes,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
