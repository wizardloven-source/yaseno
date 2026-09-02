# core/infrastructure/db/postgres/center_repository.py

"""
Cost & Profit Centers PostgreSQL Repository - مستودع مراكز التكلفة والربح
✅ مصحح: إزالة استيراد dtos الخاطئ
✅ مصحح: استخدام المحولات من application layer
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import Session, selectinload

from core.domain.centers.entities import Center, CenterAllocation
from core.domain.centers.value_objects import (
    CenterId, CenterCode, CenterType, CenterStatus,
    CenterBudget, CenterHierarchy,
    AllocationRule, AllocationMethod, AllocationFrequency
)
from core.domain.centers.interfaces import (
    ICenterRepository,
    IAllocationRepository,
    IAllocationRuleRepository
)
from core.shared.exceptions import ConcurrentModificationError, NotFoundError

from ..models.center_model import (
    CenterModel,
    CenterAllocationModel,
    CenterAllocationRuleModel
)

# ✅ استيراد المحولات من application layer (وليس من infrastructure)
from core.application.centers.converters import (
    center_to_dto,
    center_to_node_dto,
    center_to_dict,
    allocation_to_dto,
    allocation_rule_to_dto,
)


# =============================================================================
# دوال التحويل الداخلية (Domain <-> Model)
# =============================================================================

def _model_to_domain_center(model: CenterModel) -> Center:
    """تحويل نموذج ORM إلى كيان Domain - Center"""
    if not model:
        return None
    
    # تحويل CenterBudget
    budget = None
    if model.budget_total > 0:
        budget = CenterBudget(
            total_budget=model.budget_total,
            used_amount=model.budget_used,
            currency=model.budget_currency
        )
    
    # تحويل CenterType
    center_type_map = {
        'cost': CenterType.COST,
        'profit': CenterType.PROFIT,
        'both': CenterType.BOTH,
    }
    center_type = center_type_map.get(model.center_type, CenterType.COST)
    
    # تحويل CenterStatus
    status_map = {
        'draft': CenterStatus.DRAFT,
        'active': CenterStatus.ACTIVE,
        'suspended': CenterStatus.SUSPENDED,
        'closed': CenterStatus.CLOSED,
        'archived': CenterStatus.ARCHIVED,
    }
    status = status_map.get(model.status, CenterStatus.DRAFT)
    
    center = Center(
        id=CenterId(model.id),
        code=CenterCode(model.code),
        name=model.name,
        center_type=center_type,
        status=status,
        parent_code=model.parent_code,
        level=model.level,
        path=model.path,
        manager_id=model.manager_id,
        manager_name=model.manager_name,
        department=model.department,
        budget=budget,
        description=model.description,
        notes=model.notes,
        tags=model.tags or [],
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version,
    )
    
    return center


def _domain_to_model_center(center: Center) -> CenterModel:
    """تحويل كيان Domain إلى نموذج ORM - Center"""
    return CenterModel(
        id=center.id.value,
        code=center.code.value,
        name=center.name,
        center_type=center.center_type.value,
        status=center.status.value,
        parent_code=center.parent_code,
        level=center.level,
        path=center.path,
        manager_id=center.manager_id,
        manager_name=center.manager_name,
        department=center.department,
        budget_total=center.budget.total_budget if center.budget else Decimal('0'),
        budget_used=center.budget.used_amount if center.budget else Decimal('0'),
        budget_currency=center.budget.currency if center.budget else "USD",
        description=center.description,
        notes=center.notes,
        tags=center.tags,
        created_at=center.created_at,
        created_by=center.created_by,
        updated_at=center.updated_at,
        updated_by=center.updated_by,
        version=center.version,
    )


def _allocation_model_to_domain(model: CenterAllocationModel) -> CenterAllocation:
    """تحويل نموذج ORM إلى كيان Domain - Allocation"""
    if not model:
        return None
    
    return CenterAllocation(
        id=str(model.id),
        source_center_code=model.source_center_code,
        period_start=model.period_start,
        period_end=model.period_end,
        total_amount=model.total_amount,
        allocations={k: (Decimal(str(v)) if isinstance(v, str) else v) for k, v in (model.allocations or {}).items()},
        status=model.status,
        journal_entry_id=model.journal_entry_id,
        description=model.description,
        created_at=model.created_at,
        created_by=model.created_by,
        posted_at=model.posted_at,
        posted_by=model.posted_by,
    )


def _domain_to_allocation_model(allocation: CenterAllocation) -> CenterAllocationModel:
    """تحويل كيان Domain إلى نموذج ORM - Allocation"""
    return CenterAllocationModel(
        id=UUID(allocation.id),
        source_center_code=allocation.source_center_code,
        total_amount=allocation.total_amount,
        allocations={k: (str(v) if isinstance(v, Decimal) else v) for k, v in (allocation.allocations or {}).items()},
        period_start=allocation.period_start,
        period_end=allocation.period_end,
        status=allocation.status,
        journal_entry_id=allocation.journal_entry_id,
        description=allocation.description,
        created_at=allocation.created_at,
        created_by=allocation.created_by,
        posted_at=allocation.posted_at,
        posted_by=allocation.posted_by,
    )


def _rule_model_to_domain(model: CenterAllocationRuleModel) -> AllocationRule:
    """تحويل نموذج ORM إلى كيان Domain - AllocationRule"""
    if not model:
        return None
    
    method_map = {
        'percentage': AllocationMethod.PERCENTAGE,
        'fixed_amount': AllocationMethod.FIXED_AMOUNT,
        'manual': AllocationMethod.MANUAL,
        'equal': AllocationMethod.EQUAL,
        'weighted': AllocationMethod.WEIGHTED,
        'activity_based': AllocationMethod.ACTIVITY_BASED,
    }
    
    frequency_map = {
        'daily': AllocationFrequency.DAILY,
        'weekly': AllocationFrequency.WEEKLY,
        'monthly': AllocationFrequency.MONTHLY,
        'quarterly': AllocationFrequency.QUARTERLY,
        'yearly': AllocationFrequency.YEARLY,
        'one_time': AllocationFrequency.ONE_TIME,
    }
    
    return AllocationRule(
        id=str(model.id),
        name=model.name,
        source_center_code=model.source_center_code,
        target_center_codes=model.target_center_codes or [],
        method=method_map.get(model.method, AllocationMethod.EQUAL),
        percentage=model.percentage,
        fixed_amount=model.fixed_amount,
        weights=model.weights,
        frequency=frequency_map.get(model.frequency, AllocationFrequency.MONTHLY),
        valid_from=model.valid_from,
        valid_to=model.valid_to,
        description=model.description,
    )


def _domain_to_rule_model(rule: AllocationRule) -> CenterAllocationRuleModel:
    """تحويل كيان Domain إلى نموذج ORM - AllocationRule"""
    return CenterAllocationRuleModel(
        id=UUID(rule.id),
        name=rule.name,
        source_center_code=rule.source_center_code,
        target_center_codes=rule.target_center_codes,
        method=rule.method.value,
        percentage=rule.percentage,
        fixed_amount=rule.fixed_amount,
        weights=rule.weights,
        frequency=rule.frequency.value,
        is_active=rule.is_active,
        valid_from=rule.valid_from,
        valid_to=rule.valid_to,
        description=rule.description,
    )


# =============================================================================
# PostgresCenterRepository - مستودع المراكز
# =============================================================================

class PostgresCenterRepository(ICenterRepository):
    """تطبيق PostgreSQL لمستودع مراكز التكلفة والربح"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, center: Center) -> None:
        """حفظ المركز (جديد أو محدث)"""
        existing = self._session.execute(
            select(CenterModel).where(CenterModel.id == center.id.value)
        ).scalar_one_or_none()
        
        if existing:
            self._update_existing_center(existing, center)
        else:
            self._create_new_center(center)
    
    def _update_existing_center(self, existing: CenterModel, center: Center) -> None:
        """تحديث مركز موجود مع Optimistic Locking"""
        # نسخة الكيان قد تكون مساوية لنسخة قاعدة البيانات (تعديل مباشر)
        # أو أكبر بواحد إذا زادها أسلوب دومين (تحديث عبر طريقة كائنية)
        if existing.version != center.version and existing.version != center.version - 1:
            raise ConcurrentModificationError(
                "Center",
                str(center.id),
                center.version,
                existing.version
            )
        expected_version = existing.version
        new_version = existing.version + 1
        
        result = self._session.execute(
            update(CenterModel)
            .where(
                CenterModel.id == center.id.value,
                CenterModel.version == expected_version
            )
            .values(
                code=center.code.value,
                name=center.name,
                center_type=center.center_type.value,
                status=center.status.value,
                parent_code=center.parent_code,
                level=center.level,
                path=center.path,
                manager_id=center.manager_id,
                manager_name=center.manager_name,
                department=center.department,
                budget_total=center.budget.total_budget if center.budget else Decimal('0'),
                budget_used=center.budget.used_amount if center.budget else Decimal('0'),
                budget_currency=center.budget.currency if center.budget else "USD",
                description=center.description,
                notes=center.notes,
                tags=center.tags,
                updated_at=datetime.now(),
                updated_by=center.updated_by,
                version=new_version,
            )
        )
        
        if result.rowcount == 0:
            raise ConcurrentModificationError(
                "Center",
                str(center.id),
                center.version,
                existing.version
            )
        
        center.version = new_version
    
    def _create_new_center(self, center: Center) -> None:
        """إنشاء مركز جديد"""
        model = _domain_to_model_center(center)
        self._session.add(model)
        self._session.flush()
        center.version = 1
    
    def get_by_id(self, center_id: CenterId) -> Optional[Center]:
        """الحصول على مركز بواسطة المعرف"""
        model = self._session.execute(
            select(CenterModel).where(CenterModel.id == center_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain_center(model)
    
    def get_by_code(self, code: CenterCode) -> Optional[Center]:
        """الحصول على مركز بواسطة الكود"""
        model = self._session.execute(
            select(CenterModel).where(CenterModel.code == code.value)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain_center(model)
    
    def get_by_path(self, path: str) -> Optional[Center]:
        """الحصول على مركز بواسطة المسار"""
        model = self._session.execute(
            select(CenterModel).where(CenterModel.path == path)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain_center(model)
    
    def list_all(
        self,
        center_type: Optional[CenterType] = None,
        status: Optional[CenterStatus] = None,
        parent_code: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Center]:
        """قائمة المراكز مع خيارات التصفية"""
        query = select(CenterModel)
        
        if center_type:
            query = query.where(CenterModel.center_type == center_type.value)
        
        if status:
            query = query.where(CenterModel.status == status.value)
        
        if parent_code is not None:
            if parent_code:
                query = query.where(CenterModel.parent_code == parent_code)
            else:
                query = query.where(CenterModel.parent_code.is_(None))
        
        if not include_inactive:
            query = query.where(CenterModel.status != CenterStatus.CLOSED.value)
            query = query.where(CenterModel.status != CenterStatus.ARCHIVED.value)
        
        models = self._session.execute(
            query.order_by(CenterModel.code)
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [_model_to_domain_center(m) for m in models]
    
    def get_children(self, parent_code: str) -> List[Center]:
        """الحصول على المراكز الفرعية"""
        models = self._session.execute(
            select(CenterModel)
            .where(CenterModel.parent_code == parent_code)
            .order_by(CenterModel.code)
        ).scalars().all()
        
        return [_model_to_domain_center(m) for m in models]
    
    def get_tree(self, root_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """الحصول على الشجرة الهرمية للمراكز"""
        # هذه دالة مساعدة تستخدم المحولات من application layer
        # ولكنها تعيد قاموسات متداخلة
        
        if root_code:
            root = self.get_by_code(CenterCode(root_code))
            if not root:
                return []
            return [self._build_tree_node(root)]
        else:
            # جلب جميع المراكز الجذرية (بدون أب)
            roots = self._session.execute(
                select(CenterModel)
                .where(CenterModel.parent_code.is_(None))
                .order_by(CenterModel.code)
            ).scalars().all()
            
            return [self._build_tree_node(_model_to_domain_center(r)) for r in roots]
    
    def _build_tree_node(self, center: Center) -> Dict[str, Any]:
        """بناء عقدة شجرة بشكل متكرر"""
        children = self.get_children(center.code.value)
        
        return {
            'id': str(center.id),
            'code': center.code.value,
            'name': center.name,
            'type': center.center_type.value,
            'status': center.status.value,
            'level': center.level,
            'budget': {
                'total': float(center.budget.total_budget) if center.budget else 0,
                'used': float(center.budget.used_amount) if center.budget else 0,
                'currency': center.budget.currency if center.budget else 'USD',
            } if center.budget else None,
            'children': [self._build_tree_node(child) for child in children],
        }
    
    def get_center_with_children(self, code: str) -> Dict[str, Any]:
        """الحصول على مركز مع جميع فروعه"""
        center = self.get_by_code(CenterCode(code))
        if not center:
            return {}
        
        return self._build_tree_node(center)
    
    def search(self, search_text: str, limit: int = 50) -> List[Center]:
        """البحث عن المراكز"""
        search_term = f"%{search_text}%"
        models = self._session.execute(
            select(CenterModel)
            .where(
                or_(
                    CenterModel.code.ilike(search_term),
                    CenterModel.name.ilike(search_term),
                    CenterModel.description.ilike(search_term),
                )
            )
            .limit(limit)
        ).scalars().all()
        
        return [_model_to_domain_center(m) for m in models]
    
    def exists_by_code(self, code: CenterCode) -> bool:
        """التحقق من وجود مركز بالكود"""
        result = self._session.execute(
            select(CenterModel.id).where(CenterModel.code == code.value)
        ).first()
        
        return result is not None
    
    def delete(self, center_id: CenterId) -> bool:
        """حذف مركز"""
        result = self._session.execute(
            delete(CenterModel).where(CenterModel.id == center_id.value)
        )
        self._session.flush()
        return result.rowcount > 0
    
    def get_next_code(self, prefix: str = "C") -> str:
        """توليد كود تلقائي للمركز"""
        # البحث عن آخر كود
        result = self._session.execute(
            select(CenterModel.code)
            .where(CenterModel.code.startswith(prefix))
            .order_by(CenterModel.code.desc())
        ).first()
        
        if result:
            last_code = result[0]
            try:
                num = int(last_code[len(prefix):])
                next_num = num + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1
        
        return f"{prefix}{next_num:04d}"


# =============================================================================
# PostgresAllocationRepository - مستودع التوزيعات
# =============================================================================

class PostgresAllocationRepository(IAllocationRepository):
    """تطبيق PostgreSQL لمستودع توزيعات مراكز التكلفة"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, allocation: CenterAllocation) -> None:
        """حفظ توزيع (جديد أو محدث)"""
        existing = self._session.execute(
            select(CenterAllocationModel).where(CenterAllocationModel.id == UUID(allocation.id))
        ).scalar_one_or_none()
        
        if existing:
            # تحديث التوزيع
            self._session.execute(
                update(CenterAllocationModel)
                .where(CenterAllocationModel.id == UUID(allocation.id))
                .values(
                    source_center_code=allocation.source_center_code,
                    total_amount=allocation.total_amount,
                    allocations={k: (str(v) if isinstance(v, Decimal) else v) for k, v in (allocation.allocations or {}).items()},
                    period_start=allocation.period_start,
                    period_end=allocation.period_end,
                    status=allocation.status,
                    journal_entry_id=allocation.journal_entry_id,
                    description=allocation.description,
                    posted_at=allocation.posted_at,
                    posted_by=allocation.posted_by,
                )
            )
        else:
            # إنشاء توزيع جديد
            model = _domain_to_allocation_model(allocation)
            self._session.add(model)
        
        self._session.flush()
    
    def get_by_id(self, allocation_id: str) -> Optional[CenterAllocation]:
        """الحصول على توزيع بواسطة المعرف"""
        model = self._session.execute(
            select(CenterAllocationModel).where(CenterAllocationModel.id == UUID(allocation_id))
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _allocation_model_to_domain(model)
    
    def list_by_center(
        self,
        center_code: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CenterAllocation]:
        """قائمة توزيعات مركز معين"""
        query = select(CenterAllocationModel).where(
            or_(
                CenterAllocationModel.source_center_code == center_code,
                # البحث في allocations JSON
            )
        )
        
        if from_date:
            query = query.where(CenterAllocationModel.period_start >= from_date)
        if to_date:
            query = query.where(CenterAllocationModel.period_end <= to_date)
        
        models = self._session.execute(
            query.order_by(CenterAllocationModel.period_start.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [_allocation_model_to_domain(m) for m in models]
    
    def list_by_period(
        self,
        from_date: date,
        to_date: date,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CenterAllocation]:
        """قائمة التوزيعات في فترة زمنية"""
        query = select(CenterAllocationModel).where(
            CenterAllocationModel.period_start <= to_date,
            CenterAllocationModel.period_end >= from_date
        )
        
        if status:
            query = query.where(CenterAllocationModel.status == status)
        
        models = self._session.execute(
            query.order_by(CenterAllocationModel.period_start.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [_allocation_model_to_domain(m) for m in models]
    
    def get_total_allocated(
        self,
        center_code: str,
        from_date: date,
        to_date: date
    ) -> Decimal:
        """الحصول على إجمالي المبلغ الموزع على مركز"""
        # هذه دالة معقدة تحتاج إلى البحث في JSONB
        # تنفيذ مبسط
        result = self._session.execute(
            select(func.sum(CenterAllocationModel.total_amount))
            .where(
                CenterAllocationModel.source_center_code == center_code,
                CenterAllocationModel.status == 'posted',
                CenterAllocationModel.period_start >= from_date,
                CenterAllocationModel.period_end <= to_date,
            )
        ).scalar()
        
        return result or Decimal('0')
    
    def delete(self, allocation_id: str) -> bool:
        """حذف توزيع"""
        result = self._session.execute(
            delete(CenterAllocationModel).where(CenterAllocationModel.id == UUID(allocation_id))
        )
        self._session.flush()
        return result.rowcount > 0


# =============================================================================
# PostgresAllocationRuleRepository - مستودع قواعد التوزيع
# =============================================================================

class PostgresAllocationRuleRepository(IAllocationRuleRepository):
    """تطبيق PostgreSQL لمستودع قواعد توزيع مراكز التكلفة"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, rule: AllocationRule) -> None:
        """حفظ قاعدة توزيع (جديدة أو محدثة)"""
        existing = self._session.execute(
            select(CenterAllocationRuleModel).where(CenterAllocationRuleModel.id == UUID(rule.id))
        ).scalar_one_or_none()
        
        if existing:
            # تحديث القاعدة
            self._session.execute(
                update(CenterAllocationRuleModel)
                .where(CenterAllocationRuleModel.id == UUID(rule.id))
                .values(
                    name=rule.name,
                    source_center_code=rule.source_center_code,
                    target_center_codes=rule.target_center_codes,
                    method=rule.method.value,
                    percentage=rule.percentage,
                    fixed_amount=rule.fixed_amount,
                    weights=rule.weights,
                    frequency=rule.frequency.value,
                    is_active=rule.is_active,
                    valid_from=rule.valid_from,
                    valid_to=rule.valid_to,
                    description=rule.description,
                )
            )
        else:
            # إنشاء قاعدة جديدة
            model = _domain_to_rule_model(rule)
            self._session.add(model)
        
        self._session.flush()
    
    def get_by_id(self, rule_id: str) -> Optional[AllocationRule]:
        """الحصول على قاعدة توزيع بواسطة المعرف"""
        model = self._session.execute(
            select(CenterAllocationRuleModel).where(CenterAllocationRuleModel.id == UUID(rule_id))
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _rule_model_to_domain(model)
    
    def get_by_source_center(self, center_code: str) -> List[AllocationRule]:
        """الحصول على قواعد توزيع حسب المركز المصدر"""
        models = self._session.execute(
            select(CenterAllocationRuleModel)
            .where(CenterAllocationRuleModel.source_center_code == center_code)
            .order_by(CenterAllocationRuleModel.name)
        ).scalars().all()
        
        return [_rule_model_to_domain(m) for m in models]
    
    def get_by_target_center(self, center_code: str) -> List[AllocationRule]:
        """الحصول على قواعد توزيع حسب المركز المستهدف"""
        # البحث في JSONB array
        models = self._session.execute(
            select(CenterAllocationRuleModel)
            .where(
                # استخدام PostgreSQL JSONB containment
                CenterAllocationRuleModel.target_center_codes.contains([center_code])
            )
            .order_by(CenterAllocationRuleModel.name)
        ).scalars().all()
        
        return [_rule_model_to_domain(m) for m in models]
    
    def list_all(self, is_active: Optional[bool] = None) -> List[AllocationRule]:
        """قائمة جميع قواعد التوزيع"""
        query = select(CenterAllocationRuleModel)
        
        if is_active is not None:
            query = query.where(CenterAllocationRuleModel.is_active == is_active)
        
        models = self._session.execute(
            query.order_by(CenterAllocationRuleModel.name)
        ).scalars().all()
        
        return [_rule_model_to_domain(m) for m in models]
    
    def delete(self, rule_id: str) -> bool:
        """حذف قاعدة توزيع"""
        result = self._session.execute(
            delete(CenterAllocationRuleModel).where(CenterAllocationRuleModel.id == UUID(rule_id))
        )
        self._session.flush()
        return result.rowcount > 0


__all__ = [
    "PostgresCenterRepository",
    "PostgresAllocationRepository",
    "PostgresAllocationRuleRepository",
]