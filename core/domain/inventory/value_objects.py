# core/domain/inventory/value_objects.py
"""
Inventory Value Objects - كائنات القيمة للمخزون
الإصدار المُصلح - v3.1.0

✅ دعم طرق تقييم المخزون المتقدمة (FIFO, LIFO, Weighted Average)
✅ دعم طبقات المخزون (Inventory Layers)
✅ دعم الدفعات والأرقام التسلسلية
✅ دعم العملات المتعددة
✅ مصلح: إضافة __all__ بشكل صحيح
✅ مصلح: تحسين ExpiryDate
✅ مصلح: إضافة طرق التسلسل
"""

from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID, uuid4

# ✅ استيراد EntityId من shared
from core.domain.shared.value_objects import EntityId


# =============================================================================
# Enums الأساسية
# =============================================================================

class StockMovementType(Enum):
    """نوع حركة المخزون"""
    PURCHASE = "purchase"          # شراء
    SALE = "sale"                  # بيع
    RETURN = "return"              # مرتجع
    ADJUSTMENT_IN = "adjustment_in"   # تعديل إيجابي
    ADJUSTMENT_OUT = "adjustment_out" # تعديل سلبي
    TRANSFER_IN = "transfer_in"    # تحويل وارد
    TRANSFER_OUT = "transfer_out"  # تحويل صادر
    DAMAGE = "damage"              # تالف
    EXPIRED = "expired"            # منتهي الصلاحية
    
    @property
    def is_inbound(self) -> bool:
        """هل الحركة تزيد المخزون؟"""
        return self in [
            StockMovementType.PURCHASE,
            StockMovementType.RETURN,
            StockMovementType.ADJUSTMENT_IN,
            StockMovementType.TRANSFER_IN,
        ]
    
    @property
    def is_outbound(self) -> bool:
        """هل الحركة تنقص المخزون؟"""
        return self in [
            StockMovementType.SALE,
            StockMovementType.ADJUSTMENT_OUT,
            StockMovementType.TRANSFER_OUT,
            StockMovementType.DAMAGE,
            StockMovementType.EXPIRED,
        ]
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        names = {
            "purchase": "شراء",
            "sale": "بيع",
            "return": "مرتجع",
            "adjustment_in": "تعديل إيجابي",
            "adjustment_out": "تعديل سلبي",
            "transfer_in": "تحويل وارد",
            "transfer_out": "تحويل صادر",
            "damage": "تالف",
            "expired": "منتهي الصلاحية",
        }
        return names.get(self.value, self.value)


class StockBatchStatus(Enum):
    """حالة دفعة المخزون"""
    ACTIVE = "active"
    PARTIALLY_CONSUMED = "partially_consumed"
    FULLY_CONSUMED = "fully_consumed"
    EXPIRED = "expired"
    QUARANTINED = "quarantined"
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        names = {
            "active": "نشطة",
            "partially_consumed": "مستهلكة جزئياً",
            "fully_consumed": "مستهلكة بالكامل",
            "expired": "منتهية الصلاحية",
            "quarantined": "محجوزة",
        }
        return names.get(self.value, self.value)


