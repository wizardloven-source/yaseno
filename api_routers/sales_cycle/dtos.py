# api_routers/sales_cycle/dtos.py
"""
Sales Cycle DTOs - نماذج طلب/استجابة دورة المبيعات
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


# =============================================================================
# عناصر المستندات (سطور)
# =============================================================================

class SalesLineRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    tax_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    unit: str = Field(default="pcs", max_length=50)
    notes: Optional[str] = None


# =============================================================================
# عروض الأسعار - Quotations
# =============================================================================

class CreateQuotationRequest(BaseModel):
    customer_id: str = Field(..., min_length=1)
    customer_name: Optional[str] = None
    currency: str = Field("USD", min_length=3, max_length=3)
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    global_discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    global_discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    billing_address: Optional[Dict[str, Any]] = None
    shipping_address: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    branch_id: Optional[str] = None
    lines: List[SalesLineRequest] = Field(..., min_length=1)


class UpdateQuotationRequest(BaseModel):
    customer_name: Optional[str] = None
    expiry_date: Optional[date] = None
    global_discount_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    global_discount_amount: Optional[Decimal] = Field(default=None, ge=0)
    billing_address: Optional[Dict[str, Any]] = None
    shipping_address: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    lines: Optional[List[SalesLineRequest]] = None


class RejectQuotationRequest(BaseModel):
    reason: str = Field(..., min_length=1)


# =============================================================================
# أوامر المبيعات - Sales Orders
# =============================================================================

class CreateOrderRequest(BaseModel):
    customer_id: str = Field(..., min_length=1)
    customer_name: Optional[str] = None
    currency: str = Field("USD", min_length=3, max_length=3)
    order_date: Optional[date] = None
    expected_delivery_date: Optional[date] = None
    quotation_id: Optional[str] = None
    priority: str = Field("normal", max_length=20)
    global_discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    global_discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    shipping_cost: Decimal = Field(default=Decimal("0"), ge=0)
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None
    billing_address: Optional[Dict[str, Any]] = None
    shipping_address: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None
    branch_id: Optional[str] = None
    lines: Optional[List[SalesLineRequest]] = None


class UpdateOrderRequest(BaseModel):
    expected_delivery_date: Optional[date] = None
    priority: Optional[str] = None
    shipping_method: Optional[str] = None
    tracking_number: Optional[str] = None
    carrier: Optional[str] = None
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class CancelOrderRequest(BaseModel):
    reason: Optional[str] = None


class CreateInvoiceFromOrderRequest(BaseModel):
    payment_type: str = Field("cash", max_length=50)
    payment_currency: Optional[str] = None
    fund_id: Optional[str] = None
    notes: Optional[str] = None
    quantity_on: str = Field("delivered", pattern="^(delivered|ordered)$")


# =============================================================================
# إشعارات التسليم - Delivery Notes
# =============================================================================

class DeliveryLineRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    quantity: Decimal = Field(..., gt=0)
    notes: Optional[str] = None


class CreateDeliveryRequest(BaseModel):
    order_id: str = Field(..., min_length=1)
    delivery_date: Optional[date] = None
    scheduled_date: Optional[date] = None
    carrier: Optional[str] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    delivery_address: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    lines: Optional[List[DeliveryLineRequest]] = None


class CompleteDeliveryRequest(BaseModel):
    received_by: str = Field(..., min_length=1)
    received_by_title: Optional[str] = None
    actual_delivery_time: Optional[datetime] = None
    notes: Optional[str] = None
    lines: Optional[List[DeliveryLineRequest]] = None


class FailDeliveryRequest(BaseModel):
    reason: str = Field(..., min_length=1)
    notes: Optional[str] = None