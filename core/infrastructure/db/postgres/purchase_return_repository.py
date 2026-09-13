"""
مستودع إرجاع المشتريات - PostgreSQL Implementation
يعمل كطبقة وصول للبيانات لإرجاعات المشتريات
"""
from typing import List, Optional
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from core.domain.purchasing.entities import PurchaseReturn, PurchaseReturnItem
from core.domain.purchasing.value_objects import (
    PurchaseReturnId, PurchaseReturnNumber, PurchaseReturnStatus,
    DebitNoteId
)
from core.domain.purchasing.interfaces import IPurchaseReturnRepository
from core.infrastructure.db.models.purchase_return_model import (
    PurchaseReturnModel, PurchaseReturnItemModel
)
from core.infrastructure.db.postgres.unit_of_work import PostgresUnitOfWork


class PostgresPurchaseReturnRepository(IPurchaseReturnRepository):
    """تنفيذ مستودع إرجاع المشتريات باستخدام PostgreSQL"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, purchase_return: PurchaseReturn) -> None:
        """إضافة إرجاع مشتريات جديد"""
        model = PurchaseReturnModel(
            id=str(purchase_return.id.value),
            return_number=purchase_return.return_number.value,
            supplier_code=purchase_return.supplier_code,
            supplier_name=purchase_return.supplier_name,
            original_po_number=purchase_return.original_po_number,
            original_invoice_id=purchase_return.original_invoice_id,
            return_date=purchase_return.return_date,
            status=purchase_return.status.value,
            subtotal=purchase_return.subtotal.amount,
            discount_amount=purchase_return.discount_amount.amount if purchase_return.discount_amount else None,
            discount_percent=purchase_return.discount_percent,
            tax_amount=purchase_return.tax_amount.amount if purchase_return.tax_amount else None,
            tax_rate=purchase_return.tax_rate,
            total_amount=purchase_return.total_amount.amount,
            currency=purchase_return.currency,
            notes=purchase_return.notes,
            shipping_method=purchase_return.shipping_method,
            tracking_number=purchase_return.tracking_number,
            debit_note_id=str(purchase_return.debit_note_id.value) if purchase_return.debit_note_id else None,
            created_by=purchase_return.created_by,
            created_at=purchase_return.created_at,
            version=purchase_return.version
        )
        
        # إضافة الأصناف
        for item in purchase_return.items:
            item_model = PurchaseReturnItemModel(
                product_code=item.product_code,
                product_name=item.product_name,
                quantity=item.quantity.value,
                unit=item.unit,
                unit_price=item.unit_price.amount,
                reason=item.reason,
                condition=item.condition.value,
                batch_number=item.batch_number,
                serial_number=item.serial_number,
                expiry_date=item.expiry_date,
                discount_percent=item.discount_percent,
                discount_amount=item.discount_amount.amount if item.discount_amount else None,
                tax_rate=item.tax_rate,
                tax_amount=item.tax_amount.amount if item.tax_amount else None,
                subtotal=item.subtotal.amount,
                total_with_tax=item.total_with_tax.amount
            )
            model.items.append(item_model)
        
        self.session.add(model)
        await self.session.flush()

    async def get_by_id(self, return_id: PurchaseReturnId) -> Optional[PurchaseReturn]:
        """الحصول على إرجاع مشتريات بالمعرف"""
        stmt = select(PurchaseReturnModel).where(
            PurchaseReturnModel.id == str(return_id.value)
        ).options(selectinload(PurchaseReturnModel.items))
        
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)

    async def get_by_number(self, return_number: PurchaseReturnNumber) -> Optional[PurchaseReturn]:
        """الحصول على إرجاع مشتريات بالرقم"""
        stmt = select(PurchaseReturnModel).where(
            PurchaseReturnModel.return_number == return_number.value
        ).options(selectinload(PurchaseReturnModel.items))
        
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)

    async def get_by_status(self, status: PurchaseReturnStatus) -> List[PurchaseReturn]:
        """الحصول على إرجاعات مشتريات حسب الحالة"""
        stmt = select(PurchaseReturnModel).where(
            PurchaseReturnModel.status == status.value
        ).options(selectinload(PurchaseReturnModel.items))
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]

    async def get_by_supplier(self, supplier_code: str) -> List[PurchaseReturn]:
        """الحصول على إرجاعات مشتريات لمورد معين"""
        stmt = select(PurchaseReturnModel).where(
            PurchaseReturnModel.supplier_code == supplier_code
        ).options(selectinload(PurchaseReturnModel.items))
        
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        
        return [self._model_to_entity(model) for model in models]

    async def update(self, purchase_return: PurchaseReturn) -> None:
        """تحديث إرجاع مشتريات موجود"""
        stmt = update(PurchaseReturnModel).where(
            PurchaseReturnModel.id == str(purchase_return.id.value)
        ).values(
            status=purchase_return.status.value,
            subtotal=purchase_return.subtotal.amount,
            discount_amount=purchase_return.discount_amount.amount if purchase_return.discount_amount else None,
            discount_percent=purchase_return.discount_percent,
            tax_amount=purchase_return.tax_amount.amount if purchase_return.tax_amount else None,
            tax_rate=purchase_return.tax_rate,
            total_amount=purchase_return.total_amount.amount,
            notes=purchase_return.notes,
            shipping_method=purchase_return.shipping_method,
            tracking_number=purchase_return.tracking_number,
            debit_note_id=str(purchase_return.debit_note_id.value) if purchase_return.debit_note_id else None,
            updated_at=purchase_return.updated_at,
            version=purchase_return.version
        )
        
        await self.session.execute(stmt)
        
        # تحديث الأصناف (حذف القديم وإضافة الجديد)
        await self.session.execute(
            delete(PurchaseReturnItemModel).where(
                PurchaseReturnItemModel.return_id == str(purchase_return.id.value)
            )
        )
        
        for item in purchase_return.items:
            item_model = PurchaseReturnItemModel(
                return_id=str(purchase_return.id.value),
                product_code=item.product_code,
                product_name=item.product_name,
                quantity=item.quantity.value,
                unit=item.unit,
                unit_price=item.unit_price.amount,
                reason=item.reason,
                condition=item.condition.value,
                batch_number=item.batch_number,
                serial_number=item.serial_number,
                expiry_date=item.expiry_date,
                discount_percent=item.discount_percent,
                discount_amount=item.discount_amount.amount if item.discount_amount else None,
                tax_rate=item.tax_rate,
                tax_amount=item.tax_amount.amount if item.tax_amount else None,
                subtotal=item.subtotal.amount,
                total_with_tax=item.total_with_tax.amount
            )
            self.session.add(item_model)

    async def delete(self, return_id: PurchaseReturnId) -> None:
        """حذف إرجاع مشتريات (فقط إذا كان في حالة DRAFT)"""
        await self.session.execute(
            delete(PurchaseReturnModel).where(
                PurchaseReturnModel.id == str(return_id.value)
            )
        )

    async def exists_by_number(self, return_number: PurchaseReturnNumber) -> bool:
        """التحقق من وجود رقم إرجاع"""
        stmt = select(PurchaseReturnModel.id).where(
            PurchaseReturnModel.return_number == return_number.value
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_next_return_number(self, prefix: str = "PR") -> PurchaseReturnNumber:
        """إنشاء رقم إرجاع جديد"""
        # منطق بسيط لإنشاء الرقم التالي
        # في الإنتاج، يجب استخدام تسلسل قاعدة البيانات
        stmt = select(PurchaseReturnModel.return_number).where(
            PurchaseReturnModel.return_number.like(f"{prefix}%")
        ).order_by(PurchaseReturnModel.return_number.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        last_number = result.scalar_one_or_none()
        
        if not last_number:
            return PurchaseReturnNumber(f"{prefix}-00001")
        
        # استخراج الجزء الرقمي وزيادة
        try:
            parts = last_number.split("-")
            if len(parts) == 2:
                num = int(parts[1]) + 1
                return PurchaseReturnNumber(f"{prefix}-{num:05d}")
        except ValueError:
            pass
        
        return PurchaseReturnNumber(f"{prefix}-00001")

    def _model_to_entity(self, model: PurchaseReturnModel) -> PurchaseReturn:
        """تحويل نموذج قاعدة البيانات إلى كيان مجال"""
        from decimal import Decimal
        from core.domain.shared.value_objects import Money, Quantity
        from core.domain.purchasing.value_objects import ReturnCondition
        
        items = []
        for item_model in model.items:
            item = PurchaseReturnItem(
                product_code=item_model.product_code,
                product_name=item_model.product_name,
                quantity=Quantity(Decimal(str(item_model.quantity))),
                unit=item_model.unit,
                unit_price=Money(Decimal(str(item_model.unit_price)), model.currency),
                reason=item_model.reason,
                condition=ReturnCondition(item_model.condition),
                batch_number=item_model.batch_number,
                serial_number=item_model.serial_number,
                expiry_date=item_model.expiry_date,
                discount_percent=item_model.discount_percent,
                discount_amount=Money(Decimal(str(item_model.discount_amount or 0)), model.currency),
                tax_rate=item_model.tax_rate,
                tax_amount=Money(Decimal(str(item_model.tax_amount or 0)), model.currency),
                subtotal=Money(Decimal(str(item_model.subtotal)), model.currency),
                total_with_tax=Money(Decimal(str(item_model.total_with_tax)), model.currency)
            )
            items.append(item)
        
        return PurchaseReturn(
            id=PurchaseReturnId(model.id),
            return_number=PurchaseReturnNumber(model.return_number),
            supplier_code=model.supplier_code,
            supplier_name=model.supplier_name,
            original_po_number=model.original_po_number,
            original_invoice_id=model.original_invoice_id,
            return_date=model.return_date,
            status=PurchaseReturnStatus(model.status),
            items=items,
            subtotal=Money(Decimal(str(model.subtotal)), model.currency),
            discount_amount=Money(Decimal(str(model.discount_amount or 0)), model.currency),
            discount_percent=model.discount_percent,
            tax_rate=model.tax_rate,
            tax_amount=Money(Decimal(str(model.tax_amount or 0)), model.currency),
            total_amount=Money(Decimal(str(model.total_amount)), model.currency),
            currency=model.currency,
            notes=model.notes,
            shipping_method=model.shipping_method,
            tracking_number=model.tracking_number,
            debit_note_id=DebitNoteId(model.debit_note_id) if model.debit_note_id else None,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version
        )
