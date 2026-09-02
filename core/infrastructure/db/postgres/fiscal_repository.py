# core/infrastructure/db/postgres/fiscal_repository.py
"""
Fiscal Year Repository - مستودع السنة المالية
✅ محدث: استخدام Clock Service للوقت
✅ محدث: دعم الفترات المالية المتقدمة
✅ محدث: إضافة حقل name للفترات المالية
"""

from typing import Optional, List
from datetime import date
from uuid import UUID

from sqlalchemy import select, update, and_, or_, func, delete, desc, text
from sqlalchemy.orm import Session, selectinload

from core.domain.shared.clock import get_clock
from core.domain.fiscal.entities import FiscalYear, FiscalPeriod
from core.domain.fiscal.value_objects import (
    FiscalYearId, FiscalYearCode, FiscalYearStatus,
    FiscalPeriodId, FiscalPeriodType, FiscalPeriodReference
)
from core.domain.fiscal.interfaces import IFiscalYearRepository, IFiscalPeriodRepository
from core.shared.exceptions import ConcurrentModificationError

# ✅ استيراد النماذج من الموقع الصحيح (account_model)
from ..models.account_model import FiscalYearModel, FiscalPeriodModel


# =============================================================================
# دوال التحويل المحسنة
# =============================================================================

def _model_to_domain_year(model: FiscalYearModel) -> FiscalYear:
    """
    تحويل ORM Model إلى Domain Entity - FiscalYear
    
    ✅ محدث: استخدام Clock Service للوقت
    """
    if not model:
        return None
    
    # تحديد الحالة
    status_map = {
        'draft': FiscalYearStatus.DRAFT,
        'open': FiscalYearStatus.OPEN,
        'closing': FiscalYearStatus.CLOSING,
        'closed': FiscalYearStatus.CLOSED,
        'archived': FiscalYearStatus.ARCHIVED,
    }
    status = status_map.get(model.status, FiscalYearStatus.DRAFT)
    
    # تحويل الفترات
    periods = []
    for p in model.periods:
        period_type = {
            'month': FiscalPeriodType.MONTH,
            'quarter': FiscalPeriodType.QUARTER,
            'adjustment': FiscalPeriodType.ADJUSTMENT,
        }.get(p.period_type, FiscalPeriodType.MONTH)
        
        period = FiscalPeriod(
            id=FiscalPeriodId(str(p.id)),
            reference=FiscalPeriodReference(p.year, p.period_number),
            name=p.name or "",
            start_date=p.start_date,
            end_date=p.end_date,
            period_type=period_type,
            is_closed=p.is_closed,
            closed_at=p.closed_at,
            closed_by=p.closed_by,
            fiscal_year_id=FiscalYearId(str(model.id)),
            is_adjustment=p.is_adjustment,
            adjustment_reason=p.adjustment_reason,
            version=p.version
        )
        periods.append(period)
    
    return FiscalYear(
        id=FiscalYearId(str(model.id)),
        code=FiscalYearCode(model.code),
        name=model.name,
        start_date=model.start_date,
        end_date=model.end_date,
        status=status,
        periods=periods,
        periods_per_year=model.periods_per_year,
        period_type=FiscalPeriodType(model.period_type),
        closed_at=model.closed_at,
        closed_by=model.closed_by,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )


def _domain_to_model_period(period: FiscalPeriod) -> dict:
    """تحويل Domain Period إلى قاموس للتحديث"""
    return {
        'name': period.name,
        'year': period.reference.year,
        'period_number': period.reference.period_number,
        'period_type': period.period_type.value,
        'start_date': period.start_date,
        'end_date': period.end_date,
        'is_closed': period.is_closed,
        'closed_at': period.closed_at,
        'closed_by': period.closed_by,
        'is_adjustment': period.is_adjustment,
        'adjustment_reason': period.adjustment_reason,
    }


# =============================================================================
# PostgresFiscalYearRepository - التنفيذ الكامل
# =============================================================================