class CostFlowMethod(Enum):
    """طريقة تدفق التكلفة"""
    FIFO = "fifo"                  # First In, First Out
    LIFO = "lifo"                  # Last In, First Out
    WEIGHTED_AVERAGE = "weighted_average"  # المتوسط المرجح
    SPECIFIC_ID = "specific_id"    # التحديد المحدد (للدُفعات)
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض"""
        names = {
            "fifo": "FIFO (First-In, First-Out)",
            "lifo": "LIFO (Last-In, First-Out)",
            "weighted_average": "المتوسط المرجح",
            "specific_id": "التحديد المحدد",
        }
        return names.get(self.value, self.value)


# =============================================================================
# معرفات (IDs) - مُحسّنة
# =============================================================================

@dataclass(frozen=True)
class StockMovementId:
    """معرف حركة المخزون"""
    value: UUID
    
    @classmethod
    def generate(cls) -> 'StockMovementId':
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> 'StockMovementId':
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"StockMovementId({self.value})"


@dataclass(frozen=True)
class StockBatchId:
    """معرف دفعة المخزون"""
    value: UUID
    
    @classmethod
    def generate(cls) -> 'StockBatchId':
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> 'StockBatchId':
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"StockBatchId({self.value})"


@dataclass(frozen=True)
class StockTransferId:
    """معرف تحويل المخزون"""
    value: UUID
    
    @classmethod
    def generate(cls) -> 'StockTransferId':
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> 'StockTransferId':
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)
    
    def __repr__(self) -> str:
        return f"StockTransferId({self.value})"


# =============================================================================
# كائنات القيمة الأساسية - مُحسّنة
# =============================================================================

@dataclass(frozen=True)
class BatchNumber:
    """رقم الدفعة"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Batch number cannot be empty")
        # تنظيف القيمة
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"BatchNumber('{self.value}')"
    
    def to_dict(self) -> Dict[str, Any]:
        return {"batch_number": self.value}


@dataclass(frozen=True)
class SerialNumber:
    """رقم تسلسلي"""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Serial number cannot be empty")
        # تنظيف القيمة
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"SerialNumber('{self.value}')"
    
    def to_dict(self) -> Dict[str, Any]:
        return {"serial_number": self.value}


@dataclass(frozen=True)
class ExpiryDate:
    """تاريخ الانتهاء - مُصلح"""
    value: date
    
    def __post_init__(self):
        # ✅ مصلح: استخدام date.today() بدلاً من datetime.now().date()
        today = date.today()
        if self.value < today:
            raise ValueError(f"Expiry date {self.value} is in the past")
    
    @property
    def days_remaining(self) -> int:
        """عدد الأيام المتبقية حتى الانتهاء"""
        return (self.value - date.today()).days
    
    @property
    def is_expired(self) -> bool:
        """هل التاريخ منتهي؟"""
        return self.value < date.today()
    
    @property
    def is_expiring_soon(self, days_threshold: int = 30) -> bool:
        """هل التاريخ يقترب من الانتهاء؟"""
        return 0 <= self.days_remaining <= days_threshold
    
    @property
    def is_valid(self) -> bool:
        """هل التاريخ صالح؟"""
        return not self.is_expired
    
    def __str__(self) -> str:
        return self.value.isoformat()
    
    def __repr__(self) -> str:
        return f"ExpiryDate('{self.value.isoformat()}')"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "expiry_date": self.value.isoformat(),
            "days_remaining": self.days_remaining,
            "is_expired": self.is_expired,
            "is_expiring_soon": self.is_expiring_soon
        }


