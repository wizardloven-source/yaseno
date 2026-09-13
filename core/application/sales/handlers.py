# core/application/sales/handlers.py
"""
Sales Command Handlers - معالجات الأوامر لوحدة المبيعات
✅ SalesQuotation Handlers
✅ SalesOrder Handlers
✅ Delivery Handlers
✅ SalesReturn Handlers (NEW - PHASE 1)
"""

from typing import Optional
from decimal import Decimal

from core.domain.sales.entities import (
    SalesQuotation, QuotationItem,
    SalesOrder, OrderItem,
    DeliveryNote, DeliveryItem,
    SalesReturn, ReturnItem
)
from core.domain.sales.value_objects import ShippingAddress, PaymentTerms
from core.domain.shared.value_objects import Money
from core.domain.sales.interfaces import IQuotationRepository, IOrderRepository, IDeliveryRepository, IReturnRepository
from core.application.sales.commands import (
    CreateQuotationCommand, UpdateQuotationCommand, SendQuotationCommand,
    AcceptQuotationCommand, RejectQuotationCommand, ConvertQuotationCommand,
    CreateOrderCommand, ConfirmOrderCommand, CancelOrderCommand,
    CreateDeliveryCommand, ScheduleDeliveryCommand, CompleteDeliveryCommand,
    CreateSalesReturnCommand, SubmitSalesReturnCommand, ApproveSalesReturnCommand,
    RejectSalesReturnCommand, ReceiveSalesReturnCommand, InspectSalesReturnCommand,
    CompleteSalesReturnCommand, CancelSalesReturnCommand
)
from core.shared.exceptions import ValidationError, NotFoundError


class CreateQuotationHandler:
    """معالج إنشاء عرض سعر"""
    
    def __init__(self, quotation_repository: IQuotationRepository):
        self.repository = quotation_repository
    
    async def handle(self, command: CreateQuotationCommand) -> SalesQuotation:
        # إنشاء عرض السعر
        quotation = SalesQuotation.create(
            customer_id=command.customer_id,
            customer_name=command.customer_name,
            customer_branch_id=command.customer_branch_id,
            customer_branch_name=command.customer_branch_name,
            currency=command.currency,
            valid_days=command.valid_days,
            sales_person_id=command.sales_person_id,
            sales_person_name=command.sales_person_name,
            sequence=command.sequence or await self.repository.get_next_sequence()
        )
        
        # إضافة العناصر
        for item_cmd in command.items:
            unit_price = Money(item_cmd.unit_price_amount, item_cmd.currency)
            
            # حساب الضريبة
            tax_amount = Money.zero(item_cmd.currency)
            if item_cmd.tax_rate > 0:
                base_amount = unit_price.amount * Decimal(str(item_cmd.quantity))
                if item_cmd.discount_percent > 0:
                    base_amount = base_amount * (Decimal('1') - item_cmd.discount_percent / Decimal('100'))
                tax_amount = Money(base_amount * (item_cmd.tax_rate / Decimal('100')), item_cmd.currency)
            
            quotation.add_item(QuotationItem(
                product_code=item_cmd.product_code,
                product_name=item_cmd.product_name,
                quantity=item_cmd.quantity,
                unit_price=unit_price,
                discount_percent=item_cmd.discount_percent,
                tax_rate=item_cmd.tax_rate,
                tax_amount=tax_amount,
                notes=item_cmd.notes
            ))
        
        # تعيين الخصم العام
        if command.global_discount_percent > 0:
            quotation.global_discount_percent = command.global_discount_percent
        elif command.global_discount_amount > 0:
            quotation.global_discount_amount = Money(command.global_discount_amount, command.currency)
        
        # تعيين الملاحظات
        quotation.notes = command.notes
        quotation.internal_notes = command.internal_notes
        
        # تعيين عنوان الشحن
        if command.shipping_address_street:
            quotation.shipping_address = ShippingAddress(
                street=command.shipping_address_street,
                city=command.shipping_address_city or "",
                state=command.shipping_address_state or "",
                postal_code=command.shipping_address_postal_code or "",
                country=command.shipping_address_country or "SA"
            )
        
        # تعيين شروط الدفع
        if command.payment_terms_days > 0:
            quotation.payment_terms = PaymentTerms(days=command.payment_terms_days)
        
        # حفظ وعرض النتيجة
        return await self.repository.save(quotation)


