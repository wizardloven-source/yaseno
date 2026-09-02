"""
Product Aggregate Root - The Heart of Products Module
كيان المنتج - الجذر التجميعي لنظام المنتجات
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Any, Dict
from uuid import uuid4

from core.domain.shared.value_objects import Money
from .value_objects import (
    ProductId, ProductCode, ProductStatus, 
    StockMovementType, StockMovement
)
from .exceptions import (
    InvalidStockQuantityError,
    NegativeStockNotAllowedError,
    InsufficientStockError,
    ProductAlreadyActiveError,
    ProductAlreadyInactiveError,
    CannotModifyInactiveProductError,
)
from .events import (
    ProductCreatedEvent,
    ProductUpdatedEvent,
    ProductDeletedEvent,
    ProductReactivatedEvent,
    StockUpdatedEvent,
    LowStockAlertEvent,
    OutOfStockEvent,
    PriceChangedEvent,
)


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


@dataclass
class Product:
    """
    AGGREGATE ROOT - المنتج
    
    يمثل المنتج في النظام، ويتحكم في:
    - البيانات الأساسية (الاسم، الكود، السعر)
    - إدارة المخزون
    - حالة المنتج (نشط/غير نشط)
    - توليد الأحداث domain events
    
    ملاحظة: الـ version هو للتحكم في التزامن (Optimistic Locking)
    يتم إدارته فقط بواسطة الـ Repository ولا يتم تعديله داخل الـ Entity
    """
    
    # === معلومات أساسية ===
    id: ProductId = field(default_factory=ProductId.generate)
    code: ProductCode = field(default_factory=lambda: ProductCode(""))
    name: str = ""
    
    # === معلومات مالية ===
    unit_price: Money = field(default_factory=lambda: Money(Decimal('0'), "USD"))
    tax_rate: Decimal = Decimal('0')
    
    # === معلومات إضافية ===
    description: Optional[str] = None
    category: Optional[str] = None
    
    # === المخزون ===
    stock_quantity: int = 0
    low_stock_threshold: int = 10  # حد التحذير للمخزون المنخفض
    
    # === الحالة ===
    status: ProductStatus = ProductStatus.ACTIVE
    
    # === بيانات التدقيق ===
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = ""
    
    # === التحكم في التزامن (تتم إدارته فقط بواسطة Repository) ===
    version: int = 1
    
    # === سجل حركات المخزون ===
    stock_movements: List[StockMovement] = field(default_factory=list, repr=False)
    
    # === أحداث المجال ===
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # ========== الخصائص المحسوبة ==========
    
    @property
    def is_active(self) -> bool:
        """هل المنتج نشط؟"""
        return self.status == ProductStatus.ACTIVE
    
    @property
    def is_inactive(self) -> bool:
        """هل المنتج غير نشط؟"""
        return self.status == ProductStatus.INACTIVE
    
    @property
    def is_discontinued(self) -> bool:
        """هل تم إيقاف المنتج؟"""
        return self.status == ProductStatus.DISCONTINUED
    
    @property
    def is_low_stock(self) -> bool:
        """هل المخزون منخفض؟"""
        return 0 < self.stock_quantity <= self.low_stock_threshold
    
    @property
    def is_out_of_stock(self) -> bool:
        """هل المخزون نفد؟"""
        return self.stock_quantity <= 0
    
    @property
    def stock_value(self) -> Money:
        """قيمة المخزون الإجمالية (السعر × الكمية)"""
        return Money(self.unit_price.amount * Decimal(str(self.stock_quantity)), self.unit_price.currency)
    
    @property
    def unit_price_with_tax(self) -> Decimal:
        """سعر الوحدة شامل الضريبة"""
        return self.unit_price.amount * (Decimal('1') + self.tax_rate / Decimal('100'))
    
    # ========== الطرق الأساسية ==========
    
    def activate(self, activated_by: str) -> None:
        """
        تنشيط المنتج (جعله متاحاً للبيع)
        
        ملاحظة: الـ version لا يتغير هنا - يتم تحديثه فقط بواسطة Repository
        """
        if self.is_active:
            raise ProductAlreadyActiveError(str(self.code))
        
        self.status = ProductStatus.ACTIVE
        self.updated_at = utc_now()
        self.updated_by = activated_by
        
        # تسجيل حدث إعادة التنشيط
        self._events.append(ProductReactivatedEvent(
            product_id=self.id,
            product_code=self.code,
            product_name=self.name,
            reactivated_by=activated_by,
        ))
    
    def deactivate(self, deactivated_by: str, reason: Optional[str] = None) -> None:
        """
        تعطيل المنتج (إزالته من البيع مؤقتاً)
        
        ملاحظة: الـ version لا يتغير هنا - يتم تحديثه فقط بواسطة Repository
        """
        if self.is_inactive:
            raise ProductAlreadyInactiveError(str(self.code))
        
        self.status = ProductStatus.INACTIVE
        self.updated_at = utc_now()
        self.updated_by = deactivated_by
        
        # تسجيل حدث الحذف/التعطيل
        self._events.append(ProductDeletedEvent(
            product_id=self.id,
            product_code=self.code,
            product_name=self.name,
            deleted_by=deactivated_by,
            reason=reason,
        ))
    
    def update(
        self,
        code: Optional[ProductCode] = None,
        name: Optional[str] = None,
        unit_price: Optional[Money] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tax_rate: Optional[Decimal] = None,
        low_stock_threshold: Optional[int] = None,
        updated_by: str = "",
    ) -> None:
        """
        تحديث بيانات المنتج
        
        ملاحظة: الـ version لا يتغير هنا - يتم تحديثه فقط بواسطة Repository
        """
        # التحقق من إمكانية تعديل المنتج غير النشط
        if self.is_inactive and (code or name or unit_price):
            raise CannotModifyInactiveProductError(str(self.code))
        
        changes = {}
        
        if code is not None and code != self.code:
            changes['code'] = {'old': str(self.code), 'new': str(code)}
            self.code = code
        
        if name is not None and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name
        
        if unit_price is not None and unit_price != self.unit_price:
            old_price = self.unit_price
            changes['unit_price'] = {'old': str(old_price.amount), 'new': str(unit_price.amount)}
            self.unit_price = unit_price
            
            # تسجيل حدث تغيير السعر
            self._events.append(PriceChangedEvent(
                product_id=self.id,
                product_code=self.code,
                product_name=self.name,
                old_price=old_price,
                new_price=unit_price,
                changed_by=updated_by,
            ))
        
        if description is not None and description != self.description:
            changes['description'] = {'old': self.description, 'new': description}
            self.description = description
        
        if category is not None and category != self.category:
            changes['category'] = {'old': self.category, 'new': category}
            self.category = category
        
        if tax_rate is not None and tax_rate != self.tax_rate:
            changes['tax_rate'] = {'old': str(self.tax_rate), 'new': str(tax_rate)}
            self.tax_rate = tax_rate
        
        if low_stock_threshold is not None and low_stock_threshold != self.low_stock_threshold:
            changes['low_stock_threshold'] = {'old': self.low_stock_threshold, 'new': low_stock_threshold}
            self.low_stock_threshold = low_stock_threshold
        
        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            
            # تسجيل حدث التحديث
            self._events.append(ProductUpdatedEvent(
                product_id=self.id,
                product_code=self.code,
                product_name=self.name,
                changes=changes,
                updated_by=updated_by,
            ))
    
    def update_stock(
        self,
        quantity_change: int,
        movement_type: StockMovementType,
        reason: str,
        updated_by: str,
        reference_id: Optional[str] = None,
    ) -> None:
        """
        تحديث كمية المخزون
        
        Args:
            quantity_change: التغيير في الكمية (موجب للإضافة، سالب للخصم)
            movement_type: نوع الحركة
            reason: سبب التغيير
            updated_by: من قام بالتغيير
            reference_id: مرجع الحركة (رقم فاتورة، أمر شراء، إلخ)
            
        ملاحظة: الـ version لا يتغير هنا - يتم تحديثه فقط بواسطة Repository
        """
        # التحقق من صحة الكمية
        if quantity_change == 0:
            raise InvalidStockQuantityError(quantity_change, "Quantity change cannot be zero")
        
        # التحقق من عدم السماح بالمخزون السالب
        if quantity_change < 0 and (self.stock_quantity + quantity_change) < 0:
            raise NegativeStockNotAllowedError(str(self.code), self.stock_quantity, abs(quantity_change))
        
        old_quantity = self.stock_quantity
        new_quantity = self.stock_quantity + quantity_change
        
        self.stock_quantity = new_quantity
        self.updated_at = utc_now()
        self.updated_by = updated_by
        
        # تسجيل حركة المخزون
        movement = StockMovement(
            id=uuid4(),
            product_id=self.id,
            quantity_change=quantity_change,
            type=movement_type,
            reason=reason,
            reference_id=reference_id,
            created_at=utc_now(),
            created_by=updated_by,
        )
        self.stock_movements.append(movement)
        
        # تسجيل حدث تحديث المخزون
        self._events.append(StockUpdatedEvent(
            product_id=self.id,
            product_code=self.code,
            product_name=self.name,
            old_quantity=old_quantity,
            new_quantity=new_quantity,
            quantity_change=quantity_change,
            movement_type=movement_type,
            reason=reason,
            reference_id=reference_id,
            updated_by=updated_by,
        ))
        
        # التحقق من المخزون المنخفض
        if self.is_low_stock:
            self._events.append(LowStockAlertEvent(
                product_id=self.id,
                product_code=self.code,
                product_name=self.name,
                current_quantity=self.stock_quantity,
                threshold=self.low_stock_threshold,
            ))
        
        # التحقق من نفاد المخزون
        if self.is_out_of_stock and old_quantity > 0:
            self._events.append(OutOfStockEvent(
                product_id=self.id,
                product_code=self.code,
                product_name=self.name,
            ))
    
    def increase_stock(
        self,
        quantity: int,
        movement_type: StockMovementType,
        reason: str,
        updated_by: str,
        reference_id: Optional[str] = None,
    ) -> None:
        """زيادة المخزون"""
        if quantity <= 0:
            raise InvalidStockQuantityError(quantity, "Increase quantity must be positive")
        self.update_stock(quantity, movement_type, reason, updated_by, reference_id)
    
    def decrease_stock(
        self,
        quantity: int,
        movement_type: StockMovementType,
        reason: str,
        updated_by: str,
        reference_id: Optional[str] = None,
    ) -> None:
        """نقصان المخزون"""
        if quantity <= 0:
            raise InvalidStockQuantityError(quantity, "Decrease quantity must be positive")
        
        if quantity > self.stock_quantity:
            raise InsufficientStockError(str(self.code), self.stock_quantity, quantity)
        
        self.update_stock(-quantity, movement_type, reason, updated_by, reference_id)
    
    def can_supply(self, requested_quantity: int) -> bool:
        """التحقق من إمكانية توفير الكمية المطلوبة"""
        return self.is_active and self.stock_quantity >= requested_quantity
    
    # ========== Domain Events ==========
    
    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المجمعة"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def add_event(self, event: Any) -> None:
        """إضافة حدث إلى المجموعة"""
        self._events.append(event)
    
    # ========== دالة المصنع ==========
    
    @classmethod
    def create(
        cls,
        code: ProductCode,
        name: str,
        unit_price: Money,
        description: Optional[str] = None,
        category: Optional[str] = None,
        tax_rate: Decimal = Decimal('0'),
        stock_quantity: int = 0,
        low_stock_threshold: int = 10,
        created_by: str = "",
    ) -> 'Product':
        """
        مصنع لإنشاء منتج جديد مع حدث الإنشاء
        
        ملاحظة: الـ version يبدأ بـ 1 للمنتج الجديد
        """
        product = cls(
            code=code,
            name=name,
            unit_price=unit_price,
            description=description,
            category=category,
            tax_rate=tax_rate,
            stock_quantity=stock_quantity,
            low_stock_threshold=low_stock_threshold,
            status=ProductStatus.ACTIVE,
            created_by=created_by,
            updated_by=created_by,
            version=1,  # الإصدار الأولي
        )
        
        # تسجيل حدث الإنشاء
        product._events.append(ProductCreatedEvent(
            product_id=product.id,
            product_code=product.code,
            product_name=product.name,
            unit_price=product.unit_price,
            category=product.category,
            created_by=created_by,
        ))
        
        return product
    
    # ========== التوثيق ==========
    
    def __repr__(self) -> str:
        return f"Product(id={self.id}, code={self.code}, name={self.name}, stock={self.stock_quantity}, active={self.is_active}, version={self.version})"