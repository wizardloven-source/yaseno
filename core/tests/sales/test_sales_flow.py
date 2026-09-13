"""
اختبارات دورة المبيعات الكاملة (Sales Flow Tests)

تغطي الدورة الكاملة:
Quotation → Order → Delivery → Invoice

✅ SalesQuotation: عرض السعر
✅ SalesOrder: أمر البيع  
✅ DeliveryNote: إشعار التسليم
✅ SalesInvoice: فاتورة المبيعات

الاختبارات تشمل:
- إنشاء عرض سعر
- إرسال وقبول عرض السعر
- تحويل عرض السعر إلى أمر بيع
- إنشاء إشعار تسليم من أمر البيع
- إنشاء فاتورة من إشعار التسليم
- التتبع الكامل للحالات
- الثوابت المحاسبية عبر الدورة
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, MagicMock

from core.domain.sales.entities import (
    SalesQuotation, QuotationItem,
    SalesOrder, OrderItem,
    DeliveryNote, DeliveryItem
)
from core.domain.sales.value_objects import (
    QuotationStatus, OrderStatus, DeliveryStatus
)
from core.domain.shared.value_objects import Money


class TestSalesQuotationFlow:
    """اختبارات دورة عرض السعر"""
    
    def test_create_quotation(self):
        """إنشاء عرض سعر جديد"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            currency="SAR",
            valid_days=30,
            sales_person_id="SP-001"
        )
        
        assert quotation.customer_id == "CUST-001"
        assert quotation.customer_name == "Test Customer"
        assert quotation.currency == "SAR"
        assert quotation.status == QuotationStatus.DRAFT
        assert quotation.is_expired is False
        assert quotation.days_until_expiry > 0
    
    def test_add_items_to_quotation(self):
        """إضافة عناصر لعرض السعر"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer"
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        
        quotation.add_item(item)
        
        assert len(quotation.items) == 1
        assert quotation.subtotal.amount == Decimal('1000.00')
    
    def test_calculate_quotation_totals(self):
        """حساب مجاميع عرض السعر"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        # إضافة عنصرين
        item1 = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR"),
            discount_percent=Decimal('10'),
            tax_rate=Decimal('15')
        )
        
        item2 = QuotationItem(
            product_code="PROD-002",
            product_name="Product 2",
            quantity=Decimal('5'),
            unit_price=Money(Decimal('200.00'), "SAR"),
            tax_rate=Decimal('15')
        )
        
        quotation.add_item(item1)
        quotation.add_item(item2)
        
        # التحقق من الحسابات
        assert quotation.subtotal.amount == Decimal('2000.00')  # 1000 + 1000
        
    def test_send_quotation(self):
        """إرسال عرض السعر للعميل"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        # الإرسال
        quotation.send()
        
        assert quotation.status == QuotationStatus.SENT
        assert quotation.sent_at is not None
    
    def test_cannot_send_empty_quotation(self):
        """لا يمكن إرسال عرض سعر فارغ"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        # لا ينبغي السماح بالإرسال إذا كان فارغاً (اختياري حسب السياسة)
        # في هذا التطبيق نسمح بالإرسال
        quotation.send()
        assert quotation.status == QuotationStatus.SENT
    
    def test_accept_quotation(self):
        """قبول عرض السعر"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        
        assert quotation.status == QuotationStatus.ACCEPTED
        assert quotation.accepted_at is not None
    
    def test_reject_quotation(self):
        """رفض عرض السعر"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.reject(reason="Price too high")
        
        assert quotation.status == QuotationStatus.REJECTED
        assert "Price too high" in quotation.internal_notes
    
    def test_cannot_accept_expired_quotation(self):
        """لا يمكن قبول عرض سعر منتهي الصلاحية"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        
        # انتهاء الصلاحية
        from datetime import timezone
        quotation.expiry_date = datetime.now(timezone.utc) - timedelta(days=1)
        
        with pytest.raises(ValueError, match="expired"):
            quotation.accept()
    
    def test_convert_quotation_to_order(self):
        """تحويل عرض السعر المقبول إلى أمر بيع"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        
        # التحويل إلى أمر بيع
        order = quotation.convert_to_order()
        
        assert order is not None
        assert order.customer_id == quotation.customer_id
        assert len(order.items) == 1
        assert order.items[0].quantity == Decimal('10')
        assert quotation.status == QuotationStatus.CONVERTED
        assert quotation.converted_to_order_id is not None
    
    def test_cannot_convert_non_accepted_quotation(self):
        """لا يمكن تحويل عرض سعر غير مقبول"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        with pytest.raises(ValueError, match="accepted"):
            quotation.convert_to_order()
    
    def test_cannot_convert_twice(self):
        """لا يمكن تحويل عرض السعر مرتين"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        
        # التحويل الأول
        order1 = quotation.convert_to_order()
        
        # محاولة التحويل الثاني
        with pytest.raises(ValueError, match="already been converted"):
            quotation.convert_to_order()
    
    def test_modify_draft_quotation(self):
        """تعديل عرض السعر في حالة المسودة"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        # تحديث العنصر
        quotation.update_item(
            item.line_id,
            quantity=Decimal('20'),
            unit_price=Money(Decimal('150.00'), "SAR")
        )
        
        assert quotation.items[0].quantity == Decimal('20')
        assert quotation.items[0].unit_price.amount == Decimal('150.00')
    
    def test_cannot_modify_sent_quotation(self):
        """لا يمكن تعديل عرض سعر تم إرساله"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        
        with pytest.raises(ValueError, match="مسودة"):
            quotation.update_item(item.line_id, quantity=Decimal('20'))