class UpdateQuotationHandler:
    """معالج تحديث عرض السعر"""
    
    def __init__(self, quotation_repository: IQuotationRepository):
        self.repository = quotation_repository
    
    async def handle(self, command: UpdateQuotationCommand) -> SalesQuotation:
        # الحصول على عرض السعر
        from core.domain.sales.value_objects import QuotationId
        quotation = await self.repository.get_by_id(QuotationId(command.quotation_id))
        
        if not quotation:
            raise NotFoundError(f"Quotation not found with ID: {command.quotation_id}")
        
        # التحقق من الحالة
        if quotation.status.name != 'DRAFT':
            raise ValidationError("Only draft quotations can be updated")
        
        # تحديث البيانات الأساسية
        if command.customer_name:
            quotation.customer_name = command.customer_name
        if command.customer_branch_name:
            quotation.customer_branch_name = command.customer_branch_name
        
        # تحديث العناصر إذا تم توفيرها
        if command.items is not None:
            quotation.items = []
            for item_cmd in command.items:
                unit_price = Money(item_cmd.unit_price_amount, item_cmd.currency)
                
                tax_amount = Money.zero(item_cmd.currency)
                if item_cmd.tax_rate > 0:
                    base_amount = unit_price.amount * Decimal(str(item_cmd.quantity))
                    if item_cmd.discount_percent > 0:
                        base_amount = base_amount * (Decimal('1') - item_cmd.discount_percent / Decimal('100'))
                    tax_amount = Money(base_amount * (item_cmd.tax_rate / Decimal('100')), item_cmd.currency)
                
                quotation.add_item(QuotationItem(
                    product_code=item_cmd.product_code,
                    product_name=item_cmd.product_name,
                    quantity=item_cmd.quantity,
                    unit_price=unit_price,
                    discount_percent=item_cmd.discount_percent,
                    tax_rate=item_cmd.tax_rate,
                    tax_amount=tax_amount,
                    notes=item_cmd.notes
                ))
        
        # تحديث الخصم العام
        if command.global_discount_percent is not None:
            quotation.global_discount_percent = command.global_discount_percent
        if command.global_discount_amount is not None:
            quotation.global_discount_amount = Money(command.global_discount_amount, quotation.currency)
        
        # تحديث الملاحظات
        if command.notes is not None:
            quotation.notes = command.notes
        if command.internal_notes is not None:
            quotation.internal_notes = command.internal_notes
        
        # حفظ
        return await self.repository.save(quotation)


class SendQuotationHandler:
    """معالج إرسال عرض السعر"""
    
    def __init__(self, quotation_repository: IQuotationRepository):
        self.repository = quotation_repository
    
    async def handle(self, command: SendQuotationCommand) -> SalesQuotation:
        from core.domain.sales.value_objects import QuotationId
        
        quotation = await self.repository.get_by_id(QuotationId(command.quotation_id))
        
        if not quotation:
            raise NotFoundError(f"Quotation not found with ID: {command.quotation_id}")
        
        quotation.send()
        return await self.repository.save(quotation)


class AcceptQuotationHandler:
    """معالج قبول عرض السعر"""
    
    def __init__(self, quotation_repository: IQuotationRepository):
        self.repository = quotation_repository
    
    async def handle(self, command: AcceptQuotationCommand) -> SalesQuotation:
        from core.domain.sales.value_objects import QuotationId
        
        quotation = await self.repository.get_by_id(QuotationId(command.quotation_id))
        
        if not quotation:
            raise NotFoundError(f"Quotation not found with ID: {command.quotation_id}")
        
        quotation.accept()
        return await self.repository.save(quotation)


