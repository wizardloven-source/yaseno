"""
Sales Quotation Command Handlers
معالجات أوامر عروض الأسعار
"""

from typing import Optional
from datetime import date
import uuid
from decimal import Decimal

from core.domain.sales_cycle.entities import SalesQuotation, QuotationItem
from core.domain.sales_cycle.value_objects import QuotationStatus, Address, Money
from core.domain.shared.value_objects import Currency
from core.application.sales_cycle.commands.quotation_commands import (
    CreateQuotationCommand,
    UpdateQuotationCommand,
    SendQuotationCommand,
    AcceptQuotationCommand,
    RejectQuotationCommand,
    ConvertQuotationToOrderCommand,
    QuotationItemCommand,
    AddressCommand,
)
from core.infrastructure.database.db_manager import DatabaseManager


class CreateQuotationHandler:
    """معالج إنشاء عرض سعر جديد"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def handle(self, command: CreateQuotationCommand):
        """إنشاء عرض سعر جديد"""
        try:
            # تحويل العناصر من Command إلى Domain Entities
            items = []
            for item_cmd in command.items:
                item = QuotationItem(
                    product_id=item_cmd.product_id,
                    product_name=item_cmd.product_name,
                    quantity=Decimal(str(item_cmd.quantity)),
                    unit_price=Decimal(str(item_cmd.unit_price)),
                    discount_percent=Decimal(str(item_cmd.discount_percent)),
                    tax_percent=Decimal(str(item_cmd.tax_percent)),
                    unit=item_cmd.unit,
                    notes=item_cmd.notes
                )
                items.append(item)
            
            # تحويل العناوين
            billing_address = None
            if command.billing_address:
                addr = command.billing_address
                billing_address = Address(
                    street=addr.street,
                    city=addr.city,
                    state=addr.state,
                    postal_code=addr.postal_code,
                    country=addr.country,
                    building_number=addr.building_number,
                    unit_number=addr.unit_number,
                    district=addr.district
                )
            
            shipping_address = None
            if command.shipping_address:
                addr = command.shipping_address
                shipping_address = Address(
                    street=addr.street,
                    city=addr.city,
                    state=addr.state,
                    postal_code=addr.postal_code,
                    country=addr.country,
                    building_number=addr.building_number,
                    unit_number=addr.unit_number,
                    district=addr.district
                )
            
            # تحديد تاريخ الانتهاء إذا لم يتم تحديده
            expiry_date = command.expiry_date
            if not expiry_date:
                from datetime import timedelta
                expiry_date = command.issue_date + timedelta(days=30)
            
            # إنشاء عرض السعر
            quotation = SalesQuotation.create(
                customer_id=command.customer_id,
                customer_name=command.customer_name,
                currency=Currency(command.currency),
                issue_date=command.issue_date,
                expiry_date=expiry_date,
                items=items,
                billing_address=billing_address,
                shipping_address=shipping_address,
                global_discount_percent=Decimal(str(command.global_discount_percent)),
                global_discount_amount=Decimal(str(command.global_discount_amount)),
                notes=command.notes,
                internal_notes=command.internal_notes,
                sales_person_id=command.sales_person_id,
                sales_person_name=command.sales_person_name,
                branch_id=command.branch_id,
                company_id=command.company_id,
                custom_fields=command.custom_fields,
                created_by="system"  # Should come from user context
            )
            
            # حفظ في قاعدة البيانات
            with self.db.session() as session:
                from core.infrastructure.sales_cycle.models import SalesQuotationModel
                model = SalesQuotationModel.from_domain(quotation)
                session.add(model)
                session.commit()
                
                return {
                    "id": str(quotation.id.value),
                    "quotation_number": str(quotation.quotation_number),
                    "status": quotation.status.value,
                    "total_amount": float(quotation.total_amount),
                    "currency": quotation.currency.value
                }
        
        except Exception as e:
            raise Exception(f"فشل إنشاء عرض السعر: {str(e)}")


class UpdateQuotationHandler:
    """معالج تحديث عرض السعر"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def handle(self, command: UpdateQuotationCommand):
        """تحديث عرض سعر موجود"""
        try:
            with self.db.session() as session:
                from core.infrastructure.sales_cycle.models import SalesQuotationModel
                model = session.query(SalesQuotationModel).filter(
                    SalesQuotationModel.id == uuid.UUID(command.quotation_id)
                ).first()
                
                if not model:
                    raise ValueError("عرض السعر غير موجود")
                
                if model.status != QuotationStatus.DRAFT.value:
                    raise ValueError("يمكن فقط تعديل عروض المسودات")
                
                # تحديث الحقول
                if command.customer_name:
                    model.customer_name = command.customer_name
                if command.currency:
                    model.currency = command.currency
                if command.expiry_date:
                    model.expiry_date = command.expiry_date
                if command.notes is not None:
                    model.notes = command.notes
                if command.internal_notes is not None:
                    model.internal_notes = command.internal_notes
                
                # تحديث العناصر إذا تم تقديمها
                if command.items is not None:
                    # حذف العناصر القديمة وإضافة الجديدة
                    session.query(SalesQuotationModel.items).filter(
                        SalesQuotationModel.id == model.id
                    ).delete()
                    
                    for item_cmd in command.items:
                        new_item = QuotationItem(
                            product_id=item_cmd.product_id,
                            product_name=item_cmd.product_name,
                            quantity=Decimal(str(item_cmd.quantity)),
                            unit_price=Decimal(str(item_cmd.unit_price)),
                            discount_percent=Decimal(str(item_cmd.discount_percent)),
                            tax_percent=Decimal(str(item_cmd.tax_percent)),
                            unit=item_cmd.unit,
                            notes=item_cmd.notes
                        )
                        model.items.append(new_item)
                
                # إعادة حساب المجاميع
                model.calculate_totals()
                
                session.commit()
                
                return {
                    "id": str(model.id),
                    "status": model.status,
                    "message": "تم التحديث بنجاح"
                }
        
        except Exception as e:
            raise Exception(f"فشل تحديث عرض السعر: {str(e)}")


