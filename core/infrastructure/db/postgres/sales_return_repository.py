# core/infrastructure/db/postgres/sales_return_repository.py
"""
PostgreSQL Repository for Sales Returns and Credit Notes
✅ جديد: دعم إرجاع المبيعات ومذكرات الدائنة
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_, or_, text, update, desc, asc, delete
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from core.domain.shared.clock import get_clock, utc_now, to_utc
from core.domain.sales.entities import SalesReturn, ReturnItem
from core.domain.sales.value_objects import (
    ReturnId, ReturnNumber, ReturnStatus, 
    CreditNoteId, CreditNoteNumber, CreditNoteStatus
)
from core.domain.sales.exceptions import ReturnNotFoundException, InvalidReturnStatusError
from core.domain.invoicing.entities import CreditNote, CreditNoteLine
from core.domain.invoicing.value_objects import CreditNoteId as DomainCreditNoteId, CreditNoteStatus as DomainCreditNoteStatus
from core.domain.invoicing.exceptions import CreditNoteNotFoundException
from core.domain.sales.interfaces import IReturnRepository, ReturnStatistics, ReturnFilter
from core.domain.shared.value_objects import Money
from core.shared.exceptions import ConcurrentModificationError, NotFoundError, ValidationError

from ..models.sales_return_model import (
    SalesReturnModel, SalesReturnLineModel,
    CreditNoteModel, CreditNoteLineModel, DebitNoteModel
)

import logging

logger = logging.getLogger(__name__)


# =============================================================================
# دوال التحويل بين Domain و ORM
# =============================================================================

def _model_to_domain(model: SalesReturnModel) -> SalesReturn:
    """تحويل ORM Model إلى Domain Entity"""
    
    # تحويل حالة الإرجاع
    status_map = {
        "draft": ReturnStatus.DRAFT,
        "submitted": ReturnStatus.SUBMITTED,
        "approved": ReturnStatus.APPROVED,
        "rejected": ReturnStatus.REJECTED,
        "received": ReturnStatus.RECEIVED,
        "inspected": ReturnStatus.INSPECTED,
        "completed": ReturnStatus.COMPLETED,
        "cancelled": ReturnStatus.CANCELLED,
    }
    status = status_map.get(model.status, ReturnStatus.DRAFT)
    
    # تحويل الأسطر
    lines = []
    for line_model in model.lines:
        condition_map = {
            "good": "good",
            "damaged": "damaged",
            "expired": "expired",
            "defective": "defective",
        }
        condition = condition_map.get(line_model.condition, "good")
        
        line = ReturnItem(
            product_code=line_model.product_code,
            product_name=line_model.product_name,
            quantity=line_model.quantity,
            unit_price=Money(line_model.unit_price, line_model.currency),
            reason=line_model.reason or "",
            condition=condition,
            discount_percent=line_model.discount_percent,
            discount_amount=Money(line_model.discount_amount, line_model.currency),
            tax_rate=line_model.tax_rate,
            tax_amount=Money(line_model.tax_amount, line_model.currency),
        )
        lines.append(line)
    
    # تحويل حالة مذكرة الدائنة إذا وجدت
    credit_note_status = None
    if model.credit_note_id:
        cn_status_map = {
            "draft": CreditNoteStatus.DRAFT,
            "issued": CreditNoteStatus.ISSUED,
            "posted": CreditNoteStatus.POSTED,
            "applied": CreditNoteStatus.APPLIED,
            "cancelled": CreditNoteStatus.CANCELLED,
        }
        # نحتاج لجلب حالة مذكرة الدائنة من الجدول
        credit_note_status = CreditNoteStatus.DRAFT  # Default
    
    sales_return = SalesReturn(
        id=ReturnId.from_string(str(model.id)),
        number=ReturnNumber(model.number),
        return_date=model.return_date,
        customer_id=model.customer_id,
        customer_name=model.customer_name,
        original_invoice_id=model.original_invoice_id,
        original_delivery_id=model.original_delivery_id,
        original_invoice_number=model.original_invoice_number,
        currency=model.currency,
        lines=lines,
        reason=model.reason or "",
        notes=model.notes or "",
        status=status,
        credit_note_id=CreditNoteId.from_string(str(model.credit_note_id)) if model.credit_note_id else None,
        credit_note_number=CreditNoteNumber(model.credit_note_number) if model.credit_note_number else None,
        journal_entry_id=model.journal_entry_id,
        created_at=model.created_at,
        created_by=model.created_by,
        submitted_at=model.submitted_at,
        submitted_by=model.submitted_by,
        approved_at=model.approved_at,
        approved_by=model.approved_by,
        rejected_at=model.rejected_at,
        rejected_by=model.rejected_by,
        received_at=model.received_at,
        received_by=model.received_by,
        inspected_at=model.inspected_at,
        inspected_by=model.inspected_by,
        completed_at=model.completed_at,
        completed_by=model.completed_by,
        cancelled_at=model.cancelled_at,
        cancelled_by=model.cancelled_by,
        version=model.version
    )
    
    return sales_return


def _domain_to_model(sales_return: SalesReturn) -> SalesReturnModel:
    """تحويل Domain Entity إلى ORM Model"""
    
    # تحويل حالة الإرجاع
    status_map = {
        ReturnStatus.DRAFT: "draft",
        ReturnStatus.SUBMITTED: "submitted",
        ReturnStatus.APPROVED: "approved",
        ReturnStatus.REJECTED: "rejected",
        ReturnStatus.RECEIVED: "received",
        ReturnStatus.INSPECTED: "inspected",
        ReturnStatus.COMPLETED: "completed",
        ReturnStatus.CANCELLED: "cancelled",
    }
    status = status_map.get(sales_return.status, "draft")
    
    return SalesReturnModel(
        id=sales_return.id.value,
        number=str(sales_return.number),
        return_date=sales_return.return_date,
        customer_id=sales_return.customer_id,
        customer_name=sales_return.customer_name,
        original_invoice_id=sales_return.original_invoice_id,
        original_delivery_id=sales_return.original_delivery_id,
        original_invoice_number=sales_return.original_invoice_number,
        currency=sales_return.currency,
        subtotal=sales_return.subtotal.amount,
        discount_amount=sales_return.total_discount.amount,
        tax_amount=sales_return.tax_amount.amount,
        total_amount=sales_return.total_amount.amount,
        status=status,
        reason=sales_return.reason,
        notes=sales_return.notes,
        credit_note_id=sales_return.credit_note_id.value if sales_return.credit_note_id else None,
        credit_note_number=str(sales_return.credit_note_number) if sales_return.credit_note_number else None,
        journal_entry_id=sales_return.journal_entry_id,
        created_at=sales_return.created_at,
        created_by=sales_return.created_by,
        submitted_at=sales_return.submitted_at,
        submitted_by=sales_return.submitted_by,
        approved_at=sales_return.approved_at,
        approved_by=sales_return.approved_by,
        rejected_at=sales_return.rejected_at,
        rejected_by=sales_return.rejected_by,
        received_at=sales_return.received_at,
        received_by=sales_return.received_by,
        inspected_at=sales_return.inspected_at,
        inspected_by=sales_return.inspected_by,
        completed_at=sales_return.completed_at,
        completed_by=sales_return.completed_by,
        cancelled_at=sales_return.cancelled_at,
        cancelled_by=sales_return.cancelled_by,
        version=sales_return.version
    )


def _sync_return_lines(sales_return: SalesReturn, session: Session) -> None:
    """مزامنة أسطر إرجاع المبيعات"""
    # حذف الأسطر القديمة
    session.execute(
        delete(SalesReturnLineModel).where(SalesReturnLineModel.sales_return_id == sales_return.id.value)
    )
    
    # إضافة الأسطر الجديدة
    for idx, line in enumerate(sales_return.lines):
        condition_map = {
            "good": "good",
            "damaged": "damaged",
            "expired": "expired",
            "defective": "defective",
        }
        condition = condition_map.get(line.condition, "good")
        
        line_model = SalesReturnLineModel(
            sales_return_id=sales_return.id.value,
            product_code=line.product_code,
            product_name=line.product_name,
            quantity=line.quantity,
            unit_price=line.unit_price.amount,
            discount_percent=line.discount_percent,
            discount_amount=line.discount_amount.amount,
            tax_rate=line.tax_rate,
            tax_amount=line.tax_amount.amount,
            reason=line.reason,
            condition=condition,
            currency=line.unit_price.currency,
            notes=line.notes,
            line_order=idx
        )
        session.add(line_model)


# =============================================================================
# PostgresReturnRepository - المستودع الرئيسي
# =============================================================================

class PostgresReturnRepository(IReturnRepository):
    """
    PostgreSQL implementation of IReturnRepository
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    # =========================================================================
    # العمليات الأساسية
    # =========================================================================
    
    def save(self, sales_return: SalesReturn) -> None:
        """حفظ إرجاع المبيعات (جديد أو محدث) مع Optimistic Locking"""
        existing = self._session.execute(
            select(SalesReturnModel).where(SalesReturnModel.id == sales_return.id.value)
        ).scalar_one_or_none()
        
        if existing:
            self._update_existing_return(existing, sales_return)
        else:
            self._create_new_return(sales_return)
    
    def _update_existing_return(self, existing: SalesReturnModel, sales_return: SalesReturn) -> None:
        """تحديث إرجاع موجود مع Optimistic Locking"""
        clock = get_clock()
        now = clock.now()
        new_version = existing.version + 1
        
        # تحويل الحالة
        status_map = {
            ReturnStatus.DRAFT: "draft",
            ReturnStatus.SUBMITTED: "submitted",
            ReturnStatus.APPROVED: "approved",
            ReturnStatus.REJECTED: "rejected",
            ReturnStatus.RECEIVED: "received",
            ReturnStatus.INSPECTED: "inspected",
            ReturnStatus.COMPLETED: "completed",
            ReturnStatus.CANCELLED: "cancelled",
        }
        status = status_map.get(sales_return.status, "draft")
        
        # تحديث الإرجاع باستخدام UPDATE مع شرط الإصدار
        result = self._session.execute(
            update(SalesReturnModel)
            .where(
                SalesReturnModel.id == sales_return.id.value,
                SalesReturnModel.version == sales_return.version
            )
            .values(
                number=str(sales_return.number),
                return_date=sales_return.return_date,
                customer_id=sales_return.customer_id,
                customer_name=sales_return.customer_name,
                original_invoice_id=sales_return.original_invoice_id,
                original_delivery_id=sales_return.original_delivery_id,
                original_invoice_number=sales_return.original_invoice_number,
                currency=sales_return.currency,
                subtotal=sales_return.subtotal.amount,
                discount_amount=sales_return.total_discount.amount,
                tax_amount=sales_return.tax_amount.amount,
                total_amount=sales_return.total_amount.amount,
                reason=sales_return.reason,
                notes=sales_return.notes,
                status=status,
                credit_note_id=sales_return.credit_note_id.value if sales_return.credit_note_id else None,
                credit_note_number=str(sales_return.credit_note_number) if sales_return.credit_note_number else None,
                journal_entry_id=sales_return.journal_entry_id,
                submitted_at=sales_return.submitted_at,
                submitted_by=sales_return.submitted_by,
                approved_at=sales_return.approved_at,
                approved_by=sales_return.approved_by,
                rejected_at=sales_return.rejected_at,
                rejected_by=sales_return.rejected_by,
                received_at=sales_return.received_at,
                received_by=sales_return.received_by,
                inspected_at=sales_return.inspected_at,
                inspected_by=sales_return.inspected_by,
                completed_at=sales_return.completed_at,
                completed_by=sales_return.completed_by,
                cancelled_at=sales_return.cancelled_at,
                cancelled_by=sales_return.cancelled_by,
                version=new_version
            )
        )
        
        # التحقق من تعارض الإصدار
        if result.rowcount == 0:
            raise ConcurrentModificationError(
                "SalesReturn",
                str(sales_return.id),
                sales_return.version,
                existing.version
            )
        
        # تحديث الإصدار المحلي
        sales_return.version = new_version
        
        # مزامنة الأسطر
        _sync_return_lines(sales_return, self._session)
    
    def _create_new_return(self, sales_return: SalesReturn) -> None:
        """إنشاء إرجاع جديد"""
        # التأكد من وجود رقم إرجاع
        if not sales_return.number:
            sales_return.number = self.get_next_number()
        
        model = _domain_to_model(sales_return)
        self._session.add(model)
        self._session.flush()
        sales_return.version = 1
        
        # إضافة الأسطر
        _sync_return_lines(sales_return, self._session)
    
    # =========================================================================
    # الاستعلامات
    # =========================================================================
    
    def get_by_id(self, return_id: ReturnId) -> Optional[SalesReturn]:
        """الحصول على إرجاع بواسطة المعرف"""
        model = self._session.execute(
            select(SalesReturnModel)
            .options(selectinload(SalesReturnModel.lines))
            .where(SalesReturnModel.id == return_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_number(self, number: ReturnNumber) -> Optional[SalesReturn]:
        """الحصول على إرجاع بواسطة الرقم"""
        model = self._session.execute(
            select(SalesReturnModel)
            .options(selectinload(SalesReturnModel.lines))
            .where(SalesReturnModel.number == str(number))
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_customer(self, customer_id: str, limit: int = 100) -> List[SalesReturn]:
        """الحصول على جميع عمليات الإرجاع لعميل معين"""
        models = self._session.execute(
            select(SalesReturnModel)
            .options(selectinload(SalesReturnModel.lines))
            .where(SalesReturnModel.customer_id == customer_id)
            .order_by(desc(SalesReturnModel.return_date))
            .limit(limit)
        ).scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def get_by_invoice(self, invoice_id: UUID) -> List[SalesReturn]:
        """الحصول على عمليات الإرجاع لفاتورة معينة"""
        models = self._session.execute(
            select(SalesReturnModel)
            .options(selectinload(SalesReturnModel.lines))
            .where(SalesReturnModel.original_invoice_id == invoice_id)
            .order_by(desc(SalesReturnModel.return_date))
        ).scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def find(self, filter: ReturnFilter) -> List[SalesReturn]:
        """البحث عن عمليات الإرجاع مع فلاتر متعددة"""
        query = select(SalesReturnModel).options(selectinload(SalesReturnModel.lines))
        
        # تطبيق الفلاتر
        if filter.customer_id:
            query = query.where(SalesReturnModel.customer_id == filter.customer_id)
        
        if filter.status:
            status_map = {
                ReturnStatus.DRAFT: "draft",
                ReturnStatus.SUBMITTED: "submitted",
                ReturnStatus.APPROVED: "approved",
                ReturnStatus.REJECTED: "rejected",
                ReturnStatus.RECEIVED: "received",
                ReturnStatus.INSPECTED: "inspected",
                ReturnStatus.COMPLETED: "completed",
                ReturnStatus.CANCELLED: "cancelled",
            }
            query = query.where(SalesReturnModel.status == status_map[filter.status])
        
        if filter.date_from:
            query = query.where(SalesReturnModel.return_date >= filter.date_from)
        
        if filter.date_to:
            query = query.where(SalesReturnModel.return_date <= filter.date_to)
        
        if filter.original_invoice_id:
            query = query.where(SalesReturnModel.original_invoice_id == filter.original_invoice_id)
        
        # الترتيب
        query = query.order_by(desc(SalesReturnModel.return_date))
        
        # Pagination
        if filter.limit:
            query = query.limit(filter.limit)
        
        if filter.offset:
            query = query.offset(filter.offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain(m) for m in models]
    
    # =========================================================================
    # أرقام التسلسل
    # =========================================================================
    
    def get_next_number(self) -> ReturnNumber:
        """الحصول على رقم الإرجاع التالي"""
        # الحصول على آخر رقم في السنة الحالية
        clock = get_clock()
        current_year = clock.now().year
        
        # البحث عن آخر رقم
        result = self._session.execute(
            select(func.max(SalesReturnModel.number))
            .where(SalesReturnModel.number.like(f"SR-{current_year}-%"))
        ).scalar_one_or_none()
        
        if result:
            # استخراج الرقم وتسلسله
            last_number = result
            parts = last_number.split("-")
            if len(parts) == 3:
                try:
                    last_seq = int(parts[2])
                    next_seq = last_seq + 1
                except ValueError:
                    next_seq = 1
            else:
                next_seq = 1
        else:
            next_seq = 1
        
        return ReturnNumber(f"SR-{current_year}-{next_seq:06d}")
    
    # =========================================================================
    # الإحصائيات
    # =========================================================================
    
    def get_statistics(self, filter: ReturnFilter) -> ReturnStatistics:
        """الحصول على إحصائيات عمليات الإرجاع"""
        query = select(
            func.count(SalesReturnModel.id).label("total_count"),
            func.sum(SalesReturnModel.total_amount).label("total_amount"),
            func.avg(SalesReturnModel.total_amount).label("avg_amount"),
        ).where(True)
        
        # تطبيق الفلاتر
        if filter.customer_id:
            query = query.where(SalesReturnModel.customer_id == filter.customer_id)
        
        if filter.status:
            status_map = {
                ReturnStatus.DRAFT: "draft",
                ReturnStatus.SUBMITTED: "submitted",
                ReturnStatus.APPROVED: "approved",
                ReturnStatus.REJECTED: "rejected",
                ReturnStatus.RECEIVED: "received",
                ReturnStatus.INSPECTED: "inspected",
                ReturnStatus.COMPLETED: "completed",
                ReturnStatus.CANCELLED: "cancelled",
            }
            query = query.where(SalesReturnModel.status == status_map[filter.status])
        
        if filter.date_from:
            query = query.where(SalesReturnModel.return_date >= filter.date_from)
        
        if filter.date_to:
            query = query.where(SalesReturnModel.return_date <= filter.date_to)
        
        result = self._session.execute(query).one()
        
        class Stats:
            total_count = result.total_count or 0
            total_amount = Money(result.total_amount or Decimal('0'), "USD")
            avg_amount = Money(result.avg_amount or Decimal('0'), "USD")
        
        return Stats()


__all__ = ["PostgresReturnRepository"]
