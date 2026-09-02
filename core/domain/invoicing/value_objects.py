# core/domain/invoicing/value_objects.py
"""Value Objects for Invoicing Context"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class InvoiceStatus(Enum):
    """حالات الفاتورة"""
    DRAFT = "draft"           # مسودة - يمكن تعديلها
    POSTED = "posted"         # مرحلة - تم إنشاء قيد محاسبي
    CANCELLED = "cancelled"   # ملغاة


class PaymentType(Enum):
    """طرق الدفع"""
    CASH = "cash"         # نقدي
    CREDIT = "credit"     # آجل
    CHECK = "check"       # شيك
    TRANSFER = "transfer" # تحويل بنكي


@dataclass(frozen=True)
class InvoiceNumber:
    """رقم الفاتورة - Value Object"""
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("Invoice number cannot be empty")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class InvoiceId:
    """معرف الفاتورة الفريد - يقبل UUID أو String"""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            # إذا كان string، نحوله إلى UUID
            if isinstance(self.value, str):
                object.__setattr__(self, 'value', UUID(self.value))
            else:
                raise ValueError("InvoiceId must be UUID or UUID string")
    
    @classmethod
    def generate(cls) -> "InvoiceId":
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "InvoiceId":
        """إنشاء InvoiceId من نص"""
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)