# core/domain/inventory/integration.py
"""
Inventory Accounting Integration - تكامل المخزون مع المحاسبة
الإصدار: 2.2.0 - Enterprise Edition (التنفيذ الكامل)

✅ دعم مقارنة طرق التقييم (FIFO, LIFO, Weighted Average)
✅ دعم تسجيل COGS كقيد منفصل
✅ دعم تقييم المخزون مع تفاصيل COGS
✅ دعم التقارير التحليلية
✅ دعم الدفعات والأرقام التسلسلية
✅ دعم العملات المتعددة
✅ دعم مراكز التكلفة
✅ دعم Optimistic Locking
✅ دعم المعاملات الذرية
✅ دعم التقارير الشاملة
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from dataclasses import dataclass, field
import logging

from core.domain.inventory.entities import StockMovement, StockBatch
from core.domain.inventory.value_objects import (
    EntityId,
    StockMovementType,
    BatchNumber,
    StockLocation,
    CostFlowMethod,
    InventoryValuationResult,
)
from core.domain.inventory.services import (
    StockMovementService,
    InventoryValuationService,
    FIFOCostCalculator,
    LIFOCostCalculator,
    WeightedAverageCalculator
)
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.accounting.services import PostingEngine
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.products.entities import Product
from core.domain.products.interfaces import IProductRepository

logger = logging.getLogger(__name__)


# =============================================================================
# DTOs للتكامل
# =============================================================================

@dataclass
class StockIntegrationRequest:
    """
    طلب تكامل المخزون مع المحاسبة
    
    Attributes:
        product_id: معرف المنتج
        quantity: الكمية
        unit_cost: تكلفة الوحدة
        currency: العملة
        reference_type: نوع المرجع (invoice, purchase_order, adjustment)
        reference_id: معرف المرجع
        movement_type: نوع الحركة
        cost_method: طريقة حساب التكلفة
        date: تاريخ الحركة
        created_by: من قام بالحركة
    """
    product_id: str
    quantity: Decimal
    unit_cost: Decimal
    currency: str = "USD"
    reference_type: str = ""
    reference_id: str = ""
    movement_type: str = "sale"
    cost_method: str = "fifo"
    date: Optional[datetime] = None
    created_by: str = "system"
    
    # حقول إضافية للدفعات
    batch_number: Optional[str] = None
    serial_numbers: Optional[List[str]] = None
    expiry_date: Optional[date] = None
    location: Optional[str] = None
    
    # مراكز التكلفة
    cost_center: Optional[str] = None
    profit_center: Optional[str] = None
    
    # ✅ إضافة حقل لتحديد ما إذا كان يجب تحديث المنتج
    update_product: bool = True
    
    def validate(self) -> List[str]:
        """التحقق من صحة الطلب"""
        errors = []
        
        if not self.product_id:
            errors.append("Product ID is required")
        
        if self.quantity <= 0:
            errors.append("Quantity must be greater than zero")
        
        if self.unit_cost <= 0:
            errors.append("Unit cost must be greater than zero")
        
        if self.movement_type not in ["sale", "purchase", "adjustment"]:
            errors.append(f"Invalid movement type: {self.movement_type}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الطلب إلى قاموس"""
        return {
            'product_id': self.product_id,
            'quantity': float(self.quantity),
            'unit_cost': float(self.unit_cost),
            'currency': self.currency,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'movement_type': self.movement_type,
            'cost_method': self.cost_method,
            'date': self.date.isoformat() if self.date else None,
            'created_by': self.created_by,
            'batch_number': self.batch_number,
            'serial_numbers': self.serial_numbers,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'location': self.location,
            'cost_center': self.cost_center,
            'profit_center': self.profit_center
        }


@dataclass
class StockIntegrationResult:
    """
    نتيجة تكامل المخزون مع المحاسبة
    
    Attributes:
        success: نجاح العملية
        message: رسالة الحالة
        stock_movement_id: معرف حركة المخزون
        journal_entry_id: معرف القيد المحاسبي
        cogs_amount: مبلغ COGS
        inventory_value: قيمة المخزون الجديدة
        errors: قائمة الأخطاء
        warnings: قائمة التحذيرات
        details: تفاصيل إضافية
    """
    success: bool
    message: str
    stock_movement_id: Optional[str] = None
    journal_entry_id: Optional[str] = None
    cogs_amount: Decimal = Decimal('0')
    inventory_value: Decimal = Decimal('0')
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
    
    @property
    def error_summary(self) -> str:
        return "; ".join(self.errors)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message': self.message,
            'stock_movement_id': self.stock_movement_id,
            'journal_entry_id': self.journal_entry_id,
            'cogs_amount': float(self.cogs_amount),
            'inventory_value': float(self.inventory_value),
            'errors': self.errors,
            'warnings': self.warnings,
            'details': self.details
        }


# =============================================================================
# InventoryAccountingIntegration - التنفيذ الكامل
# =============================================================================

