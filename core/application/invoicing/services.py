# core/application/invoicing/services.py
"""Invoice Services - Business Logic Layer"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.infrastructure.db.models.invoice_model import InvoiceModel, InvoiceLineModel
from core.infrastructure.db.models.product_model import ProductModel
from core.infrastructure.db.models.customer_model import CustomerModel


class InvoiceService:
    """خدمة الفواتير - تحتوي على منطق الأعمال"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def generate_invoice_number(self) -> str:
        """توليد رقم فاتورة جديد"""
        last_invoice = self._session.query(InvoiceModel).order_by(
            InvoiceModel.created_at.desc()
        ).first()
        
        if last_invoice and last_invoice.number:
            last_num = int(last_invoice.number.replace('INV-', ''))
            next_num = last_num + 1
        else:
            next_num = 1
        
        return f"INV-{next_num:05d}"
    
    def create_invoice(self, customer_id: str, customer_name: str,
                       currency: str = "USD", payment_type: str = "cash",
                       site_id: str = None, site_name: str = None,
                       notes: str = "", created_by: str = "system") -> Dict[str, Any]:
        """إنشاء فاتورة جديدة"""
        
        invoice_number = self.generate_invoice_number()
        
        invoice = InvoiceModel(
            id=uuid4(),
            number=invoice_number,
            invoice_date=datetime.now(timezone.utc),
            customer_id=customer_id,
            customer_name=customer_name,
            site_id=site_id,
            site_name=site_name,
            currency=currency,
            payment_type=payment_type,
            subtotal=Decimal('0'),
            tax_amount=Decimal('0'),
            total_amount=Decimal('0'),
            status='draft',
            notes=notes,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
            version=1
        )
        
        self._session.add(invoice)
        self._session.flush()
        
        return {
            'id': str(invoice.id),
            'number': invoice.number,
            'customer_id': invoice.customer_id,
            'customer_name': invoice.customer_name,
            'currency': invoice.currency,
            'payment_type': invoice.payment_type,
            'status': invoice.status,
            'subtotal': float(invoice.subtotal),
            'total': float(invoice.total_amount),
            'notes': invoice.notes
        }
    
    def add_line(self, invoice_id: str, product_code: str, product_name: str,
                 quantity: Decimal, unit_price: Decimal,
                 currency: str, notes: str = "") -> Dict[str, Any]:
        """إضافة سطر إلى الفاتورة"""
        
        # جلب الفاتورة
        invoice = self._session.query(InvoiceModel).filter(
            InvoiceModel.id == invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"الفاتورة {invoice_id} غير موجودة")
        
        if invoice.status == 'posted':
            raise ValueError("لا يمكن تعديل فاتورة مرحلة")
        
        # حساب الإجمالي
        total_amount = quantity * unit_price
        
        # إنشاء السطر
        line = InvoiceLineModel(
            id=uuid4(),
            invoice_id=invoice.id,
            product_code=product_code,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            currency=currency,
            notes=notes,
            line_order=len(invoice.lines) if invoice.lines else 0
        )
        
        self._session.add(line)
        
        # تحديث إجماليات الفاتورة
        all_lines = self._session.query(InvoiceLineModel).filter(
            InvoiceLineModel.invoice_id == invoice.id
        ).all()
        
        new_subtotal = sum(l.total_amount for l in all_lines)
        invoice.subtotal = new_subtotal
        invoice.total_amount = new_subtotal
        
        self._session.flush()
        
        return {
            'line_id': str(line.id),
            'product_code': line.product_code,
            'product_name': line.product_name,
            'quantity': float(line.quantity),
            'unit_price': float(line.unit_price),
            'total': float(line.total_amount),
            'currency': line.currency,
            'notes': line.notes,
            'invoice_subtotal': float(new_subtotal),
            'invoice_total': float(new_subtotal)
        }
    
    def remove_line(self, invoice_id: str, line_id: str) -> Dict[str, Any]:
        """حذف سطر من الفاتورة"""
        
        line = self._session.query(InvoiceLineModel).filter(
            InvoiceLineModel.id == line_id
        ).first()
        
        if not line:
            raise ValueError(f"السطر {line_id} غير موجود")
        
        self._session.delete(line)
        
        # تحديث إجماليات الفاتورة
        invoice = self._session.query(InvoiceModel).filter(
            InvoiceModel.id == invoice_id
        ).first()
        
        if invoice:
            all_lines = self._session.query(InvoiceLineModel).filter(
                InvoiceLineModel.invoice_id == invoice.id
            ).all()
            
            new_subtotal = sum(l.total_amount for l in all_lines)
            invoice.subtotal = new_subtotal
            invoice.total_amount = new_subtotal
            self._session.flush()
            
            return {
                'invoice_subtotal': float(new_subtotal),
                'invoice_total': float(new_subtotal)
            }
        
        return {}
    
    def post_invoice(self, invoice_id: str, posted_by: str) -> Dict[str, Any]:
        """ترحيل الفاتورة"""
        
        invoice = self._session.query(InvoiceModel).filter(
            InvoiceModel.id == invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"الفاتورة {invoice_id} غير موجودة")
        
        if invoice.status == 'posted':
            raise ValueError("الفاتورة مرحلة مسبقاً")
        
        lines = self._session.query(InvoiceLineModel).filter(
            InvoiceLineModel.invoice_id == invoice.id
        ).all()
        
        if len(lines) == 0:
            raise ValueError("لا يمكن ترحيل فاتورة بدون بنود")
        
        invoice.status = 'posted'
        invoice.posted_at = datetime.now(timezone.utc)
        invoice.posted_by = posted_by
        
        self._session.flush()
        
        return {
            'invoice_id': str(invoice.id),
            'invoice_number': invoice.number,
            'status': invoice.status,
            'posted_at': invoice.posted_at.isoformat() if invoice.posted_at else None
        }
    
    def get_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """جلب فاتورة مع بنودها"""
        
        invoice = self._session.query(InvoiceModel).filter(
            InvoiceModel.id == invoice_id
        ).first()
        
        if not invoice:
            return None
        
        lines = self._session.query(InvoiceLineModel).filter(
            InvoiceLineModel.invoice_id == invoice.id
        ).order_by(InvoiceLineModel.line_order).all()
        
        return {
            'id': str(invoice.id),
            'number': invoice.number,
            'customer_id': invoice.customer_id,
            'customer_name': invoice.customer_name,
            'currency': invoice.currency,
            'payment_type': invoice.payment_type,
            'status': invoice.status,
            'subtotal': float(invoice.subtotal),
            'total': float(invoice.total_amount),
            'notes': invoice.notes,
            'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
            'posted_at': invoice.posted_at.isoformat() if invoice.posted_at else None,
            'lines': [
                {
                    'line_id': str(l.id),
                    'product_code': l.product_code,
                    'product_name': l.product_name,
                    'quantity': float(l.quantity),
                    'unit_price': float(l.unit_price),
                    'total': float(l.total_amount),
                    'currency': l.currency,
                    'notes': l.notes
                }
                for l in lines
            ]
        }