class PostgresFiscalYearRepository(IFiscalYearRepository):
    """
    تطبيق PostgreSQL لمستودع السنة المالية
    
    ✅ محدث: استخدام Clock Service للوقت
    ✅ محدث: دعم الفهارس المحسنة
    ✅ محدث: دوال بحث إضافية
    """
    
    def __init__(self, session: Session):
        self._session = session

    # =========================================================================
    # العمليات الأساسية
    # =========================================================================

    def save(self, fiscal_year: FiscalYear) -> None:
        """حفظ السنة المالية مع Optimistic Locking"""
        existing = self._session.execute(
            select(FiscalYearModel)
            .options(selectinload(FiscalYearModel.periods))
            .where(FiscalYearModel.id == UUID(str(fiscal_year.id)))
        ).unique().scalar_one_or_none()

        if existing:
            self._update_existing_year(existing, fiscal_year)
        else:
            self._create_new_year(fiscal_year)

    def _update_existing_year(self, existing: FiscalYearModel, fiscal_year: FiscalYear) -> None:
        """تحديث سنة مالية موجودة"""
        clock = get_clock()
        now = clock.now()
        new_version = existing.version + 1

        # تحديث السنة المالية مع التحقق من الإصدار
        result = self._session.execute(
            update(FiscalYearModel)
            .where(
                FiscalYearModel.id == UUID(str(fiscal_year.id)),
                FiscalYearModel.version == fiscal_year.version
            )
            .values(
                code=str(fiscal_year.code),
                name=fiscal_year.name,
                start_date=fiscal_year.start_date,
                end_date=fiscal_year.end_date,
                status=fiscal_year.status.value,
                periods_per_year=fiscal_year.periods_per_year,
                period_type=fiscal_year.period_type.value,
                closed_at=fiscal_year.closed_at,
                closed_by=fiscal_year.closed_by,
                updated_at=now,
                updated_by=fiscal_year.updated_by,
                version=new_version
            )
        )

        if result.rowcount == 0:
            raise ConcurrentModificationError(
                "FiscalYear",
                str(fiscal_year.id),
                fiscal_year.version,
                existing.version
            )

        fiscal_year.version = new_version

        # تحديث الفترات
        self._sync_periods(existing, fiscal_year)

    def _create_new_year(self, fiscal_year: FiscalYear) -> None:
        """إنشاء سنة مالية جديدة"""
        model = FiscalYearModel(
            id=UUID(str(fiscal_year.id)),
            code=str(fiscal_year.code),
            name=fiscal_year.name,
            start_date=fiscal_year.start_date,
            end_date=fiscal_year.end_date,
            status=fiscal_year.status.value,
            periods_per_year=fiscal_year.periods_per_year,
            period_type=fiscal_year.period_type.value,
            closed_at=fiscal_year.closed_at,
            closed_by=fiscal_year.closed_by,
            created_by=fiscal_year.created_by,
            updated_by=fiscal_year.updated_by,
            version=1
        )
        self._session.add(model)
        self._session.flush()

        # إضافة الفترات
        for period in fiscal_year.periods:
            self._save_period(period, fiscal_year.id)

    def _sync_periods(self, existing: FiscalYearModel, fiscal_year: FiscalYear) -> None:
        """مزامنة الفترات (حذف + إضافة/تحديث)"""
        existing_period_ids = {str(p.id) for p in existing.periods}
        new_period_ids = {str(p.id) for p in fiscal_year.periods}

        # حذف الفترات المحذوفة
        for period_id in existing_period_ids - new_period_ids:
            self._session.execute(
                delete(FiscalPeriodModel).where(FiscalPeriodModel.id == UUID(period_id))
            )

        # تحديث أو إضافة الفترات
        for period in fiscal_year.periods:
            self._save_period(period, fiscal_year.id)

    def _save_period(self, period: FiscalPeriod, fiscal_year_id: FiscalYearId) -> None:
        """حفظ فترة مالية مع اسم"""
        existing = self._session.execute(
            select(FiscalPeriodModel).where(FiscalPeriodModel.id == UUID(str(period.id)))
        ).scalar_one_or_none()

        clock = get_clock()
        now = clock.now()

        if existing:
            # تحديث الفترة مع التحقق من الإصدار
            result = self._session.execute(
                update(FiscalPeriodModel)
                .where(
                    FiscalPeriodModel.id == UUID(str(period.id)),
                    FiscalPeriodModel.version == period.version
                )
                .values(
                    name=period.name,
                    year=period.reference.year,
                    period_number=period.reference.period_number,
                    period_type=period.period_type.value,
                    start_date=period.start_date,
                    end_date=period.end_date,
                    is_closed=period.is_closed,
                    closed_at=period.closed_at,
                    closed_by=period.closed_by,
                    is_adjustment=period.is_adjustment,
                    adjustment_reason=period.adjustment_reason,
                    version=existing.version + 1
                )
            )
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "FiscalPeriod",
                    str(period.id),
                    period.version,
                    existing.version
                )
            period.version = existing.version + 1
        else:
            # إنشاء فترة جديدة مع الاسم
            model = FiscalPeriodModel(
                id=UUID(str(period.id)),
                fiscal_year_id=UUID(str(fiscal_year_id)),
                name=period.name,
                year=period.reference.year,
                period_number=period.reference.period_number,
                period_type=period.period_type.value,
                start_date=period.start_date,
                end_date=period.end_date,
                is_closed=period.is_closed,
                closed_at=period.closed_at,
                closed_by=period.closed_by,
                is_adjustment=period.is_adjustment,
                adjustment_reason=period.adjustment_reason,
                version=1
            )
            self._session.add(model)
            period.version = 1

    # =========================================================================
    # دوال الاستعلام الأساسية
    # =========================================================================

    def get_by_id(self, fiscal_year_id: FiscalYearId) -> Optional[FiscalYear]:
        """الحصول على سنة مالية بواسطة المعرف"""
        model = self._session.execute(
            select(FiscalYearModel)
            .options(selectinload(FiscalYearModel.periods))
            .where(FiscalYearModel.id == UUID(str(fiscal_year_id)))
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        return _model_to_domain_year(model)

    def get_by_code(self, code: FiscalYearCode) -> Optional[FiscalYear]:
        """الحصول على سنة مالية بواسطة الكود"""
        model = self._session.execute(
            select(FiscalYearModel)
            .options(selectinload(FiscalYearModel.periods))
            .where(FiscalYearModel.code == str(code))
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        return _model_to_domain_year(model)

    def get_current(self) -> Optional[FiscalYear]:
        """الحصول على السنة المالية الحالية"""
        clock = get_clock()
        today = clock.today()
        
        model = self._session.execute(
            select(FiscalYearModel)
            .options(selectinload(FiscalYearModel.periods))
            .where(
                and_(
                    FiscalYearModel.start_date <= today,
                    FiscalYearModel.end_date >= today,
                    FiscalYearModel.status.in_(['open', 'draft'])
                )
            )
            .order_by(desc(FiscalYearModel.start_date))
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        return _model_to_domain_year(model)

    def get_current_open(self) -> Optional[FiscalYear]:
        """الحصول على السنة المالية المفتوحة الحالية"""
        clock = get_clock()
        today = clock.today()
        
        model = self._session.execute(
            select(FiscalYearModel)
            .options(selectinload(FiscalYearModel.periods))
            .where(
                and_(
                    FiscalYearModel.start_date <= today,
                    FiscalYearModel.end_date >= today,
                    FiscalYearModel.status == 'open'
                )
            )
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        return _model_to_domain_year(model)

    def get_all(
        self, 
        include_closed: bool = False, 
        include_archived: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[FiscalYear]:
        """الحصول على جميع السنوات المالية مع Pagination"""
        query = select(FiscalYearModel).options(selectinload(FiscalYearModel.periods))
        
        if not include_closed:
            query = query.where(FiscalYearModel.status != 'closed')
        if not include_archived:
            query = query.where(FiscalYearModel.status != 'archived')
        
        query = query.order_by(desc(FiscalYearModel.start_date))
        
        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)
        
        models = self._session.execute(query).unique().scalars().all()
        return [_model_to_domain_year(m) for m in models]

    def get_by_year(self, year: int) -> Optional[FiscalYear]:
        """الحصول على سنة مالية بواسطة السنة"""
        model = self._session.execute(
            select(FiscalYearModel)
            .options(selectinload(FiscalYearModel.periods))
            .where(
                and_(
                    FiscalYearModel.start_date >= date(year, 1, 1),
                    FiscalYearModel.end_date <= date(year, 12, 31)
                )
            )
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        return _model_to_domain_year(model)

    def get_by_date_range(
        self, 
        start_date: date, 
        end_date: date
    ) -> List[FiscalYear]:
        """الحصول على السنوات المالية في نطاق زمني"""
        models = self._session.execute(
            select(FiscalYearModel)
            .options(selectinload(FiscalYearModel.periods))
            .where(
                or_(
                    and_(
                        FiscalYearModel.start_date <= start_date,
                        FiscalYearModel.end_date >= start_date
                    ),
                    and_(
                        FiscalYearModel.start_date <= end_date,
                        FiscalYearModel.end_date >= end_date
                    ),
                    and_(
                        FiscalYearModel.start_date >= start_date,
                        FiscalYearModel.end_date <= end_date
                    )
                )
            )
            .order_by(desc(FiscalYearModel.start_date))
        ).unique().scalars().all()
        
        return [_model_to_domain_year(m) for m in models]

    def get_overlapping(
        self, 
        start_date: date, 
        end_date: date,
        exclude_id: Optional[FiscalYearId] = None
    ) -> Optional[FiscalYear]:
        """الحصول على سنة مالية متداخلة مع التواريخ المحددة"""
        query = select(FiscalYearModel).where(
            or_(
                and_(
                    FiscalYearModel.start_date <= start_date,
                    FiscalYearModel.end_date >= start_date
                ),
                and_(
                    FiscalYearModel.start_date <= end_date,
                    FiscalYearModel.end_date >= end_date
                ),
                and_(
                    FiscalYearModel.start_date >= start_date,
                    FiscalYearModel.end_date <= end_date
                )
            )
        )
        
        if exclude_id:
            query = query.where(FiscalYearModel.id != UUID(str(exclude_id)))
        
        model = query.limit(1).scalar_one_or_none()
        
        if not model:
            return None
        return _model_to_domain_year(model)

    # =========================================================================
    # دوال البحث عن الفترات
    # =========================================================================

    def get_period(
        self, 
        fiscal_year_id: FiscalYearId, 
        reference: FiscalPeriodReference
    ) -> Optional[FiscalPeriod]:
        """الحصول على فترة مالية محددة"""
        model = self._session.execute(
            select(FiscalPeriodModel)
            .where(
                and_(
                    FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id)),
                    FiscalPeriodModel.year == reference.year,
                    FiscalPeriodModel.period_number == reference.period_number
                )
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        period_type = {
            'month': FiscalPeriodType.MONTH,
            'quarter': FiscalPeriodType.QUARTER,
            'adjustment': FiscalPeriodType.ADJUSTMENT,
        }.get(model.period_type, FiscalPeriodType.MONTH)
        
        return FiscalPeriod(
            id=FiscalPeriodId(str(model.id)),
            reference=reference,
            name=model.name or "",
            start_date=model.start_date,
            end_date=model.end_date,
            period_type=period_type,
            is_closed=model.is_closed,
            closed_at=model.closed_at,
            closed_by=model.closed_by,
            fiscal_year_id=fiscal_year_id,
            is_adjustment=model.is_adjustment,
            adjustment_reason=model.adjustment_reason,
            version=model.version
        )

    def get_period_by_date(
        self, 
        fiscal_year_id: FiscalYearId, 
        dt: date
    ) -> Optional[FiscalPeriod]:
        """الحصول على الفترة التي تحتوي على تاريخ معين"""
        model = self._session.execute(
            select(FiscalPeriodModel)
            .where(
                and_(
                    FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id)),
                    FiscalPeriodModel.start_date <= dt,
                    FiscalPeriodModel.end_date >= dt
                )
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        period_type = {
            'month': FiscalPeriodType.MONTH,
            'quarter': FiscalPeriodType.QUARTER,
            'adjustment': FiscalPeriodType.ADJUSTMENT,
        }.get(model.period_type, FiscalPeriodType.MONTH)
        
        return FiscalPeriod(
            id=FiscalPeriodId(str(model.id)),
            reference=FiscalPeriodReference(model.year, model.period_number),
            name=model.name or "",
            start_date=model.start_date,
            end_date=model.end_date,
            period_type=period_type,
            is_closed=model.is_closed,
            closed_at=model.closed_at,
            closed_by=model.closed_by,
            fiscal_year_id=fiscal_year_id,
            is_adjustment=model.is_adjustment,
            adjustment_reason=model.adjustment_reason,
            version=model.version
        )

    def get_periods_by_year(self, year: int) -> List[FiscalPeriod]:
        """الحصول على جميع فترات سنة معينة"""
        models = self._session.execute(
            select(FiscalPeriodModel)
            .where(FiscalPeriodModel.year == year)
            .order_by(FiscalPeriodModel.period_number)
        ).scalars().all()
        
        periods = []
        for model in models:
            period_type = {
                'month': FiscalPeriodType.MONTH,
                'quarter': FiscalPeriodType.QUARTER,
                'adjustment': FiscalPeriodType.ADJUSTMENT,
            }.get(model.period_type, FiscalPeriodType.MONTH)
            
            periods.append(FiscalPeriod(
                id=FiscalPeriodId(str(model.id)),
                reference=FiscalPeriodReference(model.year, model.period_number),
                name=model.name or "",
                start_date=model.start_date,
                end_date=model.end_date,
                period_type=period_type,
                is_closed=model.is_closed,
                closed_at=model.closed_at,
                closed_by=model.closed_by,
                fiscal_year_id=FiscalYearId(str(model.fiscal_year_id)),
                is_adjustment=model.is_adjustment,
                adjustment_reason=model.adjustment_reason,
                version=model.version
            ))
        
        return periods

    def get_open_periods(self, fiscal_year_id: FiscalYearId) -> List[FiscalPeriod]:
        """الحصول على الفترات المفتوحة لسنة مالية"""
        models = self._session.execute(
            select(FiscalPeriodModel)
            .where(
                and_(
                    FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id)),
                    FiscalPeriodModel.is_closed == False
                )
            )
            .order_by(FiscalPeriodModel.period_number)
        ).scalars().all()
        
        periods = []
        for model in models:
            period_type = {
                'month': FiscalPeriodType.MONTH,
                'quarter': FiscalPeriodType.QUARTER,
                'adjustment': FiscalPeriodType.ADJUSTMENT,
            }.get(model.period_type, FiscalPeriodType.MONTH)
            
            periods.append(FiscalPeriod(
                id=FiscalPeriodId(str(model.id)),
                reference=FiscalPeriodReference(model.year, model.period_number),
                name=model.name or "",
                start_date=model.start_date,
                end_date=model.end_date,
                period_type=period_type,
                is_closed=model.is_closed,
                closed_at=model.closed_at,
                closed_by=model.closed_by,
                fiscal_year_id=fiscal_year_id,
                is_adjustment=model.is_adjustment,
                adjustment_reason=model.adjustment_reason,
                version=model.version
            ))
        
        return periods

    def get_closed_periods(self, fiscal_year_id: FiscalYearId) -> List[FiscalPeriod]:
        """الحصول على الفترات المغلقة لسنة مالية"""
        models = self._session.execute(
            select(FiscalPeriodModel)
            .where(
                and_(
                    FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id)),
                    FiscalPeriodModel.is_closed == True
                )
            )
            .order_by(FiscalPeriodModel.period_number)
        ).scalars().all()
        
        periods = []
        for model in models:
            period_type = {
                'month': FiscalPeriodType.MONTH,
                'quarter': FiscalPeriodType.QUARTER,
                'adjustment': FiscalPeriodType.ADJUSTMENT,
            }.get(model.period_type, FiscalPeriodType.MONTH)
            
            periods.append(FiscalPeriod(
                id=FiscalPeriodId(str(model.id)),
                reference=FiscalPeriodReference(model.year, model.period_number),
                name=model.name or "",
                start_date=model.start_date,
                end_date=model.end_date,
                period_type=period_type,
                is_closed=model.is_closed,
                closed_at=model.closed_at,
                closed_by=model.closed_by,
                fiscal_year_id=fiscal_year_id,
                is_adjustment=model.is_adjustment,
                adjustment_reason=model.adjustment_reason,
                version=model.version
            ))
        
        return periods

    # =========================================================================
    # دوال الإحصائيات
    # =========================================================================

    def count_years(self, include_closed: bool = False, include_archived: bool = False) -> int:
        """حساب عدد السنوات المالية"""
        query = select(func.count()).select_from(FiscalYearModel)
        
        if not include_closed:
            query = query.where(FiscalYearModel.status != 'closed')
        if not include_archived:
            query = query.where(FiscalYearModel.status != 'archived')
        
        result = self._session.execute(query).scalar()
        return result or 0

    def count_periods_by_year(self, year: int) -> int:
        """حساب عدد الفترات في سنة معينة"""
        result = self._session.execute(
            select(func.count()).select_from(FiscalPeriodModel)
            .where(FiscalPeriodModel.year == year)
        ).scalar()
        return result or 0

    def count_open_periods(self, fiscal_year_id: FiscalYearId) -> int:
        """حساب عدد الفترات المفتوحة"""
        result = self._session.execute(
            select(func.count()).select_from(FiscalPeriodModel)
            .where(
                and_(
                    FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id)),
                    FiscalPeriodModel.is_closed == False
                )
            )
        ).scalar()
        return result or 0

    def count_closed_periods(self, fiscal_year_id: FiscalYearId) -> int:
        """حساب عدد الفترات المغلقة"""
        result = self._session.execute(
            select(func.count()).select_from(FiscalPeriodModel)
            .where(
                and_(
                    FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id)),
                    FiscalPeriodModel.is_closed == True
                )
            )
        ).scalar()
        return result or 0

    # =========================================================================
    # عمليات إضافية
    # =========================================================================

    def delete(self, fiscal_year_id: FiscalYearId) -> bool:
        """حذف سنة مالية (فقط إذا كانت مسودة)"""
        model = self._session.execute(
            select(FiscalYearModel).where(FiscalYearModel.id == UUID(str(fiscal_year_id)))
        ).scalar_one_or_none()
        
        if not model or model.status != 'draft':
            return False
        
        # حذف الفترات المرتبطة أولاً
        self._session.execute(
            delete(FiscalPeriodModel).where(
                FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id))
            )
        )
        
        self._session.delete(model)
        return True

    def delete_period(self, period_id: str) -> bool:
        """حذف فترة مالية (فقط إذا كانت مفتوحة)"""
        model = self._session.execute(
            select(FiscalPeriodModel).where(FiscalPeriodModel.id == UUID(period_id))
        ).scalar_one_or_none()
        
        if not model or model.is_closed:
            return False
        
        self._session.delete(model)
        return True

    def close_all_periods(self, fiscal_year_id: FiscalYearId, closed_by: str) -> int:
        """إغلاق جميع الفترات المفتوحة دفعة واحدة"""
        clock = get_clock()
        now = clock.now()
        
        result = self._session.execute(
            update(FiscalPeriodModel)
            .where(
                and_(
                    FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id)),
                    FiscalPeriodModel.is_closed == False
                )
            )
            .values(
                is_closed=True,
                closed_at=now,
                closed_by=closed_by,
                version=FiscalPeriodModel.version + 1
            )
        )
        
        return result.rowcount

    def open_all_periods(self, fiscal_year_id: FiscalYearId, opened_by: str) -> int:
        """فتح جميع الفترات المغلقة دفعة واحدة (للمسؤولين فقط)"""
        result = self._session.execute(
            update(FiscalPeriodModel)
            .where(
                and_(
                    FiscalPeriodModel.fiscal_year_id == UUID(str(fiscal_year_id)),
                    FiscalPeriodModel.is_closed == True
                )
            )
            .values(
                is_closed=False,
                closed_at=None,
                closed_by=None,
                version=FiscalPeriodModel.version + 1
            )
        )
        
        return result.rowcount


