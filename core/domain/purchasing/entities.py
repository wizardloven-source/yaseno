# core/domain/purchasing/entities.py
"""
Purchasing Entities - كيانات المشتريات
✅ محدث: دعم متكامل للمخزون (StockMovement)
✅ محدث: دعم Batch/Lot Tracking
✅ محدث: دعم Serial Numbers
✅ محدث: دمج مع محرك المخزون الجديد
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
import uuid

from ..shared.value_objects import Money, AccountCode
from .value_objects import (
    PurchaseOrderId, PurchaseOrderNumber, PurchaseOrderStatus, PaymentTerms,
    PurchaseReturnId, PurchaseReturnNumber, PurchaseReturnStatus,
    DebitNoteId, DebitNoteNumber, DebitNoteStatus
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PurchaseLine:
    """
    سطر في أمر الشراء - محدث لدعم المخزون المتقدم
    
    ✅ يدعم Batch/Lot Tracking
    ✅ يدعم Serial Numbers
    ✅ يدعم Expiry Dates
    ✅ يدعم مواقع التخزين
    """
    
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Money
    notes: str = ""
    line_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    received_quantity: Decimal = Decimal('0')
    
    # ========== ✅ حقول المخزون الجديدة ==========
    batch_number: Optional[str] = None
    serial_numbers: List[str] = field(default_factory=list)
    expiry_date: Optional[datetime] = None
    location: Optional[str] = None  # موقع التخزين (مستودع - رف - صندوق)
    
    # تكلفة الوحدة عند الاستلام (تُستخدم لحساب المخزون)
    unit_cost: Money = field(init=False)
    
    def __post_init__(self):
        """تعيين unit_cost نفس unit_price عند الإنشاء"""
        if not hasattr(self, 'unit_cost') or self.unit_cost is None:
            object.__setattr__(self, 'unit_cost', self.unit_price)
    
    @property
    def total(self) -> Money:
        """الإجمالي = الكمية × سعر الوحدة"""
        return Money(self.quantity * self.unit_price.amount, self.unit_price.currency)
    
    @property
    def total_cost(self) -> Money:
        """التكلفة الإجمالية = الكمية × تكلفة الوحدة"""
        return Money(self.quantity * self.unit_cost.amount, self.unit_cost.currency)
    
    @property
    def is_fully_received(self) -> bool:
        return self.received_quantity >= self.quantity
    
    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.received_quantity
    
    @property
    def inventory_account(self) -> AccountCode:
        """الحساب المحاسبي للمخزون"""
        return AccountCode("1030")  # حساب المخزون
    
    @property
    def currency(self) -> str:
        return self.unit_price.currency
    
    @property
    def has_batch(self) -> bool:
        """هل يحتوي السطر على رقم دفعة؟"""
        return bool(self.batch_number)
    
    @property
    def has_serial_numbers(self) -> bool:
        """هل يحتوي السطر على أرقام تسلسلية؟"""
        return len(self.serial_numbers) > 0
    
    @property
    def has_expiry(self) -> bool:
        """هل يحتوي السطر على تاريخ انتهاء؟"""
        return self.expiry_date is not None
    
    @property
    def received_cost(self) -> Money:
        """تكلفة الكمية المستلمة"""
        return Money(
            self.received_quantity * self.unit_cost.amount,
            self.unit_cost.currency
        )
    
    def mark_as_received(
        self, 
        quantity: Decimal, 
        batch_number: Optional[str] = None,
        serial_numbers: Optional[List[str]] = None,
        expiry_date: Optional[datetime] = None,
        location: Optional[str] = None
    ) -> None:
        """
        تسجيل استلام كمية من السطر مع تفاصيل المخزون
        
        Args:
            quantity: الكمية المستلمة
            batch_number: رقم الدفعة (اختياري)
            serial_numbers: الأرقام التسلسلية (اختياري)
            expiry_date: تاريخ الانتهاء (اختياري)
            location: موقع التخزين (اختياري)
        """
        if quantity <= 0:
            raise ValueError("Received quantity must be greater than zero")
        
        if self.received_quantity + quantity > self.quantity:
            raise ValueError(
                f"Cannot receive more than ordered quantity. "
                f"Ordered: {self.quantity}, Already received: {self.received_quantity}"
            )
        
        # تحديث الكمية المستلمة
        self.received_quantity += quantity
        
        # تحديث تفاصيل المخزون (إذا تم توفيرها)
        if batch_number:
            self.batch_number = batch_number
        if serial_numbers:
            self.serial_numbers.extend(serial_numbers)
        if expiry_date:
            self.expiry_date = expiry_date
        if location:
            self.location = location
    
    def to_dict(self) -> dict:
        """تحويل السطر إلى قاموس"""
        return {
            'line_id': self.line_id,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'quantity': float(self.quantity),
            'received_quantity': float(self.received_quantity),
            'unit_price': float(self.unit_price.amount),
            'unit_cost': float(self.unit_cost.amount),
            'currency': self.currency,
            'total': float(self.total.amount),
            'total_cost': float(self.total_cost.amount),
            'batch_number': self.batch_number,
            'serial_numbers': self.serial_numbers,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'location': self.location,
            'notes': self.notes,
        }


@dataclass
class PurchaseOrder:
    """
    AGGREGATE ROOT - أمر الشراء
    كل أمر شراء يولد قيداً محاسبياً عند ترحيله (زيادة المخزون وزيادة الدائنون)
    
    ✅ محدث: دعم إنشاء حركات مخزون عند الاستلام
    ✅ محدث: دعم استلام جزئي وكامل
    ✅ محدث: ربط مع محرك المخزون الجديد
    
    ملاحظة: الـ version هو للتحكم في التزامن (Optimistic Locking)
    يتم إدارته فقط بواسطة الـ Repository ولا يتم تعديله داخل الـ Entity
    """
    
    id: PurchaseOrderId = field(default_factory=PurchaseOrderId.generate)
    number: Optional[PurchaseOrderNumber] = None
    date: datetime = field(default_factory=utc_now)
    expected_delivery_date: Optional[datetime] = None
    
    supplier_id: str = ""
    supplier_name: str = ""
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    
    currency: str = "USD"
    payment_terms: PaymentTerms = PaymentTerms.NET_30
    notes: str = ""
    
    lines: List[PurchaseLine] = field(default_factory=list)
    
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    journal_entry_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None
    received_at: Optional[datetime] = None
    received_by: Optional[str] = None
    
    # ✅ سجل حركات المخزون المرتبطة
    stock_movement_ids: List[str] = field(default_factory=list)
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # التحكم في التزامن (تتم إدارته فقط بواسطة Repository)
    version: int = 1
    
    @property
    def subtotal(self) -> Money:
        total = Decimal('0')
        for line in self.lines:
            total += line.total.amount
        return Money(total, self.currency)
    
    @property
    def total(self) -> Money:
        return self.subtotal
    
    @property
    def is_posted(self) -> bool:
        return self.status == PurchaseOrderStatus.POSTED
    
    @property
    def is_draft(self) -> bool:
        return self.status == PurchaseOrderStatus.DRAFT
    
    @property
    def is_fully_received(self) -> bool:
        if not self.lines:
            return False
        return all(line.is_fully_received for line in self.lines)
    
    @property
    def total_received_quantity(self) -> Decimal:
        """إجمالي الكميات المستلمة"""
        return sum(line.received_quantity for line in self.lines)
    
    @property
    def total_ordered_quantity(self) -> Decimal:
        """إجمالي الكميات المطلوبة"""
        return sum(line.quantity for line in self.lines)
    
    @property
    def received_percentage(self) -> Decimal:
        """نسبة الاستلام"""
        if self.total_ordered_quantity == 0:
            return Decimal('0')
        return (self.total_received_quantity / self.total_ordered_quantity) * 100
    
    def add_line(self, line: PurchaseLine) -> None:
        """إضافة سطر إلى أمر الشراء"""
        if self.is_posted:
            from .exceptions import CannotModifyPostedPurchaseOrderError
            raise CannotModifyPostedPurchaseOrderError(str(self.id))
        
        if line.quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        
        self.lines.append(line)
    
    def remove_line(self, line_id: str) -> bool:
        """حذف سطر من أمر الشراء"""
        if self.is_posted:
            from .exceptions import CannotModifyPostedPurchaseOrderError
            raise CannotModifyPostedPurchaseOrderError(str(self.id))
        
        for i, line in enumerate(self.lines):
            if line.line_id == line_id:
                self.lines.pop(i)
                return True
        return False
    
    def clear_lines(self) -> None:
        """مسح جميع البنود"""
        if self.is_posted:
            from .exceptions import CannotModifyPostedPurchaseOrderError
            raise CannotModifyPostedPurchaseOrderError(str(self.id))
        self.lines.clear()
    
    def update_line(self, line_id: str, quantity: Decimal, unit_price: Money, notes: str = "") -> None:
        """تحديث سطر موجود"""
        if self.is_posted:
            from .exceptions import CannotModifyPostedPurchaseOrderError
            raise CannotModifyPostedPurchaseOrderError(str(self.id))
        
        for line in self.lines:
            if line.line_id == line_id:
                line.quantity = quantity
                line.unit_price = unit_price
                line.notes = notes
                return
        
        raise ValueError(f"Line {line_id} not found")
    
    def post(self, posted_by: str, journal_entry_id: str) -> None:
        """ترحيل أمر الشراء"""
        if self.is_posted:
            from .exceptions import PurchaseOrderAlreadyPostedError
            raise PurchaseOrderAlreadyPostedError(str(self.id))
        
        if len(self.lines) == 0:
            raise ValueError("Cannot post purchase order with no lines")
        
        self.status = PurchaseOrderStatus.POSTED
        self.posted_at = utc_now()
        self.posted_by = posted_by
        self.journal_entry_id = journal_entry_id
        
        from .events import PurchaseOrderPostedEvent
        self._events.append(PurchaseOrderPostedEvent(
            order_id=self.id,
            order_number=str(self.number) if self.number else None,
            journal_entry_id=journal_entry_id,
            total_amount=self.total,
            supplier_id=self.supplier_id,
            posted_by=posted_by
        ))
    
    def receive_line(
        self, 
        line_id: str, 
        quantity: Decimal, 
        received_by: str,
        batch_number: Optional[str] = None,
        serial_numbers: Optional[List[str]] = None,
        expiry_date: Optional[datetime] = None,
        location: Optional[str] = None
    ) -> PurchaseLine:
        """
        استلام جزء أو كل البضاعة من أمر الشراء مع تفاصيل المخزون
        
        ✅ محدث: يدعم Batch/Lot Tracking
        ✅ محدث: يدعم Serial Numbers
        ✅ محدث: يدعم Expiry Dates
        ✅ محدث: يدعم مواقع التخزين
        
        Args:
            line_id: معرف السطر
            quantity: الكمية المستلمة
            received_by: من قام بالاستلام
            batch_number: رقم الدفعة (اختياري)
            serial_numbers: الأرقام التسلسلية (اختياري)
            expiry_date: تاريخ الانتهاء (اختياري)
            location: موقع التخزين (اختياري)
        
        Returns:
            PurchaseLine: السطر المحدث
        
        Raises:
            CannotReceiveUnpostedPurchaseOrderError: إذا لم يكن الأمر مرحلاً
            ValueError: إذا كانت الكمية غير صالحة
        """
        if not self.is_posted:
            from .exceptions import CannotReceiveUnpostedPurchaseOrderError
            raise CannotReceiveUnpostedPurchaseOrderError(str(self.id))
        
        for line in self.lines:
            if line.line_id == line_id:
                line.mark_as_received(
                    quantity=quantity,
                    batch_number=batch_number,
                    serial_numbers=serial_numbers,
                    expiry_date=expiry_date,
                    location=location
                )
                
                # بث حدث الاستلام
                from .events import PurchaseOrderReceivedEvent
                self._events.append(PurchaseOrderReceivedEvent(
                    order_id=self.id,
                    line_id=line_id,
                    product_code=line.product_code,
                    quantity=quantity,
                    received_by=received_by,
                    batch_number=batch_number,
                    serial_numbers=serial_numbers,
                    expiry_date=expiry_date,
                    location=location
                ))
                
                # تحديث حالة الأمر إذا تم استلام الكل
                if self.is_fully_received:
                    self.status = PurchaseOrderStatus.FULLY_RECEIVED
                    self.received_at = utc_now()
                    self.received_by = received_by
                elif self.total_received_quantity > 0:
                    self.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
                
                return line
        
        raise ValueError(f"Line {line_id} not found")
    
    def receive_all(
        self,
        received_by: str,
        batch_numbers: Optional[Dict[str, str]] = None,
        serial_numbers: Optional[Dict[str, List[str]]] = None,
        expiry_dates: Optional[Dict[str, datetime]] = None,
        locations: Optional[Dict[str, str]] = None
    ) -> List[PurchaseLine]:
        """
        استلام جميع البضاعة دفعة واحدة
        
        ✅ محدث: دعم تفاصيل المخزون لكل سطر
        
        Args:
            received_by: من قام بالاستلام
            batch_numbers: قاموس {line_id: batch_number}
            serial_numbers: قاموس {line_id: [serial_numbers]}
            expiry_dates: قاموس {line_id: expiry_date}
            locations: قاموس {line_id: location}
        
        Returns:
            List[PurchaseLine]: الأسطر المحدثة
        """
        received_lines = []
        
        for line in self.lines:
            if line.is_fully_received:
                continue
            
            remaining = line.remaining_quantity
            
            received_line = self.receive_line(
                line_id=line.line_id,
                quantity=remaining,
                received_by=received_by,
                batch_number=batch_numbers.get(line.line_id) if batch_numbers else None,
                serial_numbers=serial_numbers.get(line.line_id) if serial_numbers else None,
                expiry_date=expiry_dates.get(line.line_id) if expiry_dates else None,
                location=locations.get(line.line_id) if locations else None
            )
            received_lines.append(received_line)
        
        return received_lines
    
    def to_journal_entry_lines(self) -> List[tuple]:
        """
        تحويل أمر الشراء إلى أسطر قيد محاسبي
        Returns: List of (account_code, debit, credit, currency)
        """
        lines = []
        
        # سطر المدين: حساب المخزون (باستخدام التكلفة الفعلية)
        for line in self.lines:
            lines.append((
                line.inventory_account,
                line.total.amount,
                Decimal('0'),
                line.currency
            ))
        
        # سطر الدائن: حساب الدائنون
        lines.append((
            AccountCode("2010"),  # الدائنون
            Decimal('0'),
            self.total.amount,
            self.currency
        ))
        
        return lines
    
    def generate_journal_entry_description(self) -> str:
        return f"PURCHASE ORDER {self.number or 'DRAFT'} - Supplier: {self.supplier_name} ({len(self.lines)} items)"
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events
    
    def add_stock_movement(self, movement_id: str) -> None:
        """إضافة معرف حركة مخزون إلى سجل الأمر"""
        if movement_id not in self.stock_movement_ids:
            self.stock_movement_ids.append(movement_id)
    
    def to_dict(self) -> dict:
        """تحويل الأمر إلى قاموس"""
        return {
            'id': str(self.id),
            'number': str(self.number) if self.number else None,
            'date': self.date.isoformat() if self.date else None,
            'expected_delivery_date': self.expected_delivery_date.isoformat() if self.expected_delivery_date else None,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier_name,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'currency': self.currency,
            'payment_terms': self.payment_terms.value,
            'status': self.status.value,
            'subtotal': float(self.subtotal.amount),
            'total': float(self.total.amount),
            'total_received_quantity': float(self.total_received_quantity),
            'received_percentage': float(self.received_percentage),
            'is_fully_received': self.is_fully_received,
            'journal_entry_id': self.journal_entry_id,
            'stock_movement_ids': self.stock_movement_ids,
            'notes': self.notes,
            'lines': [line.to_dict() for line in self.lines],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'posted_by': self.posted_by,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'received_by': self.received_by,
            'version': self.version
        }


# ========== ✅ Purchase Return Entities ==========

@dataclass
class PurchaseReturnItem:
    """
    سطر في إرجاع المشتريات
    
    Args:
        product_code: رمز المنتج
        product_name: اسم المنتج
        quantity: الكمية المُرجعة
        unit_price: سعر الوحدة
        reason: سبب الإرجاع (تالف، خطأ في الطلب، منتهي الصلاحية، إلخ)
        condition: حالة المنتج (good/damaged/expired)
        batch_number: رقم الدفعة (إذا وجد)
        serial_numbers: الأرقام التسلسلية (إذا وجد)
        discount_percent: نسبة الخصم
        discount_amount: قيمة الخصم
        tax_rate: نسبة الضريبة
        tax_amount: قيمة الضريبة
    """
    
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Money
    reason: str = ""
    condition: str = "good"  # good, damaged, expired
    batch_number: Optional[str] = None
    serial_numbers: List[str] = field(default_factory=list)
    discount_percent: Decimal = Decimal('0')
    discount_amount: Money = field(default_factory=lambda: Money(Decimal('0'), "USD"))
    tax_rate: Decimal = Decimal('0')
    tax_amount: Money = field(default_factory=lambda: Money(Decimal('0'), "USD"))
    line_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    @property
    def subtotal(self) -> Money:
        """المجموع الفرعي قبل الخصم والضريبة"""
        return Money(self.quantity * self.unit_price.amount, self.unit_price.currency)
    
    @property
    def total_discount(self) -> Money:
        """إجمالي الخصم"""
        if self.discount_percent > 0:
            return Money(self.subtotal.amount * (self.discount_percent / Decimal('100')), self.unit_price.currency)
        return self.discount_amount
    
    @property
    def total_after_discount(self) -> Money:
        """الإجمالي بعد الخصم"""
        return Money(self.subtotal.amount - self.total_discount.amount, self.unit_price.currency)
    
    @property
    def total_with_tax(self) -> Money:
        """الإجمالي مع الضريبة"""
        return Money(
            self.total_after_discount.amount + self.tax_amount.amount,
            self.unit_price.currency
        )
    
    def to_dict(self) -> dict:
        """تحويل السطر إلى قاموس"""
        return {
            'line_id': self.line_id,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price.amount),
            'reason': self.reason,
            'condition': self.condition,
            'batch_number': self.batch_number,
            'serial_numbers': self.serial_numbers,
            'discount_percent': float(self.discount_percent),
            'discount_amount': float(self.discount_amount.amount),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount.amount),
            'subtotal': float(self.subtotal.amount),
            'total_discount': float(self.total_discount.amount),
            'total_after_discount': float(self.total_after_discount.amount),
            'total_with_tax': float(self.total_with_tax.amount),
            'currency': self.unit_price.currency
        }


@dataclass
class PurchaseReturn:
    """
    AGGREGATE ROOT - إرجاع مشتريات
    
    دورة الحياة:
    DRAFT → SUBMITTED → APPROVED → SHIPPED → RECEIVED_BY_SUPPLIER → COMPLETED
                                    ↓
                                REJECTED/CANCELLED
    
    Args:
        id: المعرف الفريد
        number: رقم الإرجاع
        date: تاريخ الإرجاع
        purchase_order_id: معرف أمر الشراء الأصلي
        purchase_order_number: رقم أمر الشراء الأصلي
        supplier_id: معرف المورد
        supplier_name: اسم المورد
        currency: العملة
        lines: أسطر الإرجاع
        status: حالة الإرجاع
        debit_note_id: معرف مذكرة المدين المرتبطة
        notes: ملاحظات
        created_at: تاريخ الإنشاء
        created_by: أنشأ بواسطة
        submitted_at: تاريخ التقديم
        submitted_by: قُدم بواسطة
        approved_at: تاريخ الموافقة
        approved_by: ووفِق بواسطة
        shipped_at: تاريخ الشحن
        shipped_by: شُحن بواسطة
        received_at: تاريخ الاستلام من المورد
        completed_at: تاريخ الإكمال
        rejected_at: تاريخ الرفض
        cancelled_at: تاريخ الإلغاء
        reason: سبب الإرجاع العام
        warehouse_id: معرف المستودع
        shipping_method: طريقة الشحن
        tracking_number: رقم التتبع
    """
    
    id: PurchaseReturnId = field(default_factory=PurchaseReturnId.generate)
    number: Optional[PurchaseReturnNumber] = None
    date: datetime = field(default_factory=utc_now)
    
    purchase_order_id: Optional[str] = None
    purchase_order_number: Optional[str] = None
    supplier_id: str = ""
    supplier_name: str = ""
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    
    currency: str = "USD"
    lines: List[PurchaseReturnItem] = field(default_factory=list)
    
    status: PurchaseReturnStatus = PurchaseReturnStatus.DRAFT
    debit_note_id: Optional[str] = None
    
    notes: str = ""
    reason: str = ""
    warehouse_id: Optional[str] = None
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    shipped_at: Optional[datetime] = None
    shipped_by: Optional[str] = None
    received_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    _events: List[Any] = field(default_factory=list, repr=False)
    version: int = 1
    
    @property
    def subtotal(self) -> Money:
        """المجموع الفرعي للإرجاع"""
        total = sum(line.subtotal.amount for line in self.lines)
        return Money(total, self.currency)
    
    @property
    def total_discount(self) -> Money:
        """إجمالي الخصم"""
        total = sum(line.total_discount.amount for line in self.lines)
        return Money(total, self.currency)
    
    @property
    def total_after_discount(self) -> Money:
        """الإجمالي بعد الخصم"""
        total = sum(line.total_after_discount.amount for line in self.lines)
        return Money(total, self.currency)
    
    @property
    def total_tax(self) -> Money:
        """إجمالي الضريبة"""
        total = sum(line.tax_amount.amount for line in self.lines)
        return Money(total, self.currency)
    
    @property
    def total_amount(self) -> Money:
        """إجمالي مبلغ الإرجاع"""
        total = sum(line.total_with_tax.amount for line in self.lines)
        return Money(total, self.currency)
    
    @property
    def is_completed(self) -> bool:
        """هل اكتمل الإرجاع؟"""
        return self.status == PurchaseReturnStatus.COMPLETED
    
    @property
    def is_cancelled(self) -> bool:
        """هل أُلغي الإرجاع؟"""
        return self.status == PurchaseReturnStatus.CANCELLED
    
    @property
    def is_rejected(self) -> bool:
        """هل رُفض الإرجاع؟"""
        return self.status == PurchaseReturnStatus.REJECTED
    
    @property
    def can_submit(self) -> bool:
        """هل يمكن تقديم الإرجاع؟"""
        return self.status == PurchaseReturnStatus.DRAFT and len(self.lines) > 0
    
    @property
    def can_approve(self) -> bool:
        """هل يمكن الموافقة على الإرجاع؟"""
        return self.status == PurchaseReturnStatus.SUBMITTED
    
    @property
    def can_ship(self) -> bool:
        """هل يمكن شحن الإرجاع؟"""
        return self.status == PurchaseReturnStatus.APPROVED
    
    @property
    def can_complete(self) -> bool:
        """هل يمكن إكمال الإرجاع؟"""
        return self.status == PurchaseReturnStatus.RECEIVED_BY_SUPPLIER
    
    def add_line(self, line: PurchaseReturnItem) -> None:
        """إضافة سطر إرجاع"""
        if self.status != PurchaseReturnStatus.DRAFT:
            raise CannotModifyCompletedReturnError(str(self.id))
        
        if line.quantity <= 0:
            raise ValueError("Return quantity must be greater than zero")
        
        self.lines.append(line)
    
    def remove_line(self, line_id: str) -> bool:
        """حذف سطر إرجاع"""
        if self.status != PurchaseReturnStatus.DRAFT:
            raise CannotModifyCompletedReturnError(str(self.id))
        
        for i, line in enumerate(self.lines):
            if line.line_id == line_id:
                self.lines.pop(i)
                return True
        return False
    
    def submit(self, submitted_by: str) -> None:
        """تقديم الإرجاع للموافقة"""
        if not self.can_submit:
            raise InvalidPurchaseReturnStatusError(
                str(self.id), 
                self.status.value, 
                "submit"
            )
        
        self.status = PurchaseReturnStatus.SUBMITTED
        self.submitted_at = utc_now()
        self.submitted_by = submitted_by
        
        from .events import PurchaseReturnSubmittedEvent
        self._events.append(PurchaseReturnSubmittedEvent(
            return_id=self.id,
            return_number=str(self.number) if self.number else None,
            submitted_by=submitted_by
        ))
    
    def approve(self, approved_by: str) -> None:
        """الموافقة على الإرجاع"""
        if not self.can_approve:
            raise InvalidPurchaseReturnStatusError(
                str(self.id),
                self.status.value,
                "approve"
            )
        
        self.status = PurchaseReturnStatus.APPROVED
        self.approved_at = utc_now()
        self.approved_by = approved_by
        
        from .events import PurchaseReturnApprovedEvent
        self._events.append(PurchaseReturnApprovedEvent(
            return_id=self.id,
            return_number=str(self.number) if self.number else None,
            approved_by=approved_by
        ))
    
    def ship(self, shipped_by: str, tracking_number: Optional[str] = None) -> None:
        """شحن الإرجاع للمورد"""
        if not self.can_ship:
            raise InvalidPurchaseReturnStatusError(
                str(self.id),
                self.status.value,
                "ship"
            )
        
        self.status = PurchaseReturnStatus.SHIPPED
        self.shipped_at = utc_now()
        self.shipped_by = shipped_by
        if tracking_number:
            self.tracking_number = tracking_number
        
        from .events import PurchaseReturnShippedEvent
        self._events.append(PurchaseReturnShippedEvent(
            return_id=self.id,
            return_number=str(self.number) if self.number else None,
            shipped_by=shipped_by,
            tracking_number=tracking_number
        ))
    
    def receive_by_supplier(self, received_at: Optional[datetime] = None) -> None:
        """تأكيد استلام المورد للإرجاع"""
        if self.status not in [PurchaseReturnStatus.SHIPPED, PurchaseReturnStatus.APPROVED]:
            raise InvalidPurchaseReturnStatusError(
                str(self.id),
                self.status.value,
                "receive_by_supplier"
            )
        
        self.status = PurchaseReturnStatus.RECEIVED_BY_SUPPLIER
        self.received_at = received_at or utc_now()
        
        from .events import PurchaseReturnReceivedBySupplierEvent
        self._events.append(PurchaseReturnReceivedBySupplierEvent(
            return_id=self.id,
            return_number=str(self.number) if self.number else None,
            received_at=self.received_at
        ))
    
    def complete(self, debit_note_id: str) -> None:
        """
        إكمال الإرجاع وإنشاء مذكرة مدين
        
        Args:
            debit_note_id: معرف مذكرة المدين المنشأة
        """
        if not self.can_complete:
            raise InvalidPurchaseReturnStatusError(
                str(self.id),
                self.status.value,
                "complete"
            )
        
        self.status = PurchaseReturnStatus.COMPLETED
        self.completed_at = utc_now()
        self.debit_note_id = debit_note_id
        
        from .events import PurchaseReturnCompletedEvent
        self._events.append(PurchaseReturnCompletedEvent(
            return_id=self.id,
            return_number=str(self.number) if self.number else None,
            debit_note_id=debit_note_id,
            total_amount=self.total_amount
        ))
    
    def reject(self, reason: str, rejected_by: str) -> None:
        """رفض الإرجاع"""
        if self.status not in [PurchaseReturnStatus.SUBMITTED, PurchaseReturnStatus.APPROVED]:
            raise InvalidPurchaseReturnStatusError(
                str(self.id),
                self.status.value,
                "reject"
            )
        
        self.status = PurchaseReturnStatus.REJECTED
        self.rejected_at = utc_now()
        self.reason = reason
        
        from .events import PurchaseReturnRejectedEvent
        self._events.append(PurchaseReturnRejectedEvent(
            return_id=self.id,
            return_number=str(self.number) if self.number else None,
            reason=reason,
            rejected_by=rejected_by
        ))
    
    def cancel(self, reason: str) -> None:
        """إلغاء الإرجاع"""
        if self.status in [PurchaseReturnStatus.COMPLETED, PurchaseReturnStatus.REJECTED]:
            raise InvalidPurchaseReturnStatusError(
                str(self.id),
                self.status.value,
                "cancel"
            )
        
        self.status = PurchaseReturnStatus.CANCELLED
        self.cancelled_at = utc_now()
        self.reason = reason
        
        from .events import PurchaseReturnCancelledEvent
        self._events.append(PurchaseReturnCancelledEvent(
            return_id=self.id,
            return_number=str(self.number) if self.number else None,
            reason=reason
        ))
    
    def to_dict(self) -> dict:
        """تحويل الإرجاع إلى قاموس"""
        return {
            'id': str(self.id),
            'number': str(self.number) if self.number else None,
            'date': self.date.isoformat() if self.date else None,
            'purchase_order_id': self.purchase_order_id,
            'purchase_order_number': self.purchase_order_number,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier_name,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'currency': self.currency,
            'status': self.status.value,
            'debit_note_id': self.debit_note_id,
            'subtotal': float(self.subtotal.amount),
            'total_discount': float(self.total_discount.amount),
            'total_after_discount': float(self.total_after_discount.amount),
            'total_tax': float(self.total_tax.amount),
            'total_amount': float(self.total_amount.amount),
            'notes': self.notes,
            'reason': self.reason,
            'warehouse_id': self.warehouse_id,
            'shipping_method': self.shipping_method,
            'tracking_number': self.tracking_number,
            'lines': [line.to_dict() for line in self.lines],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'submitted_by': self.submitted_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by,
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'shipped_by': self.shipped_by,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'rejected_at': self.rejected_at.isoformat() if self.rejected_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'version': self.version
        }