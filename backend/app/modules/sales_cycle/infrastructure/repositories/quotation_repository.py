"""
SQLAlchemy Implementation of Quotation Repository
Infrastructure layer implementation
"""

from typing import Optional, List
from datetime import date, timedelta
from decimal import Decimal
import logging

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales_cycle.domain.entities.quotation import (
    SalesQuotation, 
    QuotationStatus, 
    QuotationItem
)
from app.modules.sales_cycle.domain.repositories.quotation_repository import IQuotationRepository
from app.modules.sales_cycle.infrastructure.models.quotation_model import (
    SalesQuotationModel, 
    QuotationItemModel
)

logger = logging.getLogger(__name__)


class SQLAlchemyQuotationRepository(IQuotationRepository):
    """
    تطبيق مستودع عروض الأسعار باستخدام SQLAlchemy
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add(self, quotation: SalesQuotation) -> SalesQuotation:
        """إضافة عرض سعر جديد"""
        try:
            # Create model from entity
            model = SalesQuotationModel(
                id=quotation.id,
                quotation_number=quotation.quotation_number,
                customer_id=quotation.customer_id,
                customer_name=quotation.customer_name,
                branch_id=quotation.branch_id,
                issue_date=quotation.issue_date,
                expiry_date=quotation.expiry_date,
                status=quotation.status.value,
                subtotal=quotation.subtotal if hasattr(quotation, 'subtotal') else Decimal('0'),
                discount_amount=quotation.discount_amount,
                discount_percentage=quotation.discount_percentage,
                tax_amount=quotation.tax_amount,
                total_amount=quotation.total_amount,
                currency_code=quotation.currency_code,
                exchange_rate=quotation.exchange_rate,
                notes=quotation.notes,
                terms_conditions=quotation.terms_conditions,
                valid_for_days=quotation.valid_for_days,
                sales_person_id=quotation.sales_person_id,
                created_by=quotation.created_by,
                converted_to_order_id=quotation.converted_to_order_id,
            )
            
            # Add items
            for item in quotation.items:
                item_model = QuotationItemModel(
                    id=item.id,
                    quotation_id=model.id,
                    line_number=item.line_number,
                    product_id=item.product_id,
                    product_name=item.product_name,
                    description=item.description,
                    quantity=item.quantity,
                    unit_of_measure=item.unit_of_measure,
                    unit_price=item.unit_price,
                    discount_percentage=item.discount_percentage,
                    tax_percentage=item.tax_percentage,
                    line_total=item.line_total,
                )
                model.items.append(item_model)
            
            self.session.add(model)
            await self.session.commit()
            await self.session.refresh(model)
            
            logger.info(f"Created quotation: {model.quotation_number}")
            return await self.get_by_id(model.id)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error creating quotation: {e}")
            raise
    
    async def get_by_id(self, quotation_id: str) -> Optional[SalesQuotation]:
        """الحصول على عرض سعر بالمعرف"""
        try:
            result = await self.session.execute(
                select(SalesQuotationModel)
                .where(SalesQuotationModel.id == quotation_id)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                return None
            
            return self._map_to_entity(model)
            
        except Exception as e:
            logger.error(f"Error getting quotation by ID: {e}")
            raise
    
    async def get_by_number(self, quotation_number: str) -> Optional[SalesQuotation]:
        """الحصول على عرض سعر بالرقم"""
        try:
            result = await self.session.execute(
                select(SalesQuotationModel)
                .where(SalesQuotationModel.quotation_number == quotation_number)
            )
            model = result.scalar_one_or_none()
            
            if not model:
                return None
            
            return self._map_to_entity(model)
            
        except Exception as e:
            logger.error(f"Error getting quotation by number: {e}")
            raise
    
    async def update(self, quotation: SalesQuotation) -> SalesQuotation:
        """تحديث عرض سعر موجود"""
        try:
            model = await self.session.get(SalesQuotationModel, quotation.id)
            if not model:
                raise ValueError(f"Quotation {quotation.id} not found")
            
            # Update fields
            model.customer_name = quotation.customer_name
            model.branch_id = quotation.branch_id
            model.expiry_date = quotation.expiry_date
            model.status = quotation.status.value
            model.discount_percentage = quotation.discount_percentage
            model.notes = quotation.notes
            model.terms_conditions = quotation.terms_conditions
            model.updated_by = quotation.updated_by if hasattr(quotation, 'updated_by') else None
            
            # Clear existing items
            model.items.clear()
            
            # Add updated items
            for item in quotation.items:
                item_model = QuotationItemModel(
                    id=item.id,
                    quotation_id=model.id,
                    line_number=item.line_number,
                    product_id=item.product_id,
                    product_name=item.product_name,
                    description=item.description,
                    quantity=item.quantity,
                    unit_of_measure=item.unit_of_measure,
                    unit_price=item.unit_price,
                    discount_percentage=item.discount_percentage,
                    tax_percentage=item.tax_percentage,
                    line_total=item.line_total,
                )
                model.items.append(item_model)
            
            await self.session.commit()
            await self.session.refresh(model)
            
            logger.info(f"Updated quotation: {model.quotation_number}")
            return await self.get_by_id(model.id)
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error updating quotation: {e}")
            raise
    
    async def delete(self, quotation_id: str) -> bool:
        """حذف عرض سعر"""
        try:
            model = await self.session.get(SalesQuotationModel, quotation_id)
            if model:
                await self.session.delete(model)
                await self.session.commit()
                logger.info(f"Deleted quotation: {quotation_id}")
                return True
            return False
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error deleting quotation: {e}")
            raise
    
    async def list(
        self,
        customer_id: Optional[str] = None,
        status: Optional[QuotationStatus] = None,
        sales_person_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[SalesQuotation]:
        """قائمة عروض الأسعار مع فلترة"""
        try:
            query = select(SalesQuotationModel)
            
            # Apply filters
            conditions = []
            if customer_id:
                conditions.append(SalesQuotationModel.customer_id == customer_id)
            if status:
                conditions.append(SalesQuotationModel.status == status.value)
            if sales_person_id:
                conditions.append(SalesQuotationModel.sales_person_id == sales_person_id)
            if from_date:
                conditions.append(SalesQuotationModel.issue_date >= from_date)
            if to_date:
                conditions.append(SalesQuotationModel.issue_date <= to_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Order by creation date descending
            query = query.order_by(SalesQuotationModel.created_at.desc())
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            result = await self.session.execute(query)
            models = result.scalars().all()
            
            return [self._map_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error(f"Error listing quotations: {e}")
            raise
    
    async def count(
        self,
        customer_id: Optional[str] = None,
        status: Optional[QuotationStatus] = None,
        sales_person_id: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> int:
        """عدد عروض الأسعار"""
        try:
            query = select(func.count()).select_from(SalesQuotationModel)
            
            conditions = []
            if customer_id:
                conditions.append(SalesQuotationModel.customer_id == customer_id)
            if status:
                conditions.append(SalesQuotationModel.status == status.value)
            if sales_person_id:
                conditions.append(SalesQuotationModel.sales_person_id == sales_person_id)
            if from_date:
                conditions.append(SalesQuotationModel.issue_date >= from_date)
            if to_date:
                conditions.append(SalesQuotationModel.issue_date <= to_date)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = await self.session.execute(query)
            return result.scalar()
            
        except Exception as e:
            logger.error(f"Error counting quotations: {e}")
            raise
    
    async def get_pending_quotations(self, days_threshold: int = 7) -> List[SalesQuotation]:
        """الحصول على عروض الأسعار المعلقة التي اقترب تاريخ انتهائها"""
        try:
            threshold_date = date.today() + timedelta(days=days_threshold)
            
            result = await self.session.execute(
                select(SalesQuotationModel)
                .where(
                    and_(
                        SalesQuotationModel.status.in_(['sent', 'viewed']),
                        SalesQuotationModel.expiry_date <= threshold_date,
                        SalesQuotationModel.expiry_date >= date.today()
                    )
                )
            )
            models = result.scalars().all()
            
            return [self._map_to_entity(model) for model in models]
            
        except Exception as e:
            logger.error(f"Error getting pending quotations: {e}")
            raise
    
    async def expire_overdue_quotations(self) -> int:
        """إنهاء صلاحية عروض الأسعار منتهية الصلاحية"""
        try:
            result = await self.session.execute(
                select(SalesQuotationModel)
                .where(
                    and_(
                        SalesQuotationModel.status.in_(['draft', 'sent', 'viewed']),
                        SalesQuotationModel.expiry_date < date.today()
                    )
                )
            )
            models = result.scalars().all()
            
            expired_count = 0
            for model in models:
                model.status = 'expired'
                expired_count += 1
            
            if expired_count > 0:
                await self.session.commit()
                logger.info(f"Expired {expired_count} quotations")
            
            return expired_count
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error expiring quotations: {e}")
            raise
    
    def _map_to_entity(self, model: SalesQuotationModel) -> SalesQuotation:
        """تحويل النموذج إلى كيان"""
        items = [
            QuotationItem(
                id=item.id,
                line_number=item.line_number,
                product_id=item.product_id,
                product_name=item.product_name,
                description=item.description,
                quantity=Decimal(str(item.quantity)),
                unit_of_measure=item.unit_of_measure,
                unit_price=Decimal(str(item.unit_price)),
                discount_percentage=Decimal(str(item.discount_percentage)),
                tax_percentage=Decimal(str(item.tax_percentage)),
            )
            for item in model.items
        ] if model.items else []
        
        return SalesQuotation(
            id=model.id,
            quotation_number=model.quotation_number,
            customer_id=model.customer_id,
            customer_name=model.customer_name,
            branch_id=model.branch_id,
            issue_date=model.issue_date,
            expiry_date=model.expiry_date,
            status=QuotationStatus(model.status),
            items=items,
            subtotal=Decimal(str(model.subtotal)) if model.subtotal else Decimal('0'),
            discount_amount=Decimal(str(model.discount_amount)) if model.discount_amount else Decimal('0'),
            discount_percentage=Decimal(str(model.discount_percentage)) if model.discount_percentage else Decimal('0'),
            tax_amount=Decimal(str(model.tax_amount)) if model.tax_amount else Decimal('0'),
            total_amount=Decimal(str(model.total_amount)) if model.total_amount else Decimal('0'),
            currency_code=model.currency_code,
            exchange_rate=Decimal(str(model.exchange_rate)) if model.exchange_rate else Decimal('1'),
            notes=model.notes,
            terms_conditions=model.terms_conditions,
            valid_for_days=model.valid_for_days,
            sales_person_id=model.sales_person_id,
            created_by=model.created_by,
            converted_to_order_id=model.converted_to_order_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
