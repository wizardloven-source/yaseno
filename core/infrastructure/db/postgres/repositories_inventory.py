# core/infrastructure/db/postgres/repositories_inventory.py
"""
Inventory Repository Implementation - PostgreSQL
التنفيذ الكامل لمستودع المخزون مع دعم FIFO و Optimistic Locking
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import UUID, uuid4
import json
import logging

from sqlalchemy import select, and_, or_, func, desc, case, update, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from core.domain.inventory.entities import StockMovement, StockBatch, StockTransfer
from core.domain.inventory.value_objects import (
    StockMovementId, StockBatchId, StockTransferId,
    EntityId, StockMovementType, StockBatchStatus,
    BatchNumber, SerialNumber, ExpiryDate, StockLocation,
    Money as InventoryMoney
)
from core.domain.inventory.interfaces import (
    IStockMovementRepository, IStockBatchRepository, IStockTransferRepository
)
from core.shared.exceptions import ConcurrentModificationError

# استيراد النماذج
from core.infrastructure.db.models.inventory_models import (
    StockMovementModel,
    StockBatchModel,
    StockTransferModel,
    StockLayerModel,
    StockSerialNumberModel
)

logger = logging.getLogger(__name__)


# =============================================================================
# دوال مساعدة للتحويل
# =============================================================================

def _entity_id_from_string(entity_type: str, entity_id: str) -> EntityId:
    """إنشاء EntityId من نص"""
    return EntityId(entity_type, entity_id)


def _money_to_db(amount: Decimal, currency: str) -> Dict[str, Any]:
    """تحويل Money إلى صيغة مناسبة للتخزين"""
    return {
        'amount': str(amount),
        'currency': currency
    }


def _money_from_db(data: Dict[str, Any]) -> InventoryMoney:
    """تحويل البيانات المخزنة إلى Money"""
    if isinstance(data, dict):
        return InventoryMoney(
            amount=Decimal(data.get('amount', '0')),
            currency=data.get('currency', 'USD')
        )
    return InventoryMoney.zero()


def _serial_numbers_to_db(serial_numbers: List[SerialNumber]) -> List[str]:
    """تحويل الأرقام التسلسلية إلى نص"""
    return [str(s) for s in serial_numbers]


def _serial_numbers_from_db(data: Any) -> List[SerialNumber]:
    """تحويل البيانات المخزنة إلى أرقام تسلسلية"""
    if isinstance(data, list):
        return [SerialNumber(s) for s in data if s]
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            return [SerialNumber(s) for s in parsed if s]
        except:
            return []
    return []


# =============================================================================
# StockMovement Repository - التنفيذ الكامل
# =============================================================================

class PostgresStockMovementRepository(IStockMovementRepository):
    """تطبيق PostgreSQL لمستودع حركات المخزون"""
    
    def __init__(self, session: Session):
        self._session = session
    
    # =========================================================================
    # العمليات الأساسية
    # =========================================================================
    
    def save(self, movement: StockMovement) -> None:
        """
        حفظ حركة مخزون (جديدة أو محدثة)
        
        يدعم Optimistic Locking عبر حقل version
        """
        if not movement:
            raise ValueError("Movement cannot be None")
        
        # التحقق من وجود الحركة
        existing = self._session.execute(
            select(StockMovementModel).where(
                StockMovementModel.id == str(movement.id.value)
            )
        ).scalar_one_or_none()
        
        if existing:
            # تحديث - التحقق من الإصدار
            if existing.version != movement.version:
                raise ConcurrentModificationError(
                    entity_type="StockMovement",
                    entity_id=str(movement.id.value),
                    expected_version=movement.version,
                    actual_version=existing.version
                )
            
            # تحديث النموذج
            self._update_model(existing, movement)
            existing.version = movement.version + 1
            existing.updated_at = datetime.now(timezone.utc)
            
            self._session.merge(existing)
        else:
            # إنشاء جديد
            model = self._to_model(movement)
            self._session.add(model)
        
        self._session.flush()
        logger.debug(f"StockMovement saved: {movement.id}")
    
    def get_by_id(self, movement_id: StockMovementId) -> Optional[StockMovement]:
        """الحصول على حركة بواسطة المعرف"""
        if not movement_id:
            return None
        
        model = self._session.execute(
            select(StockMovementModel)
            .where(StockMovementModel.id == str(movement_id.value))
            
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self._to_domain(model)
    
    def get_by_entity(
        self,
        entity: EntityId,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockMovement]:
        """الحصول على حركات كيان معين"""
        if not entity:
            return []
        
        models = self._session.execute(
            select(StockMovementModel)
            .where(
                StockMovementModel.entity_type == entity.entity_type,
                StockMovementModel.entity_id == entity.entity_id
            )
            .order_by(desc(StockMovementModel.movement_date))
            .limit(limit)
            .offset(offset)
            
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    def get_by_reference(
        self,
        reference_type: str,
        reference_id: str
    ) -> List[StockMovement]:
        """الحصول على حركات مرجع معين"""
        if not reference_type or not reference_id:
            return []
        
        models = self._session.execute(
            select(StockMovementModel)
            .where(
                StockMovementModel.reference_type == reference_type,
                StockMovementModel.reference_id == reference_id
            )
            .order_by(desc(StockMovementModel.movement_date))
            
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    def get_by_date_range(
        self,
        entity: EntityId,
        from_date: datetime,
        to_date: datetime,
        movement_type: Optional[StockMovementType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockMovement]:
        """الحصول على حركات في نطاق زمني"""
        if not entity:
            return []
        
        query = select(StockMovementModel).where(
            StockMovementModel.entity_type == entity.entity_type,
            StockMovementModel.entity_id == entity.entity_id,
            StockMovementModel.movement_date >= from_date,
            StockMovementModel.movement_date <= to_date
        )
        
        if movement_type:
            query = query.where(StockMovementModel.movement_type == movement_type.value)
        
        models = self._session.execute(
            query
            .order_by(desc(StockMovementModel.movement_date))
            .limit(limit)
            .offset(offset)
            
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    # =========================================================================
    # حسابات الكميات
    # =========================================================================
    
    def get_current_quantity(self, entity: EntityId) -> Decimal:
        """الحصول على الكمية الحالية لكيان"""
        if not entity:
            return Decimal('0')
        
        # مجموع جميع الحركات (الواردة موجبة، الصادرة سالبة)
        outbound_types = ['sale', 'adjustment_out', 'transfer_out', 'damage', 'expired']
        signed_quantity = case(
            (StockMovementModel.movement_type.in_(outbound_types), -StockMovementModel.quantity),
            else_=StockMovementModel.quantity
        )
        result = self._session.execute(
            select(func.coalesce(func.sum(signed_quantity), 0))
            .where(
                StockMovementModel.entity_type == entity.entity_type,
                StockMovementModel.entity_id == entity.entity_id
            )
        ).scalar()
        
        return Decimal(str(result)) if result else Decimal('0')
    
    def get_quantity_at_date(self, entity: EntityId, as_of_date: date) -> Decimal:
        """الحصول على الكمية في تاريخ معين"""
        if not entity or not as_of_date:
            return Decimal('0')
        
        # تحويل التاريخ إلى datetime
        as_of_datetime = datetime.combine(as_of_date, datetime.max.time(), tzinfo=timezone.utc)
        
        outbound_types = ['sale', 'adjustment_out', 'transfer_out', 'damage', 'expired']
        signed_quantity = case(
            (StockMovementModel.movement_type.in_(outbound_types), -StockMovementModel.quantity),
            else_=StockMovementModel.quantity
        )
        result = self._session.execute(
            select(func.coalesce(func.sum(signed_quantity), 0))
            .where(
                StockMovementModel.entity_type == entity.entity_type,
                StockMovementModel.entity_id == entity.entity_id,
                StockMovementModel.movement_date <= as_of_datetime
            )
        ).scalar()
        
        return Decimal(str(result)) if result else Decimal('0')
    
    # =========================================================================
    # FIFO Layers - الأهم للتقييم
    # =========================================================================
    
    def get_layers_for_fifo(
        self,
        entity: EntityId,
        as_of_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        الحصول على طبقات المخزون لـ FIFO
        
        تعيد قائمة منظمة ترتيباً زمنياً (الأقدم أولاً)
        """
        if not entity:
            return []
        
        # بناء الاستعلام
        query = select(StockMovementModel).where(
            StockMovementModel.entity_type == entity.entity_type,
            StockMovementModel.entity_id == entity.entity_id,
            StockMovementModel.movement_type.in_([
                StockMovementType.PURCHASE.value,
                StockMovementType.RETURN.value,
                StockMovementType.ADJUSTMENT_IN.value,
                StockMovementType.TRANSFER_IN.value
            ])
        )
        
        if as_of_date:
            as_of_datetime = datetime.combine(as_of_date, datetime.max.time(), tzinfo=timezone.utc)
            query = query.where(StockMovementModel.movement_date <= as_of_datetime)
        
        # ترتيب من الأقدم إلى الأحدث
        models = self._session.execute(
            query.order_by(StockMovementModel.movement_date.asc())
        ).scalars().all()
        
        layers = []
        for model in models:
            # حساب الكمية المتبقية (الكمية الأصلية - الكمية المستهلكة)
            consumed = self._get_consumed_quantity_for_movement(model.id)
            remaining = model.quantity - consumed
            
            if remaining > 0:
                layers.append({
                    'layer_id': str(model.id),
                    'quantity': remaining,
                    'unit_cost': Decimal(str(model.unit_cost)),
                    'currency': model.currency,
                    'purchase_date': model.movement_date.date() if model.movement_date else None,
                    'batch_number': model.batch_number,
                    'serial_numbers': self._get_serial_numbers_for_movement(model.id),
                    'original_quantity': model.quantity,
                    'consumed_quantity': consumed,
                    'movement_id': str(model.id),
                })
        
        return layers
    
    def _get_consumed_quantity_for_movement(self, movement_id: str) -> Decimal:
        """حساب الكمية المستهلكة من حركة معينة"""
        # جلب جميع الحركات الصادرة التي تشير إلى هذه الحركة
        result = self._session.execute(
            select(func.coalesce(func.sum(StockMovementModel.quantity), 0))
            .where(
                StockMovementModel.reference_id == movement_id,
                StockMovementModel.movement_type.in_([
                    StockMovementType.SALE.value,
                    StockMovementType.ADJUSTMENT_OUT.value,
                    StockMovementType.TRANSFER_OUT.value,
                    StockMovementType.DAMAGE.value,
                    StockMovementType.EXPIRED.value
                ])
            )
        ).scalar()
        
        return abs(Decimal(str(result))) if result else Decimal('0')
    
    def _get_serial_numbers_for_movement(self, movement_id: str) -> List[str]:
        """الحصول على الأرقام التسلسلية لحركة معينة"""
        models = self._session.execute(
            select(StockSerialNumberModel)
            .where(StockSerialNumberModel.movement_id == movement_id)
        ).scalars().all()
        
        return [m.serial_number for m in models]
    
    # =========================================================================
    # الحذف
    # =========================================================================
    
    def delete(self, movement_id: StockMovementId) -> bool:
        """حذف حركة مخزون"""
        if not movement_id:
            return False
        
        try:
            # الحصول على الحركة
            model = self._session.execute(
                select(StockMovementModel)
                .where(StockMovementModel.id == str(movement_id.value))
            ).scalar_one_or_none()
            
            if not model:
                return False
            
            # حذف الأرقام التسلسلية المرتبطة
            self._session.execute(
                delete(StockSerialNumberModel)
                .where(StockSerialNumberModel.movement_id == str(movement_id.value))
            )
            
            # حذف الحركة
            self._session.delete(model)
            self._session.flush()
            
            logger.info(f"StockMovement deleted: {movement_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting movement {movement_id}: {e}")
            return False
    
    # =========================================================================
    # دوال التحويل (Domain ↔ Model)
    # =========================================================================
    
    def _to_model(self, movement: StockMovement) -> StockMovementModel:
        """تحويل كيان Domain إلى Model"""
        return StockMovementModel(
            id=str(movement.id.value),
            entity_type=movement.entity.entity_type,
            entity_id=movement.entity.entity_id,
            movement_type=movement.movement_type.value,
            quantity=movement.quantity,
            unit_cost=movement.unit_cost.amount,
            currency=movement.unit_cost.currency,
            total_cost=movement.total_cost.amount,
            reference_type=movement.reference_type,
            reference_id=movement.reference_id,
            batch_number=str(movement.batch_number) if movement.batch_number else None,
            expiry_date=movement.expiry_date.value if movement.expiry_date else None,
            location=str(movement.location) if movement.location else None,
            notes=movement.notes,
            movement_date=movement.movement_date,
            created_at=movement.created_at,
            created_by=movement.created_by,
            version=movement.version
        )
    
    def _update_model(self, model: StockMovementModel, movement: StockMovement) -> None:
        """تحديث Model من كيان Domain"""
        model.entity_type = movement.entity.entity_type
        model.entity_id = movement.entity.entity_id
        model.movement_type = movement.movement_type.value
        model.quantity = movement.quantity
        model.unit_cost = movement.unit_cost.amount
        model.currency = movement.unit_cost.currency
        model.total_cost = movement.total_cost.amount
        model.reference_type = movement.reference_type
        model.reference_id = movement.reference_id
        model.batch_number = str(movement.batch_number) if movement.batch_number else None
        model.expiry_date = movement.expiry_date.value if movement.expiry_date else None
        model.location = str(movement.location) if movement.location else None
        model.notes = movement.notes
        model.movement_date = movement.movement_date
        model.updated_at = datetime.now(timezone.utc)
    
    def _to_domain(self, model: StockMovementModel) -> StockMovement:
        """تحويل Model إلى كيان Domain"""
        from core.domain.inventory.entities import StockMovement
        
        # إنشاء EntityId
        entity = EntityId(model.entity_type, model.entity_id)
        
        # إنشاء Money
        unit_cost = InventoryMoney(
            amount=Decimal(str(model.unit_cost)),
            currency=model.currency or "USD"
        )
        total_cost = InventoryMoney(
            amount=Decimal(str(model.total_cost or model.unit_cost * model.quantity)),
            currency=model.currency or "USD"
        )
        
        # إنشاء الحركة
        movement = StockMovement(
            id=StockMovementId(model.id),
            entity=entity,
            movement_type=StockMovementType(model.movement_type),
            quantity=Decimal(str(model.quantity)),
            unit_cost=unit_cost,
            total_cost=total_cost,
            reference_type=model.reference_type or "",
            reference_id=model.reference_id or "",
            batch_number=BatchNumber(model.batch_number) if model.batch_number else None,
            expiry_date=ExpiryDate(model.expiry_date) if model.expiry_date else None,
            location=StockLocation.from_string(model.location) if model.location else None,
            notes=model.notes or "",
            movement_date=model.movement_date or datetime.now(timezone.utc),
            created_at=model.created_at or datetime.now(timezone.utc),
            created_by=model.created_by or "system",
            version=model.version or 1
        )
        
        return movement