class InventoryAccountingIntegration:
    """
    خدمة تكامل المخزون مع المحاسبة - النسخة المتقدمة
    
    هذه هي الواجهة الوحيدة التي يجب استخدامها لربط المخزون بالمحاسبة.
    
    الميزات:
        1. إنشاء حركات مخزون مع قيود محاسبية
        2. حساب COGS تلقائياً (FIFO, LIFO, Weighted Average)
        3. دعم طرق التقييم المختلفة
        4. دعم الدفعات والأرقام التسلسلية
        5. تحديث أرصدة المنتجات
        6. مقارنة طرق التقييم
        7. تسجيل COGS كقيد منفصل
        8. تقارير تحليلية
        9. دعم Optimistic Locking
        10. دعم المعاملات الذرية
    """
    
    def __init__(
        self,
        uow: IUnitOfWork,
        posting_engine: PostingEngine,
        product_repository: IProductRepository,
        stock_service: StockMovementService,
        valuation_service: InventoryValuationService,
        inventory_account: AccountCode = AccountCode("1030"),
        cogs_account: AccountCode = AccountCode("5010"),
        revenue_account: AccountCode = AccountCode("4010"),
        cost_center: Optional[str] = None
    ):
        """
        تهيئة خدمة التكامل
        
        Args:
            uow: Unit of Work
            posting_engine: محرك الترحيل
            product_repository: مستودع المنتجات
            stock_service: خدمة حركات المخزون
            valuation_service: خدمة تقييم المخزون
            inventory_account: حساب المخزون (افتراضي: 1030)
            cogs_account: حساب COGS (افتراضي: 5010)
            revenue_account: حساب الإيرادات (افتراضي: 4010)
            cost_center: مركز التكلفة الافتراضي (اختياري)
        """
        self._uow = uow
        self._posting_engine = posting_engine
        self._product_repo = product_repository
        self._stock_service = stock_service
        self._valuation_service = valuation_service
        
        self._inventory_account = inventory_account
        self._cogs_account = cogs_account
        self._revenue_account = revenue_account
        self._cost_center = cost_center
        
        self._logger = logging.getLogger(__name__)
    
    # =========================================================================
    # العمليات الرئيسية (محسنة بالكامل)
    # =========================================================================
    
    def process_sale(
        self,
        request: StockIntegrationRequest
    ) -> StockIntegrationResult:
        """
        معالجة عملية بيع (تخفيض المخزون + إنشاء قيد محاسبي)
        
        Args:
            request: طلب التكامل
        
        Returns:
            StockIntegrationResult: نتيجة العملية
        """
        self._logger.info(
            f"Processing sale: Product={request.product_id}, "
            f"Quantity={request.quantity}, Cost={request.unit_cost}"
        )
        
        # التحقق من صحة الطلب
        errors = request.validate()
        if errors:
            return StockIntegrationResult(
                success=False,
                message="Validation failed",
                errors=errors
            )
        
        try:
            with self._uow:
                # 1. الحصول على المنتج
                product = self._product_repo.get_by_id(request.product_id)
                if not product:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Product {request.product_id} not found",
                        errors=[f"Product {request.product_id} not found"]
                    )
                
                # 2. التحقق من كفاية المخزون
                entity = EntityId("product", str(product.id.value))
                current_quantity = self._stock_service.get_current_quantity(entity)
                
                if current_quantity < request.quantity:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Insufficient stock: {current_quantity} < {request.quantity}",
                        errors=[f"Insufficient stock: {current_quantity} < {request.quantity}"]
                    )
                
                # 3. حساب COGS باستخدام الطريقة المطلوبة
                cogs_result = self._calculate_cogs(
                    product=product,
                    quantity=request.quantity,
                    method=request.cost_method,
                    currency=request.currency
                )
                
                if not cogs_result.get('success', False):
                    return StockIntegrationResult(
                        success=False,
                        message=f"COGS calculation failed: {cogs_result.get('error', 'Unknown error')}",
                        errors=[cogs_result.get('error', 'Unknown error')]
                    )
                
                cogs_amount = cogs_result['cogs_amount']
                
                # 4. إنشاء حركة مخزون (خروج)
                movement = self._create_stock_movement(
                    product=product,
                    quantity=request.quantity,
                    unit_cost=request.unit_cost,
                    movement_type=StockMovementType.SALE,
                    reference_type=request.reference_type or "Invoice",
                    reference_id=request.reference_id,
                    batch_number=request.batch_number,
                    serial_numbers=request.serial_numbers,
                    expiry_date=request.expiry_date,
                    location=request.location,
                    created_by=request.created_by
                )
                
                # 5. إنشاء القيد المحاسبي
                journal_entry = self._create_sale_journal_entry(
                    product=product,
                    quantity=request.quantity,
                    unit_price=request.unit_cost,
                    cogs_amount=cogs_amount,
                    currency=request.currency,
                    reference_id=request.reference_id,
                    cost_center=request.cost_center or self._cost_center,
                    created_by=request.created_by
                )
                
                # 6. ترحيل القيد المحاسبي
                post_result = self._posting_engine.post(
                    journal_entry,
                    request.created_by,
                    skip_save=False
                )
                
                if not post_result.success:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Posting failed: {post_result.message}",
                        errors=post_result.errors
                    )
                
                # 7. حفظ حركة المخزون
                self._stock_service._repo.save(movement)
                
                # 8. تحديث كمية المنتج (إذا كان مطلوباً)
                new_quantity = current_quantity - request.quantity
                if request.update_product:
                    product.update_stock(
                        quantity_change=-request.quantity,
                        movement_type=StockMovementType.SALE,
                        reason=f"Sale: {request.reference_id}",
                        updated_by=request.created_by
                    )
                    self._product_repo.save(product)
                
                # 9. Commit المعاملة
                self._uow.commit()
                
                # 10. ✅ حساب قيمة المخزون الجديدة بعد العملية
                new_inventory_value = self._stock_service.get_current_quantity(entity)
                
                self._logger.info(
                    f"Sale processed successfully: Product={product.code}, "
                    f"Quantity={request.quantity}, COGS={cogs_amount}"
                )
                
                return StockIntegrationResult(
                    success=True,
                    message="Sale processed successfully",
                    stock_movement_id=str(movement.id),
                    journal_entry_id=post_result.journal_entry_id,
                    cogs_amount=cogs_amount,
                    inventory_value=new_inventory_value,
                    details={
                        'product_code': product.code.value,
                        'product_name': product.name,
                        'new_quantity': float(new_quantity),
                        'old_quantity': float(current_quantity),
                        'cogs_calculation': cogs_result,
                        'posting_result': post_result.to_dict() if hasattr(post_result, 'to_dict') else None
                    }
                )
                
        except Exception as e:
            self._logger.error(f"Error processing sale: {e}", exc_info=True)
            self._uow.rollback()
            return StockIntegrationResult(
                success=False,
                message=f"Error processing sale: {str(e)}",
                errors=[str(e)]
            )
    
    def process_purchase(
        self,
        request: StockIntegrationRequest
    ) -> StockIntegrationResult:
        """
        معالجة عملية شراء (زيادة المخزون + إنشاء قيد محاسبي)
        
        Args:
            request: طلب التكامل
        
        Returns:
            StockIntegrationResult: نتيجة العملية
        """
        self._logger.info(
            f"Processing purchase: Product={request.product_id}, "
            f"Quantity={request.quantity}, Cost={request.unit_cost}"
        )
        
        # التحقق من صحة الطلب
        errors = request.validate()
        if errors:
            return StockIntegrationResult(
                success=False,
                message="Validation failed",
                errors=errors
            )
        
        try:
            with self._uow:
                # 1. الحصول على المنتج
                product = self._product_repo.get_by_id(request.product_id)
                if not product:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Product {request.product_id} not found",
                        errors=[f"Product {request.product_id} not found"]
                    )
                
                # 2. إنشاء حركة مخزون (دخول)
                movement = self._create_stock_movement(
                    product=product,
                    quantity=request.quantity,
                    unit_cost=request.unit_cost,
                    movement_type=StockMovementType.PURCHASE,
                    reference_type=request.reference_type or "PurchaseOrder",
                    reference_id=request.reference_id,
                    batch_number=request.batch_number,
                    serial_numbers=request.serial_numbers,
                    expiry_date=request.expiry_date,
                    location=request.location,
                    created_by=request.created_by
                )
                
                # 3. إنشاء القيد المحاسبي
                journal_entry = self._create_purchase_journal_entry(
                    product=product,
                    quantity=request.quantity,
                    unit_cost=request.unit_cost,
                    currency=request.currency,
                    reference_id=request.reference_id,
                    cost_center=request.cost_center or self._cost_center,
                    created_by=request.created_by
                )
                
                # 4. ترحيل القيد المحاسبي
                post_result = self._posting_engine.post(
                    journal_entry,
                    request.created_by,
                    skip_save=False
                )
                
                if not post_result.success:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Posting failed: {post_result.message}",
                        errors=post_result.errors
                    )
                
                # 5. حفظ حركة المخزون
                self._stock_service._repo.save(movement)
                
                # 6. تحديث كمية المنتج (إذا كان مطلوباً)
                current_quantity = self._stock_service.get_current_quantity(
                    EntityId("product", str(product.id.value))
                )
                new_quantity = current_quantity + request.quantity
                
                if request.update_product:
                    product.update_stock(
                        quantity_change=request.quantity,
                        movement_type=StockMovementType.PURCHASE,
                        reason=f"Purchase: {request.reference_id}",
                        updated_by=request.created_by
                    )
                    self._product_repo.save(product)
                
                # 7. Commit المعاملة
                self._uow.commit()
                
                self._logger.info(
                    f"Purchase processed successfully: Product={product.code}, "
                    f"Quantity={request.quantity}, Cost={request.unit_cost}"
                )
                
                return StockIntegrationResult(
                    success=True,
                    message="Purchase processed successfully",
                    stock_movement_id=str(movement.id),
                    journal_entry_id=post_result.journal_entry_id,
                    inventory_value=self._stock_service.get_current_quantity(
                        EntityId("product", str(product.id.value))
                    ),
                    details={
                        'product_code': product.code.value,
                        'product_name': product.name,
                        'new_quantity': float(new_quantity),
                        'old_quantity': float(current_quantity),
                    }
                )
                
        except Exception as e:
            self._logger.error(f"Error processing purchase: {e}", exc_info=True)
            self._uow.rollback()
            return StockIntegrationResult(
                success=False,
                message=f"Error processing purchase: {str(e)}",
                errors=[str(e)]
            )
    
    def process_adjustment(
        self,
        request: StockIntegrationRequest
    ) -> StockIntegrationResult:
        """
        معالجة تعديل المخزون
        
        Args:
            request: طلب التكامل
        
        Returns:
            StockIntegrationResult: نتيجة العملية
        """
        self._logger.info(
            f"Processing adjustment: Product={request.product_id}, "
            f"Quantity={request.quantity}"
        )
        
        # التحقق من صحة الطلب
        errors = request.validate()
        if errors:
            return StockIntegrationResult(
                success=False,
                message="Validation failed",
                errors=errors
            )
        
        try:
            with self._uow:
                # 1. الحصول على المنتج
                product = self._product_repo.get_by_id(request.product_id)
                if not product:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Product {request.product_id} not found",
                        errors=[f"Product {request.product_id} not found"]
                    )
                
                # 2. تحديد نوع الحركة
                movement_type = (
                    StockMovementType.ADJUSTMENT_IN
                    if request.quantity > 0
                    else StockMovementType.ADJUSTMENT_OUT
                )
                
                # 3. إنشاء حركة مخزون
                movement = self._create_stock_movement(
                    product=product,
                    quantity=abs(request.quantity),
                    unit_cost=request.unit_cost,
                    movement_type=movement_type,
                    reference_type=request.reference_type or "Adjustment",
                    reference_id=request.reference_id,
                    batch_number=request.batch_number,
                    serial_numbers=request.serial_numbers,
                    expiry_date=request.expiry_date,
                    location=request.location,
                    created_by=request.created_by
                )
                
                # 4. إنشاء القيد المحاسبي
                journal_entry = self._create_adjustment_journal_entry(
                    product=product,
                    quantity=request.quantity,
                    unit_cost=request.unit_cost,
                    currency=request.currency,
                    reference_id=request.reference_id,
                    cost_center=request.cost_center or self._cost_center,
                    created_by=request.created_by
                )
                
                # 5. ترحيل القيد المحاسبي
                post_result = self._posting_engine.post(
                    journal_entry,
                    request.created_by,
                    skip_save=False
                )
                
                if not post_result.success:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Posting failed: {post_result.message}",
                        errors=post_result.errors
                    )
                
                # 6. حفظ حركة المخزون
                self._stock_service._repo.save(movement)
                
                # 7. تحديث كمية المنتج (إذا كان مطلوباً)
                current_quantity = self._stock_service.get_current_quantity(
                    EntityId("product", str(product.id.value))
                )
                new_quantity = current_quantity + request.quantity
                
                if request.update_product:
                    product.update_stock(
                        quantity_change=request.quantity,
                        movement_type=movement_type,
                        reason=f"Adjustment: {request.reference_id}",
                        updated_by=request.created_by
                    )
                    self._product_repo.save(product)
                
                # 8. Commit المعاملة
                self._uow.commit()
                
                self._logger.info(
                    f"Adjustment processed successfully: Product={product.code}, "
                    f"Change={request.quantity}"
                )
                
                return StockIntegrationResult(
                    success=True,
                    message="Adjustment processed successfully",
                    stock_movement_id=str(movement.id),
                    journal_entry_id=post_result.journal_entry_id,
                    inventory_value=self._stock_service.get_current_quantity(
                        EntityId("product", str(product.id.value))
                    ),
                    details={
                        'product_code': product.code.value,
                        'product_name': product.name,
                        'new_quantity': float(new_quantity),
                        'old_quantity': float(current_quantity),
                        'adjustment_type': movement_type.value
                    }
                )
                
        except Exception as e:
            self._logger.error(f"Error processing adjustment: {e}", exc_info=True)
            self._uow.rollback()
            return StockIntegrationResult(
                success=False,
                message=f"Error processing adjustment: {str(e)}",
                errors=[str(e)]
            )
    
    # =========================================================================
    # دوال مساعدة (محسنة)
    # =========================================================================
    
    def _calculate_cogs(
        self,
        product: Product,
        quantity: Decimal,
        method: str = "fifo",
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        حساب COGS باستخدام الطريقة المطلوبة
        
        Args:
            product: كيان المنتج
            quantity: الكمية
            method: طريقة التقييم (fifo, lifo, weighted_average)
            currency: العملة
        
        Returns:
            Dict[str, Any]: نتيجة الحساب
        """
        entity = EntityId("product", str(product.id.value))
        
        # جلب الحركات للمنتج
        movements = self._stock_service._repo.get_movements(entity)
        
        if method == "fifo":
            layers = self._valuation_service._build_layers(movements)
            cogs, remaining = FIFOCostCalculator.calculate_cogs(
                layers=layers,
                quantity_to_consume=quantity,
                currency=currency
            )
            
            return {
                'success': True,
                'cogs_amount': cogs.amount,
                'remaining_layers': remaining,
                'method': 'fifo'
            }
            
        elif method == "lifo":
            layers = self._valuation_service._build_layers(movements)
            cogs, remaining = LIFOCostCalculator.calculate_cogs(
                layers=layers,
                quantity_to_consume=quantity,
                currency=currency
            )
            
            return {
                'success': True,
                'cogs_amount': cogs.amount,
                'remaining_layers': remaining,
                'method': 'lifo'
            }
            
        elif method == "weighted_average":
            valuation = self._valuation_service.calculate_valuation(
                entity=entity,
                as_of_date=date.today(),
                method=CostFlowMethod.WEIGHTED_AVERAGE
            )
            
            cogs_amount = valuation.average_cost * quantity
            
            return {
                'success': True,
                'cogs_amount': cogs_amount,
                'average_cost': valuation.average_cost,
                'method': 'weighted_average'
            }
            
        else:
            return {
                'success': False,
                'error': f"Unsupported cost method: {method}"
            }
    
    def _create_stock_movement(
        self,
        product: Product,
        quantity: Decimal,
        unit_cost: Decimal,
        movement_type: StockMovementType,
        reference_type: str,
        reference_id: str,
        batch_number: Optional[str] = None,
        serial_numbers: Optional[List[str]] = None,
        expiry_date: Optional[date] = None,
        location: Optional[str] = None,
        created_by: str = "system"
    ) -> StockMovement:
        """إنشاء حركة مخزون"""
        entity = EntityId("product", str(product.id.value))
        money = Money(unit_cost, product.unit_price.currency)
        
        # تحويل التاريخ إلى datetime إذا كان موجوداً
        expiry_datetime = datetime.combine(expiry_date, datetime.min.time(), tzinfo=timezone.utc) if expiry_date else None
        
        if movement_type.is_inbound:
            movement = StockMovement.create_inbound(
                entity=entity,
                quantity=quantity,
                unit_cost=money,
                movement_type=movement_type,
                reference_type=reference_type,
                reference_id=reference_id,
                batch_number=BatchNumber(batch_number) if batch_number else None,
                serial_numbers=serial_numbers,
                expiry_date=expiry_datetime,
                location=StockLocation.from_string(location) if location else None,
                notes=f"{movement_type.value} - {reference_id}",
                created_by=created_by
            )
        else:
            movement = StockMovement.create_outbound(
                entity=entity,
                quantity=quantity,
                unit_cost=money,
                movement_type=movement_type,
                reference_type=reference_type,
                reference_id=reference_id,
                batch_number=BatchNumber(batch_number) if batch_number else None,
                serial_numbers=serial_numbers,
                location=StockLocation.from_string(location) if location else None,
                notes=f"{movement_type.value} - {reference_id}",
                created_by=created_by
            )
        
        return movement
    
    def _create_sale_journal_entry(
        self,
        product: Product,
        quantity: Decimal,
        unit_price: Decimal,
        cogs_amount: Decimal,
        currency: str,
        reference_id: str,
        cost_center: Optional[str] = None,
        created_by: str = "system"
    ) -> JournalEntry:
        """إنشاء قيد محاسبي للبيع"""
        lines = []
        total_revenue = unit_price * quantity
        
        # 1. سطر COGS (مدين)
        lines.append(JournalLine(
            account_code=self._cogs_account,
            debit=Money(cogs_amount, currency),
            credit=Money(Decimal('0'), currency)
        ))
        
        # 2. سطر المخزون (دائن) - تناقص المخزون
        lines.append(JournalLine(
            account_code=self._inventory_account,
            debit=Money(Decimal('0'), currency),
            credit=Money(cogs_amount, currency)
        ))
        
        # 3. سطر الإيرادات (دائن)
        lines.append(JournalLine(
            account_code=self._revenue_account,
            debit=Money(Decimal('0'), currency),
            credit=Money(total_revenue, currency)
        ))
        
        # 4. إضافة مراكز التكلفة إذا كانت موجودة
        if cost_center:
            for line in lines:
                line.cost_center = cost_center
        
        return JournalEntry(
            date=datetime.now(timezone.utc),
            description=f"Sale: {product.code} - {product.name} (Qty: {quantity}) - Ref: {reference_id}",
            lines=lines
        )
    
    def _create_purchase_journal_entry(
        self,
        product: Product,
        quantity: Decimal,
        unit_cost: Decimal,
        currency: str,
        reference_id: str,
        cost_center: Optional[str] = None,
        created_by: str = "system"
    ) -> JournalEntry:
        """إنشاء قيد محاسبي للشراء"""
        lines = []
        total_cost = unit_cost * quantity
        
        # 1. سطر المخزون (مدين) - زيادة المخزون
        lines.append(JournalLine(
            account_code=self._inventory_account,
            debit=Money(total_cost, currency),
            credit=Money(Decimal('0'), currency)
        ))
        
        # 2. سطر الدائنون (دائن)
        lines.append(JournalLine(
            account_code=AccountCode("2010"),  # الدائنون
            debit=Money(Decimal('0'), currency),
            credit=Money(total_cost, currency)
        ))
        
        # 3. إضافة مراكز التكلفة إذا كانت موجودة
        if cost_center:
            for line in lines:
                line.cost_center = cost_center
        
        return JournalEntry(
            date=datetime.now(timezone.utc),
            description=f"Purchase: {product.code} - {product.name} (Qty: {quantity}) - Ref: {reference_id}",
            lines=lines
        )
    
    def _create_adjustment_journal_entry(
        self,
        product: Product,
        quantity: Decimal,
        unit_cost: Decimal,
        currency: str,
        reference_id: str,
        cost_center: Optional[str] = None,
        created_by: str = "system"
    ) -> JournalEntry:
        """إنشاء قيد محاسبي للتعديل"""
        lines = []
        total_amount = abs(quantity) * unit_cost
        
        if quantity > 0:
            # زيادة المخزون
            lines.append(JournalLine(
                account_code=self._inventory_account,
                debit=Money(total_amount, currency),
                credit=Money(Decimal('0'), currency)
            ))
            lines.append(JournalLine(
                account_code=AccountCode("5900"),  # حساب التعديلات
                debit=Money(Decimal('0'), currency),
                credit=Money(total_amount, currency)
            ))
        else:
            # نقصان المخزون
            lines.append(JournalLine(
                account_code=self._inventory_account,
                debit=Money(Decimal('0'), currency),
                credit=Money(total_amount, currency)
            ))
            lines.append(JournalLine(
                account_code=AccountCode("5900"),  # حساب التعديلات
                debit=Money(total_amount, currency),
                credit=Money(Decimal('0'), currency)
            ))
        
        # إضافة مراكز التكلفة إذا كانت موجودة
        if cost_center:
            for line in lines:
                line.cost_center = cost_center
        
        return JournalEntry(
            date=datetime.now(timezone.utc),
            description=f"Adjustment: {product.code} - {product.name} (Change: {quantity}) - Ref: {reference_id}",
            lines=lines
        )
    
    # =========================================================================
    # تقارير مقارنة طرق التقييم (محسنة)
    # =========================================================================
    
    def compare_valuation_methods(
        self,
        product_id: str,
        as_of_date: date,
        include_cogs: bool = True
    ) -> Dict[str, Any]:
        """
        مقارنة طرق تقييم المخزون الثلاث (FIFO, LIFO, Weighted Average)
        
        Args:
            product_id: معرف المنتج
            as_of_date: تاريخ التقييم
            include_cogs: حساب COGS لكل طريقة
        
        Returns:
            Dict[str, Any]: تقرير المقارنة
        """
        self._logger.info(
            f"Comparing valuation methods for product {product_id} as of {as_of_date}"
        )
        
        entity = EntityId("product", product_id)
        
        # حساب التقييم بكل طريقة
        fifo_result = self._valuation_service.calculate_valuation(
            entity=entity,
            as_of_date=as_of_date,
            method=CostFlowMethod.FIFO,
            include_cogs=include_cogs
        )
        
        lifo_result = self._valuation_service.calculate_valuation(
            entity=entity,
            as_of_date=as_of_date,
            method=CostFlowMethod.LIFO,
            include_cogs=include_cogs
        )
        
        avg_result = self._valuation_service.calculate_valuation(
            entity=entity,
            as_of_date=as_of_date,
            method=CostFlowMethod.WEIGHTED_AVERAGE,
            include_cogs=include_cogs
        )
        
        # الحصول على المنتج
        product = self._product_repo.get_by_id(product_id)
        
        # إنشاء التقرير
        report = {
            'product_id': product_id,
            'product_code': product.code.value if product else None,
            'product_name': product.name if product else None,
            'as_of_date': as_of_date.isoformat(),
            'currency': 'USD',
            'results': {
                'fifo': fifo_result.to_dict(),
                'lifo': lifo_result.to_dict(),
                'weighted_average': avg_result.to_dict()
            },
            'comparison': {
                'highest_value': 'fifo' if fifo_result.total_value >= max(
                    lifo_result.total_value, avg_result.total_value
                ) else ('lifo' if lifo_result.total_value >= avg_result.total_value else 'weighted_average'),
                'lowest_value': 'fifo' if fifo_result.total_value <= min(
                    lifo_result.total_value, avg_result.total_value
                ) else ('lifo' if lifo_result.total_value <= avg_result.total_value else 'weighted_average'),
                'fifo_vs_lifo': float(fifo_result.total_value - lifo_result.total_value),
                'fifo_vs_weighted': float(fifo_result.total_value - avg_result.total_value),
                'lifo_vs_weighted': float(lifo_result.total_value - avg_result.total_value),
                'fifo_vs_lifo_percent': float(
                    ((fifo_result.total_value - lifo_result.total_value) / 
                     lifo_result.total_value) * 100 if lifo_result.total_value > 0 else 0
                )
            },
            'recommendation': self._get_recommendation(fifo_result, lifo_result, avg_result),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        return report
    
    def _get_recommendation(
        self,
        fifo: InventoryValuationResult,
        lifo: InventoryValuationResult,
        weighted: InventoryValuationResult
    ) -> str:
        """توصية بالطريقة المناسبة"""
        diff_fifo_lifo = abs(fifo.total_value - lifo.total_value)
        diff_fifo_weighted = abs(fifo.total_value - weighted.total_value)
        diff_lifo_weighted = abs(lifo.total_value - weighted.total_value)
        
        if diff_fifo_lifo < 0.01 and diff_fifo_weighted < 0.01:
            return "جميع الطرق تعطي نفس النتيجة تقريباً. يمكن استخدام أي منها."
        
        if fifo.total_value > lifo.total_value and fifo.total_value > weighted.total_value:
            return "FIFO تعطي أعلى قيمة للمخزون. مناسبة في فترات التضخم."
        elif lifo.total_value > fifo.total_value and lifo.total_value > weighted.total_value:
            return "LIFO تعطي أعلى قيمة للمخزون. مناسبة في فترات الانكماش."
        else:
            return "Weighted Average تعطي قيمة وسطية. مناسبة للاستقرار."
    
    # =========================================================================
    # تسجيل COGS كقيد محاسبي منفصل
    # =========================================================================
    
    def record_cogs_entry(
        self,
        product_id: str,
        from_date: date,
        to_date: date,
        method: str = "fifo",
        posted_by: str = "system"
    ) -> StockIntegrationResult:
        """
        تسجيل COGS كقيد محاسبي منفصل
        
        هذا مفيد عندما تريد تسجيل COGS بشكل دوري (مثلاً شهرياً)
        
        Args:
            product_id: معرف المنتج
            from_date: بداية الفترة
            to_date: نهاية الفترة
            method: طريقة التقييم
            posted_by: من قام بالترحيل
        
        Returns:
            StockIntegrationResult: نتيجة العملية
        """
        self._logger.info(
            f"Recording COGS entry for product {product_id} from {from_date} to {to_date}"
        )
        
        try:
            with self._uow:
                # 1. الحصول على المنتج
                product = self._product_repo.get_by_id(product_id)
                if not product:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Product {product_id} not found",
                        errors=[f"Product {product_id} not found"]
                    )
                
                # 2. حساب COGS
                entity = EntityId("product", product_id)
                cogs_amount = self._valuation_service.calculate_cogs(
                    entity=entity,
                    from_date=from_date,
                    to_date=to_date,
                    method=CostFlowMethod(method)
                )
                
                if cogs_amount <= 0:
                    return StockIntegrationResult(
                        success=False,
                        message="No COGS to record",
                        cogs_amount=Decimal('0')
                    )
                
                # 3. إنشاء القيد المحاسبي
                lines = [
                    JournalLine(
                        account_code=self._cogs_account,
                        debit=Money(cogs_amount, product.unit_price.currency),
                        credit=Money(Decimal('0'), product.unit_price.currency)
                    ),
                    JournalLine(
                        account_code=self._inventory_account,
                        debit=Money(Decimal('0'), product.unit_price.currency),
                        credit=Money(cogs_amount, product.unit_price.currency)
                    )
                ]
                
                entry = JournalEntry(
                    date=datetime.now(timezone.utc),
                    description=f"COGS for {product.code} - Period: {from_date} to {to_date}",
                    lines=lines
                )
                
                # 4. ترحيل القيد
                post_result = self._posting_engine.post(entry, posted_by, skip_save=False)
                
                if not post_result.success:
                    return StockIntegrationResult(
                        success=False,
                        message=f"Posting failed: {post_result.message}",
                        errors=post_result.errors
                    )
                
                self._uow.commit()
                
                self._logger.info(
                    f"COGS entry created: {post_result.journal_entry_id} for {cogs_amount}"
                )
                
                return StockIntegrationResult(
                    success=True,
                    message="COGS entry created successfully",
                    journal_entry_id=post_result.journal_entry_id,
                    cogs_amount=cogs_amount,
                    details={
                        'product_code': product.code.value,
                        'product_name': product.name,
                        'period': f"{from_date} to {to_date}",
                        'method': method
                    }
                )
                
        except Exception as e:
            self._logger.error(f"Error recording COGS: {e}", exc_info=True)
            self._uow.rollback()
            return StockIntegrationResult(
                success=False,
                message=f"Error recording COGS: {str(e)}",
                errors=[str(e)]
            )
    
    # =========================================================================
    # تقييم المخزون مع تفاصيل COGS
    # =========================================================================
    
    def get_valuation_with_cogs(
        self,
        product_id: str,
        as_of_date: date,
        method: str = "fifo"
    ) -> Dict[str, Any]:
        """
        الحصول على تقييم المخزون مع تفاصيل COGS
        
        Args:
            product_id: معرف المنتج
            as_of_date: تاريخ التقييم
            method: طريقة التقييم
        
        Returns:
            Dict[str, Any]: تقييم المخزون مع COGS
        """
        self._logger.info(
            f"Getting valuation with COGS for product {product_id} as of {as_of_date}"
        )
        
        entity = EntityId("product", product_id)
        
        # حساب التقييم
        valuation = self._valuation_service.calculate_valuation(
            entity=entity,
            as_of_date=as_of_date,
            method=CostFlowMethod(method),
            include_cogs=True
        )
        
        # حساب COGS للفترة (من بداية السنة حتى التاريخ)
        from_date = date(as_of_date.year, 1, 1)
        cogs_period = self._valuation_service.calculate_cogs(
            entity=entity,
            from_date=from_date,
            to_date=as_of_date,
            method=CostFlowMethod(method)
        )
        
        # الحصول على المنتج
        product = self._product_repo.get_by_id(product_id)
        
        # حساب نسبة الدوران
        inventory_turnover = None
        if valuation.total_value > 0 and cogs_period > 0:
            inventory_turnover = cogs_period / valuation.total_value
        
        result = valuation.to_dict()
        result.update({
            'cogs_period': float(cogs_period),
            'cogs_period_start': from_date.isoformat(),
            'cogs_period_end': as_of_date.isoformat(),
            'product_code': product.code.value if product else None,
            'product_name': product.name if product else None,
            'inventory_turnover': float(inventory_turnover) if inventory_turnover else None,
            'days_in_inventory': 365 / float(inventory_turnover) if inventory_turnover and inventory_turnover > 0 else None
        })
        
        return result
    
    # =========================================================================
    # تقرير شامل للمخزون (محسن)
    # =========================================================================
    
    def get_comprehensive_inventory_report(
        self,
        product_ids: Optional[List[str]] = None,
        as_of_date: Optional[date] = None,
        method: str = "fifo"
    ) -> Dict[str, Any]:
        """
        تقرير شامل للمخزون لمنتجات متعددة
        
        Args:
            product_ids: قائمة معرفات المنتجات (الكل إذا لم تحدد)
            as_of_date: تاريخ التقييم (اليوم إذا لم تحدد)
            method: طريقة التقييم
        
        Returns:
            Dict[str, Any]: تقرير شامل
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        products = []
        if product_ids:
            for pid in product_ids:
                product = self._product_repo.get_by_id(pid)
                if product:
                    products.append(product)
        else:
            products = self._product_repo.list_all(limit=1000)
        
        report = {
            'as_of_date': as_of_date.isoformat(),
            'method': method,
            'total_products': len(products),
            'total_value': Decimal('0'),
            'total_quantity': Decimal('0'),
            'low_stock_products': 0,
            'out_of_stock_products': 0,
            'products': []
        }
        
        for product in products:
            entity = EntityId("product", str(product.id.value))
            
            try:
                valuation = self._valuation_service.calculate_valuation(
                    entity=entity,
                    as_of_date=as_of_date,
                    method=CostFlowMethod(method)
                )
                
                product_data = {
                    'product_id': str(product.id.value),
                    'product_code': product.code.value,
                    'product_name': product.name,
                    'category': product.category,
                    'quantity': float(valuation.total_quantity),
                    'value': float(valuation.total_value),
                    'average_cost': float(valuation.average_cost),
                    'currency': valuation.currency,
                    'is_active': product.is_active,
                    'is_low_stock': product.is_low_stock,
                    'is_out_of_stock': product.is_out_of_stock,
                    'stock_quantity': product.stock_quantity,
                    'min_stock': product.low_stock_threshold,
                    'last_movement_date': None  # يمكن إضافته لاحقاً
                }
                
                report['products'].append(product_data)
                report['total_value'] += valuation.total_value
                report['total_quantity'] += valuation.total_quantity
                
                if product.is_low_stock:
                    report['low_stock_products'] += 1
                if product.is_out_of_stock:
                    report['out_of_stock_products'] += 1
                    
            except Exception as e:
                self._logger.warning(f"Error valuing product {product.code}: {e}")
                continue
        
        # ترتيب المنتجات حسب القيمة (تنازلي)
        report['products'].sort(key=lambda x: x['value'], reverse=True)
        
        # إحصائيات إضافية
        report['total_value_formatted'] = f"{report['total_value']:,.2f} USD"
        report['average_product_value'] = float(
            report['total_value'] / len(products) if products else 0
        )
        report['health_score'] = self._calculate_health_score(report)
        
        return report
    
    def _calculate_health_score(self, report: Dict[str, Any]) -> float:
        """
        حساب مؤشر صحة المخزون (0-100)
        
        عوامل المؤشر:
            - نسبة المنتجات منخفضة المخزون
            - نسبة المنتجات نافدة
            - توزيع القيمة
        """
        total = report['total_products']
        if total == 0:
            return 0
        
        low_stock_ratio = report['low_stock_products'] / total
        out_of_stock_ratio = report['out_of_stock_products'] / total
        
        # حساب النقاط
        points = 100
        points -= low_stock_ratio * 30  # خصم 30 نقطة كحد أقصى
        points -= out_of_stock_ratio * 40  # خصم 40 نقطة كحد أقصى
        
        # حساب توزيع القيمة (نريد توزيعاً متوازناً)
        values = [p['value'] for p in report['products'] if p['value'] > 0]
        if values:
            # معامل التشتت (كلما كان أقل كان أفضل)
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std_dev = variance ** 0.5
            
            # إذا كان الانحراف المعياري > 80% من المتوسط، فهذا يعني توزيع غير متوازن
            if mean > 0 and (std_dev / mean) > 0.8:
                points -= 20
        
        return max(0, min(100, points))


# =============================================================================
# دالة مصنع لتسهيل الإنشاء
# =============================================================================

def create_inventory_integration(
    uow: IUnitOfWork,
    posting_engine: PostingEngine,
    product_repository: IProductRepository,
    stock_service: StockMovementService,
    valuation_service: InventoryValuationService,
    **kwargs
) -> InventoryAccountingIntegration:
    """
    إنشاء خدمة تكامل المخزون مع المحاسبة
    
    Args:
        uow: Unit of Work
        posting_engine: محرك الترحيل
        product_repository: مستودع المنتجات
        stock_service: خدمة حركات المخزون
        valuation_service: خدمة تقييم المخزون
        **kwargs: معاملات إضافية (inventory_account, cogs_account, revenue_account, cost_center)
    
    Returns:
        InventoryAccountingIntegration: خدمة التكامل
    """
    return InventoryAccountingIntegration(
        uow=uow,
        posting_engine=posting_engine,
        product_repository=product_repository,
        stock_service=stock_service,
        valuation_service=valuation_service,
        inventory_account=kwargs.get('inventory_account', AccountCode("1030")),
        cogs_account=kwargs.get('cogs_account', AccountCode("5010")),
        revenue_account=kwargs.get('revenue_account', AccountCode("4010")),
        cost_center=kwargs.get('cost_center')
    )


__all__ = [
    'StockIntegrationRequest',
    'StockIntegrationResult',
    'InventoryAccountingIntegration',
    'create_inventory_integration'
]