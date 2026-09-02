# core/domain/inventory/entities.py
"""
Inventory Entities - كيانات المخزون
الإصدار: 3.0.0
✅ دعم كامل لحركات المخزون (دخول/خروج)
✅ دعم الدفعات (Batch/Lot Tracking)
✅ دعم الأرقام التسلسلية (Serial Numbers)
✅ دعم تحويلات المخزون بين المواقع
✅ دعم تقييم المخزون (FIFO/LIFO) عبر الطبقات
✅ دعم أحداث المجال (Domain Events)
✅ دعم العملات المتعددة
✅ دعم Optimistic Locking
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, List, Any, Dict
from uuid import UUID, uuid4

from core.domain.shared.value_objects import EntityId
from core.domain.inventory.value_objects import (
    StockMovementId,
    StockBatchId,
    StockTransferId,
    StockMovementType,
    StockBatchStatus,
    BatchNumber,
    SerialNumber,
    ExpiryDate,
    StockLocation,
    Money,
    InventoryLayer,
    CostFlowMethod,
)


def utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


# =============================================================================
# StockMovement - حركة المخزون
# =============================================================================

@dataclass
class StockMovement:
    """
    حركة مخزون - تسجيل تغيير في كمية المخزون
    
    هذه هي الوحدة الأساسية لتتبع المخزون. كل حركة تمثل تغييراً في كمية
    منتج معين، سواء كان دخولاً (شراء، مرتجع، إلخ) أو خروجاً (بيع، تعديل، إلخ).
    
    Attributes:
        id: معرف فريد للحركة
        entity: الكيان المرتبط (منتج، مادة خام، إلخ)
        movement_type: نوع الحركة (شراء، بيع، إلخ)
        quantity: الكمية (موجبة دائماً، يتم تحديد الاتجاه عبر movement_type)
        unit_cost: تكلفة الوحدة
        total_cost: التكلفة الإجمالية (quantity × unit_cost)
        reference_type: نوع المرجع (فاتورة، أمر شراء، إلخ)
        reference_id: معرف المرجع
        batch_number: رقم الدفعة (اختياري)
        serial_numbers: الأرقام التسلسلية (اختياري)
        expiry_date: تاريخ الانتهاء (اختياري)
        location: موقع التخزين (اختياري)
        notes: ملاحظات إضافية
        movement_date: تاريخ الحركة
        created_at: تاريخ الإنشاء
        created_by: من قام بالإنشاء
    """
    
    id: StockMovementId = field(default_factory=StockMovementId.generate)
    entity: EntityId = field(default_factory=lambda: EntityId("product", ""))
    movement_type: StockMovementType = StockMovementType.PURCHASE
    quantity: Decimal = Decimal('0')
    unit_cost: Money = field(default_factory=lambda: Money.zero())
    total_cost: Money = field(default_factory=lambda: Money.zero())
    
    reference_type: str = ""
    reference_id: str = ""
    
    batch_number: Optional[BatchNumber] = None
    serial_numbers: List[SerialNumber] = field(default_factory=list)
    expiry_date: Optional[ExpiryDate] = None
    location: Optional[StockLocation] = None
    
    notes: str = ""
    movement_date: datetime = field(default_factory=utc_now)
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    
    # Optimistic Locking
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def is_inbound(self) -> bool:
        """هل الحركة تزيد المخزون؟"""
        return self.movement_type.is_inbound
    
    @property
    def is_outbound(self) -> bool:
        """هل الحركة تنقص المخزون؟"""
        return self.movement_type.is_outbound
    
    @property
    def total_cost_formatted(self) -> str:
        """التكلفة الإجمالية منسقة"""
        return f"{self.total_cost.amount:,.2f} {self.total_cost.currency}"
    
    @property
    def quantity_formatted(self) -> str:
        """الكمية منسقة"""
        return f"{self.quantity:,.2f}"
    
    @property
    def unit_cost_formatted(self) -> str:
        """تكلفة الوحدة منسقة"""
        return f"{self.unit_cost.amount:,.2f} {self.unit_cost.currency}"
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض للحركة"""
        return f"{self.movement_type.value} - {self.entity} - {self.quantity} units"
    
    @classmethod
    def create_inbound(
        cls,
        entity: EntityId,
        quantity: Decimal,
        unit_cost: Money,
        movement_type: StockMovementType,
        reference_type: str,
        reference_id: str,
        batch_number: Optional[BatchNumber] = None,
        serial_numbers: Optional[List[SerialNumber]] = None,
        expiry_date: Optional[ExpiryDate] = None,
        location: Optional[StockLocation] = None,
        notes: str = "",
        created_by: str = "system"
    ) -> 'StockMovement':
        """
        إنشاء حركة واردة (تزيد المخزون)
        
        Args:
            entity: الكيان المرتبط
            quantity: الكمية (موجبة)
            unit_cost: تكلفة الوحدة
            movement_type: نوع الحركة (يجب أن يكون من النوع الوارد)
            reference_type: نوع المرجع
            reference_id: معرف المرجع
            batch_number: رقم الدفعة (اختياري)
            serial_numbers: الأرقام التسلسلية (اختياري)
            expiry_date: تاريخ الانتهاء (اختياري)
            location: موقع التخزين (اختياري)
            notes: ملاحظات
            created_by: من قام بالإنشاء
        
        Returns:
            StockMovement: الحركة المنشأة
        
        Raises:
            ValueError: إذا كان نوع الحركة ليس وارداً أو الكمية سالبة
        """
        if not movement_type.is_inbound:
            raise ValueError(f"{movement_type.value} is not an inbound movement")
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive for inbound movement")
        
        total_cost = Money(unit_cost.amount * quantity, unit_cost.currency)
        
        return cls(
            entity=entity,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            batch_number=batch_number,
            serial_numbers=serial_numbers or [],
            expiry_date=expiry_date,
            location=location,
            notes=notes,
            created_by=created_by,
            version=1
        )
    
    @classmethod
    def create_outbound(
        cls,
        entity: EntityId,
        quantity: Decimal,
        unit_cost: Money,
        movement_type: StockMovementType,
        reference_type: str,
        reference_id: str,
        batch_number: Optional[BatchNumber] = None,
        serial_numbers: Optional[List[SerialNumber]] = None,
        location: Optional[StockLocation] = None,
        notes: str = "",
        created_by: str = "system"
    ) -> 'StockMovement':
        """
        إنشاء حركة صادرة (تنقص المخزون)
        
        Args:
            entity: الكيان المرتبط
            quantity: الكمية (موجبة)
            unit_cost: تكلفة الوحدة
            movement_type: نوع الحركة (يجب أن يكون من النوع الصادر)
            reference_type: نوع المرجع
            reference_id: معرف المرجع
            batch_number: رقم الدفعة (اختياري)
            serial_numbers: الأرقام التسلسلية (اختياري)
            location: موقع التخزين (اختياري)
            notes: ملاحظات
            created_by: من قام بالإنشاء
        
        Returns:
            StockMovement: الحركة المنشأة
        
        Raises:
            ValueError: إذا كان نوع الحركة ليس صادراً أو الكمية سالبة
        """
        if not movement_type.is_outbound:
            raise ValueError(f"{movement_type.value} is not an outbound movement")
        
        if quantity <= 0:
            raise ValueError("Quantity must be positive for outbound movement")
        
        total_cost = Money(unit_cost.amount * quantity, unit_cost.currency)
        
        return cls(
            entity=entity,
            movement_type=movement_type,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            batch_number=batch_number,
            serial_numbers=serial_numbers or [],
            location=location,
            notes=notes,
            created_by=created_by,
            version=1
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الحركة إلى قاموس"""
        return {
            'id': str(self.id.value),
            'entity_type': self.entity.entity_type,
            'entity_id': self.entity.entity_id,
            'movement_type': self.movement_type.value,
            'quantity': float(self.quantity),
            'unit_cost': float(self.unit_cost.amount),
            'currency': self.unit_cost.currency,
            'total_cost': float(self.total_cost.amount),
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'batch_number': str(self.batch_number) if self.batch_number else None,
            'serial_numbers': [str(s) for s in self.serial_numbers],
            'expiry_date': str(self.expiry_date) if self.expiry_date else None,
            'location': str(self.location) if self.location else None,
            'notes': self.notes,
            'movement_date': self.movement_date.isoformat() if self.movement_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'version': self.version,
            'is_inbound': self.is_inbound,
            'is_outbound': self.is_outbound
        }
    
    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def add_event(self, event: Any) -> None:
        """إضافة حدث"""
        self._events.append(event)
    
    def __repr__(self) -> str:
        return f"StockMovement(id={self.id}, type={self.movement_type.value}, qty={self.quantity}, entity={self.entity})"


# =============================================================================
# StockBatch - دفعة المخزون
# =============================================================================

@dataclass
class StockBatch:
    """
    دفعة مخزون - تتبع الدفعات (Batch/Lot Tracking)
    
    تستخدم لتتبع المنتجات حسب الدفعات، مفيدة للمنتجات ذات تاريخ انتهاء
    أو المنتجات التي تحتاج إلى تتبع دقيق.
    
    Attributes:
        id: معرف فريد للدفعة
        entity: الكيان المرتبط (منتج)
        batch_number: رقم الدفعة (فريد)
        initial_quantity: الكمية الأولية
        current_quantity: الكمية الحالية
        unit_cost: تكلفة الوحدة
        total_cost: التكلفة الإجمالية
        production_date: تاريخ الإنتاج
        expiry_date: تاريخ الانتهاء
        location: موقع التخزين
        status: حالة الدفعة
        notes: ملاحظات
        created_at: تاريخ الإنشاء
        created_by: من قام بالإنشاء
        updated_at: تاريخ آخر تحديث
        updated_by: من قام بآخر تحديث
        version: رقم الإصدار (للتحكم في التزامن)
    """
    
    id: StockBatchId = field(default_factory=StockBatchId.generate)
    entity: EntityId = field(default_factory=lambda: EntityId("product", ""))
    batch_number: BatchNumber = field(default_factory=lambda: BatchNumber(""))
    
    initial_quantity: Decimal = Decimal('0')
    current_quantity: Decimal = Decimal('0')
    
    unit_cost: Money = field(default_factory=lambda: Money.zero())
    total_cost: Money = field(default_factory=lambda: Money.zero())
    
    production_date: Optional[datetime] = None
    expiry_date: Optional[ExpiryDate] = None
    
    location: Optional[StockLocation] = None
    status: StockBatchStatus = StockBatchStatus.ACTIVE
    
    notes: str = ""
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def is_active(self) -> bool:
        """هل الدفعة نشطة؟"""
        return self.status == StockBatchStatus.ACTIVE
    
    @property
    def is_fully_consumed(self) -> bool:
        """هل تم استهلاك الدفعة بالكامل؟"""
        return self.status == StockBatchStatus.FULLY_CONSUMED
    
    @property
    def is_expired(self) -> bool:
        """هل الدفعة منتهية الصلاحية؟"""
        return self.status == StockBatchStatus.EXPIRED
    
    @property
    def is_partially_consumed(self) -> bool:
        """هل تم استهلاك جزء من الدفعة؟"""
        return self.status == StockBatchStatus.PARTIALLY_CONSUMED
    
    @property
    def consumed_quantity(self) -> Decimal:
        """الكمية المستهلكة"""
        return self.initial_quantity - self.current_quantity
    
    @property
    def consumption_percentage(self) -> Decimal:
        """نسبة الاستهلاك"""
        if self.initial_quantity == 0:
            return Decimal('0')
        return (self.consumed_quantity / self.initial_quantity) * 100
    
    @property
    def remaining_percentage(self) -> Decimal:
        """النسبة المتبقية"""
        return Decimal('100') - self.consumption_percentage
    
    @property
    def total_cost_formatted(self) -> str:
        """التكلفة الإجمالية منسقة"""
        return f"{self.total_cost.amount:,.2f} {self.total_cost.currency}"
    
    @property
    def unit_cost_formatted(self) -> str:
        """تكلفة الوحدة منسقة"""
        return f"{self.unit_cost.amount:,.2f} {self.unit_cost.currency}"
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض للدفعة"""
        return f"Batch {self.batch_number} - {self.entity} ({self.current_quantity}/{self.initial_quantity})"
    
    @classmethod
    def create(
        cls,
        entity: EntityId,
        batch_number: BatchNumber,
        initial_quantity: Decimal,
        unit_cost: Money,
        total_cost: Money,
        production_date: Optional[datetime] = None,
        expiry_date: Optional[ExpiryDate] = None,
        location: Optional[StockLocation] = None,
        notes: str = "",
        created_by: str = "system"
    ) -> 'StockBatch':
        """
        إنشاء دفعة مخزون جديدة
        
        Args:
            entity: الكيان المرتبط
            batch_number: رقم الدفعة
            initial_quantity: الكمية الأولية
            unit_cost: تكلفة الوحدة
            total_cost: التكلفة الإجمالية
            production_date: تاريخ الإنتاج (اختياري)
            expiry_date: تاريخ الانتهاء (اختياري)
            location: موقع التخزين (اختياري)
            notes: ملاحظات
            created_by: من قام بالإنشاء
        
        Returns:
            StockBatch: الدفعة المنشأة
        """
        return cls(
            entity=entity,
            batch_number=batch_number,
            initial_quantity=initial_quantity,
            current_quantity=initial_quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            production_date=production_date,
            expiry_date=expiry_date,
            location=location,
            notes=notes,
            created_by=created_by,
            updated_by=created_by,
            version=1
        )
    
    def consume(
        self,
        quantity: Decimal,
        reference_type: str = "",
        reference_id: str = "",
        consumed_by: str = "system"
    ) -> None:
        """
        استهلاك كمية من الدفعة
        
        Args:
            quantity: الكمية المراد استهلاكها
            reference_type: نوع المرجع المرتبط بالاستهلاك
            reference_id: معرف المرجع المرتبط بالاستهلاك
            consumed_by: من قام بالاستهلاك
        
        Raises:
            ValueError: إذا كانت الكمية غير صالحة أو غير كافية
        """
        if quantity <= 0:
            raise ValueError("Consumption quantity must be positive")
        
        if quantity > self.current_quantity:
            raise ValueError(
                f"Insufficient quantity in batch: {self.current_quantity} < {quantity}"
            )
        
        old_status = self.status
        self.current_quantity -= quantity
        self.updated_at = utc_now()
        self.version += 1
        
        # تحديث الحالة
        if self.current_quantity == 0:
            self.status = StockBatchStatus.FULLY_CONSUMED
        elif self.current_quantity < self.initial_quantity:
            self.status = StockBatchStatus.PARTIALLY_CONSUMED
        
        # تسجيل الحدث
        from .events import StockBatchConsumedEvent
        self._events.append(StockBatchConsumedEvent(
            batch_id=self.id,
            entity=self.entity,
            batch_number=self.batch_number,
            consumed_quantity=quantity,
            remaining_quantity=self.current_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            consumed_by=consumed_by or self.updated_by or "system"
        ))
    
    def expire(self) -> None:
        """تعليم الدفعة كمنتهية الصلاحية"""
        if self.is_expired:
            return
        
        old_status = self.status
        self.status = StockBatchStatus.EXPIRED
        self.updated_at = utc_now()
        self.version += 1
        
        from .events import StockBatchExpiredEvent
        self._events.append(StockBatchExpiredEvent(
            batch_id=self.id,
            entity=self.entity,
            batch_number=self.batch_number,
            expired_quantity=self.current_quantity,
            expiry_date=self.expiry_date
        ))
    
    def replenish(self, quantity: Decimal, unit_cost: Money) -> None:
        """
        إعادة تزويد الدفعة بكمية إضافية
        
        Args:
            quantity: الكمية المضافة
            unit_cost: تكلفة الوحدة الجديدة (يتم حساب المتوسط)
        """
        if quantity <= 0:
            raise ValueError("Replenishment quantity must be positive")
        
        # حساب متوسط التكلفة الجديد
        total_old_cost = self.unit_cost.amount * self.current_quantity
        total_new_cost = unit_cost.amount * quantity
        total_quantity = self.current_quantity + quantity
        
        new_unit_cost = (total_old_cost + total_new_cost) / total_quantity
        
        self.current_quantity = total_quantity
        self.unit_cost = Money(new_unit_cost, unit_cost.currency)
        self.total_cost = Money(new_unit_cost * total_quantity, unit_cost.currency)
        self.updated_at = utc_now()
        self.version += 1
        
        if self.status == StockBatchStatus.FULLY_CONSUMED:
            self.status = StockBatchStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الدفعة إلى قاموس"""
        return {
            'id': str(self.id.value),
            'entity_type': self.entity.entity_type,
            'entity_id': self.entity.entity_id,
            'batch_number': str(self.batch_number),
            'initial_quantity': float(self.initial_quantity),
            'current_quantity': float(self.current_quantity),
            'consumed_quantity': float(self.consumed_quantity),
            'consumption_percentage': float(self.consumption_percentage),
            'unit_cost': float(self.unit_cost.amount),
            'currency': self.unit_cost.currency,
            'total_cost': float(self.total_cost.amount),
            'production_date': self.production_date.isoformat() if self.production_date else None,
            'expiry_date': str(self.expiry_date) if self.expiry_date else None,
            'location': str(self.location) if self.location else None,
            'status': self.status.value,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by,
            'version': self.version
        }
    
    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def add_event(self, event: Any) -> None:
        """إضافة حدث"""
        self._events.append(event)
    
    def __repr__(self) -> str:
        return f"StockBatch(id={self.id}, batch={self.batch_number}, qty={self.current_quantity}/{self.initial_quantity}, status={self.status.value})"


# =============================================================================
# StockTransfer - تحويل المخزون
# =============================================================================

@dataclass
class StockTransfer:
    """
    تحويل مخزون - نقل بين مواقع التخزين
    
    يستخدم لنقل المنتجات من موقع إلى آخر (مستودع إلى مستودع، رف إلى رف، إلخ)
    
    Attributes:
        id: معرف فريد للتحويل
        entity: الكيان المرتبط (منتج)
        quantity: الكمية
        unit_cost: تكلفة الوحدة
        total_cost: التكلفة الإجمالية
        from_location: موقع المصدر
        to_location: موقع الهدف
        reference_type: نوع المرجع
        reference_id: معرف المرجع
        batch_number: رقم الدفعة (اختياري)
        serial_numbers: الأرقام التسلسلية (اختياري)
        status: حالة التحويل (pending, in_transit, completed, cancelled)
        notes: ملاحظات
        created_at: تاريخ الإنشاء
        created_by: من قام بالإنشاء
        completed_at: تاريخ الإكمال
        completed_by: من قام بالإكمال
        version: رقم الإصدار (للتحكم في التزامن)
    """
    
    id: StockTransferId = field(default_factory=StockTransferId.generate)
    entity: EntityId = field(default_factory=lambda: EntityId("product", ""))
    
    quantity: Decimal = Decimal('0')
    unit_cost: Money = field(default_factory=lambda: Money.zero())
    total_cost: Money = field(default_factory=lambda: Money.zero())
    
    from_location: StockLocation = field(default_factory=lambda: StockLocation(""))
    to_location: StockLocation = field(default_factory=lambda: StockLocation(""))
    
    reference_type: str = "StockTransfer"
    reference_id: str = ""
    
    batch_number: Optional[BatchNumber] = None
    serial_numbers: List[SerialNumber] = field(default_factory=list)
    
    status: str = "pending"  # pending, in_transit, completed, cancelled
    notes: str = ""
    
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    version: int = 1
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @property
    def is_pending(self) -> bool:
        """هل التحويل معلق؟"""
        return self.status == "pending"
    
    @property
    def is_in_transit(self) -> bool:
        """هل التحويل قيد النقل؟"""
        return self.status == "in_transit"
    
    @property
    def is_completed(self) -> bool:
        """هل التحويل مكتمل؟"""
        return self.status == "completed"
    
    @property
    def is_cancelled(self) -> bool:
        """هل التحويل ملغي؟"""
        return self.status == "cancelled"
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض للتحويل"""
        return f"Transfer {self.id} - {self.entity} ({self.quantity} units) from {self.from_location} to {self.to_location}"
    
    @classmethod
    def create(
        cls,
        entity: EntityId,
        quantity: Decimal,
        unit_cost: Money,
        from_location: StockLocation,
        to_location: StockLocation,
        reference_type: str = "StockTransfer",
        reference_id: str = "",
        batch_number: Optional[BatchNumber] = None,
        serial_numbers: Optional[List[SerialNumber]] = None,
        notes: str = "",
        created_by: str = "system"
    ) -> 'StockTransfer':
        """
        إنشاء تحويل مخزون جديد
        
        Args:
            entity: الكيان المرتبط
            quantity: الكمية
            unit_cost: تكلفة الوحدة
            from_location: موقع المصدر
            to_location: موقع الهدف
            reference_type: نوع المرجع
            reference_id: معرف المرجع
            batch_number: رقم الدفعة (اختياري)
            serial_numbers: الأرقام التسلسلية (اختياري)
            notes: ملاحظات
            created_by: من قام بالإنشاء
        
        Returns:
            StockTransfer: التحويل المنشأ
        """
        total_cost = Money(unit_cost.amount * quantity, unit_cost.currency)
        
        return cls(
            entity=entity,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            from_location=from_location,
            to_location=to_location,
            reference_type=reference_type,
            reference_id=reference_id,
            batch_number=batch_number,
            serial_numbers=serial_numbers or [],
            notes=notes,
            created_by=created_by,
            version=1
        )
    
    def start_transit(self, started_by: str) -> None:
        """بدء عملية النقل"""
        if not self.is_pending:
            raise ValueError(f"Cannot start transit for transfer in status: {self.status}")
        
        self.status = "in_transit"
        self.updated_at = utc_now()
        self.updated_by = started_by
        self.version += 1
    
    def complete(self, completed_by: str) -> None:
        """إكمال التحويل"""
        if self.is_completed:
            raise ValueError("Transfer already completed")
        
        if self.is_cancelled:
            raise ValueError("Transfer is cancelled")
        
        self.status = "completed"
        self.completed_at = utc_now()
        self.completed_by = completed_by
        self.version += 1
        
        from .events import StockTransferCompletedEvent
        self._events.append(StockTransferCompletedEvent(
            transfer_id=self.id,
            entity=self.entity,
            quantity=self.quantity,
            from_location=self.from_location,
            to_location=self.to_location,
            completed_by=completed_by
        ))
    
    def cancel(self, cancelled_by: str, reason: Optional[str] = None) -> None:
        """إلغاء التحويل"""
        if self.is_completed:
            raise ValueError("Cannot cancel completed transfer")
        
        if self.is_cancelled:
            raise ValueError("Transfer already cancelled")
        
        self.status = "cancelled"
        self.notes = f"{self.notes}\nCancelled by {cancelled_by}: {reason if reason else 'No reason provided'}"
        self.version += 1
        
        from .events import StockTransferCancelledEvent
        self._events.append(StockTransferCancelledEvent(
            transfer_id=self.id,
            entity=self.entity,
            cancelled_by=cancelled_by,
            reason=reason
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل التحويل إلى قاموس"""
        return {
            'id': str(self.id.value),
            'entity_type': self.entity.entity_type,
            'entity_id': self.entity.entity_id,
            'quantity': float(self.quantity),
            'unit_cost': float(self.unit_cost.amount),
            'currency': self.unit_cost.currency,
            'total_cost': float(self.total_cost.amount),
            'from_location': str(self.from_location),
            'to_location': str(self.to_location),
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'batch_number': str(self.batch_number) if self.batch_number else None,
            'serial_numbers': [str(s) for s in self.serial_numbers],
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'completed_by': self.completed_by,
            'version': self.version
        }
    
    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def add_event(self, event: Any) -> None:
        """إضافة حدث"""
        self._events.append(event)
    
    def __repr__(self) -> str:
        return f"StockTransfer(id={self.id}, status={self.status}, qty={self.quantity}, from={self.from_location}, to={self.to_location})"


# =============================================================================
# InventoryValuation - تقييم المخزون (للقراءة فقط)
# =============================================================================

@dataclass(frozen=True)
class InventoryValuation:
    """
    تقييم المخزون - نتيجة قراءة فقط
    
    يستخدم لتخزين نتائج تقييم المخزون دون تعديلها
    
    Attributes:
        entity: الكيان المرتبط
        as_of_date: تاريخ التقييم
        total_quantity: الكمية الإجمالية
        total_value: القيمة الإجمالية
        average_cost: متوسط التكلفة
        method: طريقة التقييم
        layers: طبقات المخزون (لـ FIFO/LIFO)
        cogs: تكلفة البضاعة المباعة (اختياري)
        currency: العملة
    """
    entity: EntityId
    as_of_date: date
    total_quantity: Decimal
    total_value: Money
    average_cost: Money
    method: CostFlowMethod
    layers: Optional[List[InventoryLayer]] = None
    cogs: Optional[Money] = None
    currency: str = "USD"
    
    @property
    def total_value_formatted(self) -> str:
        """القيمة الإجمالية منسقة"""
        return f"{self.total_value.amount:,.2f} {self.currency}"
    
    @property
    def average_cost_formatted(self) -> str:
        """متوسط التكلفة منسق"""
        return f"{self.average_cost.amount:,.2f} {self.currency}"
    
    @property
    def cogs_formatted(self) -> str:
        """COGS منسق"""
        if self.cogs is None:
            return "N/A"
        return f"{self.cogs.amount:,.2f} {self.currency}"
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل التقييم إلى قاموس"""
        return {
            'entity_type': self.entity.entity_type,
            'entity_id': self.entity.entity_id,
            'as_of_date': self.as_of_date.isoformat(),
            'total_quantity': float(self.total_quantity),
            'total_value': float(self.total_value.amount),
            'currency': self.currency,
            'average_cost': float(self.average_cost.amount),
            'method': self.method.value,
            'cogs': float(self.cogs.amount) if self.cogs else None,
            'layers': [
                {
                    'quantity': float(l.quantity),
                    'unit_cost': float(l.unit_cost),
                    'currency': l.currency,
                    'purchase_date': l.purchase_date.isoformat() if l.purchase_date else None,
                    'batch_number': l.batch_number
                }
                for l in (self.layers or [])
            ]
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "StockMovement",
    "StockBatch",
    "StockTransfer",
    "InventoryValuation",
]