"""
Quotation Commands
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Dict, Any


@dataclass
class QuotationItemCommand:
    """عنصر في عرض السعر"""
    product_id: str
    product_name: str
    quantity: float
    unit_price: float
    discount_percent: float = 0.0
    tax_percent: float = 15.0
    unit: str = "pcs"
    notes: Optional[str] = None


@dataclass
class AddressCommand:
    """عنوان"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "SA"
    building_number: Optional[str] = None
    unit_number: Optional[str] = None
    district: Optional[str] = None


@dataclass
class CreateQuotationCommand:
    """إنشاء عرض سعر جديد"""
    customer_id: str
    customer_name: str
    currency: str = "SAR"
    issue_date: date = field(default_factory=date.today)
    expiry_date: Optional[date] = None
    
    # العناوين
    billing_address: Optional[AddressCommand] = None
    shipping_address: Optional[AddressCommand] = None
    
    # العناصر
    items: List[QuotationItemCommand] = field(default_factory=list)
    
    # الخصومات
    global_discount_percent: float = 0.0
    global_discount_amount: float = 0.0
    
    # الملاحظات
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    # بيانات النظام
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    branch_id: Optional[str] = None
    company_id: Optional[str] = None
    
    # حقول مخصصة
    custom_fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UpdateQuotationCommand:
    """تحديث عرض سعر موجود"""
    quotation_id: str
    
    # الحقول القابلة للتحديث
    customer_name: Optional[str] = None
    currency: Optional[str] = None
    expiry_date: Optional[date] = None
    
    billing_address: Optional[AddressCommand] = None
    shipping_address: Optional[AddressCommand] = None
    
    items: Optional[List[QuotationItemCommand]] = None
    
    global_discount_percent: Optional[float] = None
    global_discount_amount: Optional[float] = None
    
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    
    custom_fields: Optional[Dict[str, Any]] = None


@dataclass
class SendQuotationCommand:
    """إرسال عرض السعر للعميل"""
    quotation_id: str
    sent_via: str = "email"  # email, whatsapp, sms, manual
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    message: Optional[str] = None


@dataclass
class AcceptQuotationCommand:
    """قبول عرض السعر"""
    quotation_id: str
    accepted_by: Optional[str] = None
    acceptance_notes: Optional[str] = None


@dataclass
class RejectQuotationCommand:
    """رفض عرض السعر"""
    quotation_id: str
    reason: str
    rejected_by: Optional[str] = None


@dataclass
class ConvertQuotationToOrderCommand:
    """تحويل عرض السعر لأمر بيع"""
    quotation_id: str
    order_date: date = field(default_factory=date.today)
    expected_delivery_date: Optional[date] = None
    priority: str = "normal"
    converted_by: Optional[str] = None