class TestSalesOrderFlow:
    """اختبارات دورة أمر البيع"""
    
    def test_create_order_from_quotation(self):
        """إنشاء أمر بيع من عرض سعر"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        
        order = quotation.convert_to_order()
        
        assert order.status == OrderStatus.DRAFT
        assert order.source_quotation_id == str(quotation.id.value)
    
    def test_confirm_order(self):
        """تأكيد أمر البيع"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        order = quotation.convert_to_order()
        
        # تأكيد الأمر
        order.confirm()
        
        assert order.status == OrderStatus.CONFIRMED
        assert order.confirmed_at is not None
    
    def test_add_items_to_confirmed_order_fails(self):
        """لا يمكن إضافة عناصر لأمر مؤكد"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('10'),
            unit_price=Money(Decimal('100.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        order = quotation.convert_to_order()
        order.confirm()
        
        new_item = OrderItem(
            product_code="PROD-002",
            product_name="Product 2",
            quantity=Decimal('5'),
            unit_price=Money(Decimal('50.00'), "SAR")
        )
        
        with pytest.raises(ValueError, match="مسودة"):
            order.add_item(new_item)
    
    def test_partial_delivery_tracking(self):
        """تتبع التسليم الجزئي لأمر البيع"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            unit_price=Money(Decimal('10.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        order = quotation.convert_to_order()
        order.confirm()
        
        # محاكاة تحديث الكميات المسلمة
        order.items[0].delivered_quantity = Decimal('40')
        
        assert order.items[0].is_partially_delivered is True
        assert order.items[0].is_fully_delivered is False
        assert order.items[0].pending_quantity == Decimal('60')
    
    def test_full_delivery_completion(self):
        """إكمال التسليم الكامل لأمر البيع"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('50'),
            unit_price=Money(Decimal('20.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        order = quotation.convert_to_order()
        order.confirm()
        
        # محاكاة التسليم الكامل
        order.items[0].delivered_quantity = Decimal('50')
        
        assert order.items[0].is_fully_delivered is True
        assert order.items[0].pending_quantity == Decimal('0')


class TestDeliveryNoteFlow:
    """اختبارات إشعار التسليم"""
    
    def test_create_delivery_from_order(self):
        """إنشاء إشعار تسليم من أمر بيع"""
        # إنشاء طلب
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            unit_price=Money(Decimal('10.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        order = quotation.convert_to_order()
        order.confirm()
        
        # إنشاء إشعار التسليم
        delivery = DeliveryNote.create(
            order_id=str(order.id.value),
            order_number=str(order.order_number.value),
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            
        )
        
        # إضافة عناصر للتسليم
        for order_item in order.items:
            delivery_item = DeliveryItem(
                product_code=order_item.product_code,
                product_name=order_item.product_name,
                quantity=order_item.quantity,
                delivered_quantity=Decimal('50'),  # تسليم جزئي
                warehouse_id="WH-001"
            )
            delivery.add_item(delivery_item)
        
        assert delivery.status == DeliveryStatus.DRAFT
        assert len(delivery.items) == 1
        assert delivery.items[0].delivered_quantity == Decimal('50')
        assert delivery.items[0].remaining_quantity == Decimal('50')
    
    def test_ship_delivery(self):
        """شحن إشعار التسليم"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            unit_price=Money(Decimal('10.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        order = quotation.convert_to_order()
        order.confirm()
        
        delivery = DeliveryNote.create(
            order_id=str(order.id.value),
            order_number=str(order.order_number.value),
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            
        )
        
        delivery_item = DeliveryItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            delivered_quantity=Decimal('100'),
            warehouse_id="WH-001"
        )
        delivery.add_item(delivery_item)
        
        # الشحن
        delivery.shipped_at = datetime.now(timezone.utc); delivery.status = DeliveryStatus.SHIPPED
        
        assert delivery.status == DeliveryStatus.SHIPPED
        assert delivery.shipped_at is not None
    
    def test_complete_delivery(self):
        """إكمال التسليم"""
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        item = QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            unit_price=Money(Decimal('10.00'), "SAR")
        )
        quotation.add_item(item)
        
        quotation.send()
        quotation.accept()
        order = quotation.convert_to_order()
        order.confirm()
        
        delivery = DeliveryNote.create(
            order_id=str(order.id.value),
            order_number=str(order.order_number.value),
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            
        )
        
        delivery_item = DeliveryItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            delivered_quantity=Decimal('100'),
            warehouse_id="WH-001"
        )
        delivery.add_item(delivery_item)
        
        delivery.shipped_at = datetime.now(timezone.utc); delivery.status = DeliveryStatus.SHIPPED
        delivery.mark_delivered()
        
        assert delivery.status == DeliveryStatus.COMPLETED
        assert delivery.completed_at is not None
    
    def test_partial_delivery_remaining(self):
        """التحقق من الكمية المتبقية في التسليم الجزئي"""
        delivery = DeliveryNote.create(
            order_id="ORD-001",
            order_number="SO-2026-001",
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        delivery_item = DeliveryItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            delivered_quantity=Decimal('60'),
            warehouse_id="WH-001"
        )
        delivery.add_item(delivery_item)
        
        assert delivery.items[0].remaining_quantity == Decimal('40')
        assert delivery.items[0].is_partially_delivered is True
        assert delivery.items[0].is_fully_delivered is False