@dataclass(frozen=True)
class StockLocation:
    """موقع التخزين - مُحسّن"""
    warehouse: str
    aisle: Optional[str] = None
    shelf: Optional[str] = None
    bin: Optional[str] = None
    
    def __post_init__(self):
        if not self.warehouse or not self.warehouse.strip():
            raise ValueError("Warehouse cannot be empty")
        # تنظيف القيم
        warehouse_cleaned = self.warehouse.strip().upper()
        object.__setattr__(self, 'warehouse', warehouse_cleaned)
        if self.aisle:
            object.__setattr__(self, 'aisle', self.aisle.strip().upper())
        if self.shelf:
            object.__setattr__(self, 'shelf', self.shelf.strip().upper())
        if self.bin:
            object.__setattr__(self, 'bin', self.bin.strip().upper())
    
    @classmethod
    def from_string(cls, location_str: str) -> 'StockLocation':
        """
        إنشاء موقع من نص (مثل: 'WH01-A1-S2-B3')
        
        ✅ مصلح: التعامل مع الحالات الفارغة
        """
        if not location_str or not location_str.strip():
            raise ValueError("Location string cannot be empty")
        
        parts = location_str.split('-')
        warehouse = parts[0].strip().upper() if parts else ""
        aisle = parts[1].strip().upper() if len(parts) > 1 and parts[1].strip() else None
        shelf = parts[2].strip().upper() if len(parts) > 2 and parts[2].strip() else None
        bin = parts[3].strip().upper() if len(parts) > 3 and parts[3].strip() else None
        
        return cls(warehouse=warehouse, aisle=aisle, shelf=shelf, bin=bin)
    
    @property
    def full_path(self) -> str:
        """المسار الكامل للموقع"""
        parts = [self.warehouse]
        if self.aisle:
            parts.append(self.aisle)
        if self.shelf:
            parts.append(self.shelf)
        if self.bin:
            parts.append(self.bin)
        return '-'.join(parts)
    
    @property
    def short_path(self) -> str:
        """المسار المختصر للموقع"""
        return self.warehouse
    
    def __str__(self) -> str:
        return self.full_path
    
    def __repr__(self) -> str:
        return f"StockLocation(warehouse='{self.warehouse}', aisle={self.aisle}, shelf={self.shelf}, bin={self.bin})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "warehouse": self.warehouse,
            "aisle": self.aisle,
            "shelf": self.shelf,
            "bin": self.bin,
            "full_path": self.full_path
        }


# =============================================================================
# Money - القيمة النقدية (مُحسّنة)
# =============================================================================

@dataclass(frozen=True)
class Money:
    """قيمة مالية مع العملة - مُحسّنة"""
    amount: Decimal
    currency: str = "USD"
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not self.currency or len(self.currency) != 3:
            raise ValueError(f"Invalid currency: {self.currency}")
        # تنظيف العملة
        currency_cleaned = self.currency.upper().strip()
        object.__setattr__(self, 'currency', currency_cleaned)
    
    @classmethod
    def zero(cls, currency: str = "USD") -> 'Money':
        return cls(Decimal('0'), currency)
    
    @classmethod
    def from_float(cls, amount: float, currency: str = "USD") -> 'Money':
        return cls(Decimal(str(amount)), currency)
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        return Money(self.amount - other.amount, self.currency)
    
    def __mul__(self, multiplier: Decimal) -> 'Money':
        return Money(self.amount * multiplier, self.currency)
    
    def __truediv__(self, divisor: Decimal) -> 'Money':
        if divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Money(self.amount / divisor, self.currency)
    
    def __neg__(self) -> 'Money':
        return Money(-self.amount, self.currency)
    
    def __abs__(self) -> 'Money':
        return Money(abs(self.amount), self.currency)
    
    def is_zero(self) -> bool:
        return self.amount == 0
    
    def is_positive(self) -> bool:
        return self.amount > 0
    
    def is_negative(self) -> bool:
        return self.amount < 0
    
    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"
    
    def __repr__(self) -> str:
        return f"Money({self.amount}, '{self.currency}')"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "amount": float(self.amount),
            "currency": self.currency,
            "formatted": str(self)
        }


# =============================================================================
# طبقات المخزون (Inventory Layers) - للتقييم المتقدم
# =============================================================================

