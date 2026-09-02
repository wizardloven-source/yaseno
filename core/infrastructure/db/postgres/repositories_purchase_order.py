# core/infrastructure/db/postgres/repositories_purchase_order.py
"""
PostgreSQL Repository for Purchase Orders - مستودع أوامر الشراء
✅ محدث: استخدام Clock Service للوقت
✅ محدث: تحسين Optimistic Locking
✅ محدث: دعم Pagination المتقدم
✅ محدث: دوال إحصائيات محسنة
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_, or_, text, update, desc, asc, delete
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

# ✅ استيراد Clock Service
from core.domain.shared.clock import get_clock, utc_now, to_utc
from core.domain.purchasing.entities import PurchaseOrder, PurchaseLine
from core.domain.purchasing.value_objects import (
    PurchaseOrderId, 
    PurchaseOrderNumber, 
    PurchaseOrderStatus, 
    PaymentTerms
)
from core.domain.shared.value_objects import Money
from core.domain.purchasing.interfaces import IPurchaseOrderRepository
from core.shared.exceptions import ConcurrentModificationError, NotFoundError, ValidationError

from ..models.purchase_order_model import PurchaseOrderModel, PurchaseOrderLineModel


# =============================================================================
# دوال مساعدة للتحويل
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


def _model_to_domain(model: PurchaseOrderModel) -> PurchaseOrder:
    """تحويل ORM Model إلى Domain Entity"""
    if not model:
        return None

    status_map = {
        "draft": PurchaseOrderStatus.DRAFT,
        "posted": PurchaseOrderStatus.POSTED,
        "cancelled": PurchaseOrderStatus.CANCELLED,
        "partially_received": PurchaseOrderStatus.PARTIALLY_RECEIVED,
        "fully_received": PurchaseOrderStatus.FULLY_RECEIVED,
    }
    status = status_map.get(model.status, PurchaseOrderStatus.DRAFT)
    
    payment_map = {
        "cash": PaymentTerms.CASH,
        "net_15": PaymentTerms.NET_15,
        "net_30": PaymentTerms.NET_30,
        "net_45": PaymentTerms.NET_45,
        "net_60": PaymentTerms.NET_60,
    }
    payment_terms = payment_map.get(model.payment_terms, PaymentTerms.NET_30)
    
    lines = []
    for line_model in model.lines:
        line = PurchaseLine(
            product_code=line_model.product_code,
            product_name=line_model.product_name,
            quantity=line_model.quantity,
            unit_price=Money(line_model.unit_price, line_model.currency),
            notes=line_model.notes or "",
            line_id=str(line_model.id),
            received_quantity=line_model.received_quantity
        )
        lines.append(line)
    
    order = PurchaseOrder(
        id=PurchaseOrderId(model.id),
        number=PurchaseOrderNumber(model.number) if model.number else None,
        date=model.order_date,
        expected_delivery_date=model.expected_delivery_date,
        supplier_id=model.supplier_id,
        supplier_name=model.supplier_name,
        site_id=model.site_id,
        site_name=model.site_name,
        currency=model.currency,
        payment_terms=payment_terms,
        lines=lines,
        notes=model.notes or "",
        status=status,
        journal_entry_id=model.journal_entry_id,
        created_at=model.created_at,
        created_by=model.created_by,
        posted_at=model.posted_at,
        posted_by=model.posted_by,
        received_at=model.received_at,
        received_by=model.received_by,
        version=model.version
    )
    
    return order


def _domain_to_model(order: PurchaseOrder) -> PurchaseOrderModel:
    """تحويل Domain Entity إلى ORM Model"""
    status_map = {
        PurchaseOrderStatus.DRAFT: "draft",
        PurchaseOrderStatus.POSTED: "posted",
        PurchaseOrderStatus.CANCELLED: "cancelled",
        PurchaseOrderStatus.PARTIALLY_RECEIVED: "partially_received",
        PurchaseOrderStatus.FULLY_RECEIVED: "fully_received",
    }
    status = status_map.get(order.status, "draft")
    
    payment_map = {
        PaymentTerms.CASH: "cash",
        PaymentTerms.NET_15: "net_15",
        PaymentTerms.NET_30: "net_30",
        PaymentTerms.NET_45: "net_45",
        PaymentTerms.NET_60: "net_60",
    }
    payment_terms = payment_map.get(order.payment_terms, "net_30")
    
    return PurchaseOrderModel(
        id=order.id.value,
        number=str(order.number) if order.number else "",
        order_date=order.date,
        expected_delivery_date=order.expected_delivery_date,
        supplier_id=order.supplier_id,
        supplier_name=order.supplier_name,
        site_id=order.site_id,
        site_name=order.site_name,
        currency=order.currency,
        payment_terms=payment_terms,
        subtotal=order.subtotal.amount,
        total_amount=order.total.amount,
        status=status,
        journal_entry_id=order.journal_entry_id,
        notes=order.notes,
        created_at=order.created_at,
        created_by=order.created_by,
        posted_at=order.posted_at,
        posted_by=order.posted_by,
        received_at=order.received_at,
        received_by=order.received_by,
        version=order.version
    )


# =============================================================================
# PostgresPurchaseOrderRepository - المستودع الرئيسي
# =============================================================================

class PostgresPurchaseOrderRepository(IPurchaseOrderRepository):
    """
    PostgreSQL implementation of IPurchaseOrderRepository
    
    ✅ محدث: استخدام Clock Service للوقت
    ✅ محدث: Optimistic Locking محسن
    ✅ محدث: دوال إحصائيات متقدمة
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    # =========================================================================
    # العمليات الأساسية مع Optimistic Locking
    # =========================================================================
    
    def save(self, order: PurchaseOrder) -> None:
        """
        حفظ أمر الشراء مع Optimistic Locking
        
        ✅ محدث: استخدام Clock Service للوقت
        """
        existing = self._session.execute(
            select(PurchaseOrderModel).where(PurchaseOrderModel.id == order.id.value)
        ).scalar_one_or_none()
        
        if existing:
            self._update_existing_order(existing, order)
        else:
            self._create_new_order(order)
    
    def _update_existing_order(self, existing: PurchaseOrderModel, order: PurchaseOrder) -> None:
        """تحديث أمر شراء موجود مع Optimistic Locking"""
        clock = get_clock()
        now = clock.now()
        new_version = existing.version + 1
        
        result = self._session.execute(
            update(PurchaseOrderModel)
            .where(
                PurchaseOrderModel.id == order.id.value,
                PurchaseOrderModel.version == order.version  # ✅ شرط التحقق
            )
            .values(
                number=str(order.number) if order.number else "",
                order_date=order.date,
                expected_delivery_date=order.expected_delivery_date,
                supplier_id=order.supplier_id,
                supplier_name=order.supplier_name,
                site_id=order.site_id,
                site_name=order.site_name,
                currency=order.currency,
                payment_terms=order.payment_terms.value,
                subtotal=order.subtotal.amount,
                total_amount=order.total.amount,
                notes=order.notes,
                status=order.status.value,
                journal_entry_id=order.journal_entry_id,
                posted_at=order.posted_at,
                posted_by=order.posted_by,
                received_at=order.received_at,
                received_by=order.received_by,
                version=new_version
            )
        )
        
        if result.rowcount == 0:
            raise ConcurrentModificationError(
                "PurchaseOrder",
                str(order.id),
                order.version,
                existing.version
            )
        
        order.version = new_version
        
        # مزامنة الأسطر
        self._sync_order_lines(order)
    
    def _create_new_order(self, order: PurchaseOrder) -> None:
        """إنشاء أمر شراء جديد"""
        if not order.number:
            order.number = self.get_next_number()
        
        model = _domain_to_model(order)
        self._session.add(model)
        self._session.flush()
        order.version = 1
        
        # إضافة الأسطر
        self._sync_order_lines(order)
    
    def _sync_order_lines(self, order: PurchaseOrder) -> None:
        """مزامنة أسطر أمر الشراء (حذف + إضافة)"""
        # حذف الأسطر القديمة
        self._session.execute(
            delete(PurchaseOrderLineModel).where(PurchaseOrderLineModel.order_id == order.id.value)
        )
        
        # إضافة الأسطر الجديدة
        for idx, line in enumerate(order.lines):
            line_model = PurchaseOrderLineModel(
                order_id=order.id.value,
                product_code=line.product_code,
                product_name=line.product_name,
                quantity=line.quantity,
                unit_price=line.unit_price.amount,
                total_amount=line.total.amount,
                received_quantity=line.received_quantity,
                currency=line.unit_price.currency,
                notes=line.notes,
                line_order=idx
            )
            self._session.add(line_model)
    
    # =========================================================================
    # دوال الاستعلام الأساسية
    # =========================================================================
    
    def get_by_id(self, order_id: PurchaseOrderId) -> Optional[PurchaseOrder]:
        """الحصول على أمر شراء بواسطة المعرف"""
        model = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(PurchaseOrderModel.id == order_id.value)
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_number(self, number: PurchaseOrderNumber) -> Optional[PurchaseOrder]:
        """الحصول على أمر شراء بواسطة الرقم"""
        model = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(PurchaseOrderModel.number == str(number))
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_journal_entry_id(self, journal_entry_id: str) -> Optional[PurchaseOrder]:
        """الحصول على أمر شراء بواسطة معرف القيد المحاسبي"""
        model = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(PurchaseOrderModel.journal_entry_id == journal_entry_id)
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_supplier(self, supplier_id: str) -> List[PurchaseOrder]:
        """الحصول على جميع أوامر شراء المورد"""
        return self.list_by_supplier(supplier_id, limit=1000)
    
    # =========================================================================
    # قوائم أوامر الشراء مع Pagination
    # =========================================================================
    
    def list_by_supplier(self, supplier_id: str, limit: int = 100, offset: int = 0) -> List[PurchaseOrder]:
        """قائمة أوامر شراء المورد"""
        models = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(PurchaseOrderModel.supplier_id == supplier_id)
            .order_by(desc(PurchaseOrderModel.order_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_status(self, status: PurchaseOrderStatus, limit: int = 100, offset: int = 0) -> List[PurchaseOrder]:
        """قائمة أوامر شراء حسب الحالة"""
        models = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(PurchaseOrderModel.status == status.value)
            .order_by(desc(PurchaseOrderModel.order_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_site(self, site_id: str, limit: int = 100, offset: int = 0) -> List[PurchaseOrder]:
        """قائمة أوامر شراء حسب الموقع"""
        models = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(PurchaseOrderModel.site_id == site_id)
            .order_by(desc(PurchaseOrderModel.order_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_date_range(
        self, 
        from_date: date, 
        to_date: date, 
        limit: int = 100,
        offset: int = 0
    ) -> List[PurchaseOrder]:
        """قائمة أوامر شراء في نطاق زمني"""
        models = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                and_(
                    PurchaseOrderModel.order_date >= from_date,
                    PurchaseOrderModel.order_date <= to_date
                )
            )
            .order_by(desc(PurchaseOrderModel.order_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_payment_terms(
        self, 
        payment_terms: PaymentTerms, 
        limit: int = 100
    ) -> List[PurchaseOrder]:
        """قائمة أوامر شراء حسب شروط الدفع"""
        models = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(PurchaseOrderModel.payment_terms == payment_terms.value)
            .order_by(desc(PurchaseOrderModel.order_date))
            .limit(limit)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_filters(
        self,
        supplier_id: Optional[str] = None,
        site_id: Optional[str] = None,
        status: Optional[PurchaseOrderStatus] = None,
        payment_terms: Optional[PaymentTerms] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "date",
        order_desc: bool = True
    ) -> List[PurchaseOrder]:
        """
        قائمة أوامر شراء مع فلاتر متعددة
        
        Args:
            supplier_id: معرف المورد (اختياري)
            site_id: معرف الموقع (اختياري)
            status: حالة أمر الشراء (اختياري)
            payment_terms: شروط الدفع (اختياري)
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
            order_by: حقل الترتيب (date, number, supplier, total)
            order_desc: ترتيب تنازلي
        """
        query = select(PurchaseOrderModel).options(selectinload(PurchaseOrderModel.lines))
        
        if supplier_id:
            query = query.where(PurchaseOrderModel.supplier_id == supplier_id)
        
        if site_id:
            query = query.where(PurchaseOrderModel.site_id == site_id)
        
        if status:
            query = query.where(PurchaseOrderModel.status == status.value)
        
        if payment_terms:
            query = query.where(PurchaseOrderModel.payment_terms == payment_terms.value)
        
        if from_date:
            query = query.where(PurchaseOrderModel.order_date >= from_date)
        
        if to_date:
            query = query.where(PurchaseOrderModel.order_date <= to_date)
        
        # تحديد الترتيب
        order_map = {
            "date": PurchaseOrderModel.order_date,
            "number": PurchaseOrderModel.number,
            "supplier": PurchaseOrderModel.supplier_name,
            "total": PurchaseOrderModel.total_amount,
            "status": PurchaseOrderModel.status,
            "created_at": PurchaseOrderModel.created_at,
        }
        order_column = order_map.get(order_by, PurchaseOrderModel.order_date)
        
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        models = self._session.execute(
            query.limit(limit).offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    # =========================================================================
    # عمليات الترقيم
    # =========================================================================
    
    def get_next_number(self, prefix: str = "PO-", length: int = 5) -> PurchaseOrderNumber:
        """
        الحصول على رقم أمر الشراء التالي
        
        ✅ محدث: يدعم بادئات مخصصة وطول رقم متغير
        
        Args:
            prefix: بادئة رقم الأمر (مثل "PO-")
            length: طول الرقم التسلسلي
        
        Returns:
            PurchaseOrderNumber: رقم أمر الشراء التالي
        """
        result = self._session.execute(
            text("""
                SELECT MAX(CAST(SUBSTRING(number FROM '\d+$') AS INTEGER))
                FROM purchase_orders 
                WHERE number LIKE :prefix_pattern
            """),
            {"prefix_pattern": f"{prefix}%"}
        ).scalar()
        
        if result and result > 0:
            next_num = result + 1
        else:
            next_num = 1
        
        number_str = str(next_num).zfill(length)
        return PurchaseOrderNumber(f"{prefix}{number_str}")
    
    def reserve_number(self, number: PurchaseOrderNumber) -> bool:
        """حجز رقم أمر شراء مؤقتاً"""
        existing = self._session.execute(
            select(PurchaseOrderModel.id).where(PurchaseOrderModel.number == str(number))
        ).first()
        
        return existing is None
    
    def release_number(self, number: PurchaseOrderNumber) -> bool:
        """إلغاء حجز رقم أمر شراء"""
        existing = self._session.execute(
            select(PurchaseOrderModel.id).where(PurchaseOrderModel.number == str(number))
        ).first()
        
        return existing is not None
    
    def exists_by_number(self, number: PurchaseOrderNumber) -> bool:
        """التحقق من وجود أمر شراء برقم معين"""
        result = self._session.execute(
            select(PurchaseOrderModel.id).where(PurchaseOrderModel.number == str(number))
        ).first()
        
        return result is not None
    
    # =========================================================================
    # عمليات الحذف
    # =========================================================================
    
    def delete_draft(self, order_id: PurchaseOrderId) -> bool:
        """حذف أمر شراء مسودة (غير مرحّل)"""
        model = self._session.execute(
            select(PurchaseOrderModel).where(PurchaseOrderModel.id == order_id.value)
        ).scalar_one_or_none()
        
        if not model or model.status != "draft":
            return False
        
        # حذف الأسطر المرتبطة أولاً
        self._session.execute(
            delete(PurchaseOrderLineModel).where(PurchaseOrderLineModel.order_id == order_id.value)
        )
        
        self._session.delete(model)
        return True
    
    def soft_delete(self, order_id: PurchaseOrderId, deleted_by: str = "system") -> bool:
        """حذف ناعم (تعطيل) أمر شراء"""
        model = self._session.execute(
            select(PurchaseOrderModel).where(PurchaseOrderModel.id == order_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        clock = get_clock()
        model.status = "cancelled"
        model.version += 1
        
        return True
    
    # =========================================================================
    # دوال الإحصائيات المتقدمة
    # =========================================================================
    
    def count_by_status(self, status: PurchaseOrderStatus) -> int:
        """حساب عدد أوامر الشراء حسب الحالة"""
        result = self._session.execute(
            select(func.count())
            .select_from(PurchaseOrderModel)
            .where(PurchaseOrderModel.status == status.value)
        ).scalar()
        
        return result or 0
    
    def count_by_supplier(self, supplier_id: str, status: Optional[PurchaseOrderStatus] = None) -> int:
        """حساب عدد أوامر شراء المورد"""
        query = select(func.count()).select_from(PurchaseOrderModel).where(
            PurchaseOrderModel.supplier_id == supplier_id
        )
        
        if status:
            query = query.where(PurchaseOrderModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def count_by_site(self, site_id: str, status: Optional[PurchaseOrderStatus] = None) -> int:
        """حساب عدد أوامر شراء الموقع"""
        query = select(func.count()).select_from(PurchaseOrderModel).where(
            PurchaseOrderModel.site_id == site_id
        )
        
        if status:
            query = query.where(PurchaseOrderModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def get_total_by_supplier(self, supplier_id: str, status: Optional[PurchaseOrderStatus] = None) -> Decimal:
        """حساب إجمالي أوامر شراء المورد"""
        query = select(func.sum(PurchaseOrderModel.total_amount)).where(
            PurchaseOrderModel.supplier_id == supplier_id
        )
        
        if status:
            query = query.where(PurchaseOrderModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return Decimal(str(result or 0))
    
    def get_total_by_site(self, site_id: str, status: Optional[PurchaseOrderStatus] = None) -> Decimal:
        """حساب إجمالي أوامر شراء الموقع"""
        query = select(func.sum(PurchaseOrderModel.total_amount)).where(
            PurchaseOrderModel.site_id == site_id
        )
        
        if status:
            query = query.where(PurchaseOrderModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return Decimal(str(result or 0))
    
    def get_average_by_supplier(self, supplier_id: str) -> Decimal:
        """حساب متوسط مبالغ أوامر شراء المورد"""
        total = self.get_total_by_supplier(supplier_id)
        count = self.count_by_supplier(supplier_id)
        
        if count == 0:
            return Decimal('0')
        
        return total / Decimal(str(count))
    
    def get_supplier_statistics(self, supplier_id: str) -> Dict[str, Any]:
        """
        الحصول على إحصائيات أوامر شراء المورد
        
        Args:
            supplier_id: معرف المورد
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        total_count = self.count_by_supplier(supplier_id)
        total_amount = self.get_total_by_supplier(supplier_id)
        
        # إحصائيات حسب الحالة
        draft_count = self.count_by_supplier(supplier_id, PurchaseOrderStatus.DRAFT)
        posted_count = self.count_by_supplier(supplier_id, PurchaseOrderStatus.POSTED)
        fully_received_count = self.count_by_supplier(supplier_id, PurchaseOrderStatus.FULLY_RECEIVED)
        partially_received_count = self.count_by_supplier(supplier_id, PurchaseOrderStatus.PARTIALLY_RECEIVED)
        cancelled_count = self.count_by_supplier(supplier_id, PurchaseOrderStatus.CANCELLED)
        
        # الحصول على نطاق التواريخ
        date_range = self._session.execute(
            select(
                func.min(PurchaseOrderModel.order_date),
                func.max(PurchaseOrderModel.order_date)
            ).where(PurchaseOrderModel.supplier_id == supplier_id)
        ).first()
        
        return {
            'supplier_id': supplier_id,
            'total_count': total_count,
            'total_amount': float(total_amount),
            'draft_count': draft_count,
            'posted_count': posted_count,
            'fully_received_count': fully_received_count,
            'partially_received_count': partially_received_count,
            'cancelled_count': cancelled_count,
            'first_order_date': date_range[0].isoformat() if date_range and date_range[0] else None,
            'last_order_date': date_range[1].isoformat() if date_range and date_range[1] else None,
            'average_amount': float(total_amount / total_count) if total_count > 0 else 0,
        }
    
    def get_site_statistics(self, site_id: str) -> Dict[str, Any]:
        """
        الحصول على إحصائيات أوامر شراء الموقع
        
        Args:
            site_id: معرف الموقع
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        total_count = self.count_by_site(site_id)
        total_amount = self.get_total_by_site(site_id)
        
        draft_count = self.count_by_site(site_id, PurchaseOrderStatus.DRAFT)
        posted_count = self.count_by_site(site_id, PurchaseOrderStatus.POSTED)
        fully_received_count = self.count_by_site(site_id, PurchaseOrderStatus.FULLY_RECEIVED)
        partially_received_count = self.count_by_site(site_id, PurchaseOrderStatus.PARTIALLY_RECEIVED)
        cancelled_count = self.count_by_site(site_id, PurchaseOrderStatus.CANCELLED)
        
        date_range = self._session.execute(
            select(
                func.min(PurchaseOrderModel.order_date),
                func.max(PurchaseOrderModel.order_date)
            ).where(PurchaseOrderModel.site_id == site_id)
        ).first()
        
        return {
            'site_id': site_id,
            'total_count': total_count,
            'total_amount': float(total_amount),
            'draft_count': draft_count,
            'posted_count': posted_count,
            'fully_received_count': fully_received_count,
            'partially_received_count': partially_received_count,
            'cancelled_count': cancelled_count,
            'first_order_date': date_range[0].isoformat() if date_range and date_range[0] else None,
            'last_order_date': date_range[1].isoformat() if date_range and date_range[1] else None,
            'average_amount': float(total_amount / total_count) if total_count > 0 else 0,
        }
    
    def get_summary(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        currency: str = "USD",
    ) -> Dict[str, Any]:
        """
        الحصول على ملخص أوامر الشراء
        
        Args:
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
            currency: العملة
        
        Returns:
            قاموس يحتوي على الملخص
        """
        clock = get_clock()
        if not from_date:
            from_date = clock.today() - timedelta(days=30)
        if not to_date:
            to_date = clock.today()
        
        total_amount = self._session.execute(
            select(func.sum(PurchaseOrderModel.total_amount))
            .where(
                and_(
                    PurchaseOrderModel.currency == currency,
                    PurchaseOrderModel.order_date >= from_date,
                    PurchaseOrderModel.order_date <= to_date,
                )
            )
        ).scalar() or Decimal('0')
        
        draft_count = self._session.execute(
            select(func.count())
            .select_from(PurchaseOrderModel)
            .where(
                and_(
                    PurchaseOrderModel.status == "draft",
                    PurchaseOrderModel.order_date >= from_date,
                    PurchaseOrderModel.order_date <= to_date,
                )
            )
        ).scalar() or 0
        
        posted_count = self._session.execute(
            select(func.count())
            .select_from(PurchaseOrderModel)
            .where(
                and_(
                    PurchaseOrderModel.status == "posted",
                    PurchaseOrderModel.order_date >= from_date,
                    PurchaseOrderModel.order_date <= to_date,
                )
            )
        ).scalar() or 0
        
        received_count = self._session.execute(
            select(func.count())
            .select_from(PurchaseOrderModel)
            .where(
                and_(
                    PurchaseOrderModel.status.in_(["fully_received", "partially_received"]),
                    PurchaseOrderModel.order_date >= from_date,
                    PurchaseOrderModel.order_date <= to_date,
                )
            )
        ).scalar() or 0
        
        total_count = self._session.execute(
            select(func.count())
            .select_from(PurchaseOrderModel)
            .where(
                and_(
                    PurchaseOrderModel.order_date >= from_date,
                    PurchaseOrderModel.order_date <= to_date,
                )
            )
        ).scalar() or 0
        
        return {
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'currency': currency,
            'total_amount': float(total_amount),
            'draft_count': draft_count,
            'posted_count': posted_count,
            'received_count': received_count,
            'total_count': total_count,
            'average_amount': float(total_amount / total_count) if total_count > 0 else 0,
        }
    
    def get_latest_for_supplier(self, supplier_id: str, limit: int = 5) -> List[PurchaseOrder]:
        """الحصول على أحدث أوامر شراء المورد"""
        return self.list_by_supplier(supplier_id, limit=limit)
    
    def get_orders_to_receive(self, limit: int = 100) -> List[PurchaseOrder]:
        """الحصول على أوامر الشراء التي تحتاج إلى استلام"""
        models = self._session.execute(
            select(PurchaseOrderModel)
            .options(selectinload(PurchaseOrderModel.lines))
            .where(
                and_(
                    PurchaseOrderModel.status == "posted",
                    PurchaseOrderModel.expected_delivery_date <= get_clock().today()
                )
            )
            .order_by(desc(PurchaseOrderModel.expected_delivery_date))
            .limit(limit)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    # =========================================================================
    # العمليات الجماعية (Bulk Operations)
    # =========================================================================
    
    def bulk_save(self, orders: List[PurchaseOrder]) -> int:
        """
        حفظ عدة أوامر شراء دفعة واحدة
        
        Args:
            orders: قائمة أوامر الشراء للحفظ
        
        Returns:
            عدد أوامر الشراء المحفوظة بنجاح
        """
        saved_count = 0
        errors = []
        
        for order in orders:
            try:
                self.save(order)
                saved_count += 1
            except Exception as e:
                errors.append(f"Order {order.number}: {str(e)}")
        
        if errors:
            for error in errors:
                print(f"Error saving purchase order: {error}")
        
        return saved_count
    
    def bulk_update_status(self, order_ids: List[str], status: PurchaseOrderStatus) -> int:
        """
        تحديث حالة عدة أوامر شراء دفعة واحدة
        
        Args:
            order_ids: قائمة معرفات أوامر الشراء
            status: الحالة الجديدة
        
        Returns:
            عدد أوامر الشراء المحدثة
        """
        uuids = [UUID(id) for id in order_ids]
        clock = get_clock()
        
        result = self._session.execute(
            update(PurchaseOrderModel)
            .where(PurchaseOrderModel.id.in_(uuids))
            .values(
                status=status.value,
                version=PurchaseOrderModel.version + 1,
                posted_at=clock.now() if status == PurchaseOrderStatus.POSTED else None,
                received_at=clock.now() if status in [PurchaseOrderStatus.FULLY_RECEIVED, PurchaseOrderStatus.PARTIALLY_RECEIVED] else None,
            )
        )
        
        return result.rowcount
    
    def bulk_delete_drafts(self, order_ids: List[str]) -> int:
        """
        حذف عدة أوامر شراء مسودة دفعة واحدة
        
        Args:
            order_ids: قائمة معرفات أوامر الشراء
        
        Returns:
            عدد أوامر الشراء المحذوفة
        """
        uuids = [UUID(id) for id in order_ids]
        
        # حذف الأسطر المرتبطة أولاً
        self._session.execute(
            delete(PurchaseOrderLineModel).where(PurchaseOrderLineModel.order_id.in_(uuids))
        )
        
        # حذف أوامر الشراء
        result = self._session.execute(
            delete(PurchaseOrderModel)
            .where(
                and_(
                    PurchaseOrderModel.id.in_(uuids),
                    PurchaseOrderModel.status == "draft"
                )
            )
        )
        
        return result.rowcount


# =============================================================================
# تصدير الكلاس
# =============================================================================

__all__ = [
    "PostgresPurchaseOrderRepository",
]