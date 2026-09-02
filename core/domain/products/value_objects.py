# core/domain/products/value_objects.py
"""
Value Objects for Products Domain
كائنات القيمة للمنتجات - غير قابلة للتعديل بعد الإنشاء
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

class ProductStatus(Enum):
    """حالة المنتج"""
    ACTIVE = "active"      # نشط - متاح للبيع
    INACTIVE = "inactive"  # غير نشط - غير متاح للبيع
    DISCONTINUED = "discontinued"  # توقف إنتاجه


class StockMovementType(Enum):
    """نوع حركة المخزون"""
    PURCHASE = "purchase"      # شراء - زيادة المخزون
    SALE = "sale"              # بيع - نقص المخزون
    RETURN = "return"          # مرتجع - زيادة المخزون
    ADJUSTMENT = "adjustment"  # تعديل يدوي
    DAMAGE = "damage"          # تالف - نقص المخزون
    TRANSFER_IN = "transfer_in"    # تحويل وارد
    TRANSFER_OUT = "transfer_out"  # تحويل صادر


@dataclass(frozen=True)
class ProductId:
    """
    معرف المنتج الفريد - Value Object
    """
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            if isinstance(self.value, str):
                object.__setattr__(self, 'value', UUID(self.value))
            else:
                raise ValueError("ProductId must be UUID or UUID string")
    
    @classmethod
    def generate(cls) -> 'ProductId':
        """توليد معرف جديد"""
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> 'ProductId':
        """إنشاء ProductId من نص"""
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class ProductCode:
    """
    كود المنتج - Value Object
    يجب أن يكون فريداً في النظام
    """
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("Product code cannot be empty")
        
        # تنظيف الكود
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)
        
        # التحقق من صحة التنسيق (مثال: يجب أن يكون 3-20 حرف)
        if len(self.value) < 2 or len(self.value) > 50:
            raise ValueError(f"Product code must be between 2 and 50 characters, got {len(self.value)}")
        
        # السماح فقط بالحروف والأرقام والشرطات والشرطات السفلية
        import re
        if not re.match(r'^[A-Z0-9\-_]+$', self.value):
            raise ValueError(f"Product code can only contain letters, numbers, hyphens and underscores: {self.value}")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class StockMovement:
    """
    حركة مخزون - Value Object (سجل غير قابل للتعديل)
    """
    id: UUID
    product_id: ProductId
    quantity_change: int  # يمكن أن يكون موجب أو سالب
    type: StockMovementType
    reason: str
    reference_id: Optional[str]  # رقم الفاتورة، أمر الشراء، إلخ
    created_at: datetime
    created_by: str
    
    @property
    def is_increase(self) -> bool:
        """هل الحركة تزيد المخزون؟"""
        return self.quantity_change > 0
    
    @property
    def is_decrease(self) -> bool:
        """هل الحركة تنقص المخزون؟"""
        return self.quantity_change < 0
    
    @property
    def absolute_quantity(self) -> int:
        """القيمة المطلقة للكمية"""
        return abs(self.quantity_change)


# استيراد datetime للتأكد من وجوده في النطاق
from datetime import datetime