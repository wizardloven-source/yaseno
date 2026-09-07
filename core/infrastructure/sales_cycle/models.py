"""
Database Models for Sales Cycle
"""

from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, Date, ForeignKey, Enum, JSON, Numeric
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum as PyEnum
import uuid

from core.infrastructure.database.base import Base


class QuotationStatusEnum(str, PyEnum):
    """حالات عرض السعر"""
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONVERTED = "converted"


class OrderStatusEnum(str, PyEnum):
    """حالات أمر البيع"""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    PICKING = "picking"
    PACKING = "packing"
    READY_TO_SHIP = "ready_to_ship"
    SHIPPED = "shipped"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    PARTIALLY_DELIVERED = "partially_delivered"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"
    RETURNED = "returned"
    COMPLETED = "completed"


class DeliveryStatusEnum(str, PyEnum):
    """حالات إشعار التسليم"""
    DRAFT = "draft"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    PARTIALLY_DELIVERED = "partially_delivered"
    FAILED = "failed"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class SalesQuotationModel(Base):
    """نموذج عرض السعر"""
    __tablename__ = "sales_quotations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quotation_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # العميل
    customer_id = Column(String(36), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    
    # العملة
    currency = Column(String(3), default="SAR")
    
    # التواريخ
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date)
    
    # العناوين (JSON)
    billing_address = Column(JSON)
    shipping_address = Column(JSON)
    
    # الحالة
    status = Column(Enum(QuotationStatusEnum), default=QuotationStatusEnum.DRAFT)
    
    # المجاميع
    subtotal = Column(Numeric(18, 2), default=0)
    total_discount = Column(Numeric(18, 2), default=0)
    amount_after_discount = Column(Numeric(18, 2), default=0)
    total_tax = Column(Numeric(18, 2), default=0)
    grand_total = Column(Numeric(18, 2), default=0)
    
    # الخصم العام
    global_discount_percent = Column(Float, default=0)
    global_discount_amount = Column(Numeric(18, 2), default=0)
    
    # الملاحظات
    notes = Column(Text)
    internal_notes = Column(Text)
    
    # تواريخ الحالة
    sent_date = Column(DateTime)
    viewed_date = Column(DateTime)
    accepted_date = Column(DateTime)
    rejected_date = Column(DateTime)
    converted_date = Column(DateTime)
    
    # بيانات النظام
    created_by = Column(String(36))
    sales_person_id = Column(String(36))
    sales_person_name = Column(String(255))
    branch_id = Column(String(36))
    company_id = Column(String(36))
    
    # حقول مخصصة
    custom_fields = Column(JSON)
    
    # الطوابع الزمنية
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # العلاقات
    items = relationship("QuotationItemModel", back_populates="quotation", cascade="all, delete-orphan")
    
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
            "subtotal": float(self.subtotal) if self.subtotal else 0,
            "total_discount": float(self.total_discount) if self.total_discount else 0,
            "amount_after_discount": float(self.amount_after_discount) if self.amount_after_discount else 0,
            "total_tax": float(self.total_tax) if self.total_tax else 0,
            "grand_total": float(self.grand_total) if self.grand_total else 0,
            "notes": self.notes,
            "internal_notes": self.internal_notes,
            "sent_date": self.sent_date.isoformat() if self.sent_date else None,
            "viewed_date": self.viewed_date.isoformat() if self.viewed_date else None,
            "accepted_date": self.accepted_date.isoformat() if self.accepted_date else None,
            "rejected_date": self.rejected_date.isoformat() if self.rejected_date else None,
            "converted_date": self.converted_date.isoformat() if self.converted_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items": [item.to_dict() for item in self.items],
        }


class QuotationItemModel(Base):
    """عناصر عرض السعر"""
    __tablename__ = "quotation_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quotation_id = Column(String(36), ForeignKey("sales_quotations.id"), nullable=False, index=True)
    
    # المنتج
    product_id = Column(String(36), nullable=False)
    product_name = Column(String(255), nullable=False)
    
    # الكمية والسعر
    quantity = Column(Numeric(18, 2), nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    
    # الخصم والضريبة
    discount_percent = Column(Float, default=0)
    tax_percent = Column(Float, default=15.0)
    
    # الوحدة
    unit = Column(String(50), default="pcs")
    
    # ملاحظات
    notes = Column(Text)
    
    # المجاميع المحسوبة
    subtotal = Column(Numeric(18, 2))
    discount_amount = Column(Numeric(18, 2))
    amount_after_discount = Column(Numeric(18, 2))
    tax_amount = Column(Numeric(18, 2))
    total = Column(Numeric(18, 2))
    
    # العلاقة
    quotation = relationship("SalesQuotationModel", back_populates="items")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": float(self.quantity) if self.quantity else 0,
            "unit_price": float(self.unit_price) if self.unit_price else 0,
            "discount_percent": self.discount_percent or 0,
            "tax_percent": self.tax_percent or 15.0,
            "unit": self.unit,
            "notes": self.notes,
            "subtotal": float(self.subtotal) if self.subtotal else 0,
            "discount_amount": float(self.discount_amount) if self.discount_amount else 0,
            "amount_after_discount": float(self.amount_after_discount) if self.amount_after_discount else 0,
            "tax_amount": float(self.tax_amount) if self.tax_amount else 0,
            "total": float(self.total) if self.total else 0,
        }


