"""
Commands for Sales Cycle Module
CQRS Commands - Write Operations
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date


# ============================================================================
# Quotation Commands
# ============================================================================

@dataclass
class CreateQuotationCommand:
    """إنشاء عرض سعر جديد"""
    customer_id: str
    customer_name: str
    branch_id: Optional[str] = None
    issue_date: date = field(default_factory=date.today)
    valid_for_days: int = 30
    items: List[Dict[str, Any]] = field(default_factory=list)
    discount_percentage: Decimal = Decimal('0')
    currency_code: str = 'SAR'
    exchange_rate: Decimal = Decimal('1')
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    sales_person_id: Optional[str] = None
    created_by: Optional[str] = None


@dataclass
class UpdateQuotationCommand:
    """تحديث عرض سعر موجود"""
    quotation_id: str
    customer_name: Optional[str] = None
    branch_id: Optional[str] = None
    expiry_date: Optional[date] = None
    items: Optional[List[Dict[str, Any]]] = None
    discount_percentage: Optional[Decimal] = None
    notes: Optional[str] = None
    terms_conditions: Optional[str] = None
    updated_by: Optional[str] = None


@dataclass
class SendQuotationCommand:
    """إرسال عرض السعر للعميل"""
    quotation_id: str
    sent_by: str


@dataclass
class AcceptQuotationCommand:
    """قبول عرض السعر"""
    quotation_id: str
    accepted_by: str


@dataclass
class RejectQuotationCommand:
    """رفض عرض السعر"""
    quotation_id: str
    reason: str
    rejected_by: str


@dataclass
class ConvertQuotationCommand:
    """تحويل عرض السعر إلى أمر بيع"""
    quotation_id: str
    converted_by: str


# ============================================================================
# Sales Order Commands
# ============================================================================

@dataclass
class CreateSalesOrderCommand:
    """إنشاء أمر بيع جديد"""
    customer_id: str
    customer_name: str
    branch_id: Optional[str] = None
    issue_date: date = field(default_factory=date.today)
    expected_delivery_date: Optional[date] = None
    items: List[Dict[str, Any]] = field(default_factory=list)
    discount_percentage: Decimal = Decimal('0')
    currency_code: str = 'SAR'
    exchange_rate: Decimal = Decimal('1')
    notes: Optional[str] = None
    sales_person_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    shipping_address: Optional[Dict[str, Any]] = None
    source_quotation_id: Optional[str] = None
    payment_terms: Optional[str] = None
    created_by: Optional[str] = None


@dataclass
class UpdateSalesOrderCommand:
    """تحديث أمر بيع موجود"""
    order_id: str
    customer_name: Optional[str] = None
    branch_id: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    items: Optional[List[Dict[str, Any]]] = None
    discount_percentage: Optional[Decimal] = None
    notes: Optional[str] = None
    updated_by: Optional[str] = None


@dataclass
class SubmitOrderForApprovalCommand:
    """إرسال أمر البيع للموافقة"""
    order_id: str
    submitted_by: str


@dataclass
class ApproveOrderCommand:
    """الموافقة على أمر البيع"""
    order_id: str
    approved_by: str


@dataclass
class RejectOrderCommand:
    """رفض أمر البيع"""
    order_id: str
    reason: str
    rejected_by: str


@dataclass
class ConfirmOrderCommand:
    """تأكيد أمر البيع"""
    order_id: str
    confirmed_by: str


@dataclass
class StartOrderProcessingCommand:
    """بدء معالجة أمر البيع"""
    order_id: str
    started_by: str


@dataclass
class PickOrderItemsCommand:
    """تحضير عناصر أمر البيع"""
    order_id: str
    picked_quantities: Dict[str, Decimal] = field(default_factory=dict)
    picked_by: Optional[str] = None


@dataclass
class PackOrderItemsCommand:
    """تغليف عناصر أمر البيع"""
    order_id: str
    packed_quantities: Dict[str, Decimal] = field(default_factory=dict)
    packed_by: Optional[str] = None


@dataclass
class MarkOrderReadyForShipmentCommand:
    """وضع علامة كجاهز للشحن"""
    order_id: str
    marked_by: str


@dataclass
class ShipOrderItemsCommand:
    """شحن عناصر أمر البيع"""
    order_id: str
    shipped_quantities: Dict[str, Decimal] = field(default_factory=dict)
    tracking_number: Optional[str] = None
    shipped_by: Optional[str] = None


@dataclass
class DeliverOrderItemsCommand:
    """تسليم عناصر أمر البيع"""
    order_id: str
    delivered_quantities: Dict[str, Decimal] = field(default_factory=dict)
    delivered_by: Optional[str] = None


@dataclass
class CreateInvoiceFromOrderCommand:
    """إنشاء فاتورة من أمر البيع"""
    order_id: str
    invoice_id: str
    created_by: str


@dataclass
class CompleteOrderCommand:
    """إكمال أمر البيع"""
    order_id: str
    completed_by: str


@dataclass
class CancelOrderCommand:
    """إلغاء أمر البيع"""
    order_id: str
    reason: str
    cancelled_by: str


# ============================================================================
# Delivery Note Commands
# ============================================================================

@dataclass
class CreateDeliveryNoteCommand:
    """إنشاء إشعار تسليم جديد"""
    sales_order_id: str
    customer_id: str
    customer_name: str
    warehouse_id: str
    delivery_date: date = field(default_factory=date.today)
    expected_delivery_date: Optional[date] = None
    items: List[Dict[str, Any]] = field(default_factory=list)
    shipping_address: Optional[Dict[str, Any]] = None
    driver_name: Optional[str] = None
    vehicle_number: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None


@dataclass
class StartDeliveryCommand:
    """بدء عملية التسليم"""
    delivery_id: str
    started_by: str


@dataclass
class CompleteDeliveryCommand:
    """إكمال التسليم"""
    delivery_id: str
    delivered_quantities: Dict[str, Decimal] = field(default_factory=dict)
    completed_by: Optional[str] = None


@dataclass
class ReturnDeliveryCommand:
    """إرجاع عناصر من التسليم"""
    delivery_id: str
    returned_quantities: Dict[str, Decimal] = field(default_factory=dict)
    reason: str
    returned_by: Optional[str] = None


@dataclass
class CancelDeliveryCommand:
    """إلغاء إشعار التسليم"""
    delivery_id: str
    reason: str
    cancelled_by: str
