# core/domain/inventory/valuation_service.py
"""
Inventory Valuation Service - خدمة تقييم المخزون المتقدمة
الإصدار: 2.0.0

الميزات:
    1. دعم FIFO، LIFO، Weighted Average
    2. حساب COGS التلقائي
    3. تقييم المخزون في أي تاريخ
    4. دعم الدفعات (Batches)
    5. دمج مع المحاسبة
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging

from .value_objects import (
    InventoryLayer,
    InventoryValuationResult,
    CostFlowMethod
)
from .entities import StockMovement, StockBatch
from .interfaces import IStockMovementRepository, IStockBatchRepository
from core.domain.shared.value_objects import Money, EntityId

logger = logging.getLogger(__name__)


class InventoryValuationService:
    """
    خدمة تقييم المخزون المتقدمة
    
    تدعم ثلاث طرق للتقييم:
        1. FIFO (First-In, First-Out)
        2. LIFO (Last-In, First-Out)
        3. Weighted Average (المتوسط المرجح)
    """
    
    def __init__(
        self,
        movement_repo: IStockMovementRepository,
        batch_repo: Optional[IStockBatchRepository] = None
    ):
        self._movement_repo = movement_repo
        self._batch_repo = batch_repo
    
    # =========================================================================
    # حساب قيمة المخزون
    # =========================================================================
    
    def calculate_valuation(
        self,
        entity: EntityId,
        as_of_date: date,
        method: CostFlowMethod = CostFlowMethod.FIFO,
        include_cogs: bool = False
    ) -> InventoryValuationResult:
        """
        حساب قيمة المخزون في تاريخ معين
        
        Args:
            entity: الكيان (منتج، مادة خام، إلخ)
            as_of_date: تاريخ التقييم
            method: طريقة التقييم
            include_cogs: حساب COGS للفترة
        
        Returns:
            InventoryValuationResult: نتيجة التقييم
        """
        logger.info(f"Calculating valuation for {entity} as of {as_of_date} using {method.value}")
        
        # 1. جلب جميع الحركات حتى التاريخ المطلوب
        movements = self._get_movements_until_date(entity, as_of_date)
        
        # 2. بناء طبقات المخزون
        layers = self._build_layers(movements, as_of_date)
        
        # 3. حساب التقييم حسب الطريقة المطلوبة
        if method == CostFlowMethod.FIFO:
            return self._calculate_fifo(layers, as_of_date, include_cogs)
        elif method == CostFlowMethod.LIFO:
            return self._calculate_lifo(layers, as_of_date, include_cogs)
        elif method == CostFlowMethod.WEIGHTED_AVERAGE:
            return self._calculate_weighted_average(layers, as_of_date, include_cogs)
        else:
            raise ValueError(f"Unsupported valuation method: {method}")
    
    def _get_movements_until_date(
        self,
        entity: EntityId,
        as_of_date: date
    ) -> List[StockMovement]:
        """جلب جميع الحركات حتى تاريخ معين"""
        return self._movement_repo.get_by_date_range(
            entity=entity,
            from_date=datetime.min,
            to_date=datetime.combine(as_of_date, datetime.max.time()),
            limit=10000
        )
    
    def _build_layers(
        self,
        movements: List[StockMovement],
        as_of_date: date
    ) -> List[InventoryLayer]:
        """
        بناء طبقات المخزون من الحركات
        
        كل طبقة تمثل كمية مشتراة بنفس التكلفة
        """
        layers = []
        
        # ترتيب زمني تصاعدي (FIFO يتطلب الوارد قبل الصادر)
        ordered = sorted(movements, key=lambda m: m.movement_date or datetime.min)
        
        for movement in ordered:
            if movement.is_inbound:
                # حركة واردة = إضافة طبقة جديدة
                layers.append(InventoryLayer(
                    quantity=movement.quantity,
                    unit_cost=movement.unit_cost.amount,
                    currency=movement.unit_cost.currency,
                    purchase_date=movement.movement_date.date() if movement.movement_date else None,
                    batch_number=str(movement.batch_number) if movement.batch_number else None
                ))
            else:
                # حركة صادرة = استهلاك من الطبقات
                quantity_to_consume = abs(movement.quantity)
                layers = self._consume_layers(layers, quantity_to_consume)
        
        return layers
    
    def _consume_layers(
        self,
        layers: List[InventoryLayer],
        quantity: Decimal
    ) -> List[InventoryLayer]:
        """
        استهلاك كمية من الطبقات (FIFO)
        
        تستهلك من أقدم الطبقات أولاً
        """
        if quantity <= 0:
            return layers
        
        remaining = quantity
        remaining_layers = []
        
        for layer in layers:
            if remaining <= 0:
                remaining_layers.append(layer)
                continue
            
            if layer.quantity <= remaining:
                # استهلاك الطبقة بالكامل
                remaining -= layer.quantity
            else:
                # استهلاك جزء من الطبقة
                remaining_layer = InventoryLayer(
                    quantity=layer.quantity - remaining,
                    unit_cost=layer.unit_cost,
                    currency=layer.currency,
                    purchase_date=layer.purchase_date,
                    batch_number=layer.batch_number
                )
                remaining_layers.append(remaining_layer)
                remaining = 0
        
        if remaining > 0:
            # لا يوجد مخزون كافٍ
            logger.warning(f"Insufficient stock: {remaining} units missing")
        
        return remaining_layers
    
    # =========================================================================
    # FIFO - First In, First Out
    # =========================================================================
    
    def _calculate_fifo(
        self,
        layers: List[InventoryLayer],
        as_of_date: date,
        include_cogs: bool
    ) -> InventoryValuationResult:
        """
        حساب قيمة المخزون باستخدام FIFO
        
        المبدأ: أقدم الوحدات تباع أولاً
        """
        total_quantity = Decimal('0')
        total_value = Decimal('0')
        currency = "USD"
        
        for layer in layers:
            total_quantity += layer.quantity
            total_value += layer.quantity * layer.unit_cost
            currency = layer.currency
        
        average_cost = total_value / total_quantity if total_quantity > 0 else Decimal('0')
        
        cogs = None
        if include_cogs:
            cogs = self._calculate_cogs_fifo(layers)
        
        return InventoryValuationResult(
            total_quantity=total_quantity,
            total_value=total_value,
            average_cost=average_cost,
            currency=currency,
            valuation_method=CostFlowMethod.FIFO,
            as_of_date=as_of_date,
            layers=layers,
            cogs=cogs
        )
    
    def _calculate_cogs_fifo(self, layers: List[InventoryLayer]) -> Decimal:
        """حساب COGS باستخدام FIFO"""
        # في نظام حقيقي، COGS = مجموع تكاليف الوحدات المباعة
        # هنا نحسبها كمتوسط بسيط للتوضيح
        total_cost = sum(l.quantity * l.unit_cost for l in layers)
        return total_cost
    
    # =========================================================================
    # LIFO - Last In, First Out
    # =========================================================================
    
    def _calculate_lifo(
        self,
        layers: List[InventoryLayer],
        as_of_date: date,
        include_cogs: bool
    ) -> InventoryValuationResult:
        """
        حساب قيمة المخزون باستخدام LIFO
        
        المبدأ: أحدث الوحدات تباع أولاً
        """
        # عكس ترتيب الطبقات (الأحدث أولاً)
        reversed_layers = layers[::-1]
        
        total_quantity = Decimal('0')
        total_value = Decimal('0')
        currency = "USD"
        
        for layer in reversed_layers:
            total_quantity += layer.quantity
            total_value += layer.quantity * layer.unit_cost
            currency = layer.currency
        
        average_cost = total_value / total_quantity if total_quantity > 0 else Decimal('0')
        
        cogs = None
        if include_cogs:
            cogs = self._calculate_cogs_lifo(layers)
        
        return InventoryValuationResult(
            total_quantity=total_quantity,
            total_value=total_value,
            average_cost=average_cost,
            currency=currency,
            valuation_method=CostFlowMethod.LIFO,
            as_of_date=as_of_date,
            layers=layers,
            cogs=cogs
        )
    
    def _calculate_cogs_lifo(self, layers: List[InventoryLayer]) -> Decimal:
        """حساب COGS باستخدام LIFO"""
        # حساب تكلفة أحدث الطبقات
        total_cost = Decimal('0')
        for layer in layers[::-1]:  # من الأحدث للأقدم
            total_cost += layer.quantity * layer.unit_cost
        return total_cost
    
    # =========================================================================
    # Weighted Average - المتوسط المرجح
    # =========================================================================
    
    def _calculate_weighted_average(
        self,
        layers: List[InventoryLayer],
        as_of_date: date,
        include_cogs: bool
    ) -> InventoryValuationResult:
        """
        حساب قيمة المخزون باستخدام المتوسط المرجح
        
        المبدأ: حساب متوسط التكلفة لجميع الوحدات المتاحة
        """
        total_quantity = Decimal('0')
        total_value = Decimal('0')
        currency = "USD"
        
        for layer in layers:
            total_quantity += layer.quantity
            total_value += layer.quantity * layer.unit_cost
            currency = layer.currency
        
        average_cost = total_value / total_quantity if total_quantity > 0 else Decimal('0')
        
        cogs = None
        if include_cogs:
            cogs = self._calculate_cogs_weighted_average(layers, average_cost)
        
        return InventoryValuationResult(
            total_quantity=total_quantity,
            total_value=total_value,
            average_cost=average_cost,
            currency=currency,
            valuation_method=CostFlowMethod.WEIGHTED_AVERAGE,
            as_of_date=as_of_date,
            layers=layers,
            cogs=cogs
        )
    
    def _calculate_cogs_weighted_average(
        self,
        layers: List[InventoryLayer],
        average_cost: Decimal
    ) -> Decimal:
        """حساب COGS باستخدام المتوسط المرجح"""
        total_cost = sum(l.quantity * l.unit_cost for l in layers)
        return total_cost
    
    # =========================================================================
    # حساب COGS (تكلفة البضاعة المباعة)
    # =========================================================================
    
    def calculate_cogs(
        self,
        entity: EntityId,
        from_date: date,
        to_date: date,
        method: CostFlowMethod = CostFlowMethod.FIFO
    ) -> Decimal:
        """
        حساب تكلفة البضاعة المباعة (COGS) في فترة معينة
        
        Args:
            entity: الكيان
            from_date: بداية الفترة
            to_date: نهاية الفترة
            method: طريقة التقييم
        
        Returns:
            Decimal: إجمالي COGS
        """
        logger.info(f"Calculating COGS for {entity} from {from_date} to {to_date} using {method.value}")
        
        # 1. جلب الحركات الصادرة في الفترة
        movements = self._movement_repo.get_by_date_range(
            entity=entity,
            from_date=datetime.combine(from_date, datetime.min.time()),
            to_date=datetime.combine(to_date, datetime.max.time()),
            limit=10000
        )
        
        # 2. تصفية الحركات الصادرة فقط
        outbound_movements = [m for m in movements if m.is_outbound]
        
        # 3. حساب COGS حسب الطريقة
        if method == CostFlowMethod.FIFO:
            return self._calculate_cogs_fifo_from_movements(outbound_movements)
        elif method == CostFlowMethod.LIFO:
            return self._calculate_cogs_lifo_from_movements(outbound_movements)
        elif method == CostFlowMethod.WEIGHTED_AVERAGE:
            return self._calculate_cogs_weighted_from_movements(outbound_movements)
        else:
            raise ValueError(f"Unsupported method for COGS: {method}")
    
    def _calculate_cogs_fifo_from_movements(
        self,
        movements: List[StockMovement]
    ) -> Decimal:
        """حساب COGS من الحركات باستخدام FIFO"""
        total_cogs = Decimal('0')
        
        for movement in movements:
            total_cogs += movement.unit_cost.amount * abs(movement.quantity)
        
        return total_cogs
    
    def _calculate_cogs_lifo_from_movements(
        self,
        movements: List[StockMovement]
    ) -> Decimal:
        """حساب COGS من الحركات باستخدام LIFO"""
        # استخدام أحدث التكاليف (عكس الترتيب)
        sorted_movements = sorted(movements, key=lambda m: m.movement_date, reverse=True)
        
        total_cogs = Decimal('0')
        for movement in sorted_movements:
            total_cogs += movement.unit_cost.amount * abs(movement.quantity)
        
        return total_cogs
    
    def _calculate_cogs_weighted_from_movements(
        self,
        movements: List[StockMovement]
    ) -> Decimal:
        """حساب COGS من الحركات باستخدام المتوسط المرجح"""
        if not movements:
            return Decimal('0')
        
        total_cost = Decimal('0')
        total_quantity = Decimal('0')
        
        for movement in movements:
            total_cost += movement.unit_cost.amount * abs(movement.quantity)
            total_quantity += abs(movement.quantity)
        
        weighted_avg = total_cost / total_quantity if total_quantity > 0 else Decimal('0')
        
        # COGS = الوزن × متوسط التكلفة
        total_cogs = total_quantity * weighted_avg
        
        return total_cogs
    
    # =========================================================================
    # تقييم المخزون حسب الموقع
    # =========================================================================
    
    def calculate_valuation_by_location(
        self,
        entity: EntityId,
        location: str,
        as_of_date: date,
        method: CostFlowMethod = CostFlowMethod.FIFO
    ) -> InventoryValuationResult:
        """
        حساب قيمة المخزون في موقع معين
        
        Args:
            entity: الكيان
            location: الموقع (مستودع، رف، إلخ)
            as_of_date: تاريخ التقييم
            method: طريقة التقييم
        
        Returns:
            InventoryValuationResult: نتيجة التقييم للموقع
        """
        # جلب الحركات للموقع المحدد
        movements = self._movement_repo.get_by_location(
            location=location,
            from_date=datetime.min,
            to_date=datetime.combine(as_of_date, datetime.max.time()),
            limit=10000
        )
        
        # تصفية حركات الكيان المحدد
        entity_movements = [m for m in movements if m.entity == entity]
        
        # بناء الطبقات من الحركات
        layers = self._build_layers(entity_movements, as_of_date)
        
        # حساب التقييم
        if method == CostFlowMethod.FIFO:
            return self._calculate_fifo(layers, as_of_date, False)
        elif method == CostFlowMethod.LIFO:
            return self._calculate_lifo(layers, as_of_date, False)
        else:
            return self._calculate_weighted_average(layers, as_of_date, False)
    
    # =========================================================================
    # مقارنة طرق التقييم
    # =========================================================================
    
    def compare_valuation_methods(
        self,
        entity: EntityId,
        as_of_date: date
    ) -> Dict[str, Any]:
        """
        مقارنة نتائج طرق التقييم المختلفة
        
        Returns:
            قاموس يحتوي على نتائج الطرق الثلاث
        """
        results = {}
        
        for method in CostFlowMethod:
            if method == CostFlowMethod.SPECIFIC_ID:
                continue
            
            result = self.calculate_valuation(
                entity=entity,
                as_of_date=as_of_date,
                method=method
            )
            
            results[method.value] = {
                'total_value': float(result.total_value),
                'average_cost': float(result.average_cost),
                'total_quantity': float(result.total_quantity)
            }
        
        return {
            'entity_id': str(entity.value),
            'as_of_date': as_of_date.isoformat(),
            'results': results,
            'differences': {
                'fifo_lifo': float(
                    results['fifo']['total_value'] - results['lifo']['total_value']
                ),
                'fifo_avg': float(
                    results['fifo']['total_value'] - results['weighted_average']['total_value']
                ),
                'lifo_avg': float(
                    results['lifo']['total_value'] - results['weighted_average']['total_value']
                )
            }
        }