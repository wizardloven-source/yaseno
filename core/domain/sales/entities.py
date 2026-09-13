# core/domain/sales/entities.py
"""
Sales Entities - الكيانات التجارية لدورة المبيعات
✅ SalesQuotation: عرض السعر
✅ SalesOrder: أمر البيع
✅ DeliveryNote: إشعار التسليم
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
import uuid

from core.domain.shared.value_objects import Money
from .value_objects import (
    QuotationId, QuotationNumber, QuotationStatus,
    OrderId, OrderNumber, OrderStatus,
    DeliveryId, DeliveryNumber, DeliveryStatus,
    CustomerReference, SalesPersonReference, ShippingAddress, PaymentTerms
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ============================================================================
# Sales Quotation Entity
# ============================================================================

@dataclass
class QuotationItem:
    """عنصر في عرض السعر"""
    
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Money
    notes: str = ""
    line_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # خصم على مستوى السطر
    discount_percent: Decimal = Decimal('0')
    discount_amount: Money = field(default_factory=lambda: Money.zero())
    
    # ضريبة على مستوى السطر
    tax_rate: Decimal = Decimal('0')
    tax_amount: Money = field(default_factory=lambda: Money.zero())
    
    @property
    def subtotal(self) -> Money:
        """المجموع الجزئي قبل الخصم والضريبة"""
        return Money(self.quantity * self.unit_price.amount, self.unit_price.currency)
    
    @property
    def total_discount(self) -> Money:
        """إجمالي الخصم للسطر"""
        if self.discount_percent > 0:
            return Money(self.subtotal.amount * (self.discount_percent / Decimal('100')), self.subtotal.currency)
        return self.discount_amount
    
    @property
    def total_after_discount(self) -> Money:
        """الإجمالي بعد الخصم"""
        return Money(self.subtotal.amount - self.total_discount.amount, self.subtotal.currency)
    
    @property
    def total_with_tax(self) -> Money:
        """الإجمالي شامل الضريبة"""
        return Money(self.total_after_discount.amount + self.tax_amount.amount, self.total_after_discount.currency)
    
    @property
    def currency(self) -> str:
        return self.unit_price.currency


@dataclass
class SalesQuotation:
    """
    عرض سعر - Sales Quotation
    Aggregate Root لعروض الأسعار
    """
    
    id: QuotationId
    quotation_number: QuotationNumber
    customer_id: str
    customer_name: str
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    
    # التواريخ
    issue_date: datetime = field(default_factory=utc_now)
    expiry_date: Optional[datetime] = None
    valid_days: int = 30  # أيام الصلاحية الافتراضية
    
    # العناصر
    items: List[QuotationItem] = field(default_factory=list)
    
    # الحالة
    status: QuotationStatus = QuotationStatus.DRAFT
    
    # العملة
    currency: str = "SAR"
    exchange_rate: Decimal = Decimal('1')
    
    # المجاميع
    subtotal: Money = field(default_factory=lambda: Money.zero())
    total_discount: Money = field(default_factory=lambda: Money.zero())
    total_tax: Money = field(default_factory=lambda: Money.zero())
    total_amount: Money = field(default_factory=lambda: Money.zero())
    
    # خصم عام على الفاتورة
    global_discount_percent: Decimal = Decimal('0')
    global_discount_amount: Money = field(default_factory=lambda: Money.zero())
    
    # ملاحظات
    notes: str = ""
    internal_notes: str = ""
    
    # موظف المبيعات
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    
    # شروط الدفع
    payment_terms: Optional[PaymentTerms] = None
    
    # عنوان الشحن
    shipping_address: Optional[ShippingAddress] = None
    
    # تتبع
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None
    
    # معرفات خارجية
    converted_to_order_id: Optional[str] = None
    source_opportunity_id: Optional[str] = None  # من CRM
    
    # حقول إضافية
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        customer_id: str,
        customer_name: str,
        currency: str = "SAR",
        valid_days: int = 30,
        sales_person_id: Optional[str] = None,
        **kwargs
    ) -> 'SalesQuotation':
        """إنشاء عرض سعر جديد"""
        quotation_id = QuotationId.generate()
        
        # توليد رقم عرض السعر (يجب أن يأتي من Sequence Service)
        sequence = kwargs.get('sequence', 1)
        quotation_number = QuotationNumber.generate(prefix="QT", sequence=sequence)
        
        expiry_date = utc_now()
        if valid_days > 0:
            from datetime import timedelta
            expiry_date = utc_now() + timedelta(days=valid_days)
        
        return cls(
            id=quotation_id,
            quotation_number=quotation_number,
            customer_id=customer_id,
            customer_name=customer_name,
            currency=currency,
            valid_days=valid_days,
            expiry_date=expiry_date,
            sales_person_id=sales_person_id,
            **kwargs
        )
    
    def add_item(self, item: QuotationItem) -> None:
        """إضافة عنصر لعرض السعر"""
        if self.status != QuotationStatus.DRAFT:
            raise ValueError("Cannot add items to a non-draft quotation")
        self.items.append(item)
        self._recalculate_totals()
    
    def remove_item(self, line_id: str) -> None:
        """إزالة عنصر من عرض السعر"""
        if self.status != QuotationStatus.DRAFT:
            raise ValueError("Cannot remove items from a non-draft quotation")
        self.items = [item for item in self.items if item.line_id != line_id]
        self._recalculate_totals()
    
    def update_item(self, line_id: str, **updates) -> None:
        """تحديث عنصر في عرض السعر"""
        if self.status != QuotationStatus.DRAFT:
            raise ValueError("Cannot update items in a non-draft quotation")
        
        for item in self.items:
            if item.line_id == line_id:
                for key, value in updates.items():
                    if hasattr(item, key):
                        setattr(item, key, value)
                self._recalculate_totals()
                return
        
        raise ValueError(f"Item with line_id {line_id} not found")
    
    def _recalculate_totals(self) -> None:
        """إعادة حساب المجاميع"""
        if not self.items:
            self.subtotal = Money.zero(self.currency)
            self.total_discount = Money.zero(self.currency)
            self.total_tax = Money.zero(self.currency)
            self.total_amount = Money.zero(self.currency)
            return
        
        currency = self.items[0].currency
        
        # حساب المجاميع من العناصر
        subtotal = sum((item.subtotal.amount for item in self.items), Decimal('0'))
        total_discount = sum((item.total_discount.amount for item in self.items), Decimal('0'))
        total_after_discount = sum((item.total_after_discount.amount for item in self.items), Decimal('0'))
        total_tax = sum((item.tax_amount.amount for item in self.items), Decimal('0'))
        
        # تطبيق الخصم العام
        global_discount = Decimal('0')
        if self.global_discount_percent > 0:
            global_discount = total_after_discount * (self.global_discount_percent / Decimal('100'))
        elif self.global_discount_amount.amount > 0:
            global_discount = self.global_discount_amount.amount
        
        final_total = total_after_discount - global_discount + total_tax
        
        self.subtotal = Money(subtotal, currency)
        self.total_discount = Money(total_discount + global_discount, currency)
        self.total_tax = Money(total_tax, currency)
        self.total_amount = Money(final_total, currency)
    
    def send(self) -> None:
        """إرسال عرض السعر للعميل"""
        if self.status != QuotationStatus.DRAFT:
            raise ValueError("Only draft quotations can be sent")
        
        self.status = QuotationStatus.SENT
        self.sent_at = utc_now()
        self.updated_at = utc_now()
    
    def mark_as_viewed(self) -> None:
        """وضع علامة كـ \"شوهد\" من العميل"""
        if self.status not in [QuotationStatus.SENT]:
            raise ValueError("Only sent quotations can be marked as viewed")
        
        self.status = QuotationStatus.VIEWED
        self.viewed_at = utc_now()
        self.updated_at = utc_now()
    
    def accept(self) -> None:
        """قبول عرض السعر"""
        if self.status not in [QuotationStatus.SENT, QuotationStatus.VIEWED]:
            raise ValueError("Only sent/viewed quotations can be accepted")
        
        if self.is_expired:
            raise ValueError("Cannot accept an expired quotation")
        
        self.status = QuotationStatus.ACCEPTED
        self.accepted_at = utc_now()
        self.updated_at = utc_now()
    
    def reject(self, reason: str = "") -> None:
        """رفض عرض السعر"""
        if self.status not in [QuotationStatus.SENT, QuotationStatus.VIEWED]:
            raise ValueError("Only sent/viewed quotations can be rejected")
        
        self.status = QuotationStatus.REJECTED
        self.rejected_at = utc_now()
        self.updated_at = utc_now()
        
        if reason:
            self.internal_notes += f"\nReason for rejection: {reason}"
    
    def convert_to_order(self) -> 'SalesOrder':
        """تحويل عرض السعر إلى أمر بيع"""
        if self.status != QuotationStatus.ACCEPTED:
            raise ValueError("Only accepted quotations can be converted to orders")
        
        if self.converted_to_order_id:
            raise ValueError("This quotation has already been converted to an order")
        
        # إنشاء أمر بيع جديد
        order = SalesOrder.create(
            customer_id=self.customer_id,
            customer_name=self.customer_name,
            customer_branch_id=self.customer_branch_id,
            customer_branch_name=self.customer_branch_name,
            currency=self.currency,
            sales_person_id=self.sales_person_id,
            sales_person_name=self.sales_person_name,
            shipping_address=self.shipping_address,
            payment_terms=self.payment_terms,
            notes=self.notes,
            source_quotation_id=str(self.id.value),
            sequence=1  # يجب أن يأتي من Sequence Service
        )
        
        # نسخ العناصر
        for item in self.items:
            order.add_item(OrderItem(
                product_code=item.product_code,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                notes=item.notes,
                discount_percent=item.discount_percent,
                tax_rate=item.tax_rate
            ))
        
        # تحديث حالة عرض السعر
        self.status = QuotationStatus.CONVERTED
        self.converted_at = utc_now()
        self.updated_at = utc_now()
        
        return order
    
    @property
    def is_expired(self) -> bool:
        """هل انتهت صلاحية عرض السعر؟"""
        if self.expiry_date is None:
            return False
        return utc_now() > self.expiry_date
    
    @property
    def days_until_expiry(self) -> int:
        """عدد الأيام المتبقية حتى انتهاء الصلاحية"""
        if self.expiry_date is None:
            return -1
        delta = self.expiry_date - utc_now()
        return max(0, delta.days)
    
    @property
    def item_count(self) -> int:
        """عدد العناصر"""
        return len(self.items)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        return {
            'id': str(self.id.value),
            'quotation_number': str(self.quotation_number.value),
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'status': self.status.value,
            'issue_date': self.issue_date.isoformat(),
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'currency': self.currency,
            'subtotal': float(self.subtotal.amount),
            'total_discount': float(self.total_discount.amount),
            'total_tax': float(self.total_tax.amount),
            'total_amount': float(self.total_amount.amount),
            'item_count': self.item_count,
            'is_expired': self.is_expired,
            'days_until_expiry': self.days_until_expiry,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


# ============================================================================
# Sales Order Entity
# ============================================================================

@dataclass
class OrderItem:
    """عنصر في أمر البيع"""
    
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Money
    notes: str = ""
    line_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # الكميات المنجزة
    picked_quantity: Decimal = Decimal('0')
    packed_quantity: Decimal = Decimal('0')
    delivered_quantity: Decimal = Decimal('0')
    
    # خصم وضريبة
    discount_percent: Decimal = Decimal('0')
    discount_amount: Money = field(default_factory=lambda: Money.zero())
    tax_rate: Decimal = Decimal('0')
    tax_amount: Money = field(default_factory=lambda: Money.zero())
    
    # معلومات المخزون
    warehouse_id: Optional[str] = None
    bin_location: Optional[str] = None
    
    @property
    def subtotal(self) -> Money:
        return Money(self.quantity * self.unit_price.amount, self.unit_price.currency)
    
    @property
    def total_after_discount(self) -> Money:
        if self.discount_percent > 0:
            discount = self.subtotal.amount * (self.discount_percent / Decimal('100'))
            return Money(self.subtotal.amount - discount, self.subtotal.currency)
        return Money(self.subtotal.amount - self.discount_amount.amount, self.subtotal.currency)
    
    @property
    def total_with_tax(self) -> Money:
        return Money(self.total_after_discount.amount + self.tax_amount.amount, self.total_after_discount.currency)
    
    @property
    def is_fully_delivered(self) -> bool:
        return self.delivered_quantity >= self.quantity
    
    @property
    def is_partially_delivered(self) -> bool:
        return Decimal('0') < self.delivered_quantity < self.quantity
    
    @property
    def pending_quantity(self) -> Decimal:
        return self.quantity - self.delivered_quantity


@dataclass
class SalesOrder:
    """
    أمر بيع - Sales Order
    Aggregate Root لأوامر البيع
    """
    
    id: OrderId
    order_number: OrderNumber
    customer_id: str
    customer_name: str
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    
    # التواريخ
    order_date: datetime = field(default_factory=utc_now)
    required_date: Optional[datetime] = None
    shipped_date: Optional[datetime] = None
    delivered_date: Optional[datetime] = None
    
    # العناصر
    items: List[OrderItem] = field(default_factory=list)
    
    # الحالة
    status: OrderStatus = OrderStatus.DRAFT
    
    # العملة
    currency: str = "SAR"
    exchange_rate: Decimal = Decimal('1')
    
    # المجاميع
    subtotal: Money = field(default_factory=lambda: Money.zero())
    total_discount: Money = field(default_factory=lambda: Money.zero())
    total_tax: Money = field(default_factory=lambda: Money.zero())
    total_amount: Money = field(default_factory=lambda: Money.zero())
    
    # خصم عام
    global_discount_percent: Decimal = Decimal('0')
    global_discount_amount: Money = field(default_factory=lambda: Money.zero())
    
    # ملاحظات
    notes: str = ""
    internal_notes: str = ""
    
    # موظف المبيعات
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    
    # الشحن
    shipping_address: Optional[ShippingAddress] = None
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    
    # الدفع
    payment_terms: Optional[PaymentTerms] = None
    
    # روابط
    source_quotation_id: Optional[str] = None
    invoice_ids: List[str] = field(default_factory=list)
    delivery_ids: List[str] = field(default_factory=list)
    
    # تتبع
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # حقول إضافية
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def create(
        cls,
        customer_id: str,
        customer_name: str,
        currency: str = "SAR",
        sales_person_id: Optional[str] = None,
        source_quotation_id: Optional[str] = None,
        **kwargs
    ) -> 'SalesOrder':
        """إنشاء أمر بيع جديد"""
        order_id = OrderId.generate()
        sequence = kwargs.get('sequence', 1)
        order_number = OrderNumber.generate(prefix="SO", sequence=sequence)
        
        return cls(
            id=order_id,
            order_number=order_number,
            customer_id=customer_id,
            customer_name=customer_name,
            currency=currency,
            sales_person_id=sales_person_id,
            source_quotation_id=source_quotation_id,
            **kwargs
        )
    
    def add_item(self, item: OrderItem) -> None:
        """إضافة عنصر لأمر البيع"""
        if self.status not in [OrderStatus.DRAFT, OrderStatus.ON_HOLD]:
            raise ValueError(f"Cannot add items to order in status {self.status.value}")
        self.items.append(item)
        self._recalculate_totals()
    
    def remove_item(self, line_id: str) -> None:
        """إزالة عنصر من أمر البيع"""
        if self.status not in [OrderStatus.DRAFT, OrderStatus.ON_HOLD]:
            raise ValueError(f"Cannot remove items from order in status {self.status.value}")
        self.items = [item for item in self.items if item.line_id != line_id]
        self._recalculate_totals()
    
    def _recalculate_totals(self) -> None:
        """إعادة حساب المجاميع"""
        if not self.items:
            self.subtotal = Money.zero(self.currency)
            self.total_discount = Money.zero(self.currency)
            self.total_tax = Money.zero(self.currency)
            self.total_amount = Money.zero(self.currency)
            return
        
        currency = self.items[0].currency
        
        subtotal = sum((item.subtotal.amount for item in self.items), Decimal('0'))
        total_discount = sum((item.total_after_discount.amount - item.subtotal.amount for item in self.items), Decimal('0'))
        total_after_discount = sum((item.total_after_discount.amount for item in self.items), Decimal('0'))
        total_tax = sum((item.tax_amount.amount for item in self.items), Decimal('0'))
        
        global_discount = Decimal('0')
        if self.global_discount_percent > 0:
            global_discount = total_after_discount * (self.global_discount_percent / Decimal('100'))
        elif self.global_discount_amount.amount > 0:
            global_discount = self.global_discount_amount.amount
        
        final_total = total_after_discount - global_discount + total_tax
        
        self.subtotal = Money(subtotal, currency)
        self.total_discount = Money(abs(total_discount) + global_discount, currency)
        self.total_tax = Money(total_tax, currency)
        self.total_amount = Money(final_total, currency)
    
    def confirm(self) -> None:
        """تأكيد أمر البيع"""
        if self.status != OrderStatus.DRAFT:
            raise ValueError("Only draft orders can be confirmed")
        
        if not self.items:
            raise ValueError("Cannot confirm an order without items")
        
        self.status = OrderStatus.CONFIRMED
        self.confirmed_at = utc_now()
        self.updated_at = utc_now()
    
    def add_item(self, item: OrderItem) -> None:
        """إضافة عنصر لأمر البيع"""
        if self.status not in [OrderStatus.DRAFT, OrderStatus.ON_HOLD]:
            raise ValueError("الأمر يجب أن يكون في حالة مسودة لإضافة عناصر")
        self.items.append(item)
        self._recalculate_totals()
        self._update_delivery_progress()
    
    def remove_item(self, line_id: str) -> None:
        """إزالة عنصر من أمر البيع"""
        if self.status not in [OrderStatus.DRAFT, OrderStatus.ON_HOLD]:
            raise ValueError("الأمر يجب أن يكون في حالة مسودة لإزالة عناصر")
        self.items = [item for item in self.items if item.line_id != line_id]
        self._recalculate_totals()
        self._update_delivery_progress()
    
    def start_picking(self) -> None:
        """بدء الجرد"""
        if self.status != OrderStatus.CONFIRMED:
            raise ValueError("Only confirmed orders can start picking")
        
        self.status = OrderStatus.PICKING
        self.updated_at = utc_now()
    
    def complete_picking(self) -> None:
        """إكمال الجرد"""
        if self.status != OrderStatus.PICKING:
            raise ValueError("Only picking orders can complete picking")
        
        self.status = OrderStatus.PICKED
        self.updated_at = utc_now()
    
    def start_packing(self) -> None:
        """بدء التعبئة"""
        if self.status != OrderStatus.PICKED:
            raise ValueError("Only picked orders can start packing")
        
        self.status = OrderStatus.PACKING
        self.updated_at = utc_now()
    
    def complete_packing(self) -> None:
        """إكمال التعبئة"""
        if self.status != OrderStatus.PACKING:
            raise ValueError("Only packing orders can complete packing")
        
        self.status = OrderStatus.PACKED
        self.updated_at = utc_now()
    
    def ship(self, tracking_number: Optional[str] = None) -> None:
        """شحن الطلب"""
        if self.status not in [OrderStatus.PACKED, OrderStatus.READY_TO_SHIP]:
            raise ValueError("Only packed orders can be shipped")
        
        self.status = OrderStatus.SHIPPED
        self.tracking_number = tracking_number
        self.shipped_date = utc_now()
        self.updated_at = utc_now()
    
    def mark_delivered(self) -> None:
        """وضع علامة كـ تم التسليم"""
        if self.status not in [OrderStatus.SHIPPED, OrderStatus.IN_TRANSIT]:
            raise ValueError("Only shipped orders can be marked as delivered")
        
        self.status = OrderStatus.DELIVERED
        self.delivered_date = utc_now()
        self.updated_at = utc_now()
    
    def cancel(self, reason: str = "") -> None:
        """إلغاء أمر البيع"""
        if self.status in [OrderStatus.DELIVERED, OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel order in status {self.status.value}")
        
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = utc_now()
        self.updated_at = utc_now()
        
        if reason:
            self.internal_notes += f"\nCancellation reason: {reason}"
    
    def put_on_hold(self) -> None:
        """تعليق أمر البيع"""
        if self.status not in [OrderStatus.DRAFT, OrderStatus.CONFIRMED]:
            raise ValueError(f"Cannot put order on hold in status {self.status.value}")
        
        self.status = OrderStatus.ON_HOLD
        self.updated_at = utc_now()
    
    def resume(self) -> None:
        """استئناف أمر البيع المعلق"""
        if self.status != OrderStatus.ON_HOLD:
            raise ValueError("Only held orders can be resumed")
        
        self.status = OrderStatus.CONFIRMED
        self.updated_at = utc_now()
    
    @property
    def is_fully_delivered(self) -> bool:
        """هل تم تسليم الطلب بالكامل؟"""
        return all(item.is_fully_delivered for item in self.items)
    
    @property
    def is_partially_delivered(self) -> bool:
        """هل تم تسليم الطلب جزئياً؟"""
        return any(item.is_partially_delivered for item in self.items) and not self.is_fully_delivered
    
    @property
    def total_picked_quantity(self) -> Decimal:
        """إجمالي الكمية التي تم جردها"""
        return sum((item.picked_quantity for item in self.items), Decimal('0'))
    
    @property
    def total_packed_quantity(self) -> Decimal:
        """إجمالي الكمية التي تم تعبئتها"""
        return sum((item.packed_quantity for item in self.items), Decimal('0'))
    
    @property
    def total_delivered_quantity(self) -> Decimal:
        """إجمالي الكمية التي تم تسليمها"""
        return sum((item.delivered_quantity for item in self.items), Decimal('0'))
    
    @property
    def delivery_progress(self) -> float:
        """نسبة التقدم في التسليم (0-100)"""
        if not self.items:
            return 0.0
        total_ordered = sum((item.quantity for item in self.items), Decimal('0'))
        if total_ordered == 0:
            return 0.0
        total_delivered = sum((item.delivered_quantity for item in self.items), Decimal('0'))
        return float((total_delivered / total_ordered) * Decimal('100'))
    
    def _update_delivery_progress(self) -> None:
        """تحديث نسبة التقدم في التسويل - تُستدعى تلقائياً عند إضافة/إزالة عناصر"""
        # هذه الدالة تُستخدم لضمان تحديث التقدم عند تغيير العناصر
        # القيمة الفعلية تُحسب من خاصية delivery_progress
        pass
    
    @property
    def item_count(self) -> int:
        return len(self.items)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        return {
            'id': str(self.id.value),
            'order_number': str(self.order_number.value),
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'status': self.status.value,
            'order_date': self.order_date.isoformat(),
            'currency': self.currency,
            'subtotal': float(self.subtotal.amount),
            'total_discount': float(self.total_discount.amount),
            'total_tax': float(self.total_tax.amount),
            'total_amount': float(self.total_amount.amount),
            'item_count': self.item_count,
            'is_fully_delivered': self.is_fully_delivered,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


# ============================================================================
# Delivery Note Entity
# ============================================================================

@dataclass
class DeliveryItem:
    """عنصر في إشعار التسليم"""
    
    product_code: str
    product_name: str
    quantity: Decimal
    delivered_quantity: Decimal = Decimal('0')
    returned_quantity: Decimal = Decimal('0')
    line_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # مرجع للعنصر في أمر البيع
    order_item_line_id: Optional[str] = None
    
    @property
    def is_fully_delivered(self) -> bool:
        return self.delivered_quantity >= self.quantity
    
    @property
    def pending_quantity(self) -> Decimal:
        return self.quantity - self.delivered_quantity


@dataclass
class DeliveryNote:
    """
    إشعار تسليم - Delivery Note
    Aggregate Root لإشعارات التسليم
    """
    
    id: DeliveryId
    delivery_number: DeliveryNumber
    customer_id: str
    customer_name: str
    order_id: Optional[str] = None
    order_number: Optional[str] = None
    
    # التواريخ
    delivery_date: datetime = field(default_factory=utc_now)
    scheduled_date: Optional[datetime] = None
    actual_delivery_date: Optional[datetime] = None
    
    # العناصر
    items: List[DeliveryItem] = field(default_factory=list)
    
    # الحالة
    status: DeliveryStatus = DeliveryStatus.DRAFT
    
    # الشحن
    shipping_address: Optional[ShippingAddress] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    
    # ملاحظات
    notes: str = ""
    internal_notes: str = ""
    
    # توقيع الاستلام
    received_by: Optional[str] = None
    received_at: Optional[datetime] = None
    signature_url: Optional[str] = None
    
    # أسباب الإرجاع
    return_reason: Optional[str] = None
    
    # تتبع
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    @classmethod
    def create(
        cls,
        customer_id: str,
        customer_name: str,
        order_id: Optional[str] = None,
        order_number: Optional[str] = None,
        **kwargs
    ) -> 'DeliveryNote':
        """إنشاء إشعار تسليم جديد"""
        delivery_id = DeliveryId.generate()
        sequence = kwargs.get('sequence', 1)
        delivery_number = DeliveryNumber.generate(prefix="DN", sequence=sequence)
        
        return cls(
            id=delivery_id,
            delivery_number=delivery_number,
            order_id=order_id,
            order_number=order_number,
            customer_id=customer_id,
            customer_name=customer_name,
            **kwargs
        )
    
    def add_item(self, item: DeliveryItem) -> None:
        """إضافة عنصر لإشعار التسليم"""
        if self.status not in [DeliveryStatus.DRAFT, DeliveryStatus.SCHEDULED]:
            raise ValueError(f"Cannot add items to delivery in status {self.status.value}")
        
        # التحقق من أن الكمية المسلمة لا تتجاوز الكمية المطلوبة
        if item.delivered_quantity > item.quantity:
            raise ValueError("لا يمكن تسليم كمية أكبر من المطلوبة")
        
        self.items.append(item)
    
    def remove_item(self, line_id: str) -> None:
        """إزالة عنصر من إشعار التسليم"""
        if self.status not in [DeliveryStatus.DRAFT, DeliveryStatus.SCHEDULED]:
            raise ValueError(f"Cannot remove items from delivery in status {self.status.value}")
        self.items = [item for item in self.items if item.line_id != line_id]
    
    def schedule(self, scheduled_date: datetime) -> None:
        """جدولة التسليم"""
        if self.status != DeliveryStatus.DRAFT:
            raise ValueError("Only draft deliveries can be scheduled")
        
        self.status = DeliveryStatus.SCHEDULED
        self.scheduled_date = scheduled_date
        self.updated_at = utc_now()
    
    def start_transit(self) -> None:
        """بدء النقل"""
        if self.status != DeliveryStatus.SCHEDULED:
            raise ValueError("Only scheduled deliveries can start transit")
        
        self.status = DeliveryStatus.IN_TRANSIT
        self.updated_at = utc_now()
    
    def mark_delivered(self, received_by: Optional[str] = None) -> None:
        """وضع علامة كـ تم التسليم"""
        if self.status != DeliveryStatus.IN_TRANSIT:
            raise ValueError("Only in-transit deliveries can be marked as delivered")
        
        self.status = DeliveryStatus.DELIVERED
        self.actual_delivery_date = utc_now()
        self.received_by = received_by
        self.received_at = utc_now()
        self.updated_at = utc_now()
    
    def mark_returned(self, reason: str) -> None:
        """وضع علامة كـ تم الإرجاع"""
        if self.status not in [DeliveryStatus.IN_TRANSIT, DeliveryStatus.DELIVERED]:
            raise ValueError("Only in-transit or delivered deliveries can be returned")
        
        self.status = DeliveryStatus.RETURNED
        self.return_reason = reason
        self.updated_at = utc_now()
    
    def cancel(self) -> None:
        """إلغاء إشعار التسليم"""
        if self.status in [DeliveryStatus.DELIVERED, DeliveryStatus.RETURNED, DeliveryStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel delivery in status {self.status.value}")
        
        self.status = DeliveryStatus.CANCELLED
        self.updated_at = utc_now()
    
    @property
    def item_count(self) -> int:
        return len(self.items)
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل إلى قاموس"""
        return {
            'id': str(self.id.value),
            'delivery_number': str(self.delivery_number.value),
            'order_id': self.order_id,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'status': self.status.value,
            'delivery_date': self.delivery_date.isoformat(),
            'scheduled_date': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'item_count': self.item_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }
