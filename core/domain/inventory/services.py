# core/domain/inventory/services.py
"""
Inventory Services - خدمات المخزون المتقدمة
FIFO, LIFO, Weighted Average, Stock Valuation
"""

from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime
import logging

from .value_objects import (
    EntityId,
    StockLayer,
    StockValuation,
    CostFlowMethod,
    Money,
    BatchNumber,
    ExpiryDate,
    StockMovementType,
)
from .entities import StockMovement, StockBatch
from .interfaces import IStockMovementRepository

logger = logging.getLogger(__name__)


# =============================================================================
# FIFO Cost Calculator
# =============================================================================

class FIFOCostCalculator:
    """حاسبة التكلفة بطريقة FIFO (First-In, First-Out)"""
    
    @classmethod
    def calculate_cogs(
        cls,
        layers: List[StockLayer],
        quantity_to_consume: Decimal,
        currency: str = "USD"
    ) -> Tuple[Money, List[StockLayer]]:
        """حساب COGS باستخدام FIFO"""
        if quantity_to_consume <= 0:
            return Money.zero(currency), layers
        
        remaining_quantity = quantity_to_consume
        total_cost = Decimal('0')
        remaining_layers = []
        
        for layer in layers:
            if remaining_quantity <= 0:
                remaining_layers.append(layer)
                continue
            
            if layer.quantity <= remaining_quantity:
                total_cost += layer.unit_cost.amount * layer.quantity
                remaining_quantity -= layer.quantity
            else:
                consumed = remaining_quantity
                total_cost += layer.unit_cost.amount * consumed
                
                remaining_layer = StockLayer(
                    quantity=layer.quantity - consumed,
                    unit_cost=layer.unit_cost,
                    batch_number=layer.batch_number,
                    expiry_date=layer.expiry_date,
                    entry_date=layer.entry_date
                )
                remaining_layers.append(remaining_layer)
                remaining_quantity = 0
        
        if remaining_quantity > 0:
            raise ValueError(f"Insufficient stock: {remaining_quantity} units missing")
        
        return Money(total_cost, currency), remaining_layers
    
    @classmethod
    def calculate_average_cost(
        cls,
        layers: List[StockLayer],
        currency: str = "USD"
    ) -> Money:
        """حساب متوسط التكلفة"""
        total_quantity = sum(layer.quantity for layer in layers)
        if total_quantity == 0:
            return Money.zero(currency)
        
        total_cost = sum(layer.unit_cost.amount * layer.quantity for layer in layers)
        average = total_cost / total_quantity
        
        return Money(average, currency)


# =============================================================================
# LIFO Cost Calculator
# =============================================================================

class LIFOCostCalculator:
    """حاسبة التكلفة بطريقة LIFO (Last-In, First-Out)"""
    
    @classmethod
    def calculate_cogs(
        cls,
        layers: List[StockLayer],
        quantity_to_consume: Decimal,
        currency: str = "USD"
    ) -> Tuple[Money, List[StockLayer]]:
        """حساب COGS باستخدام LIFO"""
        reversed_layers = layers[::-1]
        
        total_cost = Decimal('0')
        remaining_quantity = quantity_to_consume
        remaining_reversed = []
        
        for layer in reversed_layers:
            if remaining_quantity <= 0:
                remaining_reversed.append(layer)
                continue
            
            if layer.quantity <= remaining_quantity:
                total_cost += layer.unit_cost.amount * layer.quantity
                remaining_quantity -= layer.quantity
            else:
                consumed = remaining_quantity
                total_cost += layer.unit_cost.amount * consumed
                
                remaining_layer = StockLayer(
                    quantity=layer.quantity - consumed,
                    unit_cost=layer.unit_cost,
                    batch_number=layer.batch_number,
                    expiry_date=layer.expiry_date,
                    entry_date=layer.entry_date
                )
                remaining_reversed.append(remaining_layer)
                remaining_quantity = 0
        
        if remaining_quantity > 0:
            raise ValueError(f"Insufficient stock: {remaining_quantity} units missing")
        
        # إعادة الترتيب
        remaining_layers = remaining_reversed[::-1]
        
        return Money(total_cost, currency), remaining_layers


# =============================================================================
# Weighted Average Calculator
# =============================================================================

