# core/application/handlers/products/update_product_handler.py
"""
Update Product Handler - تحديث منتج موجود
الإصدار المُصلح - v2.0.0

✅ محدث: Optimistic Locking صارم مع التحقق المزدوج
✅ محدث: التحقق من الإصدار قبل وبعد التحديث
✅ محدث: تسجيل التغييرات في سجل التدقيق
✅ محدث: التحقق من صحة البيانات (السعر، الضريبة، المخزون)
✅ محدث: دعم low_stock_threshold
✅ محدث: معالجة موحدة للأخطاء
✅ محدث: استخدام IAuditRepository
"""

import logging
from decimal import Decimal
from uuid import UUID
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from core.domain.products.value_objects import ProductId, ProductCode, StockMovementType
from core.domain.products.exceptions import (
    ProductNotFoundError,
    DuplicateCodeError,
    InvalidProductCodeError,
    InvalidStockQuantityError,
    NegativeStockNotAllowedError,
)
from core.domain.products.entities import Product
from core.domain.shared.value_objects import Money
from core.domain.accounting.interfaces import IUnitOfWork
from core.shared.exceptions import ConcurrentModificationError, ValidationError

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.products.commands import UpdateProductCommand
from core.application.products.dtos import ProductDTO
from core.application.products.converters import product_to_dto
from core.application.accounting.dtos import ErrorResponseDTO

logger = logging.getLogger(__name__)


# =============================================================================
# ✅ ChangeTracker - متتبع التغييرات (محسّن)
# =============================================================================

@dataclass
class ChangeTracker:
    """متتبع التغييرات لتسجيل التعديلات"""
    old_state: Dict[str, Any]
    new_state: Dict[str, Any]
    changes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def add_change(self, field: str, old_value: Any, new_value: Any) -> None:
        """إضافة تغيير"""
        if old_value != new_value:
            self.changes[field] = {
                'old': old_value,
                'new': new_value
            }
    
    def has_changes(self) -> bool:
        """هل هناك تغييرات؟"""
        return len(self.changes) > 0
    
    def get_changes_summary(self) -> str:
        """الحصول على ملخص التغييرات"""
        if not self.changes:
            return "No changes"
        return ", ".join([f"{k}: {v['old']} → {v['new']}" for k, v in self.changes.items()])
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'old_state': self.old_state,
            'new_state': self.new_state,
            'changes': self.changes,
        }


# =============================================================================
# ✅ UpdateProductHandler - المعالج الرئيسي (محسّن)
# =============================================================================

class UpdateProductHandler(BaseHandler[UpdateProductCommand, ProductDTO]):
    """
    Handler لتحديث منتج موجود مع Optimistic Locking صارم
    
    ✅ المبادئ:
        1. التحقق من الإصدار قبل أي تحديث
        2. التحقق من الإصدار بعد التحديث (للأمان)
        3. في حالة التعارض، رفع ConcurrentModificationError
        4. تسجيل جميع التغييرات في سجل التدقيق
        5. التحقق من صحة جميع البيانات المدخلة
    
    حالات الخطأ المحتملة:
        - ProductNotFoundError: المنتج غير موجود
        - DuplicateCodeError: كود المنتج مكرر
        - InvalidProductCodeError: كود المنتج غير صالح
        - InvalidStockQuantityError: كمية المخزون غير صالحة
        - NegativeStockNotAllowedError: المخزون السالب غير مسموح
        - ConcurrentModificationError: تعديل متزامن
        - ValidationError: فشل التحقق من صحة البيانات
    """
    
    def __init__(self, uow: IUnitOfWork):
        super().__init__(uow)
    
    @property
    def _audit_repo(self):
        """مستودع التدقيق - يُهيأ عند الحاجة داخل جلسة نشطة"""
        return self._uow.audit
    
    # =========================================================================
    # ✅ دوال التحقق (Validation) - محسّنة
    # =========================================================================
    
    def _validate_product_code(self, code: str, current_code: str) -> None:
        """
        التحقق من صحة كود المنتج
        
        Args:
            code: الكود الجديد
            current_code: الكود الحالي
        
        Raises:
            InvalidProductCodeError: إذا كان الكود غير صالح
            DuplicateCodeError: إذا كان الكود مكرراً
        """
        if code != current_code:
            try:
                # التحقق من صحة الكود
                product_code = ProductCode(code)
                
                # التحقق من عدم وجود كود مكرر
                with self._uow:
                    existing = self._uow.products.get_by_code(product_code)
                    if existing:
                        raise DuplicateCodeError(code)
                        
            except ValueError as e:
                raise InvalidProductCodeError(code, str(e))
    
    def _validate_price(self, price: Decimal) -> None:
        """
        التحقق من صحة السعر
        
        Args:
            price: السعر
        
        Raises:
            ValidationError: إذا كان السعر غير صالح
        """
        if price <= 0:
            raise ValidationError(
                f"Unit price must be greater than zero: {price}",
                field="unit_price",
                value=str(price)
            )
        
        if price > Decimal('999999999.99'):
            raise ValidationError(
                f"Unit price is too large: {price}",
                field="unit_price",
                value=str(price)
            )
    
    def _validate_tax_rate(self, tax_rate: Decimal) -> None:
        """
        التحقق من صحة نسبة الضريبة
        
        Args:
            tax_rate: نسبة الضريبة
        
        Raises:
            ValidationError: إذا كانت النسبة غير صالحة
        """
        if tax_rate < 0:
            raise ValidationError(
                f"Tax rate cannot be negative: {tax_rate}",
                field="tax_rate",
                value=str(tax_rate)
            )
        
        if tax_rate > 100:
            raise ValidationError(
                f"Tax rate cannot exceed 100%: {tax_rate}",
                field="tax_rate",
                value=str(tax_rate)
            )
    
    def _validate_stock(self, stock_quantity: int) -> None:
        """
        التحقق من صحة كمية المخزون
        
        Args:
            stock_quantity: كمية المخزون
        
        Raises:
            InvalidStockQuantityError: إذا كانت الكمية غير صالحة
        """
        if stock_quantity < 0:
            raise InvalidStockQuantityError(
                stock_quantity,
                "Stock quantity cannot be negative"
            )
    
    def _validate_low_stock_threshold(self, threshold: int) -> None:
        """
        التحقق من صحة حد المخزون المنخفض
        
        Args:
            threshold: حد المخزون المنخفض
        
        Raises:
            ValidationError: إذا كان الحد غير صالح
        """
        if threshold < 0:
            raise ValidationError(
                f"Low stock threshold cannot be negative: {threshold}",
                field="low_stock_threshold",
                value=str(threshold)
            )
    
    # =========================================================================
    # ✅ دوال تتبع التغييرات (Audit) - محسّنة
    # =========================================================================
    
    def _capture_product_state(self, product: Product) -> Dict[str, Any]:
        """التقاط حالة المنتج الحالية للتدقيق"""
        return {
            'code': product.code.value,
            'name': product.name,
            'unit_price': float(product.unit_price.amount),
            'currency': product.unit_price.currency,
            'description': product.description,
            'category': product.category,
            'tax_rate': float(product.tax_rate),
            'stock_quantity': product.stock_quantity,
            'low_stock_threshold': product.low_stock_threshold,
            'is_active': product.is_active,
            'version': product.version,
        }
    
    def _log_audit(
        self,
        product: Product,
        changes: Dict[str, Any],
        user_context: UserContext
    ) -> None:
        """
        تسجيل التغييرات في سجل التدقيق
        
        Args:
            product: كائن المنتج
            changes: التغييرات التي حدثت
            user_context: سياق المستخدم
        """
        if not changes:
            return
        
        try:
            if self._audit_repo:
                self._audit_repo.log_operation(
                    operation="UPDATE_PRODUCT",
                    entity_type="Product",
                    entity_id=str(product.id),
                    performed_by=user_context.user_id,
                    changes=changes
                )
                logger.info(f"Audit logged for product {product.code.value}")
            else:
                # Fallback: تسجيل في السجلات
                logger.info(
                    f"Audit - Product {product.code.value} changed by {user_context.user_id}: "
                    f"{list(changes.keys())}"
                )
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")
    
    # =========================================================================
    # ✅ المعالج الرئيسي - المحسّن بالكامل
    # =========================================================================
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: UpdateProductCommand, user_context: UserContext) -> ProductDTO:
        """
        تنفيذ تحديث المنتج مع Optimistic Locking
        
        Args:
            command: أمر تحديث المنتج
            user_context: سياق المستخدم
        
        Returns:
            ProductDTO: المنتج المحدث
        
        Raises:
            ProductNotFoundError: إذا لم يتم العثور على المنتج
            DuplicateCodeError: إذا كان كود المنتج مكرراً
            ConcurrentModificationError: إذا تم تعديل المنتج بواسطة مستخدم آخر
            ValidationError: إذا فشل التحقق من صحة البيانات
        """
        logger.info(
            f"Updating product {command.product_id} with version {command.version} "
            f"by {user_context.user_id}"
        )
        
        with self._uow:
            product_repo = self._uow.products
            
            # ========== 1. جلب المنتج الحالي ==========
            try:
                product = product_repo.get_by_id(ProductId(UUID(command.product_id)))
            except ValueError as e:
                raise ValidationError(f"Invalid product ID: {command.product_id}", field="product_id")
            
            if not product:
                raise ProductNotFoundError(command.product_id)
            
            # ========== 2. التحقق من الإصدار (Optimistic Locking) ==========
            if product.version != command.version:
                raise ConcurrentModificationError(
                    "Product",
                    str(product.id),
                    command.version,
                    product.version
                )
            
            # ========== 3. تسجيل الحالة القديمة ==========
            old_state = self._capture_product_state(product)
            tracker = ChangeTracker(
                old_state=old_state,
                new_state={}
            )
            
            # ========== 4. التحقق من صحة البيانات ==========
            try:
                # التحقق من كود المنتج
                self._validate_product_code(command.code, product.code.value)
                
                # التحقق من السعر
                self._validate_price(command.unit_price)
                
                # التحقق من نسبة الضريبة
                self._validate_tax_rate(command.tax_rate)
                
                # التحقق من المخزون
                self._validate_stock(int(command.stock_quantity) if command.stock_quantity else 0)
                
                # التحقق من حد المخزون المنخفض (إذا تم توفيره)
                if hasattr(command, 'low_stock_threshold') and command.low_stock_threshold is not None:
                    self._validate_low_stock_threshold(command.low_stock_threshold)
                    
            except (ValidationError, InvalidProductCodeError, DuplicateCodeError, InvalidStockQuantityError) as e:
                logger.warning(f"Validation failed for product {command.product_id}: {e}")
                raise
            
            # ========== 5. تطبيق التغييرات ==========
            try:
                # تحديث الكود
                if command.code != product.code.value:
                    old_code = product.code.value
                    product.code = ProductCode(command.code)
                    tracker.add_change('code', old_code, command.code)
                    logger.debug(f"  Updated code: {command.code}")
                
                # تحديث الاسم
                if command.name != product.name:
                    old_name = product.name
                    product.name = command.name
                    tracker.add_change('name', old_name, command.name)
                    logger.debug(f"  Updated name: {command.name}")
                
                # تحديث السعر
                if float(command.unit_price) != float(product.unit_price.amount):
                    old_price = float(product.unit_price.amount)
                    old_currency = product.unit_price.currency
                    product.unit_price = Money(command.unit_price, command.currency)
                    tracker.add_change('unit_price', old_price, float(command.unit_price))
                    if command.currency != old_currency:
                        tracker.add_change('currency', old_currency, command.currency)
                    logger.debug(f"  Updated price: {command.unit_price} {command.currency}")
                
                # تحديث الوصف
                if command.description is not None and command.description != product.description:
                    old_desc = product.description
                    product.description = command.description
                    tracker.add_change('description', old_desc, command.description)
                    logger.debug(f"  Updated description")
                
                # تحديث التصنيف
                if command.category is not None and command.category != product.category:
                    old_cat = product.category
                    product.category = command.category
                    tracker.add_change('category', old_cat, command.category)
                    logger.debug(f"  Updated category: {command.category}")
                
                # تحديث نسبة الضريبة
                if float(command.tax_rate) != float(product.tax_rate):
                    old_tax = float(product.tax_rate)
                    product.tax_rate = command.tax_rate
                    tracker.add_change('tax_rate', old_tax, float(command.tax_rate))
                    logger.debug(f"  Updated tax rate: {command.tax_rate}")
                
                # ✅ تحديث حد المخزون المنخفض (إذا تم توفيره)
                if hasattr(command, 'low_stock_threshold') and command.low_stock_threshold is not None:
                    if command.low_stock_threshold != product.low_stock_threshold:
                        old_threshold = product.low_stock_threshold
                        product.low_stock_threshold = command.low_stock_threshold
                        tracker.add_change('low_stock_threshold', old_threshold, command.low_stock_threshold)
                        logger.debug(f"  Updated low stock threshold: {command.low_stock_threshold}")
                
                # تحديث المخزون
                new_stock = int(command.stock_quantity) if command.stock_quantity else 0
                if new_stock != product.stock_quantity:
                    old_stock = product.stock_quantity
                    quantity_change = new_stock - product.stock_quantity
                    
                    if quantity_change != 0:
                        # ✅ استخدام StockMovementType المناسب
                        movement_type = (
                            StockMovementType.ADJUSTMENT if quantity_change > 0
                            else StockMovementType.ADJUSTMENT
                        )
                        
                        product.update_stock(
                            quantity_change=quantity_change,
                            movement_type=movement_type,
                            reason=f"تحديث يدوي للمخزون: {command.reason or 'تعديل'}",
                            updated_by=user_context.user_id
                        )
                        tracker.add_change('stock_quantity', old_stock, product.stock_quantity)
                        logger.debug(f"  Updated stock: {old_stock} → {product.stock_quantity} ({quantity_change:+.0f})")
                
                # تحديث الحالة
                if command.is_active != product.is_active:
                    old_active = product.is_active
                    if command.is_active:
                        product.activate(user_context.user_id)
                    else:
                        product.deactivate(user_context.user_id)
                    tracker.add_change('is_active', old_active, command.is_active)
                    logger.debug(f"  {'Activated' if command.is_active else 'Deactivated'} product")
                
                # تحديث بيانات التدقيق
                from core.domain.products.entities import utc_now
                product.updated_at = utc_now()
                product.updated_by = user_context.user_id
                
                tracker.new_state = self._capture_product_state(product)
                
            except (NegativeStockNotAllowedError, InvalidStockQuantityError) as e:
                logger.warning(f"Stock update failed for product {command.product_id}: {e}")
                raise
            
            # ========== 6. حفظ مع Optimistic Locking ==========
            try:
                # ✅ حفظ المنتج (الـ Repository سيتحقق من الإصدار)
                product_repo.save(product)
                
                # ✅ التحقق من الإصدار بعد الحفظ (للتأكد من عدم تغييره)
                if product.version == old_state['version']:
                    # إذا لم يتغير الإصدار، فهذا يعني أن الحفظ لم يحدث (قد يكون هناك خطأ)
                    logger.warning(f"Version did not change after save for product {command.product_id}")
                
                self._commit()
                
            except ConcurrentModificationError as e:
                logger.warning(f"Concurrent modification detected for product {command.product_id}")
                raise
            
            except Exception as e:
                logger.error(f"Error saving product {command.product_id}: {e}", exc_info=True)
                self._uow.rollback()
                raise ValidationError(f"Failed to save product: {str(e)}")
            
            # ========== 7. تسجيل التغييرات في سجل التدقيق ==========
            if tracker.has_changes():
                self._log_audit(product, tracker.changes, user_context)
                logger.info(
                    f"Product {product.code.value} updated successfully: "
                    f"version {old_state['version']} → {product.version}, "
                    f"changes: {tracker.get_changes_summary()}"
                )
            else:
                logger.info(f"Product {product.code.value} updated with no changes")
            
            # ========== 8. إرجاع المنتج المحدث ==========
            return product_to_dto(product)
    
    # =========================================================================
    # ✅ دوال مساعدة للاختبارات
    # =========================================================================
    
    def get_product_version(self, product_id: str) -> Optional[int]:
        """الحصول على إصدار المنتج (للاختبار)"""
        with self._uow:
            product = self._uow.products.get_by_id(ProductId(UUID(product_id)))
            if not product:
                return None
            return product.version
    
    def get_product_audit_trail(self, product_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """الحصول على سجل تدقيق المنتج (للاختبار)"""
        if not self._audit_repo:
            return []
        
        records = self._audit_repo.get_entity_history("Product", product_id, limit)
        return [
            {
                'timestamp': r.performed_at.isoformat(),
                'user': r.performed_by,
                'operation': r.operation,
                'changes': r.changes,
            }
            for r in records
        ]