class ProductService:
    """خدمة المنتجات"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def get_all_products(self) -> List[Dict[str, Any]]:
        """جلب جميع المنتجات النشطة"""
        products = self._session.query(ProductModel).filter(
            ProductModel.is_active == True
        ).all()
        
        return [
            {
                'id': str(p.id),
                'code': p.code,
                'name': p.name,
                'unit_price': float(p.unit_price),
                'currency': p.currency,
                'category': p.category
            }
            for p in products
        ]
    
    def create_product(self, code: str, name: str, unit_price: Decimal,
                       currency: str = "USD", category: str = None) -> Dict[str, Any]:
        """إنشاء منتج جديد"""
        
        product = ProductModel(
            id=uuid4(),
            code=code,
            name=name,
            unit_price=unit_price,
            currency=currency,
            category=category,
            is_active=True
        )
        
        self._session.add(product)
        self._session.flush()
        
        return {
            'id': str(product.id),
            'code': product.code,
            'name': product.name,
            'unit_price': float(product.unit_price),
            'currency': product.currency
        }


class CustomerService:
    """خدمة العملاء"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def get_all_customers(self) -> List[Dict[str, Any]]:
        """جلب جميع العملاء النشطين"""
        customers = self._session.query(CustomerModel).filter(
            CustomerModel.is_active == True
        ).all()
        
        return [
            {
                'id': str(c.id),
                'code': c.code,
                'name': c.name,
                'email': c.email,
                'phone': c.phone
            }
            for c in customers
        ]
    
    def create_customer(self, code: str, name: str, email: str = None,
                        phone: str = None, address: str = None) -> Dict[str, Any]:
        """إنشاء عميل جديد"""
        
        customer = CustomerModel(
            id=uuid4(),
            code=code,
            name=name,
            email=email,
            phone=phone,
            address=address,
            is_active=True
        )
        
        self._session.add(customer)
        self._session.flush()
        
        return {
            'id': str(customer.id),
            'code': customer.code,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone
        }