class SendQuotationHandler:
    """معالج إرسال عرض السعر"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def handle(self, command: SendQuotationCommand):
        """إرسال عرض السعر للعميل"""
        try:
            with self.db.session() as session:
                from core.infrastructure.sales_cycle.models import SalesQuotationModel
                model = session.query(SalesQuotationModel).filter(
                    SalesQuotationModel.id == uuid.UUID(command.quotation_id)
                ).first()
                
                if not model:
                    raise ValueError("عرض السعر غير موجود")
                
                if model.status != QuotationStatus.DRAFT.value:
                    raise ValueError("يمكن فقط إرسال عروض المسودات")
                
                # تغيير الحالة إلى sent
                model.status = QuotationStatus.SENT.value
                model.sent_at = date.today()
                model.sent_via = command.sent_via
                
                session.commit()
                
                # TODO: إرسال فعلي عبر البريد الإلكتروني أو WhatsApp
                # هنا يمكن دمج مع خدمة الإشعارات
                
                return {
                    "id": str(model.id),
                    "status": model.status,
                    "sent_via": command.sent_via,
                    "message": "تم إرسال عرض السعر بنجاح"
                }
        
        except Exception as e:
            raise Exception(f"فشل إرسال عرض السعر: {str(e)}")


class AcceptQuotationHandler:
    """معالج قبول عرض السعر"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def handle(self, command: AcceptQuotationCommand):
        """قبول عرض السعر"""
        try:
            with self.db.session() as session:
                from core.infrastructure.sales_cycle.models import SalesQuotationModel
                model = session.query(SalesQuotationModel).filter(
                    SalesQuotationModel.id == uuid.UUID(command.quotation_id)
                ).first()
                
                if not model:
                    raise ValueError("عرض السعر غير موجود")
                
                if model.status not in [QuotationStatus.DRAFT.value, QuotationStatus.SENT.value]:
                    raise ValueError("لا يمكن قبول هذا العرض في حالته الحالية")
                
                # تغيير الحالة إلى accepted
                model.status = QuotationStatus.ACCEPTED.value
                model.accepted_at = date.today()
                model.accepted_by = command.accepted_by
                model.acceptance_notes = command.acceptance_notes
                
                session.commit()
                
                return {
                    "id": str(model.id),
                    "status": model.status,
                    "message": "تم قبول عرض السعر بنجاح"
                }
        
        except Exception as e:
            raise Exception(f"فشل قبول عرض السعر: {str(e)}")