# =============================================================================
# StockBatch Repository - التنفيذ الكامل
# =============================================================================

class PostgresStockBatchRepository(IStockBatchRepository):
    """تطبيق PostgreSQL لمستودع دفعات المخزون"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, batch: StockBatch) -> None:
        """حفظ دفعة مخزون"""
        if not batch:
            raise ValueError("Batch cannot be None")
        
        existing = self._session.execute(
            select(StockBatchModel).where(
                StockBatchModel.id == str(batch.id.value)
            )
        ).scalar_one_or_none()
        
        if existing:
            # الكيان يزيد version ذاتياً قبل الحفظ → قارن مع version-1
            if existing.version != batch.version - 1:
                raise ConcurrentModificationError(
                    entity_type="StockBatch",
                    entity_id=str(batch.id.value),
                    expected_version=batch.version,
                    actual_version=existing.version
                )
            
            existing.batch_number = str(batch.batch_number)
            existing.initial_quantity = batch.initial_quantity
            existing.current_quantity = batch.current_quantity
            existing.unit_cost = batch.unit_cost.amount
            existing.currency = batch.unit_cost.currency
            existing.total_cost = batch.total_cost.amount
            existing.production_date = batch.production_date
            existing.expiry_date = batch.expiry_date.value if batch.expiry_date else None
            existing.location = str(batch.location) if batch.location else None
            existing.status = batch.status.value
            existing.notes = batch.notes
            existing.updated_at = datetime.now(timezone.utc)
            existing.version = batch.version
            
            self._session.merge(existing)
        else:
            model = StockBatchModel(
                id=str(batch.id.value),
                entity_type=batch.entity.entity_type,
                entity_id=batch.entity.entity_id,
                batch_number=str(batch.batch_number),
                initial_quantity=batch.initial_quantity,
                current_quantity=batch.current_quantity,
                unit_cost=batch.unit_cost.amount,
                currency=batch.unit_cost.currency,
                total_cost=batch.total_cost.amount,
                production_date=batch.production_date,
                expiry_date=batch.expiry_date.value if batch.expiry_date else None,
                location=str(batch.location) if batch.location else None,
                status=batch.status.value,
                notes=batch.notes,
                created_at=batch.created_at,
                created_by=batch.created_by,
                version=1
            )
            self._session.add(model)
        
        self._session.flush()
    
    def get_by_id(self, batch_id: StockBatchId) -> Optional[StockBatch]:
        """الحصول على دفعة بواسطة المعرف"""
        if not batch_id:
            return None
        
        model = self._session.execute(
            select(StockBatchModel).where(
                StockBatchModel.id == str(batch_id.value)
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self._to_domain(model)
    
    def get_by_batch_number(
        self,
        batch_number: BatchNumber,
        entity: Optional[EntityId] = None
    ) -> Optional[StockBatch]:
        """الحصول على دفعة برقم الدفعة"""
        if not batch_number:
            return None
        
        query = select(StockBatchModel).where(
            StockBatchModel.batch_number == str(batch_number)
        )
        
        if entity:
            query = query.where(
                StockBatchModel.entity_type == entity.entity_type,
                StockBatchModel.entity_id == entity.entity_id
            )
        
        model = self._session.execute(query).scalar_one_or_none()
        
        if not model:
            return None
        
        return self._to_domain(model)
    
    def get_by_entity(
        self,
        entity: EntityId,
        status: Optional[StockBatchStatus] = None,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockBatch]:
        """الحصول على دفعات كيان معين"""
        if not entity:
            return []
        
        query = select(StockBatchModel).where(
            StockBatchModel.entity_type == entity.entity_type,
            StockBatchModel.entity_id == entity.entity_id
        )
        
        if status:
            query = query.where(StockBatchModel.status == status.value)
        
        if not include_expired:
            query = query.where(
                or_(
                    StockBatchModel.expiry_date.is_(None),
                    StockBatchModel.expiry_date > date.today()
                )
            )
        
        models = self._session.execute(
            query.order_by(desc(StockBatchModel.created_at))
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    def get_expiring_batches(
        self,
        days_threshold: int = 30,
        limit: int = 100
    ) -> List[StockBatch]:
        """الحصول على الدفعات التي تنتهي قريباً"""
        if days_threshold <= 0:
            return []
        
        today = date.today()
        expiry_date = today + timedelta(days=days_threshold)
        
        models = self._session.execute(
            select(StockBatchModel)
            .where(
                StockBatchModel.expiry_date <= expiry_date,
                StockBatchModel.expiry_date >= today,
                StockBatchModel.current_quantity > 0,
                StockBatchModel.status != StockBatchStatus.EXPIRED.value
            )
            .order_by(StockBatchModel.expiry_date.asc())
            .limit(limit)
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    def get_expired_batches(self, limit: int = 100) -> List[StockBatch]:
        """الحصول على الدفعات المنتهية الصلاحية"""
        models = self._session.execute(
            select(StockBatchModel)
            .where(
                StockBatchModel.expiry_date < date.today(),
                StockBatchModel.current_quantity > 0,
                StockBatchModel.status != StockBatchStatus.EXPIRED.value
            )
            .order_by(StockBatchModel.expiry_date.asc())
            .limit(limit)
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    def delete(self, batch_id: StockBatchId) -> bool:
        """حذف دفعة مخزون"""
        if not batch_id:
            return False
        
        model = self._session.execute(
            select(StockBatchModel).where(
                StockBatchModel.id == str(batch_id.value)
            )
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        self._session.delete(model)
        self._session.flush()
        return True
    
    def _to_domain(self, model: StockBatchModel) -> StockBatch:
        """تحويل Model إلى كيان Domain"""
        from core.domain.inventory.entities import StockBatch
        
        entity = EntityId(model.entity_type, model.entity_id)
        
        return StockBatch(
            id=StockBatchId(UUID(str(model.id))),
            entity=entity,
            batch_number=BatchNumber(model.batch_number),
            initial_quantity=Decimal(str(model.initial_quantity)),
            current_quantity=Decimal(str(model.current_quantity)),
            unit_cost=InventoryMoney(
                amount=Decimal(str(model.unit_cost)),
                currency=model.currency or "USD"
            ),
            total_cost=InventoryMoney(
                amount=Decimal(str(model.total_cost or model.unit_cost * model.initial_quantity)),
                currency=model.currency or "USD"
            ),
            production_date=model.production_date,
            expiry_date=ExpiryDate(model.expiry_date) if model.expiry_date else None,
            location=StockLocation.from_string(model.location) if model.location else None,
            status=StockBatchStatus(model.status) if model.status else StockBatchStatus.ACTIVE,
            notes=model.notes or "",
            created_at=model.created_at or datetime.now(timezone.utc),
            created_by=model.created_by or "system",
            updated_at=model.updated_at or datetime.now(timezone.utc),
            updated_by=model.updated_by or "system",
            version=model.version or 1
        )


# =============================================================================
# StockTransfer Repository - التنفيذ الكامل
# =============================================================================

class PostgresStockTransferRepository(IStockTransferRepository):
    """تطبيق PostgreSQL لمستودع عمليات التحويل"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, transfer: StockTransfer) -> None:
        """حفظ عملية تحويل"""
        if not transfer:
            raise ValueError("Transfer cannot be None")
        
        existing = self._session.execute(
            select(StockTransferModel).where(
                StockTransferModel.id == str(transfer.id.value)
            )
        ).scalar_one_or_none()
        
        if existing:
            if existing.version != transfer.version - 1:
                raise ConcurrentModificationError(
                    entity_type="StockTransfer",
                    entity_id=str(transfer.id.value),
                    expected_version=transfer.version,
                    actual_version=existing.version
                )
            
            existing.quantity = transfer.quantity
            existing.unit_cost = transfer.unit_cost.amount
            existing.currency = transfer.unit_cost.currency
            existing.total_cost = transfer.total_cost.amount
            existing.from_location = str(transfer.from_location)
            existing.to_location = str(transfer.to_location)
            existing.reference_type = transfer.reference_type
            existing.reference_id = transfer.reference_id
            existing.batch_number = str(transfer.batch_number) if transfer.batch_number else None
            existing.status = transfer.status
            existing.notes = transfer.notes
            existing.updated_at = datetime.now(timezone.utc)
            existing.version = transfer.version
            
            self._session.merge(existing)
        else:
            model = StockTransferModel(
                id=str(transfer.id.value),
                entity_type=transfer.entity.entity_type,
                entity_id=transfer.entity.entity_id,
                quantity=transfer.quantity,
                unit_cost=transfer.unit_cost.amount,
                currency=transfer.unit_cost.currency,
                total_cost=transfer.total_cost.amount,
                from_location=str(transfer.from_location),
                to_location=str(transfer.to_location),
                reference_type=transfer.reference_type,
                reference_id=transfer.reference_id,
                batch_number=str(transfer.batch_number) if transfer.batch_number else None,
                status=transfer.status,
                notes=transfer.notes,
                created_at=transfer.created_at,
                created_by=transfer.created_by,
                version=1
            )
            self._session.add(model)
        
        self._session.flush()
    
    def get_by_id(self, transfer_id: StockTransferId) -> Optional[StockTransfer]:
        """الحصول على تحويل بواسطة المعرف"""
        if not transfer_id:
            return None
        
        model = self._session.execute(
            select(StockTransferModel).where(
                StockTransferModel.id == str(transfer_id.value)
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self._to_domain(model)
    
    def get_by_entity(
        self,
        entity: EntityId,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StockTransfer]:
        """الحصول على تحويلات كيان معين"""
        if not entity:
            return []
        
        query = select(StockTransferModel).where(
            StockTransferModel.entity_type == entity.entity_type,
            StockTransferModel.entity_id == entity.entity_id
        )
        
        if status:
            query = query.where(StockTransferModel.status == status)
        
        models = self._session.execute(
            query.order_by(desc(StockTransferModel.created_at))
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    def get_by_location(
        self,
        location: StockLocation,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[StockTransfer]:
        """الحصول على تحويلات موقع معين"""
        if not location:
            return []
        
        query = select(StockTransferModel).where(
            or_(
                StockTransferModel.from_location == str(location),
                StockTransferModel.to_location == str(location)
            )
        )
        
        if status:
            query = query.where(StockTransferModel.status == status)
        
        models = self._session.execute(
            query.order_by(desc(StockTransferModel.created_at))
            .limit(limit)
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    def get_pending_transfers(
        self,
        entity: Optional[EntityId] = None,
        limit: int = 100
    ) -> List[StockTransfer]:
        """الحصول على التحويلات المعلقة"""
        query = select(StockTransferModel).where(
            StockTransferModel.status.in_(["pending", "in_transit"])
        )
        
        if entity:
            query = query.where(
                StockTransferModel.entity_type == entity.entity_type,
                StockTransferModel.entity_id == entity.entity_id
            )
        
        models = self._session.execute(
            query.order_by(desc(StockTransferModel.created_at))
            .limit(limit)
        ).scalars().all()
        
        return [self._to_domain(m) for m in models]
    
    def update_status(
        self,
        transfer_id: StockTransferId,
        status: str,
        updated_by: str
    ) -> bool:
        """تحديث حالة التحويل"""
        if not transfer_id:
            return False
        
        result = self._session.execute(
            update(StockTransferModel)
            .where(StockTransferModel.id == str(transfer_id.value))
            .values(
                status=status,
                updated_at=datetime.now(timezone.utc),
                updated_by=updated_by
            )
        )
        
        self._session.flush()
        return result.rowcount > 0
    
    def delete(self, transfer_id: StockTransferId) -> bool:
        """حذف عملية تحويل"""
        if not transfer_id:
            return False
        
        model = self._session.execute(
            select(StockTransferModel).where(
                StockTransferModel.id == str(transfer_id.value)
            )
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        self._session.delete(model)
        self._session.flush()
        return True
    
    def _to_domain(self, model: StockTransferModel) -> StockTransfer:
        """تحويل Model إلى كيان Domain"""
        from core.domain.inventory.entities import StockTransfer
        
        entity = EntityId(model.entity_type, model.entity_id)
        
        return StockTransfer(
            id=StockTransferId(UUID(str(model.id))),
            entity=entity,
            quantity=Decimal(str(model.quantity)),
            unit_cost=InventoryMoney(
                amount=Decimal(str(model.unit_cost)),
                currency=model.currency or "USD"
            ),
            total_cost=InventoryMoney(
                amount=Decimal(str(model.total_cost or model.unit_cost * model.quantity)),
                currency=model.currency or "USD"
            ),
            from_location=StockLocation.from_string(model.from_location) if model.from_location else StockLocation(""),
            to_location=StockLocation.from_string(model.to_location) if model.to_location else StockLocation(""),
            reference_type=model.reference_type or "StockTransfer",
            reference_id=model.reference_id or "",
            batch_number=BatchNumber(model.batch_number) if model.batch_number else None,
            status=model.status or "pending",
            notes=model.notes or "",
            created_at=model.created_at or datetime.now(timezone.utc),
            created_by=model.created_by or "system",
            completed_at=model.completed_at,
            completed_by=model.completed_by,
            version=model.version or 1
        )


# استيراد timedelta للاستخدام في get_expiring_batches
from datetime import timedelta