class SalesOrderModel(Base):
    """نموذج أمر البيع"""
    __tablename__ = "sales_orders"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # العميل
    customer_id = Column(String(36), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    
    # العملة
    currency = Column(String(3), default="SAR")
    
    # المصدر
    source_type = Column(String(50))  # quotation, web, pos, manual
    source_id = Column(String(36))
    quotation_id = Column(String(36), index=True)
    
    # التواريخ
    order_date = Column(Date, nullable=False)
    expected_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)
    
    # العناوين
    billing_address = Column(JSON)
    shipping_address = Column(JSON)
    
    # الحالة
    status = Column(Enum(OrderStatusEnum), default=OrderStatusEnum.DRAFT)
    priority = Column(String(20), default="normal")
    
    # المجاميع
    subtotal = Column(Numeric(18, 2), default=0)
    total_discount = Column(Numeric(18, 2), default=0)
    amount_after_discount = Column(Numeric(18, 2), default=0)
    total_tax = Column(Numeric(18, 2), default=0)
    shipping_cost = Column(Numeric(18, 2), default=0)
    grand_total = Column(Numeric(18, 2), default=0)
    
    # الشحن
    shipping_method = Column(String(100))
    tracking_number = Column(String(100))
    carrier = Column(String(255))
    
    # الدفع
    payment_status = Column(String(20), default="pending")
    payment_terms = Column(String(255))
    due_date = Column(Date)
    
    # الفوترة
    invoice_id = Column(String(36))
    invoice_number = Column(String(50))
    invoiced_date = Column(DateTime)
    invoiced_amount = Column(Numeric(18, 2), default=0)
    
    # الملاحظات
    notes = Column(Text)
    internal_notes = Column(Text)
    
    # بيانات النظام
    created_by = Column(String(36))
    sales_person_id = Column(String(36))
    sales_person_name = Column(String(255))
    branch_id = Column(String(36))
    company_id = Column(String(36))
    warehouse_id = Column(String(36))
    
    # حقول مخصصة
    custom_fields = Column(JSON)
    
    # الطوابع الزمنية
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # العلاقات
    items = relationship("OrderItemModel", back_populates="order", cascade="all, delete-orphan")
    
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
            "subtotal": float(self.subtotal) if self.subtotal else 0,
            "total_discount": float(self.total_discount) if self.total_discount else 0,
            "amount_after_discount": float(self.amount_after_discount) if self.amount_after_discount else 0,
            "total_tax": float(self.total_tax) if self.total_tax else 0,
            "shipping_cost": float(self.shipping_cost) if self.shipping_cost else 0,
            "grand_total": float(self.grand_total) if self.grand_total else 0,
            "payment_status": self.payment_status,
            "tracking_number": self.tracking_number,
            "carrier": self.carrier,
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice_number,
            "notes": self.notes,
            "internal_notes": self.internal_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items": [item.to_dict() for item in self.items],
        }