class WeightedAverageCalculator:
    """حاسبة التكلفة بالمتوسط المرجح"""
    
    @classmethod
    def calculate_average_cost(
        cls,
        current_quantity: Decimal,
        current_average_cost: Money,
        new_quantity: Decimal,
        new_unit_cost: Money
    ) -> Money:
        """حساب متوسط التكلفة الجديد"""
        if current_quantity == 0 and new_quantity == 0:
            return Money.zero(current_average_cost.currency)
        
        if current_quantity == 0:
            return new_unit_cost
        
        if new_quantity == 0:
            return current_average_cost
        
        total_quantity = current_quantity + new_quantity
        total_cost = (current_average_cost.amount * current_quantity) + \
                     (new_unit_cost.amount * new_quantity)
        
        new_average = total_cost / total_quantity
        return Money(new_average, current_average_cost.currency)


# =============================================================================
# StockMovementService - خدمة حركات المخزون
# =============================================================================

class StockMovementService:
    """
    خدمة حركات المخزون - تدير إنشاء وتتبع حركات المخزون
    
    الميزات:
        1. إنشاء حركات واردة وصادرة
        2. التحقق من كفاية المخزون
        3. حساب الرصيد الحالي
        4. دعم الدفعات والأرقام التسلسلية
    """
    
    def __init__(self, repository: IStockMovementRepository):
        self._repo = repository
    
    def create_inbound_movement(
        self,
        entity: EntityId,
        quantity: Decimal,
        unit_cost: Money,
        movement_type: StockMovementType,
        reference_type: str,
        reference_id: str,
        batch_number: Optional[BatchNumber] = None,
        serial_numbers: Optional[List[str]] = None,
        expiry_date: Optional[ExpiryDate] = None,
        location: Optional[str] = None,
        notes: str = "",
        created_by: str = "system"
    ) -> StockMovement:
        """
        إنشاء حركة واردة (تزيد المخزون)
        
        Raises:
            ValueError: إذا كان نوع الحركة ليس وارداً
        """
        if not movement_type.is_inbound:
            raise ValueError(f"{movement_type.value} is not an inbound movement")
        
        from .entities import StockMovement
        from .value_objects import StockLocation, SerialNumber
        
        movement = StockMovement.create_inbound(
            entity=entity,
            quantity=quantity,
            unit_cost=unit_cost,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            batch_number=batch_number,
            serial_numbers=[SerialNumber(s) for s in (serial_numbers or [])],
            expiry_date=expiry_date,
            location=StockLocation.from_string(location) if location else None,
            notes=notes,
            created_by=created_by
        )
        
        self._repo.save(movement)
        logger.info(f"Inbound movement created: {movement.id} for {entity}")
        
        return movement
    
    def create_outbound_movement(
        self,
        entity: EntityId,
        quantity: Decimal,
        unit_cost: Money,
        movement_type: StockMovementType,
        reference_type: str,
        reference_id: str,
        batch_number: Optional[BatchNumber] = None,
        serial_numbers: Optional[List[str]] = None,
        location: Optional[str] = None,
        notes: str = "",
        created_by: str = "system"
    ) -> StockMovement:
        """
        إنشاء حركة صادرة (تنقص المخزون)
        
        Raises:
            ValueError: إذا كان نوع الحركة ليس صادراً
            ValueError: إذا كانت الكمية غير كافية
        """
        if not movement_type.is_outbound:
            raise ValueError(f"{movement_type.value} is not an outbound movement")
        
        # التحقق من كفاية المخزون
        current_quantity = self._repo.get_current_quantity(entity)
        if current_quantity < quantity:
            raise ValueError(
                f"Insufficient stock: {current_quantity} < {quantity} for {entity}"
            )
        
        from .entities import StockMovement
        from .value_objects import StockLocation, SerialNumber
        
        movement = StockMovement.create_outbound(
            entity=entity,
            quantity=quantity,
            unit_cost=unit_cost,
            movement_type=movement_type,
            reference_type=reference_type,
            reference_id=reference_id,
            batch_number=batch_number,
            serial_numbers=[SerialNumber(s) for s in (serial_numbers or [])],
            location=StockLocation.from_string(location) if location else None,
            notes=notes,
            created_by=created_by
        )
        
        self._repo.save(movement)
        logger.info(f"Outbound movement created: {movement.id} for {entity}")
        
        return movement
    
    def get_current_quantity(self, entity: EntityId) -> Decimal:
        """الحصول على الكمية الحالية لكيان"""
        return self._repo.get_current_quantity(entity)
    
    def get_quantity_at_date(self, entity: EntityId, as_of_date: date) -> Decimal:
        """الحصول على الكمية في تاريخ معين"""
        return self._repo.get_quantity_at_date(entity, as_of_date)
    
    def get_movements(
        self,
        entity: EntityId,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        movement_type: Optional[StockMovementType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockMovement]:
        """الحصول على حركات كيان معين"""
        if from_date and to_date:
            return self._repo.get_by_date_range(
                entity, from_date, to_date, movement_type, limit, offset
            )
        return self._repo.get_by_entity(entity, limit, offset)


# =============================================================================
# InventoryValuationService - خدمة تقييم المخزون
# =============================================================================

class InventoryValuationService:
    """
    خدمة تقييم المخزون - حساب قيمة المخزون الحالية
    
    الميزات:
        1. حساب قيمة المخزون باستخدام طرق مختلفة (FIFO, LIFO, Weighted Average)
        2. حساب تكلفة البضاعة المباعة (COGS)
        3. تقارير تقييم المخزون
    """
    
    def __init__(self, movement_repo: IStockMovementRepository):
        self._movement_repo = movement_repo
    
    def calculate_valuation(
        self,
        entity: EntityId,
        as_of_date: date,
        method: CostFlowMethod = CostFlowMethod.FIFO
    ) -> StockValuation:
        """
        حساب قيمة المخزون في تاريخ معين
        
        Args:
            entity: الكيان (منتج، مادة خام، إلخ)
            as_of_date: تاريخ التقييم
            method: طريقة التقييم
        
        Returns:
            StockValuation: نتيجة التقييم
        """
        # جلب جميع الحركات حتى التاريخ المطلوب
        movements = self._movement_repo.get_by_date_range(
            entity=entity,
            from_date=datetime.min,
            to_date=datetime.combine(as_of_date, datetime.max.time()),
            limit=10000  # حد كبير
        )
        
        # بناء طبقات المخزون
        layers = self._build_layers(movements)
        
        # حساب التكلفة الإجمالية
        total_quantity = sum(layer.quantity for layer in layers)
        total_cost = sum(layer.unit_cost.amount * layer.quantity for layer in layers)
        average_cost = total_cost / total_quantity if total_quantity > 0 else Decimal('0')
        
        currency = layers[0].unit_cost.currency if layers else "USD"
        
        return StockValuation(
            total_quantity=total_quantity,
            total_cost=Money(total_cost, currency),
            average_cost=Money(average_cost, currency),
            valuation_method=method,
            as_of_date=as_of_date,
            currency=currency
        )
    
    def _build_layers(self, movements: List[StockMovement]) -> List[StockLayer]:
        """بناء طبقات المخزون من الحركات"""
        layers = []
        
        # ترتيب زمني تصاعدي (FIFO يتطلب الوارد قبل الصادر)
        ordered = sorted(movements, key=lambda m: m.movement_date or datetime.min)
        
        for movement in ordered:
            if movement.is_inbound:
                # حركة واردة = إضافة طبقة جديدة
                layers.append(StockLayer(
                    quantity=movement.quantity,
                    unit_cost=movement.unit_cost,
                    batch_number=movement.batch_number,
                    expiry_date=movement.expiry_date,
                    entry_date=movement.movement_date
                ))
            else:
                # حركة صادرة = استهلاك من الطبقات
                consumed_quantity = abs(movement.quantity)
                _, layers = FIFOCostCalculator.calculate_cogs(
                    layers,
                    consumed_quantity,
                    movement.unit_cost.currency
                )
        
        return layers
    
    def calculate_cogs(
        self,
        entity: EntityId,
        from_date: date,
        to_date: date,
        method: CostFlowMethod = CostFlowMethod.FIFO
    ) -> Money:
        """
        حساب تكلفة البضاعة المباعة (COGS) في فترة
        
        Args:
            entity: الكيان
            from_date: بداية الفترة
            to_date: نهاية الفترة
            method: طريقة التقييم
        
        Returns:
            Money: إجمالي COGS
        """
        # جلب جميع الحركات الصادرة في الفترة
        movements = self._movement_repo.get_by_date_range(
            entity=entity,
            from_date=datetime.combine(from_date, datetime.min.time()),
            to_date=datetime.combine(to_date, datetime.max.time()),
            movement_type=StockMovementType.SALE,
            limit=10000
        )
        
        total_cogs = Decimal('0')
        currency = "USD"
        
        for movement in movements:
            total_cogs += movement.unit_cost.amount * abs(movement.quantity)
            currency = movement.unit_cost.currency
        
        return Money(total_cogs, currency)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "FIFOCostCalculator",
    "LIFOCostCalculator",
    "WeightedAverageCalculator",
    "StockMovementService",
    "InventoryValuationService",
]