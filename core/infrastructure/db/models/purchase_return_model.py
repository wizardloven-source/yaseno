"""
نموذج قاعدة البيانات لإرجاع المشتريات
Database Models for Purchase Returns
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import Column, String, Integer, Numeric, Date, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


class ReturnCondition(str, enum.Enum):
    """حالة الصنف المُرجع"""
    GOOD = "good"  # جيد
    DAMAGED = "damaged"  # تالف
    EXPIRED = "expired"  # منتهي الصلاحية
    DEFECTIVE = "defective"  # معيب


class PurchaseReturnModel(Base):
    """نموذج إرجاع المشتريات في قاعدة البيانات"""
    __tablename__ = "purchase_returns"

    id = Column(String(36), primary_key=True)
    return_number = Column(String(50), unique=True, nullable=False, index=True)
    
    # معلومات المورد
    supplier_code = Column(String(50), nullable=False, index=True)
    supplier_name = Column(String(200), nullable=False)
    
    # المستندات الأصلية
    original_po_number = Column(String(50), nullable=True)
    original_invoice_id = Column(String(36), nullable=True)
    
    # تاريخ الإرجاع
    return_date = Column(Date, nullable=False, default=date.today)
    
    # الحالة
    status = Column(SQLEnum("draft", "submitted", "approved", "shipped", 
                           "received_by_supplier", "completed", "rejected", "cancelled"),
                    nullable=False, default="draft")
    
    # المبالغ المالية
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=True)
    discount_percent = Column(Numeric(5, 2), nullable=True, default=0)
    tax_rate = Column(Numeric(5, 2), nullable=True, default=0)
    tax_amount = Column(Numeric(15, 2), nullable=True)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="USD")
    
    # ملاحظات ومعلومات إضافية
    notes = Column(Text, nullable=True)
    shipping_method = Column(String(100), nullable=True)
    tracking_number = Column(String(100), nullable=True)
    
    # مذكرة المدين المرتبطة
    debit_note_id = Column(String(36), nullable=True, index=True)
    
    # معلومات التتبع
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
    version = Column(Integer, nullable=False, default=0)
    
    # العلاقة مع الأصناف
    items = relationship("PurchaseReturnItemModel", back_populates="return_order", 
                        cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PurchaseReturn(return_number='{self.return_number}', status='{self.status}')>"


class PurchaseReturnItemModel(Base):
    """نموذج صنف إرجاع المشتريات في قاعدة البيانات"""
    __tablename__ = "purchase_return_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    return_id = Column(String(36), ForeignKey("purchase_returns.id"), nullable=False, index=True)
    
    # معلومات الصنف
    product_code = Column(String(50), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    
    # الكمية والسعر
    quantity = Column(Numeric(15, 3), nullable=False, default=0)
    unit = Column(String(20), nullable=False)
    unit_price = Column(Numeric(15, 4), nullable=False, default=0)
    
    # سبب الإرجاع وحالة الصنف
    reason = Column(Text, nullable=True)
    condition = Column(SQLEnum(ReturnCondition), nullable=False, default=ReturnCondition.GOOD)
    
    # تتبع الدُفعات والأرقام التسلسلية
    batch_number = Column(String(50), nullable=True)
    serial_number = Column(String(100), nullable=True)
    expiry_date = Column(Date, nullable=True)
    
    # الخصومات والضرائب
    discount_percent = Column(Numeric(5, 2), nullable=True, default=0)
    discount_amount = Column(Numeric(15, 2), nullable=True)
    tax_rate = Column(Numeric(5, 2), nullable=True, default=0)
    tax_amount = Column(Numeric(15, 2), nullable=True)
    
    # المجاميع
    subtotal = Column(Numeric(15, 2), nullable=False, default=0)
    total_with_tax = Column(Numeric(15, 2), nullable=False, default=0)
    
    # العلاقة مع الإرجاع
    return_order = relationship("PurchaseReturnModel", back_populates="items")

    def __repr__(self):
        return f"<PurchaseReturnItem(product_code='{self.product_code}', quantity={self.quantity})>"