class OrderItemModel(Base):
    """عناصر أمر البيع"""
    __tablename__ = "order_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=False, index=True)
    
    # المنتج
    product_id = Column(String(36), nullable=False)
    product_name = Column(String(255), nullable=False)
    
    # الكمية والسعر
    quantity = Column(Numeric(18, 2), nullable=False)
    unit_price = Column(Numeric(18, 2), nullable=False)
    
    # الخصم والضريبة
    discount_percent = Column(Float, default=0)
    tax_percent = Column(Float, default=15.0)
    
    # الوحدة
    unit = Column(String(50), default="pcs")
    
    # تتبع التنفيذ
    picked_quantity = Column(Numeric(18, 2), default=0)
    packed_quantity = Column(Numeric(18, 2), default=0)
    shipped_quantity = Column(Numeric(18, 2), default=0)
    delivered_quantity = Column(Numeric(18, 2), default=0)
    returned_quantity = Column(Numeric(18, 2), default=0)
    
    # المخزون
    warehouse_id = Column(String(36))
    batch_number = Column(String(100))
    serial_numbers = Column(JSON)
    
    # ملاحظات
    notes = Column(Text)
    
    # المجاميع
    subtotal = Column(Numeric(18, 2))
    discount_amount = Column(Numeric(18, 2))
    amount_after_discount = Column(Numeric(18, 2))
    tax_amount = Column(Numeric(18, 2))
    total = Column(Numeric(18, 2))
    
    # العلاقة
    order = relationship("SalesOrderModel", back_populates="items")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "quantity": float(self.quantity) if self.quantity else 0,
            "unit_price": float(self.unit_price) if self.unit_price else 0,
            "discount_percent": self.discount_percent or 0,
            "tax_percent": self.tax_percent or 15.0,
            "unit": self.unit,
            "picked_quantity": float(self.picked_quantity) if self.picked_quantity else 0,
            "packed_quantity": float(self.packed_quantity) if self.packed_quantity else 0,
            "shipped_quantity": float(self.shipped_quantity) if self.shipped_quantity else 0,
            "delivered_quantity": float(self.delivered_quantity) if self.delivered_quantity else 0,
            "returned_quantity": float(self.returned_quantity) if self.returned_quantity else 0,
            "warehouse_id": self.warehouse_id,
            "batch_number": self.batch_number,
            "serial_numbers": self.serial_numbers or [],
            "notes": self.notes,
            "subtotal": float(self.subtotal) if self.subtotal else 0,
            "discount_amount": float(self.discount_amount) if self.discount_amount else 0,
            "amount_after_discount": float(self.amount_after_discount) if self.amount_after_discount else 0,
            "tax_amount": float(self.tax_amount) if self.tax_amount else 0,
            "total": float(self.total) if self.total else 0,
        }


class DeliveryNoteModel(Base):
    """نموذج إشعار التسليم"""
    __tablename__ = "delivery_notes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    delivery_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # الأمر المرتبط
    order_id = Column(String(36), ForeignKey("sales_orders.id"), nullable=False, index=True)
    order_number = Column(String(50), nullable=False)
    
    # العميل
    customer_id = Column(String(36), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    
    # التواريخ
    delivery_date = Column(Date, nullable=False)
    scheduled_date = Column(Date)
    actual_delivery_time = Column(DateTime)
    
    # العنوان
    delivery_address = Column(JSON)
    
    # الحالة
    status = Column(Enum(DeliveryStatusEnum), default=DeliveryStatusEnum.DRAFT)
    
    # معلومات الشحن
    carrier = Column(String(255))
    vehicle_number = Column(String(50))
    driver_name = Column(String(255))
    driver_phone = Column(String(20))
    
    # الاستلام
    received_by = Column(String(255))
    received_by_title = Column(String(100))
    received_date = Column(DateTime)
    signature_url = Column(String(500))
    
    # الملاحظات
    notes = Column(Text)
    delivery_notes = Column(Text)
    failure_reason = Column(Text)
    
    # بيانات النظام
    warehouse_id = Column(String(36))
    branch_id = Column(String(36))
    company_id = Column(String(36))
    created_by = Column(String(36))
    delivered_by = Column(String(36))
    
    # حقول مخصصة
    custom_fields = Column(JSON)
    
    # الطوابع الزمنية
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # العلاقات
    items = relationship("DeliveryItemModel", back_populates="delivery_note", cascade="all, delete-orphan")
    
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
            "items": [item.to_dict() for item in self.items],
        }


class DeliveryItemModel(Base):
    """عناصر إشعار التسليم"""
    __tablename__ = "delivery_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    delivery_id = Column(String(36), ForeignKey("delivery_notes.id"), nullable=False, index=True)
    
    # المنتج
    product_id = Column(String(36), nullable=False)
    product_name = Column(String(255), nullable=False)
    
    # الكميات
    ordered_quantity = Column(Numeric(18, 2), nullable=False)
    delivered_quantity = Column(Numeric(18, 2), nullable=False)
    
    # الوحدة
    unit = Column(String(50), default="pcs")
    
    # المخزون
    warehouse_id = Column(String(36))
    batch_number = Column(String(100))
    serial_numbers = Column(JSON)
    
    # ملاحظات
    notes = Column(Text)
    
    # العلاقة
    delivery_note = relationship("DeliveryNoteModel", back_populates="items")
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "ordered_quantity": float(self.ordered_quantity) if self.ordered_quantity else 0,
            "delivered_quantity": float(self.delivered_quantity) if self.delivered_quantity else 0,
            "unit": self.unit,
            "warehouse_id": self.warehouse_id,
            "batch_number": self.batch_number,
            "serial_numbers": self.serial_numbers or [],
            "notes": self.notes,
        }
