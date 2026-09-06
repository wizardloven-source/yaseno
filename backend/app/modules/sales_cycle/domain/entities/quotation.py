"""
Sales Quotation Entity - عرض سعر
Represents a formal price quotation sent to a customer
"""

from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from enum import Enum

from app.core.domain.base_entity import BaseEntity


class QuotationStatus(str, Enum):
    """حالات عرض السعر"""
    DRAFT = "draft"  # مسودة
    SENT = "sent"  # مرسل للعميل
    VIEWED = "viewed"  # تمت مشاهدته
    ACCEPTED = "accepted"  # مقبول
    REJECTED = "rejected"  # مرفوض
    EXPIRED = "expired"  # منتهي الصلاحية
    CONVERTED = "converted"  # تم تحويله لأمر بيع


class SalesQuotation(BaseEntity):
    """
    كيان عرض السعر
    
    Attributes:
        quotation_number: رقم عرض السعر الفريد
        customer_id: معرف العميل
        customer_name: اسم العميل
        branch_id: معرف الفرع (اختياري)
        issue_date: تاريخ الإصدار
        expiry_date: تاريخ الانتهاء
        status: حالة عرض السعر
        items: عناصر عرض السعر
        subtotal: المجموع الجزئي
        discount_amount: قيمة الخصم
        discount_percentage: نسبة الخصم
        tax_amount: قيمة الضريبة
        total_amount: المبلغ الإجمالي
        currency_code: رمز العملة
        exchange_rate: سعر الصرف
        notes: ملاحظات
        terms_conditions: الشروط والأحكام
        valid_for_days: صالح لمدة (بالأيام)
        sales_person_id: معرف موظف المبيعات
        created_by: معرف من أنشأ العرض
        converted_to_order_id: معرف أمر البيع المحول إليه
    """
    
    def __init__(
        self,
        quotation_number: str,
        customer_id: str,
        customer_name: str,
        issue_date: date,
        status: QuotationStatus = QuotationStatus.DRAFT,
        branch_id: Optional[str] = None,
        expiry_date: Optional[date] = None,
        items: Optional[List['QuotationItem']] = None,
        discount_amount: Decimal = Decimal('0'),
        discount_percentage: Decimal = Decimal('0'),
        tax_amount: Decimal = Decimal('0'),
        total_amount: Decimal = Decimal('0'),
        currency_code: str = 'SAR',
        exchange_rate: Decimal = Decimal('1'),
        notes: Optional[str] = None,
        terms_conditions: Optional[str] = None,
        valid_for_days: int = 30,
        sales_person_id: Optional[str] = None,
        created_by: Optional[str] = None,
        converted_to_order_id: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        
        self.quotation_number = quotation_number
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.branch_id = branch_id
        self.issue_date = issue_date
        self.expiry_date = expiry_date or self._calculate_expiry_date(valid_for_days)
        self.status = status
        self.items = items or []
        self.discount_amount = discount_amount
        self.discount_percentage = discount_percentage
        self.tax_amount = tax_amount
        self.total_amount = total_amount
        self.currency_code = currency_code
        self.exchange_rate = exchange_rate
        self.notes = notes
        self.terms_conditions = terms_conditions
        self.valid_for_days = valid_for_days
        self.sales_person_id = sales_person_id
        self.created_by = created_by
        self.converted_to_order_id = converted_to_order_id
        
        if self.items:
            self._calculate_totals()
    
    def _calculate_expiry_date(self, days: int) -> date:
        """حساب تاريخ الانتهاء بناءً على عدد الأيام"""
        from datetime import timedelta
        return self.issue_date + timedelta(days=days)
    
    def add_item(self, item: 'QuotationItem') -> None:
        """إضافة عنصر لعرض السعر"""
        self.items.append(item)
        self._calculate_totals()
    
    def remove_item(self, item_id: str) -> bool:
        """إزالة عنصر من عرض السعر"""
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                self._calculate_totals()
                return True
        return False
    
    def update_item_quantity(self, item_id: str, quantity: Decimal) -> bool:
        """تحديث كمية عنصر"""
        for item in self.items:
            if item.id == item_id:
                item.quantity = quantity
                self._calculate_totals()
                return True
        return False
    
    def _calculate_totals(self) -> None:
        """إعادة حساب المجاميع"""
        self.subtotal = sum(
            item.line_total for item in self.items
        )
        
        # تطبيق الخصم
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / Decimal('100'))
        
        amount_after_discount = self.subtotal - self.discount_amount
        
        # حساب الضريبة
        self.tax_amount = amount_after_discount * (Decimal('15') / Decimal('100'))  # VAT 15%
        
        # المجموع الإجمالي
        self.total_amount = amount_after_discount + self.tax_amount
    
    def send_to_customer(self) -> None:
        """إرسال عرض السعر للعميل"""
        if self.status == QuotationStatus.DRAFT:
            self.status = QuotationStatus.SENT
            self.add_event('quotation_sent', {
                'quotation_id': self.id,
                'sent_at': datetime.utcnow().isoformat()
            })
    
    def mark_as_viewed(self) -> None:
        """وضع علامة كمتمت المشاهدة"""
        if self.status == QuotationStatus.SENT:
            self.status = QuotationStatus.VIEWED
    
    def accept(self) -> None:
        """قبول عرض السعر"""
        if self.status in [QuotationStatus.SENT, QuotationStatus.VIEWED]:
            self.status = QuotationStatus.ACCEPTED
            self.add_event('quotation_accepted', {
                'quotation_id': self.id,
                'accepted_at': datetime.utcnow().isoformat()
            })
    
    def reject(self, reason: str) -> None:
        """رفض عرض السعر"""
        if self.status in [QuotationStatus.SENT, QuotationStatus.VIEWED]:
            self.status = QuotationStatus.REJECTED
            self.add_event('quotation_rejected', {
                'quotation_id': self.id,
                'reason': reason,
                'rejected_at': datetime.utcnow().isoformat()
            })
    
    def expire(self) -> None:
        """إنهاء صلاحية عرض السعر"""
        if self.status not in [QuotationStatus.ACCEPTED, QuotationStatus.REJECTED, QuotationStatus.CONVERTED]:
            self.status = QuotationStatus.EXPIRED
            self.add_event('quotation_expired', {
                'quotation_id': self.id,
                'expired_at': datetime.utcnow().isoformat()
            })
    
    def convert_to_sales_order(self, order_id: str) -> 'SalesOrder':
        """تحويل عرض السعر إلى أمر بيع"""
        if self.status != QuotationStatus.ACCEPTED:
            raise ValueError("Cannot convert quotation that is not accepted")
        
        self.status = QuotationStatus.CONVERTED
        self.converted_to_order_id = order_id
        
        self.add_event('quotation_converted', {
            'quotation_id': self.id,
            'sales_order_id': order_id,
            'converted_at': datetime.utcnow().isoformat()
        })
        
        # إنشاء أمر بيع جديد
        from .sales_order import SalesOrder, SalesOrderStatus
        
        order_items = [
            SalesOrderItem(
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount_percentage=item.discount_percentage,
                tax_percentage=item.tax_percentage,
            )
            for item in self.items
        ]
        
        sales_order = SalesOrder(
            order_number=f"SO-{datetime.now().strftime('%Y%m%d')}-{order_id[:8].upper()}",
            customer_id=self.customer_id,
            customer_name=self.customer_name,
            issue_date=date.today(),
            status=SalesOrderStatus.PENDING,
            branch_id=self.branch_id,
            items=order_items,
            discount_amount=self.discount_amount,
            discount_percentage=self.discount_percentage,
            tax_amount=self.tax_amount,
            total_amount=self.total_amount,
            currency_code=self.currency_code,
            exchange_rate=self.exchange_rate,
            notes=self.notes,
            sales_person_id=self.sales_person_id,
            source_quotation_id=self.id,
            created_by=self.created_by,
        )
        
        return sales_order
    
    def is_expired(self) -> bool:
        """التحقق مما إذا كان عرض السعر منتهي الصلاحية"""
        return date.today() > self.expiry_date and self.status not in [
            QuotationStatus.ACCEPTED, 
            QuotationStatus.REJECTED,
            QuotationStatus.CONVERTED
        ]
    
    def to_dict(self) -> dict:
        """تحويل الكيان إلى قاموس"""
        return {
            'id': self.id,
            'quotation_number': self.quotation_number,
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'branch_id': self.branch_id,
            'issue_date': self.issue_date.isoformat(),
            'expiry_date': self.expiry_date.isoformat(),
            'status': self.status.value,
            'items': [item.to_dict() for item in self.items],
            'subtotal': str(self.subtotal),
            'discount_amount': str(self.discount_amount),
            'discount_percentage': str(self.discount_percentage),
            'tax_amount': str(self.tax_amount),
            'total_amount': str(self.total_amount),
            'currency_code': self.currency_code,
            'exchange_rate': str(self.exchange_rate),
            'notes': self.notes,
            'terms_conditions': self.terms_conditions,
            'valid_for_days': self.valid_for_days,
            'sales_person_id': self.sales_person_id,
            'created_by': self.created_by,
            'converted_to_order_id': self.converted_to_order_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class QuotationItem:
    """
    عنصر في عرض السعر
    
    Attributes:
        id: معرف العنصر
        line_number: رقم السطر
        product_id: معرف المنتج
        product_name: اسم المنتج
        description: الوصف
        quantity: الكمية
        unit_of_measure: وحدة القياس
        unit_price: سعر الوحدة
        discount_percentage: نسبة الخصم
        tax_percentage: نسبة الضريبة
        line_total: إجمالي السطر
    """
    
    def __init__(
        self,
        product_id: str,
        product_name: str,
        quantity: Decimal,
        unit_price: Decimal,
        description: Optional[str] = None,
        unit_of_measure: str = 'PCS',
        discount_percentage: Decimal = Decimal('0'),
        tax_percentage: Decimal = Decimal('15'),
        line_number: int = 1,
        id: Optional[str] = None,
    ):
        import uuid
        self.id = id or str(uuid.uuid4())
        self.line_number = line_number
        self.product_id = product_id
        self.product_name = product_name
        self.description = description
        self.quantity = quantity
        self.unit_of_measure = unit_of_measure
        self.unit_price = unit_price
        self.discount_percentage = discount_percentage
        self.tax_percentage = tax_percentage
        self.line_total = self._calculate_line_total()
    
    def _calculate_line_total(self) -> Decimal:
        """حساب إجمالي السطر"""
        base_amount = self.quantity * self.unit_price
        discount = base_amount * (self.discount_percentage / Decimal('100'))
        return base_amount - discount
    
    def to_dict(self) -> dict:
        """تحويل العنصر إلى قاموس"""
        return {
            'id': self.id,
            'line_number': self.line_number,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'description': self.description,
            'quantity': str(self.quantity),
            'unit_of_measure': self.unit_of_measure,
            'unit_price': str(self.unit_price),
            'discount_percentage': str(self.discount_percentage),
            'tax_percentage': str(self.tax_percentage),
            'line_total': str(self.line_total),
        }