class RejectQuotationHandler:
    """معالج رفض عرض السعر"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def handle(self, command: RejectQuotationCommand):
        """رفض عرض السعر"""
        try:
            with self.db.session() as session:
                from core.infrastructure.sales_cycle.models import SalesQuotationModel
                model = session.query(SalesQuotationModel).filter(
                    SalesQuotationModel.id == uuid.UUID(command.quotation_id)
                ).first()
                
                if not model:
                    raise ValueError("عرض السعر غير موجود")
                
                if not command.reason:
                    raise ValueError("يجب تحديد سبب الرفض")
                
                if model.status not in [QuotationStatus.DRAFT.value, QuotationStatus.SENT.value]:
                    raise ValueError("لا يمكن رفض هذا العرض في حالته الحالية")
                
                # تغيير الحالة إلى rejected
                model.status = QuotationStatus.REJECTED.value
                model.rejected_at = date.today()
                model.rejected_by = command.rejected_by
                model.rejection_reason = command.reason
                
                session.commit()
                
                return {
                    "id": str(model.id),
                    "status": model.status,
                    "message": "تم رفض عرض السعر بنجاح"
                }
        
        except Exception as e:
            raise Exception(f"فشل رفض عرض السعر: {str(e)}")


class ConvertQuotationToOrderHandler:
    """معالج تحويل عرض السعر لأمر بيع"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def handle(self, command: ConvertQuotationToOrderCommand):
        """تحويل عرض السعر المقبول لأمر بيع"""
        try:
            with self.db.session() as session:
                from core.infrastructure.sales_cycle.models import SalesQuotationModel, SalesOrderModel
                
                # جلب عرض السعر
                quotation_model = session.query(SalesQuotationModel).filter(
                    SalesQuotationModel.id == uuid.UUID(command.quotation_id)
                ).first()
                
                if not quotation_model:
                    raise ValueError("عرض السعر غير موجود")
                
                if quotation_model.status != QuotationStatus.ACCEPTED.value:
                    raise ValueError("يمكن فقط تحويل العروض المقبولة")
                
                # إنشاء أمر البيع من عرض السعر
                order = SalesOrderModel(
                    id=uuid.uuid4(),
                    order_number=f"SO-{date.today().year}-{session.query(SalesOrderModel).count() + 1:06d}",
                    quotation_id=quotation_model.id,
                    customer_id=quotation_model.customer_id,
                    customer_name=quotation_model.customer_name,
                    currency=quotation_model.currency,
                    order_date=command.order_date,
                    expected_delivery_date=command.expected_delivery_date,
                    priority=command.priority,
                    status="confirmed",
                    items=quotation_model.items,  # نسخ العناصر
                    billing_address=quotation_model.billing_address,
                    shipping_address=quotation_model.shipping_address,
                    total_amount=quotation_model.total_amount,
                    tax_amount=quotation_model.tax_amount,
                    discount_amount=quotation_model.discount_amount,
                    notes=quotation_model.notes,
                    sales_person_id=quotation_model.sales_person_id,
                    sales_person_name=quotation_model.sales_person_name,
                    branch_id=quotation_model.branch_id,
                    company_id=quotation_model.company_id,
                    created_by=command.converted_by or "system",
                    created_at=date.today()
                )
                
                session.add(order)
                
                # تحديث حالة عرض السعر
                quotation_model.status = QuotationStatus.CONVERTED.value
                
                session.commit()
                
                return {
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "quotation_id": str(quotation_model.id),
                    "status": order.status,
                    "message": "تم تحويل عرض السعر لأمر بيع بنجاح"
                }
        
        except Exception as e:
            raise Exception(f"فشل تحويل عرض السعر: {str(e)}")