# =============================================================================
# PostgresFiscalPeriodRepository - مستودع الفترات المنفصل
# =============================================================================

class PostgresFiscalPeriodRepository(IFiscalPeriodRepository):
    """
    تطبيق PostgreSQL لمستودع الفترات المالية
    
    ✅ محدث: دوال إضافية للبحث
    ✅ محدث: دعم حقل name
    """
    
    def __init__(self, session: Session):
        self._session = session

    def save(self, period: FiscalPeriod) -> None:
        """حفظ فترة مالية مع اسم"""
        existing = self._session.execute(
            select(FiscalPeriodModel).where(FiscalPeriodModel.id == UUID(str(period.id)))
        ).scalar_one_or_none()

        if existing:
            result = self._session.execute(
                text("UPDATE fiscal_periods SET name=:name, year=:yr, period_number=:pn, period_type=:pt, start_date=:sd, end_date=:ed, is_closed=:ic, closed_at=:ca, closed_by=:cb, is_adjustment=:ia, adjustment_reason=:ar, version=version+1 WHERE id=:id AND version=:ver"),
                {"name": period.name, "yr": period.reference.year, "pn": period.reference.period_number,
                 "pt": period.period_type.value, "sd": period.start_date, "ed": period.end_date,
                 "ic": period.is_closed, "ca": period.closed_at, "cb": period.closed_by,
                 "ia": period.is_adjustment, "ar": period.adjustment_reason,
                 "id": UUID(str(period.id)), "ver": period.version}
            )
            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "FiscalPeriod",
                    str(period.id),
                    period.version,
                    existing.version
                )
            period.version = existing.version + 1
        else:
            model = FiscalPeriodModel(
                id=UUID(str(period.id)),
                fiscal_year_id=UUID(str(period.fiscal_year_id)),
                name=period.name,
                year=period.reference.year,
                period_number=period.reference.period_number,
                period_type=period.period_type.value,
                start_date=period.start_date,
                end_date=period.end_date,
                is_closed=period.is_closed,
                closed_at=period.closed_at,
                closed_by=period.closed_by,
                is_adjustment=period.is_adjustment,
                adjustment_reason=period.adjustment_reason,
                version=1
            )
            self._session.add(model)
            period.version = 1

    def get_by_id(self, period_id: str) -> Optional[FiscalPeriod]:
        """الحصول على فترة مالية بواسطة المعرف"""
        model = self._session.execute(
            select(FiscalPeriodModel).where(FiscalPeriodModel.id == UUID(period_id))
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        period_type = {
            'month': FiscalPeriodType.MONTH,
            'quarter': FiscalPeriodType.QUARTER,
            'adjustment': FiscalPeriodType.ADJUSTMENT,
        }.get(model.period_type, FiscalPeriodType.MONTH)
        
        return FiscalPeriod(
            id=FiscalPeriodId(str(model.id)),
            reference=FiscalPeriodReference(model.year, model.period_number),
            name=model.name or "",
            start_date=model.start_date,
            end_date=model.end_date,
            period_type=period_type,
            is_closed=model.is_closed,
            closed_at=model.closed_at,
            closed_by=model.closed_by,
            fiscal_year_id=FiscalYearId(str(model.fiscal_year_id)),
            is_adjustment=model.is_adjustment,
            adjustment_reason=model.adjustment_reason,
            version=model.version
        )

    def get_by_reference(self, reference: FiscalPeriodReference) -> Optional[FiscalPeriod]:
        """الحصول على فترة مالية بواسطة المرجع"""
        model = self._session.execute(
            select(FiscalPeriodModel).where(
                and_(
                    FiscalPeriodModel.year == reference.year,
                    FiscalPeriodModel.period_number == reference.period_number
                )
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self.get_by_id(str(model.id))

    def get_by_date(self, dt: date) -> Optional[FiscalPeriod]:
        """الحصول على الفترة المالية التي تحتوي على تاريخ معين"""
        model = self._session.execute(
            select(FiscalPeriodModel).where(
                and_(
                    FiscalPeriodModel.start_date <= dt,
                    FiscalPeriodModel.end_date >= dt
                )
            )
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self.get_by_id(str(model.id))

    def get_period_by_date(self, dt: date) -> Optional[FiscalPeriod]:
        """توافق مع واجهة IFiscalPeriodRepository - الحصول على فترة بتاريخ معين"""
        return self.get_by_date(dt)
    
    def get_period_by_name(self, name) -> Optional[FiscalPeriod]:
        """Get fiscal period by PeriodReference (year+month/year+quarter)."""
        year_val = getattr(name, 'get_year', lambda: None)() or getattr(name, 'year', None)
        month_val = getattr(name, 'get_month', lambda: None)() or getattr(name, 'period_number', None) or getattr(name, 'month', None)
        if year_val is None or month_val is None:
            return None
        model = self._session.execute(
            select(FiscalPeriodModel).where(
                FiscalPeriodModel.year == year_val,
                FiscalPeriodModel.period_number == month_val
            )
        ).scalar_one_or_none()
        if not model:
            return None
        return self.get_by_id(str(model.id))
    
    def get_by_year(self, year: int) -> List[FiscalPeriod]:
        """الحصول على جميع فترات سنة معينة"""
        models = self._session.execute(
            select(FiscalPeriodModel)
            .where(FiscalPeriodModel.year == year)
            .order_by(FiscalPeriodModel.period_number)
        ).scalars().all()
        
        return [self.get_by_id(str(m.id)) for m in models if m]

    def get_open_periods(self, fiscal_year_id: Optional[str] = None) -> List[FiscalPeriod]:
        """الحصول على الفترات المفتوحة"""
        query = select(FiscalPeriodModel).where(FiscalPeriodModel.is_closed == False)
        
        if fiscal_year_id:
            query = query.where(FiscalPeriodModel.fiscal_year_id == UUID(fiscal_year_id))
        
        models = self._session.execute(
            query.order_by(FiscalPeriodModel.year, FiscalPeriodModel.period_number)
        ).scalars().all()
        
        return [self.get_by_id(str(m.id)) for m in models if m]

    def get_closed_periods(self, fiscal_year_id: Optional[str] = None) -> List[FiscalPeriod]:
        """الحصول على الفترات المغلقة"""
        query = select(FiscalPeriodModel).where(FiscalPeriodModel.is_closed == True)
        
        if fiscal_year_id:
            query = query.where(FiscalPeriodModel.fiscal_year_id == UUID(fiscal_year_id))
        
        models = self._session.execute(
            query.order_by(FiscalPeriodModel.year, FiscalPeriodModel.period_number)
        ).scalars().all()
        
        return [self.get_by_id(str(m.id)) for m in models if m]

    def delete(self, period_id: str) -> bool:
        """حذف فترة مالية (فقط إذا كانت مفتوحة)"""
        model = self._session.execute(
            select(FiscalPeriodModel).where(FiscalPeriodModel.id == UUID(period_id))
        ).scalar_one_or_none()
        
        if not model or model.is_closed:
            return False
        
        self._session.delete(model)
        return True


# =============================================================================
# تصدير الكلاسات
# =============================================================================

__all__ = [
    "PostgresFiscalYearRepository",
    "PostgresFiscalPeriodRepository",
]