@dataclass(frozen=True)
class InventoryLayer:
    """
    طبقة مخزون - تستخدم لحساب FIFO و LIFO
    
    تمثل مجموعة من الوحدات المشتراة بنفس التكلفة في نفس الوقت
    """
    quantity: Decimal
    unit_cost: Decimal
    currency: str = "USD"
    purchase_date: Optional[date] = None
    batch_number: Optional[str] = None
    layer_id: Optional[str] = None
    
    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError(f"Quantity must be positive: {self.quantity}")
        if self.unit_cost < 0:
            raise ValueError(f"Unit cost cannot be negative: {self.unit_cost}")
        if self.currency and len(self.currency) != 3:
            raise ValueError(f"Invalid currency: {self.currency}")
    
    @property
    def total_cost(self) -> Decimal:
        """إجمالي تكلفة الطبقة"""
        return self.quantity * self.unit_cost
    
    @property
    def unit_cost_money(self) -> Money:
        """تكلفة الوحدة ككائن Money"""
        return Money(self.unit_cost, self.currency)
    
    @property
    def total_cost_money(self) -> Money:
        """إجمالي التكلفة ككائن Money"""
        return Money(self.total_cost, self.currency)
    
    @property
    def is_empty(self) -> bool:
        """هل الطبقة فارغة؟"""
        return self.quantity == 0
    
    def consume(self, quantity: Decimal) -> Optional['InventoryLayer']:
        """
        استهلاك كمية من الطبقة وإرجاع الطبقة المتبقية
        
        Args:
            quantity: الكمية المراد استهلاكها
        
        Returns:
            Optional[InventoryLayer]: الطبقة المتبقية أو None إذا استهلكت بالكامل
        """
        if quantity > self.quantity:
            raise ValueError(f"Cannot consume {quantity} from layer with {self.quantity}")
        
        if quantity == self.quantity:
            return None
        
        # استهلاك جزئي
        return InventoryLayer(
            quantity=self.quantity - quantity,
            unit_cost=self.unit_cost,
            currency=self.currency,
            purchase_date=self.purchase_date,
            batch_number=self.batch_number,
            layer_id=self.layer_id
        )
    
    def __repr__(self) -> str:
        return (
            f"InventoryLayer(quantity={self.quantity}, unit_cost={self.unit_cost}, "
            f"currency='{self.currency}', batch='{self.batch_number}')"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "quantity": float(self.quantity),
            "unit_cost": float(self.unit_cost),
            "currency": self.currency,
            "total_cost": float(self.total_cost),
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "batch_number": self.batch_number,
            "layer_id": self.layer_id
        }


# =============================================================================
# StockLayer - للتوافق مع الكود القديم
# =============================================================================

@dataclass(frozen=True)
class StockLayer:
    """
    طبقة مخزون (للتوافق مع الكود القديم)
    يوصى باستخدام InventoryLayer بدلاً من ذلك
    """
    quantity: Decimal
    unit_cost: Money
    batch_number: Optional[BatchNumber] = None
    expiry_date: Optional[ExpiryDate] = None
    entry_date: Optional[datetime] = None
    
    @property
    def total_cost(self) -> Money:
        """إجمالي تكلفة الطبقة"""
        return Money(self.quantity * self.unit_cost.amount, self.unit_cost.currency)
    
    @property
    def is_empty(self) -> bool:
        return self.quantity == 0
    
    def __repr__(self) -> str:
        return f"StockLayer(quantity={self.quantity}, unit_cost={self.unit_cost})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "quantity": float(self.quantity),
            "unit_cost": float(self.unit_cost.amount),
            "currency": self.unit_cost.currency,
            "total_cost": float(self.total_cost.amount),
            "batch_number": str(self.batch_number) if self.batch_number else None,
            "expiry_date": str(self.expiry_date) if self.expiry_date else None,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None
        }


# =============================================================================
# نتائج التقييم - مُحسّنة
# =============================================================================

