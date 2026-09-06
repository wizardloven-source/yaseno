"""
SQLAlchemy Models for Sales Quotation
Database persistence layer
"""

from sqlalchemy import Column, String, Text, Date, Numeric, Enum as SQLEnum, ForeignKey, Table, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from decimal import Decimal
import uuid

from app.core.infrastructure.base_model import Base


# Association table for quotation items
quotation_items_table = Table(
    'sales_quotation_items',
    Base.metadata,
    Column('id', String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column('quotation_id', String(36), ForeignKey('sales_quotations.id'), nullable=False),
    Column('line_number', Integer, nullable=False),
    Column('product_id', String(36), nullable=False),
    Column('product_name', String(255), nullable=False),
    Column('description', Text, nullable=True),
    Column('quantity', Numeric(18, 4), nullable=False, default=Decimal('0')),
    Column('unit_of_measure', String(20), nullable=False, default='PCS'),
    Column('unit_price', Numeric(18, 4), nullable=False, default=Decimal('0')),
    Column('discount_percentage', Numeric(5, 2), nullable=False, default=Decimal('0')),
    Column('tax_percentage', Numeric(5, 2), nullable=False, default=Decimal('15')),
    Column('line_total', Numeric(18, 4), nullable=False, default=Decimal('0')),
)


class SalesQuotationModel(Base):
    """
    نموذج قاعدة البيانات لعرض السعر
    """
    __tablename__ = 'sales_quotations'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Basic Info
    quotation_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(String(36), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    branch_id = Column(String(36), nullable=True)
    
    # Dates
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    
    # Status
    status = Column(SQLEnum(
        'draft', 'sent', 'viewed', 'accepted', 'rejected', 'expired', 'converted',
        name='quotation_status'
    ), nullable=False, default='draft')
    
    # Financial
    subtotal = Column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    discount_amount = Column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    discount_percentage = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    tax_amount = Column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    total_amount = Column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    
    # Currency
    currency_code = Column(String(3), nullable=False, default='SAR')
    exchange_rate = Column(Numeric(18, 6), nullable=False, default=Decimal('1'))
    
    # Additional Info
    notes = Column(Text, nullable=True)
    terms_conditions = Column(Text, nullable=True)
    valid_for_days = Column(Integer, nullable=False, default=30)
    sales_person_id = Column(String(36), nullable=True)
    
    # Tracking
    created_by = Column(String(36), nullable=True)
    updated_by = Column(String(36), nullable=True)
    converted_to_order_id = Column(String(36), nullable=True)
    
    # Timestamps
    created_at = Column(func.now(), nullable=False)
    updated_at = Column(func.now(), onupdate=func.now(), nullable=True)
    
    # Relationships
    items = relationship(
        "QuotationItemModel",
        secondary=quotation_items_table,
        back_populates="quotation",
        cascade="all, delete-orphan"
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'quotation_number': self.quotation_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'branch_id': self.branch_id,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'status': self.status,
            'subtotal': str(self.subtotal) if self.subtotal else '0',
            'discount_amount': str(self.discount_amount) if self.discount_amount else '0',
            'discount_percentage': str(self.discount_percentage) if self.discount_percentage else '0',
            'tax_amount': str(self.tax_amount) if self.tax_amount else '0',
            'total_amount': str(self.total_amount) if self.total_amount else '0',
            'currency_code': self.currency_code,
            'exchange_rate': str(self.exchange_rate) if self.exchange_rate else '1',
            'notes': self.notes,
            'terms_conditions': self.terms_conditions,
            'valid_for_days': self.valid_for_days,
            'sales_person_id': self.sales_person_id,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'converted_to_order_id': self.converted_to_order_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'items': [item.to_dict() for item in self.items] if self.items else []
        }


class QuotationItemModel(Base):
    """
    نموذج قاعدة البيانات لعنصر عرض السعر
    """
    __tablename__ = 'quotation_items'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    quotation_id = Column(String(36), ForeignKey('sales_quotations.id'), nullable=False)
    
    line_number = Column(Integer, nullable=False)
    product_id = Column(String(36), nullable=False)
    product_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    unit_of_measure = Column(String(20), nullable=False, default='PCS')
    unit_price = Column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    discount_percentage = Column(Numeric(5, 2), nullable=False, default=Decimal('0'))
    tax_percentage = Column(Numeric(5, 2), nullable=False, default=Decimal('15'))
    line_total = Column(Numeric(18, 4), nullable=False, default=Decimal('0'))
    
    # Relationship
    quotation = relationship("SalesQuotationModel", back_populates="items")
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'line_number': self.line_number,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'description': self.description,
            'quantity': str(self.quantity) if self.quantity else '0',
            'unit_of_measure': self.unit_of_measure,
            'unit_price': str(self.unit_price) if self.unit_price else '0',
            'discount_percentage': str(self.discount_percentage) if self.discount_percentage else '0',
            'tax_percentage': str(self.tax_percentage) if self.tax_percentage else '0',
            'line_total': str(self.line_total) if self.line_total else '0',
        }