class RejectQuotationHandler:
    """معالج رفض عرض السعر"""
    
    def __init__(self, quotation_repository: IQuotationRepository):
        self.repository = quotation_repository
    
    async def handle(self, command: RejectQuotationCommand) -> SalesQuotation:
        from core.domain.sales.value_objects import QuotationId
        
        quotation = await self.repository.get_by_id(QuotationId(command.quotation_id))
        
        if not quotation:
            raise NotFoundError(f"Quotation not found with ID: {command.quotation_id}")
        
        quotation.reject(reason=command.reason)
        return await self.repository.save(quotation)


class ConvertQuotationHandler:
    """معالج تحويل عرض السعر إلى أمر بيع"""
    
    def __init__(self, quotation_repository: IQuotationRepository, order_repository: IOrderRepository):
        self.quotation_repository = quotation_repository
        self.order_repository = order_repository
    
    async def handle(self, command: ConvertQuotationCommand) -> SalesOrder:
        from core.domain.sales.value_objects import QuotationId
        
        quotation = await self.quotation_repository.get_by_id(QuotationId(command.quotation_id))
        
        if not quotation:
            raise NotFoundError(f"Quotation not found with ID: {command.quotation_id}")
        
        # التحويل
        order_sequence = await self.order_repository.get_next_sequence()
        order = quotation.convert_to_order()
        order.order_number = type(order.order_number).generate(prefix="SO", sequence=order_sequence)
        
        # حفظ أمر البيع
        saved_order = await self.order_repository.save(order)
        
        # تحديث عرض السعر المحول
        quotation.converted_to_order_id = str(saved_order.id.value)
        await self.quotation_repository.save(quotation)
        
        return saved_order


class CreateOrderHandler:
    """معالج إنشاء أمر بيع"""
    
    def __init__(self, order_repository: IOrderRepository):
        self.repository = order_repository
    
    async def handle(self, command: CreateOrderCommand) -> SalesOrder:
        # إنشاء أمر البيع
        order = SalesOrder.create(
            customer_id=command.customer_id,
            customer_name=command.customer_name,
            customer_branch_id=command.customer_branch_id,
            customer_branch_name=command.customer_branch_name,
            currency=command.currency,
            sales_person_id=command.sales_person_id,
            sales_person_name=command.sales_person_name,
            source_quotation_id=command.source_quotation_id,
            sequence=command.sequence or await self.repository.get_next_sequence()
        )
        
        # إضافة العناصر
        for item_cmd in command.items:
            unit_price = Money(item_cmd.unit_price_amount, item_cmd.currency)
            
            tax_amount = Money.zero(item_cmd.currency)
            if item_cmd.tax_rate > 0:
                base_amount = unit_price.amount * Decimal(str(item_cmd.quantity))
                if item_cmd.discount_percent > 0:
                    base_amount = base_amount * (Decimal('1') - item_cmd.discount_percent / Decimal('100'))
                tax_amount = Money(base_amount * (item_cmd.tax_rate / Decimal('100')), item_cmd.currency)
            
            order.add_item(OrderItem(
                product_code=item_cmd.product_code,
                product_name=item_cmd.product_name,
                quantity=item_cmd.quantity,
                unit_price=unit_price,
                discount_percent=item_cmd.discount_percent,
                tax_rate=item_cmd.tax_rate,
                tax_amount=tax_amount,
                notes=item_cmd.notes,
                warehouse_id=item_cmd.warehouse_id
            ))
        
        # تعيين الخصم العام
        if command.global_discount_percent > 0:
            order.global_discount_percent = command.global_discount_percent
        elif command.global_discount_amount > 0:
            order.global_discount_amount = Money(command.global_discount_amount, command.currency)
        
        # تعيين البيانات الأخرى
        order.notes = command.notes
        order.internal_notes = command.internal_notes
        
        if command.required_date:
            order.required_date = command.required_date
        
        if command.shipping_address_street:
            order.shipping_address = ShippingAddress(
                street=command.shipping_address_street,
                city=command.shipping_address_city or "",
                state=command.shipping_address_state or "",
                postal_code=command.shipping_address_postal_code or "",
                country=command.shipping_address_country or "SA"
            )
        
        if command.payment_terms_days > 0:
            order.payment_terms = PaymentTerms(days=command.payment_terms_days)
        
        return await self.repository.save(order)