@dataclass(frozen=True)
class InventoryValuationResult:
    """
    نتيجة تقييم المخزون
    
    تحتوي على:
        - الكمية الإجمالية
        - القيمة الإجمالية
        - متوسط التكلفة
        - طريقة التقييم المستخدمة
        - تفاصيل الطبقات (لـ FIFO/LIFO)
        - COGS (تكلفة البضاعة المباعة) إذا تم حسابه
    """
    total_quantity: Decimal
    total_value: Decimal
    average_cost: Decimal
    currency: str
    valuation_method: CostFlowMethod
    as_of_date: date
    layers: Optional[List[InventoryLayer]] = None
    cogs: Optional[Decimal] = None
    opening_value: Optional[Decimal] = None
    closing_value: Optional[Decimal] = None
    
    @property
    def total_value_formatted(self) -> str:
        return f"{self.total_value:,.2f} {self.currency}"
    
    @property
    def average_cost_formatted(self) -> str:
        return f"{self.average_cost:,.2f} {self.currency}"
    
    @property
    def cogs_formatted(self) -> str:
        if self.cogs is None:
            return "N/A"
        return f"{self.cogs:,.2f} {self.currency}"
    
    @property
    def layer_count(self) -> int:
        """عدد الطبقات"""
        return len(self.layers) if self.layers else 0
    
    @property
    def total_quantity_formatted(self) -> str:
        return f"{self.total_quantity:,.2f}"
    
    @property
    def valuation_method_display(self) -> str:
        """اسم طريقة التقييم معروضاً"""
        return self.valuation_method.display_name
    
    @property
    def is_zero(self) -> bool:
        return self.total_quantity == 0 or self.total_value == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل النتيجة إلى قاموس"""
        return {
            'total_quantity': float(self.total_quantity),
            'total_value': float(self.total_value),
            'average_cost': float(self.average_cost),
            'currency': self.currency,
            'valuation_method': self.valuation_method.value,
            'valuation_method_display': self.valuation_method_display,
            'as_of_date': self.as_of_date.isoformat(),
            'cogs': float(self.cogs) if self.cogs else None,
            'cogs_formatted': self.cogs_formatted,
            'layer_count': self.layer_count,
            'layers': [
                {
                    'quantity': float(l.quantity),
                    'unit_cost': float(l.unit_cost),
                    'currency': l.currency,
                    'total_cost': float(l.total_cost),
                    'purchase_date': l.purchase_date.isoformat() if l.purchase_date else None,
                    'batch_number': l.batch_number
                }
                for l in (self.layers or [])
            ]
        }
    
    def compare_with(self, other: 'InventoryValuationResult') -> Dict[str, Any]:
        """مقارنة نتيجة تقييم مع أخرى"""
        return {
            'value_difference': float(self.total_value - other.total_value),
            'value_difference_percent': float(
                ((self.total_value - other.total_value) / other.total_value) * 100
                if other.total_value > 0 else 0
            ),
            'average_cost_difference': float(self.average_cost - other.average_cost),
            'method1': self.valuation_method.value,
            'method2': other.valuation_method.value
        }
    
    def __repr__(self) -> str:
        return (
            f"InventoryValuationResult(total_quantity={self.total_quantity}, "
            f"total_value={self.total_value}, method={self.valuation_method.value})"
        )


# =============================================================================
# StockValuation (للتوافق مع الكود القديم)
# =============================================================================

@dataclass(frozen=True)
class StockValuation:
    """تقييم المخزون (للتوافق مع الكود القديم)"""
    total_quantity: Decimal
    total_cost: Money
    average_cost: Money
    valuation_method: CostFlowMethod
    as_of_date: date
    currency: str = "USD"
    
    @property
    def total_cost_formatted(self) -> str:
        return f"{self.total_cost.amount:,.2f} {self.currency}"
    
    @property
    def average_cost_formatted(self) -> str:
        return f"{self.average_cost.amount:,.2f} {self.currency}"
    
    @property
    def valuation_method_display(self) -> str:
        return self.valuation_method.display_name
    
    def __repr__(self) -> str:
        return (
            f"StockValuation(total_quantity={self.total_quantity}, "
            f"total_cost={self.total_cost}, method={self.valuation_method.value})"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_quantity": float(self.total_quantity),
            "total_cost": float(self.total_cost.amount),
            "average_cost": float(self.average_cost.amount),
            "currency": self.currency,
            "valuation_method": self.valuation_method.value,
            "valuation_method_display": self.valuation_method_display,
            "as_of_date": self.as_of_date.isoformat()
        }


# =============================================================================
# تقرير مقارنة طرق التقييم - مُحسّن
# =============================================================================

@dataclass(frozen=True)
class ValuationComparisonReport:
    """
    تقرير مقارنة طرق التقييم المختلفة
    
    يقارن نتائج FIFO، LIFO، و Weighted Average
    """
    entity_id: str
    as_of_date: date
    currency: str
    fifo_result: InventoryValuationResult
    lifo_result: InventoryValuationResult
    weighted_average_result: InventoryValuationResult
    
    @property
    def differences(self) -> Dict[str, float]:
        """الفروق بين الطرق المختلفة"""
        return {
            'fifo_vs_lifo': float(self.fifo_result.total_value - self.lifo_result.total_value),
            'fifo_vs_weighted': float(self.fifo_result.total_value - self.weighted_average_result.total_value),
            'lifo_vs_weighted': float(self.lifo_result.total_value - self.weighted_average_result.total_value),
            'fifo_vs_lifo_percent': float(
                ((self.fifo_result.total_value - self.lifo_result.total_value) / 
                 self.lifo_result.total_value) * 100 if self.lifo_result.total_value > 0 else 0
            )
        }
    
    @property
    def best_method(self) -> str:
        """أفضل طريقة (الأعلى قيمة)"""
        methods = {
            'FIFO': self.fifo_result.total_value,
            'LIFO': self.lifo_result.total_value,
            'Weighted Average': self.weighted_average_result.total_value
        }
        return max(methods, key=methods.get)
    
    @property
    def worst_method(self) -> str:
        """أسوأ طريقة (الأدنى قيمة)"""
        methods = {
            'FIFO': self.fifo_result.total_value,
            'LIFO': self.lifo_result.total_value,
            'Weighted Average': self.weighted_average_result.total_value
        }
        return min(methods, key=methods.get)
    
    @property
    def recommendation(self) -> str:
        """توصية بالطريقة المناسبة"""
        diff = abs(self.differences['fifo_vs_lifo'])
        if diff < 0.01:
            return "جميع الطرق تعطي نفس النتيجة تقريباً. يمكن استخدام أي منها."
        
        if self.fifo_result.total_value > self.lifo_result.total_value:
            if self.fifo_result.total_value > self.weighted_average_result.total_value:
                return "FIFO تعطي أعلى قيمة للمخزون. مناسبة في فترات التضخم."
            else:
                return "Weighted Average تعطي قيمة وسطية. مناسبة للاستقرار."
        else:
            if self.lifo_result.total_value > self.weighted_average_result.total_value:
                return "LIFO تعطي أعلى قيمة للمخزون. مناسبة في فترات الانكماش."
            else:
                return "Weighted Average تعطي قيمة وسطية. مناسبة للاستقرار."
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل التقرير إلى قاموس"""
        return {
            'entity_id': self.entity_id,
            'as_of_date': self.as_of_date.isoformat(),
            'currency': self.currency,
            'methods': {
                'fifo': self.fifo_result.to_dict(),
                'lifo': self.lifo_result.to_dict(),
                'weighted_average': self.weighted_average_result.to_dict()
            },
            'differences': self.differences,
            'best_method': self.best_method,
            'worst_method': self.worst_method,
            'recommendation': self.recommendation
        }
    
    def __repr__(self) -> str:
        return (
            f"ValuationComparisonReport(entity={self.entity_id}, "
            f"as_of={self.as_of_date}, best={self.best_method})"
        )


# =============================================================================
# ✅ تصدير جميع الكائنات
# =============================================================================

__all__ = [
    # Enums
    "StockMovementType",
    "StockBatchStatus",
    "CostFlowMethod",
    
    # IDs
    "StockMovementId",
    "StockBatchId",
    "StockTransferId",
    
    # كائنات القيمة الأساسية
    "EntityId",
    "BatchNumber",
    "SerialNumber",
    "ExpiryDate",
    "StockLocation",
    "Money",
    
    # طبقات المخزون
    "InventoryLayer",
    "StockLayer",
    
    # نتائج التقييم
    "InventoryValuationResult",
    "StockValuation",
    "ValuationComparisonReport",
]