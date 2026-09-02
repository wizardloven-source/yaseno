# core/infrastructure/db/postgres/repositories_payment.py
"""
PostgreSQL Repository for Payments - مستودع الدفعات
✅ محدث: استخدام Clock Service للوقت
✅ محدث: تحسين Optimistic Locking
✅ محدث: دعم Pagination المتقدم
✅ محدث: دوال إحصائيات محسنة
✅ محدث: إضافة PostgresPaymentLineRepository
✅ محدث: إضافة PostgresPaymentAllocationRepository
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
import random

from sqlalchemy import select, func, and_, or_, update, desc, asc, delete
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

# ✅ استيراد Clock Service
from core.domain.shared.clock import get_clock, utc_now, to_utc
from core.domain.payments.entities import Payment, PaymentLine
from core.domain.payments.value_objects import (
    PaymentId,
    PaymentCode,
    PaymentType,
    PaymentMethod,
    PaymentStatus,
    PaymentReference,
    Money,
)
from core.domain.payments.interfaces import IPaymentRepository
from core.domain.payments.exceptions import PaymentNotFoundError
from core.shared.exceptions import ConcurrentModificationError, NotFoundError, ValidationError

from ..models.payment_model import PaymentModel, PaymentLineModel


# =============================================================================
# دوال مساعدة للتحويل الآمن
# =============================================================================

def _to_decimal(value: Any) -> Decimal:
    """تحويل آمن إلى Decimal"""
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.replace(',', ''))
        except (ValueError, TypeError):
            return Decimal('0')
    if hasattr(value, 'amount'):
        return _to_decimal(value.amount)
    return Decimal('0')


def _to_uuid(value: Any) -> UUID:
    """تحويل آمن إلى UUID"""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            pass
    if hasattr(value, 'value'):
        return _to_uuid(value.value)
    raise ValueError(f"Cannot convert {type(value).__name__} to UUID: {value}")


def _model_to_domain(model: PaymentModel) -> Payment:
    """تحويل ORM Model إلى Domain Entity"""
    if not model:
        return None

    # تحويل الحالة
    status_map = {
        "draft": PaymentStatus.DRAFT,
        "pending": PaymentStatus.PENDING,
        "approved": PaymentStatus.APPROVED,
        "completed": PaymentStatus.COMPLETED,
        "rejected": PaymentStatus.REJECTED,
        "cancelled": PaymentStatus.CANCELLED,
    }
    status = status_map.get(model.status, PaymentStatus.DRAFT)

    # تحويل النوع
    type_map = {
        "receive": PaymentType.RECEIVE,
        "pay": PaymentType.PAY,
        "transfer": PaymentType.TRANSFER,
    }
    payment_type = type_map.get(model.payment_type, PaymentType.RECEIVE)

    # تحويل طريقة الدفع
    method_map = {
        "cash": PaymentMethod.CASH,
        "check": PaymentMethod.CHECK,
        "transfer": PaymentMethod.TRANSFER,
        "credit": PaymentMethod.CREDIT,
        "card": PaymentMethod.CARD,
    }
    payment_method = method_map.get(model.payment_method, PaymentMethod.CASH)

    # إنشاء كائن الدفعة
    payment = Payment(
        id=PaymentId(model.id),
        code=PaymentCode(model.code),
        date=model.payment_date,
        payment_type=payment_type,
        payment_method=payment_method,
        amount=Money(_to_decimal(model.amount), model.currency),
        currency=model.currency,
        customer_id=model.customer_id,
        customer_name=model.customer_name,
        supplier_id=model.supplier_id,
        supplier_name=model.supplier_name,
        fund_id=model.fund_id,
        fund_code=model.fund_code,
        status=status,
        notes=model.notes or "",
        approved_by=model.approved_by,
        approved_at=model.approved_at,
        completed_by=model.completed_by,
        completed_at=model.completed_at,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version,
    )

    # إضافة المراجع
    if model.reference_type and model.reference_id:
        payment.reference = PaymentReference(
            reference_type=model.reference_type,
            reference_id=model.reference_id,
        )

    # إضافة الأسطر
    for line_model in model.lines:
        line = PaymentLine(
            line_id=str(line_model.id),
            reference_type=line_model.reference_type,
            reference_id=line_model.reference_id,
            amount=Money(_to_decimal(line_model.amount), line_model.currency),
            notes=line_model.notes or "",
        )
        payment.lines.append(line)

    return payment


def _domain_to_model(payment: Payment) -> PaymentModel:
    """تحويل Domain Entity إلى ORM Model"""
    return PaymentModel(
        id=payment.id.value,
        code=str(payment.code),
        payment_date=payment.date,
        payment_type=payment.payment_type.value,
        payment_method=payment.payment_method.value,
        amount=payment.amount.amount,
        currency=payment.currency,
        customer_id=payment.customer_id,
        customer_name=payment.customer_name,
        supplier_id=payment.supplier_id,
        supplier_name=payment.supplier_name,
        fund_id=payment.fund_id,
        fund_code=payment.fund_code,
        reference_type=payment.reference.reference_type if payment.reference else None,
        reference_id=payment.reference.reference_id if payment.reference else None,
        status=payment.status.value,
        notes=payment.notes,
        approved_by=payment.approved_by,
        approved_at=payment.approved_at,
        completed_by=payment.completed_by,
        completed_at=payment.completed_at,
        created_at=payment.created_at,
        created_by=payment.created_by,
        updated_at=payment.updated_at,
        updated_by=payment.updated_by,
        version=payment.version,
    )


# =============================================================================
# PostgresPaymentRepository - المستودع الرئيسي
# =============================================================================

class PostgresPaymentRepository(IPaymentRepository):
    """
    تطبيق PostgreSQL لمستودع الدفعات
    
    ✅ محدث: استخدام Clock Service للوقت
    ✅ محدث: Optimistic Locking محسن
    ✅ محدث: دوال إحصائيات متقدمة
    """

    def __init__(self, session: Session):
        self._session = session

    # =========================================================================
    # العمليات الأساسية مع Optimistic Locking
    # =========================================================================

    def save(self, payment: Payment) -> None:
        """حفظ الدفعة مع Optimistic Locking"""
        existing = self._session.execute(
            select(PaymentModel).where(PaymentModel.id == payment.id.value)
        ).scalar_one_or_none()

        if existing:
            self._update_existing_payment(existing, payment)
        else:
            self._create_new_payment(payment)

    def _update_existing_payment(self, existing: PaymentModel, payment: Payment) -> None:
        """تحديث دفعة موجودة مع Optimistic Locking"""
        clock = get_clock()
        now = clock.now()
        new_version = existing.version + 1

        # ✅ كيان الدفعة يزيد الإصدار تلقائياً قبل الحفظ، لذا نتحقق من النسخة السابقة
        expected_version = payment.version - 1

        result = self._session.execute(
            update(PaymentModel)
            .where(
                PaymentModel.id == payment.id.value,
                PaymentModel.version == expected_version  # ✅ شرط التحقق
            )
            .values(
                code=str(payment.code),
                payment_date=payment.date,
                payment_type=payment.payment_type.value,
                payment_method=payment.payment_method.value,
                amount=payment.amount.amount,
                currency=payment.currency,
                customer_id=payment.customer_id,
                customer_name=payment.customer_name,
                supplier_id=payment.supplier_id,
                supplier_name=payment.supplier_name,
                fund_id=payment.fund_id,
                fund_code=payment.fund_code,
                reference_type=payment.reference.reference_type if payment.reference else None,
                reference_id=payment.reference.reference_id if payment.reference else None,
                status=payment.status.value,
                notes=payment.notes,
                approved_by=payment.approved_by,
                approved_at=payment.approved_at,
                completed_by=payment.completed_by,
                completed_at=payment.completed_at,
                updated_at=now,
                updated_by=payment.updated_by,
                version=new_version,
            )
        )

        if result.rowcount == 0:
            raise ConcurrentModificationError(
                "Payment",
                str(payment.id),
                payment.version,
                existing.version
            )

        payment.version = new_version

        # مزامنة الأسطر
        self._sync_payment_lines(payment)

    def _create_new_payment(self, payment: Payment) -> None:
        """إنشاء دفعة جديدة"""
        # التأكد من وجود كود
        if not payment.code or str(payment.code) == "":
            payment.code = self.get_next_code()

        model = _domain_to_model(payment)
        self._session.add(model)
        self._session.flush()
        payment.version = 1

        # إضافة الأسطر
        self._sync_payment_lines(payment)

    def _sync_payment_lines(self, payment: Payment) -> None:
        """مزامنة أسطر الدفعة (حذف + إضافة)"""
        # حذف الأسطر القديمة
        self._session.execute(
            delete(PaymentLineModel).where(PaymentLineModel.payment_id == payment.id.value)
        )

        # إضافة الأسطر الجديدة
        for idx, line in enumerate(payment.lines):
            line_model = PaymentLineModel(
                payment_id=payment.id.value,
                reference_type=line.reference_type,
                reference_id=line.reference_id,
                amount=line.amount.amount,
                currency=line.amount.currency,
                notes=line.notes,
                line_order=idx,
            )
            self._session.add(line_model)

    # =========================================================================
    # دوال الاستعلام الأساسية
    # =========================================================================

    def get_by_id(self, payment_id: PaymentId) -> Optional[Payment]:
        """الحصول على دفعة بواسطة المعرف"""
        model = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(PaymentModel.id == payment_id.value)
        ).unique().scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain(model)

    def get_by_code(self, code: PaymentCode) -> Optional[Payment]:
        """الحصول على دفعة بواسطة الكود"""
        model = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(PaymentModel.code == str(code))
        ).unique().scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain(model)

    def get_by_reference(self, reference_type: str, reference_id: str) -> List[Payment]:
        """الحصول على دفعات بواسطة المرجع"""
        models = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(
                and_(
                    PaymentModel.reference_type == reference_type,
                    PaymentModel.reference_id == reference_id,
                )
            )
            .order_by(desc(PaymentModel.payment_date))
        ).unique().scalars().all()

        return [_model_to_domain(m) for m in models]

    def get_by_customer(self, customer_id: str) -> List[Payment]:
        """الحصول على جميع دفعات العميل"""
        return self.list_by_customer(customer_id, limit=1000)

    def get_by_supplier(self, supplier_id: str) -> List[Payment]:
        """الحصول على جميع دفعات المورد"""
        return self.list_by_supplier(supplier_id, limit=1000)

    def get_by_fund(self, fund_id: str) -> List[Payment]:
        """الحصول على دفعات صندوق معين"""
        models = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(PaymentModel.fund_id == fund_id)
            .order_by(desc(PaymentModel.payment_date))
        ).unique().scalars().all()

        return [_model_to_domain(m) for m in models]

    # =========================================================================
    # قوائم الدفعات مع Pagination
    # =========================================================================

    def list_by_customer(self, customer_id: str, limit: int = 100, offset: int = 0) -> List[Payment]:
        """قائمة دفعات العميل"""
        models = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(PaymentModel.customer_id == customer_id)
            .order_by(desc(PaymentModel.payment_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()

        return [_model_to_domain(m) for m in models]

    def list_by_supplier(self, supplier_id: str, limit: int = 100, offset: int = 0) -> List[Payment]:
        """قائمة دفعات المورد"""
        models = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(PaymentModel.supplier_id == supplier_id)
            .order_by(desc(PaymentModel.payment_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()

        return [_model_to_domain(m) for m in models]

    def list_by_type(self, payment_type: PaymentType, limit: int = 100, offset: int = 0) -> List[Payment]:
        """قائمة دفعات حسب النوع"""
        models = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(PaymentModel.payment_type == payment_type.value)
            .order_by(desc(PaymentModel.payment_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()

        return [_model_to_domain(m) for m in models]

    def list_by_status(self, status: PaymentStatus, limit: int = 100, offset: int = 0) -> List[Payment]:
        """قائمة دفعات حسب الحالة"""
        models = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(PaymentModel.status == status.value)
            .order_by(desc(PaymentModel.payment_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()

        return [_model_to_domain(m) for m in models]

    def list_by_method(self, method: PaymentMethod, limit: int = 100, offset: int = 0) -> List[Payment]:
        """قائمة دفعات حسب طريقة الدفع"""
        models = self._session.execute(
            select(PaymentModel)
            .options(selectinload(PaymentModel.lines))
            .where(PaymentModel.payment_method == method.value)
            .order_by(desc(PaymentModel.payment_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()

        return [_model_to_domain(m) for m in models]

    def list_by_date_range(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        payment_type: Optional[PaymentType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Payment]:
        """قائمة دفعات في نطاق زمني"""
        query = select(PaymentModel).options(selectinload(PaymentModel.lines))
        
        if from_date:
            query = query.where(PaymentModel.payment_date >= from_date)
        
        if to_date:
            query = query.where(PaymentModel.payment_date <= to_date)

        if payment_type:
            query = query.where(PaymentModel.payment_type == payment_type.value)

        models = self._session.execute(
            query.order_by(desc(PaymentModel.payment_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()

        return [_model_to_domain(m) for m in models]

    def list_by_filters(self, filters: Dict[str, Any]) -> List[Payment]:
        """قائمة الدفعات حسب الفلاتر المتقدمة"""
        query = select(PaymentModel).options(selectinload(PaymentModel.lines))
        
        if filters.get('payment_type'):
            query = query.where(PaymentModel.payment_type == filters['payment_type'])
        
        if filters.get('status'):
            query = query.where(PaymentModel.status == filters['status'])
        
        if filters.get('customer_id'):
            query = query.where(PaymentModel.customer_id == filters['customer_id'])
        
        if filters.get('supplier_id'):
            query = query.where(PaymentModel.supplier_id == filters['supplier_id'])
        
        if filters.get('fund_id'):
            query = query.where(PaymentModel.fund_id == filters['fund_id'])
        
        if filters.get('payment_method'):
            query = query.where(PaymentModel.payment_method == filters['payment_method'])
        
        from_date = filters.get('from_date')
        if from_date:
            query = query.where(PaymentModel.payment_date >= from_date)
        
        to_date = filters.get('to_date')
        if to_date:
            query = query.where(PaymentModel.payment_date <= to_date)
        
        min_amount = filters.get('min_amount')
        if min_amount is not None:
            query = query.where(PaymentModel.amount >= min_amount)
        
        max_amount = filters.get('max_amount')
        if max_amount is not None:
            query = query.where(PaymentModel.amount <= max_amount)
        
        search = filters.get('search')
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    PaymentModel.code.ilike(search_term),
                    PaymentModel.customer_name.ilike(search_term),
                    PaymentModel.supplier_name.ilike(search_term),
                )
            )
        
        # تحديد الترتيب
        order_by_field = filters.get('order_by', 'created_at')
        order_map = {
            'date': PaymentModel.payment_date,
            'code': PaymentModel.code,
            'amount': PaymentModel.amount,
            'status': PaymentModel.status,
            'created_at': PaymentModel.created_at,
            'customer': PaymentModel.customer_name,
            'supplier': PaymentModel.supplier_name,
        }
        order_column = order_map.get(order_by_field, PaymentModel.created_at)
        
        if filters.get('order_desc', True):
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        if filters.get('limit'):
            query = query.limit(filters['limit'])
        
        if filters.get('offset'):
            query = query.offset(filters['offset'])
        
        models = self._session.execute(query).unique().scalars().all()
        return [_model_to_domain(m) for m in models]

    # =========================================================================
    # عمليات الترقيم
    # =========================================================================

    def get_next_code(self) -> PaymentCode:
        """الحصول على الكود التالي للدفعة"""
        clock = get_clock()
        date_str = clock.now().strftime("%Y%m%d")
        
        # رقم عشوائي 4 أرقام
        seq = str(random.randint(1, 9999)).zfill(4)
        
        # الكود: PAY-20240101-0001
        return PaymentCode(f"PAY-{date_str}-{seq}")

    def reserve_code(self, code: PaymentCode) -> bool:
        """حجز كود دفع مؤقتاً"""
        existing = self._session.execute(
            select(PaymentModel.id).where(PaymentModel.code == str(code))
        ).first()
        
        return existing is None

    def release_code(self, code: PaymentCode) -> bool:
        """إلغاء حجز كود دفع"""
        existing = self._session.execute(
            select(PaymentModel.id).where(PaymentModel.code == str(code))
        ).first()
        
        return existing is not None

    def exists_by_code(self, code: PaymentCode) -> bool:
        """التحقق من وجود دفعة بكود معين"""
        result = self._session.execute(
            select(PaymentModel.id).where(PaymentModel.code == str(code))
        ).first()
        
        return result is not None

    # =========================================================================
    # عمليات الحذف
    # =========================================================================

    def delete_draft(self, payment_id: PaymentId) -> bool:
        """حذف دفعة مسودة (Draft)"""
        model = self._session.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id.value)
        ).scalar_one_or_none()

        if not model:
            return False
        
        if model.status != "draft":
            return False

        # حذف الأسطر المرتبطة أولاً
        self._session.execute(
            delete(PaymentLineModel).where(PaymentLineModel.payment_id == payment_id.value)
        )

        # حذف الدفعة
        self._session.delete(model)
        return True

    def delete_payment(self, payment_id: PaymentId, permanent: bool = False) -> bool:
        """حذف دفعة (ناعم أو دائم)"""
        model = self._session.execute(
            select(PaymentModel).where(PaymentModel.id == payment_id.value)
        ).scalar_one_or_none()

        if not model:
            return False

        if permanent:
            if model.status != "draft":
                return False
            # حذف الأسطر المرتبطة
            self._session.execute(
                delete(PaymentLineModel).where(PaymentLineModel.payment_id == payment_id.value)
            )
            self._session.delete(model)
        else:
            # حذف ناعم - فقط تعطيل
            model.status = "cancelled"
            model.updated_at = get_clock().now()
            model.version += 1

        return True

    # =========================================================================
    # دوال الإحصائيات المتقدمة
    # =========================================================================

    def get_summary(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        currency: str = "USD",
    ) -> dict:
        """الحصول على ملخص الدفعات"""
        clock = get_clock()
        if not from_date:
            from_date = clock.today() - timedelta(days=30)
        if not to_date:
            to_date = clock.today()

        # إجمالي المقبوضات
        total_received = self._session.execute(
            select(func.sum(PaymentModel.amount))
            .where(
                and_(
                    PaymentModel.payment_type == "receive",
                    PaymentModel.status == "completed",
                    PaymentModel.currency == currency,
                    PaymentModel.payment_date >= from_date,
                    PaymentModel.payment_date <= to_date,
                )
            )
        ).scalar() or Decimal('0')

        # إجمالي المدفوعات
        total_paid = self._session.execute(
            select(func.sum(PaymentModel.amount))
            .where(
                and_(
                    PaymentModel.payment_type == "pay",
                    PaymentModel.status == "completed",
                    PaymentModel.currency == currency,
                    PaymentModel.payment_date >= from_date,
                    PaymentModel.payment_date <= to_date,
                )
            )
        ).scalar() or Decimal('0')

        # إحصائيات حسب الحالة
        pending_count = self._session.execute(
            select(func.count())
            .select_from(PaymentModel)
            .where(
                and_(
                    PaymentModel.status == "pending",
                    PaymentModel.payment_date >= from_date,
                    PaymentModel.payment_date <= to_date,
                )
            )
        ).scalar() or 0

        approved_count = self._session.execute(
            select(func.count())
            .select_from(PaymentModel)
            .where(
                and_(
                    PaymentModel.status == "approved",
                    PaymentModel.payment_date >= from_date,
                    PaymentModel.payment_date <= to_date,
                )
            )
        ).scalar() or 0

        completed_count = self._session.execute(
            select(func.count())
            .select_from(PaymentModel)
            .where(
                and_(
                    PaymentModel.status == "completed",
                    PaymentModel.payment_date >= from_date,
                    PaymentModel.payment_date <= to_date,
                )
            )
        ).scalar() or 0

        cancelled_count = self._session.execute(
            select(func.count())
            .select_from(PaymentModel)
            .where(
                and_(
                    PaymentModel.status == "cancelled",
                    PaymentModel.payment_date >= from_date,
                    PaymentModel.payment_date <= to_date,
                )
            )
        ).scalar() or 0

        total_count = self._session.execute(
            select(func.count())
            .select_from(PaymentModel)
            .where(
                and_(
                    PaymentModel.payment_date >= from_date,
                    PaymentModel.payment_date <= to_date,
                )
            )
        ).scalar() or 0

        # إحصائيات حسب طريقة الدفع
        by_method = {}
        for method in PaymentMethod:
            count = self._session.execute(
                select(func.count())
                .select_from(PaymentModel)
                .where(
                    and_(
                        PaymentModel.payment_method == method.value,
                        PaymentModel.payment_date >= from_date,
                        PaymentModel.payment_date <= to_date,
                    )
                )
            ).scalar() or 0
            if count > 0:
                by_method[method.value] = count

        # إحصائيات حسب العملة
        by_currency = {}
        currencies = ["USD", "LBP", "EUR", "GBP"]
        for curr in currencies:
            count = self._session.execute(
                select(func.count())
                .select_from(PaymentModel)
                .where(
                    and_(
                        PaymentModel.currency == curr,
                        PaymentModel.payment_date >= from_date,
                        PaymentModel.payment_date <= to_date,
                    )
                )
            ).scalar() or 0
            if count > 0:
                by_currency[curr] = count

        return {
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'currency': currency,
            'total_received': float(total_received),
            'total_paid': float(total_paid),
            'net_balance': float(total_received - total_paid),
            'pending_count': pending_count,
            'approved_count': approved_count,
            'completed_count': completed_count,
            'cancelled_count': cancelled_count,
            'total_count': total_count,
            'by_method': by_method,
            'by_currency': by_currency,
            'average_amount': float((total_received + total_paid) / total_count) if total_count > 0 else 0,
        }

    def get_customer_summary(self, customer_id: str) -> Dict[str, Any]:
        """الحصول على ملخص دفعات العميل"""
        payments = self.list_by_customer(customer_id)
        
        total_received = Decimal('0')
        total_paid = Decimal('0')
        pending_count = 0
        completed_count = 0
        
        for payment in payments:
            if payment.status == PaymentStatus.COMPLETED:
                if payment.payment_type == PaymentType.RECEIVE:
                    total_received += payment.amount.amount
                elif payment.payment_type == PaymentType.PAY:
                    total_paid += payment.amount.amount
            elif payment.status == PaymentStatus.PENDING:
                pending_count += 1
            elif payment.status == PaymentStatus.COMPLETED:
                completed_count += 1
        
        return {
            'customer_id': customer_id,
            'total_received': float(total_received),
            'total_paid': float(total_paid),
            'net_balance': float(total_received - total_paid),
            'pending_count': pending_count,
            'completed_count': completed_count,
            'total_count': len(payments),
            'currency': payments[0].currency if payments else "USD",
        }

    def get_supplier_summary(self, supplier_id: str) -> Dict[str, Any]:
        """الحصول على ملخص دفعات المورد"""
        payments = self.list_by_supplier(supplier_id)
        
        total_received = Decimal('0')
        total_paid = Decimal('0')
        pending_count = 0
        completed_count = 0
        
        for payment in payments:
            if payment.status == PaymentStatus.COMPLETED:
                if payment.payment_type == PaymentType.RECEIVE:
                    total_received += payment.amount.amount
                elif payment.payment_type == PaymentType.PAY:
                    total_paid += payment.amount.amount
            elif payment.status == PaymentStatus.PENDING:
                pending_count += 1
            elif payment.status == PaymentStatus.COMPLETED:
                completed_count += 1
        
        return {
            'supplier_id': supplier_id,
            'total_received': float(total_received),
            'total_paid': float(total_paid),
            'net_balance': float(total_received - total_paid),
            'pending_count': pending_count,
            'completed_count': completed_count,
            'total_count': len(payments),
            'currency': payments[0].currency if payments else "USD",
        }

    def get_payment_statistics(self, payment_id: PaymentId) -> Optional[Dict[str, Any]]:
        """الحصول على إحصائيات دفعة محددة"""
        payment = self.get_by_id(payment_id)
        if not payment:
            return None
        
        return {
            'id': str(payment.id),
            'code': str(payment.code),
            'amount': float(payment.amount.amount),
            'currency': payment.currency,
            'status': payment.status.value,
            'lines_count': len(payment.lines),
            'created_at': payment.created_at.isoformat() if payment.created_at else None,
            'updated_at': payment.updated_at.isoformat() if payment.updated_at else None,
            'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
            'customer_name': payment.customer_name,
            'supplier_name': payment.supplier_name,
        }

    # =========================================================================
    # العمليات الجماعية (Bulk Operations)
    # =========================================================================

    def bulk_save(self, payments: List[Payment]) -> int:
        """
        حفظ عدة دفعات دفعة واحدة
        
        Args:
            payments: قائمة الدفعات للحفظ
        
        Returns:
            عدد الدفعات المحفوظة بنجاح
        """
        saved_count = 0
        errors = []
        
        for payment in payments:
            try:
                self.save(payment)
                saved_count += 1
            except Exception as e:
                errors.append(f"Payment {payment.code}: {str(e)}")
        
        if errors:
            for error in errors:
                print(f"Error saving payment: {error}")
        
        return saved_count

    def bulk_update_status(self, payment_ids: List[str], status: PaymentStatus) -> int:
        """
        تحديث حالة عدة دفعات دفعة واحدة
        
        Args:
            payment_ids: قائمة معرفات الدفعات
            status: الحالة الجديدة
        
        Returns:
            عدد الدفعات المحدثة
        """
        uuids = [UUID(id) for id in payment_ids]
        clock = get_clock()
        
        result = self._session.execute(
            update(PaymentModel)
            .where(PaymentModel.id.in_(uuids))
            .values(
                status=status.value,
                updated_at=clock.now(),
                version=PaymentModel.version + 1,
                completed_at=clock.now() if status == PaymentStatus.COMPLETED else None,
            )
        )
        
        return result.rowcount

    def bulk_delete_drafts(self, payment_ids: List[str]) -> int:
        """
        حذف عدة دفعات مسودة دفعة واحدة
        
        Args:
            payment_ids: قائمة معرفات الدفعات
        
        Returns:
            عدد الدفعات المحذوفة
        """
        uuids = [UUID(id) for id in payment_ids]
        
        # حذف الأسطر المرتبطة أولاً
        self._session.execute(
            delete(PaymentLineModel).where(PaymentLineModel.payment_id.in_(uuids))
        )
        
        # حذف الدفعات
        result = self._session.execute(
            delete(PaymentModel)
            .where(
                and_(
                    PaymentModel.id.in_(uuids),
                    PaymentModel.status == "draft"
                )
            )
        )
        
        return result.rowcount

    # =========================================================================
    # دوال مساعدة إضافية
    # =========================================================================

    def get_payments_by_reference(self, reference_id: str) -> List[Payment]:
        """الحصول على الدفعات المرتبطة بمرجع معين"""
        return self.get_by_reference(None, reference_id)

    def get_latest_for_customer(self, customer_id: str, limit: int = 5) -> List[Payment]:
        """الحصول على أحدث دفعات العميل"""
        return self.list_by_customer(customer_id, limit=limit)

    def get_latest_for_supplier(self, supplier_id: str, limit: int = 5) -> List[Payment]:
        """الحصول على أحدث دفعات المورد"""
        return self.list_by_supplier(supplier_id, limit=limit)

    def count_by_status(self, status: PaymentStatus) -> int:
        """حساب عدد الدفعات حسب الحالة"""
        result = self._session.execute(
            select(func.count())
            .select_from(PaymentModel)
            .where(PaymentModel.status == status.value)
        ).scalar()
        
        return result or 0

    def count_by_type(self, payment_type: PaymentType) -> int:
        """حساب عدد الدفعات حسب النوع"""
        result = self._session.execute(
            select(func.count())
            .select_from(PaymentModel)
            .where(PaymentModel.payment_type == payment_type.value)
        ).scalar()
        
        return result or 0


# =============================================================================
# PostgresPaymentLineRepository - مستودع أسطر الدفعات
# =============================================================================

class PostgresPaymentLineRepository:
    """
    مستودع أسطر الدفعات - PostgreSQL Implementation
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, line: PaymentLine, payment_id: PaymentId) -> None:
        """حفظ سطر دفعة"""
        model = PaymentLineModel(
            payment_id=payment_id.value,
            reference_type=line.reference_type,
            reference_id=line.reference_id,
            amount=line.amount.amount,
            currency=line.amount.currency,
            notes=line.notes,
        )
        self._session.add(model)
    
    def get_by_id(self, line_id: str) -> Optional[PaymentLine]:
        """الحصول على سطر بواسطة المعرف"""
        model = self._session.execute(
            select(PaymentLineModel).where(PaymentLineModel.id == UUID(line_id))
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return PaymentLine(
            line_id=str(model.id),
            reference_type=model.reference_type,
            reference_id=model.reference_id,
            amount=Money(_to_decimal(model.amount), model.currency),
            notes=model.notes or "",
        )
    
    def get_by_payment(self, payment_id: PaymentId, limit: int = 100, offset: int = 0) -> List[PaymentLine]:
        """الحصول على أسطر دفعة معينة"""
        models = self._session.execute(
            select(PaymentLineModel)
            .where(PaymentLineModel.payment_id == payment_id.value)
            .order_by(PaymentLineModel.line_order)
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [
            PaymentLine(
                line_id=str(m.id),
                reference_type=m.reference_type,
                reference_id=m.reference_id,
                amount=Money(_to_decimal(m.amount), m.currency),
                notes=m.notes or "",
            )
            for m in models
        ]
    
    def delete(self, line_id: str) -> bool:
        """حذف سطر دفعة"""
        result = self._session.execute(
            delete(PaymentLineModel).where(PaymentLineModel.id == UUID(line_id))
        )
        self._session.flush()
        return result.rowcount > 0


# =============================================================================
# PostgresPaymentAllocationRepository - مستودع توزيعات الدفعات
# =============================================================================

class PostgresPaymentAllocationRepository:
    """
    مستودع توزيعات الدفعات - PostgreSQL Implementation
    
    ملاحظة: هذا مستودع مؤقت، سيتم تطويره بالكامل في الإصدارات القادمة
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, allocation) -> None:
        """حفظ توزيع دفعة"""
        # TODO: تنفيذ الحفظ الكامل
        # هذا مجرد نموذج مؤقت
        pass
    
    def get_by_id(self, allocation_id: str):
        """الحصول على توزيع بواسطة المعرف"""
        # TODO: تنفيذ الاستعلام الكامل
        return None
    
    def get_by_payment(self, payment_id: PaymentId):
        """الحصول على توزيعات دفعة معينة"""
        # TODO: تنفيذ الاستعلام الكامل
        return []
    
    def get_by_invoice(self, invoice_id: str):
        """الحصول على توزيعات فاتورة معينة"""
        # TODO: تنفيذ الاستعلام الكامل
        return []
    
    def delete(self, allocation_id: str) -> bool:
        """حذف توزيع"""
        # TODO: تنفيذ الحذف الكامل
        return True
    
    def get_allocations_by_payment(self, payment_id: PaymentId):
        """الحصول على توزيعات دفعة معينة (Alias)"""
        return self.get_by_payment(payment_id)


# =============================================================================
# تصدير الكلاسات
# =============================================================================

__all__ = [
    "PostgresPaymentRepository",
    "PostgresPaymentLineRepository",
    "PostgresPaymentAllocationRepository",
]