class ConfirmOrderHandler:
    """معالج تأكيد أمر البيع"""
    
    def __init__(self, order_repository: IOrderRepository):
        self.repository = order_repository
    
    async def handle(self, command: ConfirmOrderCommand) -> SalesOrder:
        from core.domain.sales.value_objects import OrderId
        
        order = await self.repository.get_by_id(OrderId(command.order_id))
        
        if not order:
            raise NotFoundError(f"Order not found with ID: {command.order_id}")
        
        order.confirm()
        return await self.repository.save(order)


class CancelOrderHandler:
    """معالج إلغاء أمر البيع"""
    
    def __init__(self, order_repository: IOrderRepository):
        self.repository = order_repository
    
    async def handle(self, command: CancelOrderCommand) -> SalesOrder:
        from core.domain.sales.value_objects import OrderId
        
        order = await self.repository.get_by_id(OrderId(command.order_id))
        
        if not order:
            raise NotFoundError(f"Order not found with ID: {command.order_id}")
        
        order.cancel(reason=command.reason)
        return await self.repository.save(order)


class CreateDeliveryHandler:
    """معالج إنشاء إشعار تسليم"""
    
    def __init__(self, delivery_repository: IDeliveryRepository):
        self.repository = delivery_repository
    
    async def handle(self, command: CreateDeliveryCommand) -> DeliveryNote:
        delivery = DeliveryNote.create(
            customer_id=command.customer_id,
            customer_name=command.customer_name,
            order_id=command.order_id,
            order_number=command.order_number,
            sequence=command.sequence or await self.repository.get_next_sequence()
        )
        
        # إضافة العناصر
        for item_cmd in command.items:
            delivery.add_item(DeliveryItem(
                product_code=item_cmd.product_code,
                product_name=item_cmd.product_name,
                quantity=item_cmd.quantity,
                order_item_line_id=item_cmd.order_item_line_id
            ))
        
        # تعيين بيانات الشحن
        if command.shipping_address_street:
            delivery.shipping_address = ShippingAddress(
                street=command.shipping_address_street,
                city=command.shipping_address_city or "",
                state=command.shipping_address_state or "",
                postal_code=command.shipping_address_postal_code or "",
                country=command.shipping_address_country or "SA"
            )
        
        delivery.carrier = command.carrier
        delivery.vehicle_number = command.vehicle_number
        delivery.driver_name = command.driver_name
        delivery.driver_phone = command.driver_phone
        delivery.notes = command.notes
        
        if command.scheduled_date:
            delivery.scheduled_date = command.scheduled_date
        
        return await self.repository.save(delivery)


class ScheduleDeliveryHandler:
    """معالج جدولة إشعار التسليم"""
    
    def __init__(self, delivery_repository: IDeliveryRepository):
        self.repository = delivery_repository
    
    async def handle(self, command: ScheduleDeliveryCommand) -> DeliveryNote:
        from core.domain.sales.value_objects import DeliveryId
        
        delivery = await self.repository.get_by_id(DeliveryId(command.delivery_id))
        
        if not delivery:
            raise NotFoundError(f"Delivery not found with ID: {command.delivery_id}")
        
        delivery.schedule(command.scheduled_date)
        return await self.repository.save(delivery)


class CompleteDeliveryHandler:
    """معالج إكمال إشعار التسليم"""
    
    def __init__(self, delivery_repository: IDeliveryRepository):
        self.repository = delivery_repository
    
    async def handle(self, command: CompleteDeliveryCommand) -> DeliveryNote:
        from core.domain.sales.value_objects import DeliveryId
        
        delivery = await self.repository.get_by_id(DeliveryId(command.delivery_id))
        
        if not delivery:
            raise NotFoundError(f"Delivery not found with ID: {command.delivery_id}")
        
        delivery.mark_delivered(received_by=command.received_by)
        return await self.repository.save(delivery)
