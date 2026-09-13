# core/application/sales/commands.py
"""
Sales Commands - أوامر CQRS لوحدة المبيعات
✅ SalesQuotation Commands
✅ SalesOrder Commands
✅ Delivery Commands
✅ SalesReturn Commands (NEW - PHASE 1)
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any


@dataclass
class QuotationItemCommand:
    """عنصر في أمر إنشاء/تحديث عرض السعر"""
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price_amount: Decimal
    currency: str = "SAR"
    discount_percent: Decimal = Decimal('0')
    tax_rate: Decimal = Decimal('0')
    notes: str = ""


@dataclass
class CreateQuotationCommand:
    """إنشاء عرض سعر جديد"""
    customer_id: str
    customer_name: str
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    
    currency: str = "SAR"
    valid_days: int = 30
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    
    items: List[QuotationItemCommand] = field(default_factory=list)
    
    global_discount_percent: Decimal = Decimal('0')
    global_discount_amount: Decimal = Decimal('0')
    
    notes: str = ""
    internal_notes: str = ""
    
    shipping_address_street: Optional[str] = None
    shipping_address_city: Optional[str] = None
    shipping_address_state: Optional[str] = None
    shipping_address_postal_code: Optional[str] = None
    shipping_address_country: Optional[str] = "SA"
    
    payment_terms_days: int = 0
    
    sequence: Optional[int] = None


@dataclass
class UpdateQuotationCommand:
    """تحديث عرض سعر موجود"""
    quotation_id: str
    
    customer_name: Optional[str] = None
    customer_branch_name: Optional[str] = None
    
    items: Optional[List[QuotationItemCommand]] = None
    
    global_discount_percent: Optional[Decimal] = None
    global_discount_amount: Optional[Decimal] = None
    
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    shipping_address_street: Optional[str] = None
    shipping_address_city: Optional[str] = None
    shipping_address_state: Optional[str] = None
    shipping_address_postal_code: Optional[str] = None
    shipping_address_country: Optional[str] = None
    
    payment_terms_days: Optional[int] = None


@dataclass
class SendQuotationCommand:
    """إرسال عرض سعر للعميل"""
    quotation_id: str
    sent_by: str = ""


@dataclass
class AcceptQuotationCommand:
    """قبول عرض سعر"""
    quotation_id: str


@dataclass
class RejectQuotationCommand:
    """رفض عرض سعر"""
    quotation_id: str
    reason: str = ""


@dataclass
class ConvertQuotationCommand:
    """تحويل عرض سعر إلى أمر بيع"""
    quotation_id: str


# ============================================================================
# Sales Order Commands
# ============================================================================

@dataclass
class OrderItemCommand:
    """عنصر في أمر إنشاء أمر بيع"""
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price_amount: Decimal
    currency: str = "SAR"
    discount_percent: Decimal = Decimal('0')
    tax_rate: Decimal = Decimal('0')
    notes: str = ""
    warehouse_id: Optional[str] = None


@dataclass
class CreateOrderCommand:
    """إنشاء أمر بيع جديد"""
    customer_id: str
    customer_name: str
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    
    currency: str = "SAR"
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    
    items: List[OrderItemCommand] = field(default_factory=list)
    
    global_discount_percent: Decimal = Decimal('0')
    global_discount_amount: Decimal = Decimal('0')
    
    notes: str = ""
    internal_notes: str = ""
    
    shipping_address_street: Optional[str] = None
    shipping_address_city: Optional[str] = None
    shipping_address_state: Optional[str] = None
    shipping_address_postal_code: Optional[str] = None
    shipping_address_country: Optional[str] = "SA"
    
    required_date: Optional[datetime] = None
    payment_terms_days: int = 0
    
    source_quotation_id: Optional[str] = None
    sequence: Optional[int] = None


@dataclass
class ConfirmOrderCommand:
    """تأكيد أمر بيع"""
    order_id: str


@dataclass
class CancelOrderCommand:
    """إلغاء أمر بيع"""
    order_id: str
    reason: str = ""


@dataclass
class ShipOrderCommand:
    """شحن أمر بيع"""
    order_id: str
    tracking_number: Optional[str] = None


@dataclass
class DeliverOrderCommand:
    """تسليم أمر بيع"""
    order_id: str
    received_by: Optional[str] = None


# ============================================================================
# Delivery Commands
# ============================================================================

@dataclass
class DeliveryItemCommand:
    """عنصر في أمر إنشاء إشعار تسليم"""
    product_code: str
    product_name: str
    quantity: Decimal
    order_item_line_id: Optional[str] = None


@dataclass
class CreateDeliveryCommand:
    """إنشاء إشعار تسليم جديد"""
    customer_id: str
    customer_name: str
    order_id: Optional[str] = None
    order_number: Optional[str] = None
    
    items: List[DeliveryItemCommand] = field(default_factory=list)
    
    shipping_address_street: Optional[str] = None
    shipping_address_city: Optional[str] = None
    shipping_address_state: Optional[str] = None
    shipping_address_postal_code: Optional[str] = None
    shipping_address_country: Optional[str] = "SA"
    
    carrier: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    
    notes: str = ""
    
    scheduled_date: Optional[datetime] = None
    sequence: Optional[int] = None


@dataclass
class ScheduleDeliveryCommand:
    """جدولة إشعار تسليم"""
    delivery_id: str
    scheduled_date: datetime


@dataclass
class StartTransitDeliveryCommand:
    """بدء نقل إشعار التسليم"""
    delivery_id: str


@dataclass
class CompleteDeliveryCommand:
    """إكمال إشعار التسليم"""
    delivery_id: str
    received_by: Optional[str] = None


@dataclass
class ReturnDeliveryCommand:
    """إرجاع إشعار التسليم"""
    delivery_id: str
    reason: str


# ============================================================================
# Sales Return Commands (NEW - PHASE 1)
# ============================================================================

@dataclass
class ReturnItemCommand:
    """عنصر في أمر إرجاع مبيعات"""
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price_amount: Decimal
    currency: str = "SAR"
    reason: str = ""  # سبب الإرجاع
    condition: str = "good"  # good, damaged, expired
    discount_percent: Decimal = Decimal('0')
    tax_rate: Decimal = Decimal('0')


@dataclass
class CreateSalesReturnCommand:
    """إنشاء إرجاع مبيعات جديد"""
    customer_id: str
    customer_name: str
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    
    original_invoice_id: Optional[str] = None
    original_invoice_number: Optional[str] = None
    original_delivery_id: Optional[str] = None
    
    currency: str = "SAR"
    warehouse_id: str = "MAIN"
    
    items: List[ReturnItemCommand] = field(default_factory=list)
    
    document_discount_percent: Decimal = Decimal('0')
    document_discount_amount: Decimal = Decimal('0')
    document_tax_rate: Decimal = Decimal('0')
    
    notes: str = ""
    internal_notes: str = ""
    
    payment_terms_days: int = 0
    
    sequence: Optional[int] = None


@dataclass
class SubmitSalesReturnCommand:
    """تقديم إرجاع المبيعات للموافقة"""
    return_id: str
    submitted_by: str


@dataclass
class ApproveSalesReturnCommand:
    """الموافقة على إرجاع المبيعات"""
    return_id: str
    approved_by: str


@dataclass
class RejectSalesReturnCommand:
    """رفض إرجاع المبيعات"""
    return_id: str
    rejected_by: str
    reason: str


@dataclass
class ReceiveSalesReturnCommand:
    """استلام إرجاع المبيعات"""
    return_id: str
    received_by: str
    actual_receive_date: Optional[datetime] = None


@dataclass
class InspectSalesReturnCommand:
    """فحص إرجاع المبيعات"""
    return_id: str
    inspected_by: str


@dataclass
class CompleteSalesReturnCommand:
    """إكمال إرجاع المبيعات وإنشاء Credit Note"""
    return_id: str
    completed_by: str
    create_credit_note: bool = True


@dataclass
class CancelSalesReturnCommand:
    """إلغاء إرجاع المبيعات"""
    return_id: str
    cancelled_by: str
    reason: str = ""