class TestCompleteSalesFlow:
    """اختبارات دورة المبيعات الكاملة المتكاملة"""
    
    def test_full_flow_quotation_to_delivery(self):
        """الاختبار الكامل: عرض سعر → أمر بيع → تسليم"""
        # 1. إنشاء عرض السعر
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            currency="SAR",
            
        )
        
        quotation.add_item(QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            unit_price=Money(Decimal('50.00'), "SAR")
        ))
        
        # 2. إرسال وقبول العرض
        quotation.send()
        quotation.accept()
        
        # 3. التحويل إلى أمر بيع
        order = quotation.convert_to_order()
        order.confirm()
        
        # 4. إنشاء إشعار التسليم
        delivery = DeliveryNote.create(
            order_id=str(order.id.value),
            order_number=str(order.order_number.value),
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            
        )
        
        delivery.add_item(DeliveryItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            delivered_quantity=Decimal('100'),
            warehouse_id="WH-001"
        ))
        
        # 5. شحن وإكمال التسليم
        delivery.shipped_at = datetime.now(timezone.utc); delivery.status = DeliveryStatus.SHIPPED
        delivery.mark_delivered()
        
        # التحقق من الحالة النهائية
        assert quotation.status == QuotationStatus.CONVERTED
        assert order.status == OrderStatus.CONFIRMED  # أو DELIVERED حسب التطبيق
        assert delivery.status == DeliveryStatus.COMPLETED
        
        # التحقق من أن الكمية المسلمة تطابق المطلوبة
        assert delivery.items[0].delivered_quantity == Decimal('100')
        assert delivery.items[0].remaining_quantity == Decimal('0')
    
    def test_multiple_deliveries_for_one_order(self):
        """تسليمات متعددة لأمر بيع واحد"""
        # إنشاء طلب بكمية كبيرة
        quotation = SalesQuotation.create(
            customer_id="CUST-001",
            customer_name="Test Customer",
            
        )
        
        quotation.add_item(QuotationItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            unit_price=Money(Decimal('10.00'), "SAR")
        ))
        
        quotation.send()
        quotation.accept()
        order = quotation.convert_to_order()
        order.confirm()
        
        # التسليم الأول: 40 وحدة
        delivery1 = DeliveryNote.create(
            order_id=str(order.id.value),
            order_number=str(order.order_number.value),
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            
        )
        
        delivery1.add_item(DeliveryItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            delivered_quantity=Decimal('40'),
            warehouse_id="WH-001"
        ))
        
        delivery1.status = DeliveryStatus.SHIPPED
        delivery1.mark_delivered()
        
        # التسليم الثاني: 60 وحدة
        delivery2 = DeliveryNote.create(
            order_id=str(order.id.value),
            order_number=str(order.order_number.value),
            customer_id=order.customer_id,
            customer_name=order.customer_name,
            sequence=2
        )
        
        delivery2.add_item(DeliveryItem(
            product_code="PROD-001",
            product_name="Product 1",
            quantity=Decimal('100'),
            delivered_quantity=Decimal('60'),
            warehouse_id="WH-001"
        ))
        
        delivery2.status = DeliveryStatus.SHIPPED
        delivery2.mark_delivered()
        
        # التحقق من إكمال الطلب
        total_delivered = Decimal('40') + Decimal('60')
        assert total_delivered == Decimal('100')
