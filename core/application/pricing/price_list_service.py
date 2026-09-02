# core/application/pricing/price_list_service.py
"""
Price List Service - خدمة قوائم الأسعار المتقدمة
✅ دعم قوائم متعددة
✅ دعم الأسعار حسب العميل والمجموعة
✅ دعم التسعير حسب الكمية
✅ دعم الخصومات والعروض
✅ دعم القواعد الديناميكية
"""

from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from dataclasses import dataclass
from functools import lru_cache

from core.domain.accounting.interfaces import IUnitOfWork
from core.infrastructure.db.models.price_list_model import (
    PriceListModel,
    PriceListItemModel,
    ProductPriceHistoryModel,
    PricingRuleModel,
)
from core.infrastructure.db.models.product_model import ProductModel
from core.domain.products.value_objects import Money


@dataclass
class PriceCalculationResult:
    """نتيجة حساب السعر"""
    base_price: Decimal
    final_price: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    price_list_code: Optional[str]
    rule_applied: Optional[str]
    currency: str
    quantity_break_applied: bool
    is_special: bool
    
    @property
    def savings(self) -> Decimal:
        """المبلغ الذي تم توفيره"""
        return self.base_price - self.final_price


class PriceListService:
    """
    خدمة قوائم الأسعار المتقدمة
    """
    
    def __init__(self, uow: IUnitOfWork):
        self._uow = uow
    
    # =========================================================================
    # حساب الأسعار
    # =========================================================================
    
    def get_product_price(
        self,
        product_code: str,
        quantity: int = 1,
        customer_id: Optional[str] = None,
        customer_group: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> Optional[PriceCalculationResult]:
        """
        الحصول على سعر المنتج مع تطبيق أفضل قائمة أسعار
        
        Args:
            product_code: كود المنتج
            quantity: الكمية المطلوبة
            customer_id: معرف العميل (اختياري)
            customer_group: مجموعة العميل (اختياري)
            date: تاريخ التسعير (اختياري)
        
        Returns:
            PriceCalculationResult أو None
        """
        check_date = date or datetime.now(timezone.utc)
        
        # 1. البحث عن المنتج
        product = self._get_product(product_code)
        if not product:
            return None
        
        # 2. الحصول على قوائم الأسعار المناسبة
        price_lists = self._get_applicable_price_lists(
            customer_id=customer_id,
            customer_group=customer_group,
            date=check_date
        )
        
        # 3. البحث عن أفضل سعر في القوائم
        best_result = None
        
        for price_list in price_lists:
            item = self._get_price_list_item(price_list.id, product.id)
            if not item or not item.is_active:
                continue
            
            # التحقق من صلاحية الخصم
            if self._is_discount_valid(item, check_date):
                price = item.get_price_for_quantity(quantity)
                base_price = item.base_price or product.unit_price
                
                result = PriceCalculationResult(
                    base_price=base_price,
                    final_price=price,
                    discount_percent=item.discount_percent,
                    discount_amount=item.discount_amount,
                    price_list_code=price_list.code,
                    rule_applied=None,
                    currency=item.currency,
                    quantity_break_applied=bool(item.quantity_prices),
                    is_special=price_list.list_type in ('promotional', 'seasonal')
                )
                
                if not best_result or result.final_price < best_result.final_price:
                    best_result = result
        
        # 4. إذا لم يتم العثور على سعر، استخدم السعر الافتراضي
        if not best_result:
            best_result = PriceCalculationResult(
                base_price=product.unit_price,
                final_price=product.unit_price,
                discount_percent=Decimal('0'),
                discount_amount=Decimal('0'),
                price_list_code=None,
                rule_applied=None,
                currency=product.currency,
                quantity_break_applied=False,
                is_special=False
            )
        
        # 5. تطبيق القواعد الديناميكية
        rules = self._get_applicable_rules(
            product_code=product_code,
            quantity=quantity,
            customer_id=customer_id,
            customer_group=customer_group
        )
        
        for rule in rules:
            best_result = self._apply_rule(best_result, rule)
        
        return best_result
    
    def get_product_price_bulk(
        self,
        items: List[Dict[str, Any]],
        customer_id: Optional[str] = None,
        customer_group: Optional[str] = None
    ) -> List[PriceCalculationResult]:
        """
        حساب أسعار منتجات متعددة دفعة واحدة
        
        Args:
            items: قائمة من {product_code, quantity}
            customer_id: معرف العميل (اختياري)
            customer_group: مجموعة العميل (اختياري)
        
        Returns:
            قائمة بنتائج حساب الأسعار
        """
        results = []
        for item in items:
            result = self.get_product_price(
                product_code=item['product_code'],
                quantity=item.get('quantity', 1),
                customer_id=customer_id,
                customer_group=customer_group
            )
            if result:
                results.append(result)
        return results
    
    # =========================================================================
    # إدارة قوائم الأسعار
    # =========================================================================
    
    def create_price_list(
        self,
        code: str,
        name: str,
        list_type: str = "standard",
        currency: str = "USD",
        description: Optional[str] = None,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        is_default: bool = False,
        conditions: Optional[dict] = None,
        created_by: str = "system"
    ) -> PriceListModel:
        """إنشاء قائمة أسعار جديدة"""
        with self._uow:
            # إذا كانت القائمة هي الافتراضية، قم بتعطيل القوائم الأخرى
            if is_default:
                self._uow.session.execute(
                    update(PriceListModel)
                    .where(PriceListModel.is_default == True)
                    .values(is_default=False, updated_by=created_by)
                )
            
            price_list = PriceListModel(
                code=code,
                name=name,
                list_type=list_type,
                currency=currency,
                description=description,
                valid_from=valid_from,
                valid_to=valid_to,
                is_default=is_default,
                conditions=conditions or {},
                created_by=created_by,
                updated_by=created_by,
            )
            self._uow.session.add(price_list)
            self._uow.commit()
            return price_list
    
    def add_item_to_price_list(
        self,
        price_list_code: str,
        product_code: str,
        price: Decimal,
        currency: Optional[str] = None,
        discount_percent: Decimal = Decimal('0'),
        discount_amount: Decimal = Decimal('0'),
        min_quantity: int = 1,
        max_quantity: Optional[int] = None,
        quantity_prices: Optional[dict] = None,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        created_by: str = "system"
    ) -> Optional[PriceListItemModel]:
        """إضافة منتج إلى قائمة الأسعار"""
        with self._uow:
            # البحث عن قائمة الأسعار
            price_list = self._uow.session.execute(
                select(PriceListModel).where(PriceListModel.code == price_list_code)
            ).scalar_one_or_none()
            
            if not price_list:
                return None
            
            # البحث عن المنتج
            product = self._get_product(product_code)
            if not product:
                return None
            
            # إضافة العنصر
            item = PriceListItemModel(
                price_list_id=price_list.id,
                product_id=product.id,
                product_code=product.code,
                product_name=product.name,
                price=price,
                currency=currency or product.currency,
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                min_quantity=min_quantity,
                max_quantity=max_quantity,
                quantity_prices=quantity_prices or {},
                is_active=True,
                created_by=created_by,
                updated_by=created_by,
            )
            self._uow.session.add(item)
            self._uow.commit()
            
            # تسجيل في تاريخ الأسعار
            self._log_price_history(
                product_code=product_code,
                old_price=product.unit_price,
                new_price=price,
                currency=currency or product.currency,
                change_reason=f"Added to price list: {price_list_code}",
                price_list_id=price_list.id,
                changed_by=created_by
            )
            
            return item
    
    def update_price_list_item(
        self,
        price_list_code: str,
        product_code: str,
        price: Optional[Decimal] = None,
        discount_percent: Optional[Decimal] = None,
        discount_amount: Optional[Decimal] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
        quantity_prices: Optional[dict] = None,
        is_active: Optional[bool] = None,
        updated_by: str = "system"
    ) -> bool:
        """تحديث منتج في قائمة الأسعار"""
        with self._uow:
            item = self._uow.session.execute(
                select(PriceListItemModel)
                .join(PriceListModel)
                .where(
                    PriceListModel.code == price_list_code,
                    PriceListItemModel.product_code == product_code
                )
            ).scalar_one_or_none()
            
            if not item:
                return False
            
            old_price = item.price
            
            if price is not None:
                item.price = price
            if discount_percent is not None:
                item.discount_percent = discount_percent
            if discount_amount is not None:
                item.discount_amount = discount_amount
            if min_quantity is not None:
                item.min_quantity = min_quantity
            if max_quantity is not None:
                item.max_quantity = max_quantity
            if quantity_prices is not None:
                item.quantity_prices = quantity_prices
            if is_active is not None:
                item.is_active = is_active
            
            item.updated_by = updated_by
            item.version += 1
            
            self._uow.commit()
            
            # تسجيل تغيير السعر
            if price is not None and price != old_price:
                self._log_price_history(
                    product_code=product_code,
                    old_price=old_price,
                    new_price=price,
                    currency=item.currency,
                    change_reason=f"Updated in price list: {price_list_code}",
                    price_list_id=item.price_list_id,
                    changed_by=updated_by
                )
            
            return True
    
    def delete_price_list_item(
        self,
        price_list_code: str,
        product_code: str,
        deleted_by: str = "system"
    ) -> bool:
        """حذف منتج من قائمة الأسعار"""
        with self._uow:
            item = self._uow.session.execute(
                select(PriceListItemModel)
                .join(PriceListModel)
                .where(
                    PriceListModel.code == price_list_code,
                    PriceListItemModel.product_code == product_code
                )
            ).scalar_one_or_none()
            
            if not item:
                return False
            
            self._uow.session.delete(item)
            self._uow.commit()
            return True
    
    # =========================================================================
    # قواعد التسعير الديناميكي
    # =========================================================================
    
    def create_pricing_rule(
        self,
        code: str,
        name: str,
        rule_type: str,
        value: Decimal,
        conditions: dict,
        description: Optional[str] = None,
        currency: str = "USD",
        priority: int = 0,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        created_by: str = "system"
    ) -> PricingRuleModel:
        """إنشاء قاعدة تسعير ديناميكية"""
        with self._uow:
            rule = PricingRuleModel(
                code=code,
                name=name,
                rule_type=rule_type,
                value=value,
                currency=currency,
                conditions=conditions,
                description=description,
                priority=priority,
                valid_from=valid_from,
                valid_to=valid_to,
                created_by=created_by,
                updated_by=created_by,
            )
            self._uow.session.add(rule)
            self._uow.commit()
            return rule
    
    # =========================================================================
    # دوال مساعدة
    # =========================================================================
    
    def _get_product(self, product_code: str) -> Optional[ProductModel]:
        """الحصول على المنتج من قاعدة البيانات"""
        return self._uow.session.execute(
            select(ProductModel).where(ProductModel.code == product_code)
        ).scalar_one_or_none()
    
    def _get_applicable_price_lists(
        self,
        customer_id: Optional[str] = None,
        customer_group: Optional[str] = None,
        date: Optional[datetime] = None
    ) -> List[PriceListModel]:
        """الحصول على قوائم الأسعار المناسبة للعميل"""
        check_date = date or datetime.now(timezone.utc)
        
        query = select(PriceListModel).where(
            PriceListModel.is_active == True,
            or_(
                PriceListModel.valid_from.is_(None),
                PriceListModel.valid_from <= check_date
            ),
            or_(
                PriceListModel.valid_to.is_(None),
                PriceListModel.valid_to >= check_date
            )
        )
        
        # أولوية القوائم:
        # 1. قائمة العميل المخصصة
        # 2. قائمة المجموعة
        # 3. قائمة ترويجية
        # 4. قائمة قياسية
        
        conditions = []
        
        if customer_id:
            conditions.append(PriceListModel.customer_id == customer_id)
        
        if customer_group:
            conditions.append(PriceListModel.customer_group == customer_group)
        
        # إذا كان هناك شروط، استخدمها
        if conditions:
            query = query.where(or_(*conditions))
        else:
            # وإلا استخدم القوائم القياسية أو الافتراضية
            query = query.where(
                or_(
                    PriceListModel.list_type == 'standard',
                    PriceListModel.is_default == True,
                    PriceListModel.list_type == 'promotional'
                )
            )
        
        # ترتيب حسب الأولوية
        query = query.order_by(
            PriceListModel.is_default.desc(),
            PriceListModel.list_type.asc(),
            PriceListModel.created_at.desc()
        )
        
        return self._uow.session.execute(query).scalars().all()
    
    def _get_price_list_item(self, price_list_id: UUID, product_id: UUID) -> Optional[PriceListItemModel]:
        """الحصول على سعر منتج في قائمة الأسعار"""
        return self._uow.session.execute(
            select(PriceListItemModel).where(
                PriceListItemModel.price_list_id == price_list_id,
                PriceListItemModel.product_id == product_id
            )
        ).scalar_one_or_none()
    
    def _is_discount_valid(self, item: PriceListItemModel, date: datetime) -> bool:
        """التحقق من صلاحية الخصم"""
        if item.discount_percent == 0 and item.discount_amount == 0:
            return True
        
        if item.discount_start and item.discount_end:
            return item.discount_start <= date <= item.discount_end
        
        return True
    
    def _get_applicable_rules(
        self,
        product_code: str,
        quantity: int,
        customer_id: Optional[str] = None,
        customer_group: Optional[str] = None
    ) -> List[PricingRuleModel]:
        """الحصول على قواعد التسعير المناسبة"""
        check_date = datetime.now(timezone.utc)
        
        query = select(PricingRuleModel).where(
            PricingRuleModel.is_active == True,
            or_(
                PricingRuleModel.valid_from.is_(None),
                PricingRuleModel.valid_from <= check_date
            ),
            or_(
                PricingRuleModel.valid_to.is_(None),
                PricingRuleModel.valid_to >= check_date
            )
        )
        
        rules = self._uow.session.execute(query.order_by(PricingRuleModel.priority)).scalars().all()
        
        # تصفية القواعد حسب الشروط
        applicable_rules = []
        for rule in rules:
            conditions = rule.conditions
            if self._check_rule_conditions(conditions, product_code, quantity, customer_id, customer_group):
                applicable_rules.append(rule)
        
        return applicable_rules
    
    def _check_rule_conditions(
        self,
        conditions: dict,
        product_code: str,
        quantity: int,
        customer_id: Optional[str] = None,
        customer_group: Optional[str] = None
    ) -> bool:
        """التحقق من شروط القاعدة"""
        if not conditions:
            return True
        
        # التحقق من الكمية
        if 'min_quantity' in conditions and quantity < conditions['min_quantity']:
            return False
        
        if 'max_quantity' in conditions and quantity > conditions['max_quantity']:
            return False
        
        # التحقق من العميل
        if 'customer_id' in conditions and customer_id != conditions['customer_id']:
            return False
        
        if 'customer_group' in conditions and customer_group != conditions['customer_group']:
            return False
        
        # التحقق من المنتج
        if 'product_code' in conditions and product_code != conditions['product_code']:
            return False
        
        if 'product_category' in conditions:
            # يجب جلب تصنيف المنتج من قاعدة البيانات
            product = self._get_product(product_code)
            if not product or product.category != conditions['product_category']:
                return False
        
        return True
    
    def _apply_rule(self, result: PriceCalculationResult, rule: PricingRuleModel) -> PriceCalculationResult:
        """تطبيق قاعدة تسعير على النتيجة"""
        if rule.rule_type == 'percentage':
            discount = result.final_price * (rule.value / 100)
            result.final_price = max(0, result.final_price - discount)
            result.discount_percent += rule.value
            result.discount_amount += discount
            result.rule_applied = rule.code
            
        elif rule.rule_type == 'fixed_amount':
            result.final_price = max(0, result.final_price - rule.value)
            result.discount_amount += rule.value
            result.rule_applied = rule.code
        
        return result
    
    def _log_price_history(
        self,
        product_code: str,
        old_price: Decimal,
        new_price: Decimal,
        currency: str,
        change_reason: str,
        price_list_id: Optional[UUID] = None,
        changed_by: str = "system"
    ) -> None:
        """تسجيل تغيير السعر في التاريخ"""
        history = ProductPriceHistoryModel(
            product_code=product_code,
            old_price=old_price,
            new_price=new_price,
            currency=currency,
            change_reason=change_reason,
            price_list_id=price_list_id,
            changed_by=changed_by
        )
        self._uow.session.add(history)
        self._uow.commit()


# =============================================================================
# دالة مساعدة للحصول على السعر
# =============================================================================

@lru_cache(maxsize=1000)
def get_cached_product_price(
    service: PriceListService,
    product_code: str,
    quantity: int = 1,
    customer_id: Optional[str] = None
) -> Optional[PriceCalculationResult]:
    """
    الحصول على سعر المنتج مع التخزين المؤقت
    
    Args:
        service: خدمة قوائم الأسعار
        product_code: كود المنتج
        quantity: الكمية
        customer_id: معرف العميل
    
    Returns:
        PriceCalculationResult أو None
    """
    return service.get_product_price(product_code, quantity, customer_id)