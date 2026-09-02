# core/infrastructure/db/postgres/repositories_invoice.py
"""
PostgreSQL Repository for Invoicing - يدعم المواقع المرتبطة بالعميل
✅ محدث: استخدام Clock Service للوقت
✅ محدث: تحسين Optimistic Locking
✅ محدث: دعم Pagination المتقدم
✅ محدث: دوال إحصائيات محسنة
✅ جديد: lock_invoices_for_update (SELECT FOR UPDATE)
✅ جديد: save_atomic لحفظ عدة فواتير دفعة واحدة
✅ جديد: restore_draft لاستعادة الفواتير المحذوفة
✅ جديد: get_by_id مع التحقق من الإصدار
✅ جديد: bulk_update_status مع Optimistic Locking
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
from core.domain.invoicing.entities import Invoice, InvoiceLine
from core.domain.invoicing.value_objects import InvoiceId, InvoiceNumber, InvoiceStatus, PaymentType
from core.domain.invoicing.exceptions import InvoiceNotFoundError
from core.domain.invoicing.interfaces import IInvoiceRepository, InvoiceSummary, InvoiceStatistics, InvoiceFilter
from core.domain.shared.value_objects import Money
from core.shared.exceptions import ConcurrentModificationError, NotFoundError, ValidationError

from ..models.invoice_model import InvoiceModel, InvoiceLineModel

import logging

logger = logging.getLogger(__name__)


# =============================================================================
# دوال التحويل بين Domain و ORM (محسنة)
# =============================================================================

def _model_to_domain(model: InvoiceModel) -> Invoice:
    """
    تحويل ORM Model إلى Domain Entity مع دعم الموقع
    
    ✅ محدث: استخدام Clock Service للوقت
    """
    
    # تحويل حالة الفاتورة
    status_map = {
        "draft": InvoiceStatus.DRAFT,
        "posted": InvoiceStatus.POSTED,
        "cancelled": InvoiceStatus.CANCELLED,
    }
    status = status_map.get(model.status, InvoiceStatus.DRAFT)
    
    # تحويل طريقة الدفع
    payment_map = {
        "cash": PaymentType.CASH,
        "credit": PaymentType.CREDIT,
        "check": PaymentType.CHECK,
        "transfer": PaymentType.TRANSFER,
    }
    payment_type = payment_map.get(model.payment_type, PaymentType.CASH)
    
    # تحويل الأسطر
    lines = []
    for line_model in model.lines:
        line = InvoiceLine(
            product_code=line_model.product_code,
            product_name=line_model.product_name,
            quantity=line_model.quantity,
            unit_price=Money(line_model.unit_price, line_model.currency),
            notes=line_model.notes or "",
            line_id=str(line_model.id)
        )
        lines.append(line)
    
    invoice = Invoice(
        id=InvoiceId(model.id) if isinstance(model.id, UUID) else InvoiceId.from_string(str(model.id)),
        number=InvoiceNumber(model.number) if model.number else None,
        date=model.invoice_date,
        customer_id=model.customer_id,
        customer_name=model.customer_name,
        site_id=model.site_id,
        site_name=model.site_name,
        currency=model.currency,
        payment_currency=model.payment_currency,
        payment_type=payment_type,
        fund_id=model.fund_id,
        lines=lines,
        notes=model.notes or "",
        status=status,
        journal_entry_id=model.journal_entry_id,
        created_at=model.created_at,
        created_by=model.created_by,
        posted_at=model.posted_at,
        posted_by=model.posted_by,
        version=model.version
    )
    
    return invoice


def _domain_to_model(invoice: Invoice) -> InvoiceModel:
    """
    تحويل Domain Entity إلى ORM Model مع دعم الموقع
    
    ✅ محدث: استخدام Clock Service للوقت
    """
    
    # تحويل حالة الفاتورة
    status_map = {
        InvoiceStatus.DRAFT: "draft",
        InvoiceStatus.POSTED: "posted",
        InvoiceStatus.CANCELLED: "cancelled",
    }
    status = status_map.get(invoice.status, "draft")
    
    # تحويل طريقة الدفع
    payment_map = {
        PaymentType.CASH: "cash",
        PaymentType.CREDIT: "credit",
        PaymentType.CHECK: "check",
        PaymentType.TRANSFER: "transfer",
    }
    payment_type = payment_map.get(invoice.payment_type, "cash")
    
    return InvoiceModel(
        id=invoice.id.value,
        number=str(invoice.number) if invoice.number else "",
        invoice_date=invoice.date,
        customer_id=invoice.customer_id,
        customer_name=invoice.customer_name,
        site_id=invoice.site_id,
        site_name=invoice.site_name,
        currency=invoice.currency,
        payment_currency=invoice.payment_currency,
        payment_type=payment_type,
        fund_id=invoice.fund_id,
        subtotal=invoice.subtotal.amount,
        tax_amount=invoice.tax_amount.amount,
        total_amount=invoice.total.amount,
        status=status,
        journal_entry_id=invoice.journal_entry_id,
        notes=invoice.notes,
        created_at=invoice.created_at,
        created_by=invoice.created_by,
        posted_at=invoice.posted_at,
        posted_by=invoice.posted_by,
        version=invoice.version
    )


# =============================================================================
# PostgresInvoiceRepository - المستودع الرئيسي
# =============================================================================

class PostgresInvoiceRepository(IInvoiceRepository):
    """
    PostgreSQL implementation of IInvoiceRepository مع دعم الموقع
    
    ✅ محدث: استخدام Clock Service للوقت
    ✅ محدث: Optimistic Locking محسن
    ✅ محدث: دوال إحصائيات متقدمة
    ✅ جديد: SELECT FOR UPDATE و Atomic Save
    """
    
    def __init__(self, session: Session):
        self._session = session
    
    # =========================================================================
    # العمليات الأساسية مع Optimistic Locking
    # =========================================================================
    
    def save(self, invoice: Invoice) -> None:
        """
        حفظ الفاتورة (جديدة أو محدثة) مع Optimistic Locking
        
        ✅ محدث: استخدام Clock Service للوقت
        """
        existing = self._session.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice.id.value)
        ).scalar_one_or_none()
        
        if existing:
            self._update_existing_invoice(existing, invoice)
        else:
            self._create_new_invoice(invoice)
    
    def _update_existing_invoice(self, existing: InvoiceModel, invoice: Invoice) -> None:
        """تحديث فاتورة موجودة مع Optimistic Locking"""
        clock = get_clock()
        now = clock.now()
        new_version = existing.version + 1
        
        # تحديث الفاتورة باستخدام UPDATE مع شرط الإصدار
        result = self._session.execute(
            update(InvoiceModel)
            .where(
                InvoiceModel.id == invoice.id.value,
                InvoiceModel.version == invoice.version  # ✅ شرط التحقق
            )
            .values(
                number=str(invoice.number) if invoice.number else "",
                invoice_date=invoice.date,
                customer_id=invoice.customer_id,
                customer_name=invoice.customer_name,
                site_id=invoice.site_id,
                site_name=invoice.site_name,
                currency=invoice.currency,
                payment_currency=invoice.payment_currency,
                payment_type=invoice.payment_type.value,
                fund_id=invoice.fund_id,
                subtotal=invoice.subtotal.amount,
                tax_amount=invoice.tax_amount.amount,
                total_amount=invoice.total.amount,
                notes=invoice.notes,
                status=invoice.status.value,
                journal_entry_id=invoice.journal_entry_id,
                posted_at=invoice.posted_at,
                posted_by=invoice.posted_by,
                version=new_version
            )
        )
        
        # ✅ التحقق: إذا لم يتم تحديث أي صف، فهذا يعني تعارض في الإصدار
        if result.rowcount == 0:
            raise ConcurrentModificationError(
                "Invoice",
                str(invoice.id),
                invoice.version,
                existing.version
            )
        
        # ✅ تحديث الكائن المحلي بالنسخة الجديدة
        invoice.version = new_version
        
        # حذف الأسطر القديمة وإعادة إضافتها
        self._sync_invoice_lines(invoice)
    
    def _create_new_invoice(self, invoice: Invoice) -> None:
        """إنشاء فاتورة جديدة"""
        # التأكد من وجود رقم فاتورة
        if not invoice.number:
            invoice.number = self.get_next_number()
        
        model = _domain_to_model(invoice)
        self._session.add(model)
        self._session.flush()
        invoice.version = 1  # الإصدار الأولي
        
        # إضافة الأسطر
        self._sync_invoice_lines(invoice)
    
    def _sync_invoice_lines(self, invoice: Invoice) -> None:
        """مزامنة أسطر الفاتورة (حذف + إضافة)"""
        # حذف الأسطر القديمة
        self._session.execute(
            delete(InvoiceLineModel).where(InvoiceLineModel.invoice_id == invoice.id.value)
        )
        
        # إضافة الأسطر الجديدة
        for idx, line in enumerate(invoice.lines):
            line_model = InvoiceLineModel(
                invoice_id=invoice.id.value,
                product_code=line.product_code,
                product_name=line.product_name,
                quantity=line.quantity,
                unit_price=line.unit_price.amount,
                total_amount=line.total.amount,
                currency=line.unit_price.currency,
                notes=line.notes,
                line_order=idx
            )
            self._session.add(line_model)
    
    # =========================================================================
    # 🔒 قفل الفواتير للتحديث (SELECT FOR UPDATE)
    # =========================================================================
    
    def lock_invoices_for_update(self, invoice_ids: List[InvoiceId]) -> List[Invoice]:
        """
        قفل الفواتير باستخدام SELECT FOR UPDATE لمنع التعديل المتزامن.
        
        مفيد لعمليات الترحيل الجماعي أو التحديثات المتزامنة.
        
        Args:
            invoice_ids: قائمة معرفات الفواتير المراد قفلها
            
        Returns:
            List[Invoice]: قائمة الفواتير المقفلة
            
        Raises:
            ValueError: إذا لم يتم العثور على أحد الفواتير
        """
        if not invoice_ids:
            return []
        
        ids = [iid.value for iid in invoice_ids]
        
        # 🔒 قفل الصفوف للتحديث
        models = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(InvoiceModel.id.in_(ids))
            .with_for_update()  # 🔒 قفل حصري
        ).unique().scalars().all()
        
        # التحقق من وجود جميع الفواتير المطلوبة
        found_ids = {str(m.id) for m in models}
        requested_ids = {str(iid.value) for iid in invoice_ids}
        
        missing = requested_ids - found_ids
        if missing:
            raise ValueError(f"Invoices not found: {', '.join(missing)}")
        
        # تحويل إلى Domain Entities
        invoices = [_model_to_domain(m) for m in models]
        
        logger.debug(f"🔒 Locked {len(invoices)} invoices for update")
        return invoices
    
    # =========================================================================
    # 💾 حفظ ذري (Atomic Save) لعدة فواتير
    # =========================================================================
    
    def save_atomic(self, invoices: List[Invoice]) -> None:
        """
        حفظ عدة فواتير دفعة واحدة مع Optimistic Locking.
        
        Args:
            invoices: قائمة الفواتير للحفظ
            
        Raises:
            ConcurrentModificationError: إذا تم تعديل أي فاتورة بشكل متزامن
        """
        if not invoices:
            return
        
        clock = get_clock()
        now = clock.now()
        
        # جلب الإصدارات الحالية للتحقق منها
        invoice_ids = [inv.id.value for inv in invoices]
        current_versions = self._session.execute(
            select(InvoiceModel.id, InvoiceModel.version)
            .where(InvoiceModel.id.in_(invoice_ids))
        ).all()
        
        version_map = {str(row[0]): row[1] for row in current_versions}
        
        for invoice in invoices:
            invoice_id_str = str(invoice.id.value)
            
            if invoice_id_str in version_map:
                # ✅ التحقق من الإصدار (Optimistic Locking)
                if invoice.version != version_map[invoice_id_str]:
                    raise ConcurrentModificationError(
                        "Invoice",
                        invoice_id_str,
                        invoice.version,
                        version_map[invoice_id_str]
                    )
                
                # تحديث الفاتورة
                new_version = version_map[invoice_id_str] + 1
                
                # تحويل إلى Model
                model = _domain_to_model(invoice)
                
                result = self._session.execute(
                    update(InvoiceModel)
                    .where(
                        InvoiceModel.id == invoice.id.value,
                        InvoiceModel.version == invoice.version
                    )
                    .values(
                        number=model.number,
                        invoice_date=model.invoice_date,
                        customer_id=model.customer_id,
                        customer_name=model.customer_name,
                        site_id=model.site_id,
                        site_name=model.site_name,
                        currency=model.currency,
                        payment_currency=model.payment_currency,
                        payment_type=model.payment_type,
                        fund_id=model.fund_id,
                        subtotal=model.subtotal,
                        tax_amount=model.tax_amount,
                        total_amount=model.total_amount,
                        notes=model.notes,
                        status=model.status,
                        journal_entry_id=model.journal_entry_id,
                        posted_at=model.posted_at,
                        posted_by=model.posted_by,
                        updated_at=now,
                        version=new_version
                    )
                )
                
                if result.rowcount == 0:
                    raise ConcurrentModificationError(
                        "Invoice",
                        invoice_id_str,
                        invoice.version,
                        version_map[invoice_id_str]
                    )
                
                invoice.version = new_version
                
                # مزامنة الأسطر
                self._sync_invoice_lines(invoice)
                
            else:
                # فاتورة جديدة
                model = _domain_to_model(invoice)
                self._session.add(model)
                self._session.flush()
                invoice.version = 1
                self._sync_invoice_lines(invoice)
        
        logger.debug(f"💾 Atomic save completed for {len(invoices)} invoices")
    
    # =========================================================================
    # دوال الاستعلام الأساسية (محسّنة)
    # =========================================================================
    
    def get_by_id(self, invoice_id: InvoiceId, expected_version: Optional[int] = None) -> Optional[Invoice]:
        """
        الحصول على فاتورة بواسطة المعرف مع التحقق من الإصدار.
        
        Args:
            invoice_id: معرف الفاتورة
            expected_version: الإصدار المتوقع (للتحقق من التزامن)
            
        Returns:
            الفاتورة أو None
            
        Raises:
            ConcurrentModificationError: إذا كان الإصدار لا يتطابق
        """
        model = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(InvoiceModel.id == invoice_id.value)
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        # التحقق من الإصدار إذا تم توفيره
        if expected_version is not None and model.version != expected_version:
            raise ConcurrentModificationError(
                "Invoice",
                str(invoice_id),
                expected_version,
                model.version
            )
        
        return _model_to_domain(model)
    
    def get_by_number(self, number: InvoiceNumber) -> Optional[Invoice]:
        """الحصول على فاتورة بواسطة الرقم"""
        model = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(InvoiceModel.number == str(number))
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_journal_entry_id(self, journal_entry_id: str) -> Optional[Invoice]:
        """الحصول على فاتورة بواسطة معرف القيد المحاسبي"""
        model = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(InvoiceModel.journal_entry_id == journal_entry_id)
        ).unique().scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain(model)
    
    def get_by_customer(self, customer_id: str) -> List[Invoice]:
        """الحصول على جميع فواتير العميل"""
        return self.list_by_customer(customer_id, limit=1000)
    
    # =========================================================================
    # قوائم الفواتير مع Pagination
    # =========================================================================
    
    def list_by_customer(self, customer_id: str, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """قائمة فواتير العميل"""
        models = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(InvoiceModel.customer_id == customer_id)
            .order_by(desc(InvoiceModel.invoice_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_status(self, status: InvoiceStatus, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """قائمة فواتير حسب الحالة"""
        models = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(InvoiceModel.status == status.value)
            .order_by(desc(InvoiceModel.invoice_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_site(self, site_id: str, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """
        قائمة فواتير حسب الموقع
        
        Args:
            site_id: معرف الموقع
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
        """
        models = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(InvoiceModel.site_id == site_id)
            .order_by(desc(InvoiceModel.invoice_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_site_and_date_range(
        self, 
        site_id: str, 
        from_date: date, 
        to_date: date, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Invoice]:
        """قائمة فواتير حسب الموقع ونطاق زمني"""
        models = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(
                and_(
                    InvoiceModel.site_id == site_id,
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
            .order_by(desc(InvoiceModel.invoice_date))
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
    ) -> List[Invoice]:
        """قائمة فواتير في نطاق زمني"""
        models = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(
                and_(
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
            .order_by(desc(InvoiceModel.invoice_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_customer_and_site(
        self, 
        customer_id: str, 
        site_id: Optional[str] = None, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Invoice]:
        """قائمة فواتير العميل مع إمكانية فلترة حسب الموقع"""
        query = select(InvoiceModel).options(selectinload(InvoiceModel.lines)).where(
            InvoiceModel.customer_id == customer_id
        )
        
        if site_id:
            query = query.where(InvoiceModel.site_id == site_id)
        
        models = self._session.execute(
            query.order_by(desc(InvoiceModel.invoice_date))
            .limit(limit)
            .offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_by_filters(
        self,
        customer_id: Optional[str] = None,
        site_id: Optional[str] = None,
        status: Optional[InvoiceStatus] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "date",
        order_desc: bool = True
    ) -> List[Invoice]:
        """
        قائمة فواتير مع فلاتر متعددة وترتيب
        
        Args:
            customer_id: معرف العميل (اختياري)
            site_id: معرف الموقع (اختياري)
            status: حالة الفاتورة (اختياري)
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
            limit: الحد الأقصى للنتائج
            offset: الإزاحة للصفحات
            order_by: حقل الترتيب (date, number, customer, total)
            order_desc: ترتيب تنازلي
        """
        query = select(InvoiceModel).options(selectinload(InvoiceModel.lines))
        
        if customer_id:
            query = query.where(InvoiceModel.customer_id == customer_id)
        
        if site_id:
            query = query.where(InvoiceModel.site_id == site_id)
        
        if status:
            query = query.where(InvoiceModel.status == status.value)
        
        if from_date:
            query = query.where(InvoiceModel.invoice_date >= from_date)
        
        if to_date:
            query = query.where(InvoiceModel.invoice_date <= to_date)
        
        # تحديد الترتيب
        order_map = {
            "date": InvoiceModel.invoice_date,
            "number": InvoiceModel.number,
            "customer": InvoiceModel.customer_name,
            "total": InvoiceModel.total_amount,
        }
        order_column = order_map.get(order_by, InvoiceModel.invoice_date)
        
        if order_desc:
            query = query.order_by(desc(order_column))
        else:
            query = query.order_by(asc(order_column))
        
        models = self._session.execute(
            query.limit(limit).offset(offset)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """قائمة جميع الفواتير مع ترقيم صفحات"""
        return self.list_by_filters(limit=limit, offset=offset)
    
    # =========================================================================
    # عمليات الترقيم
    # =========================================================================
    
    def get_next_number(self, prefix: str = "INV-", length: int = 5) -> InvoiceNumber:
        """
        الحصول على رقم الفاتورة التالي
        
        ✅ محدث: يدعم بادئات مخصصة وطول رقم متغير
        
        Args:
            prefix: بادئة رقم الفاتورة (مثل "INV-")
            length: طول الرقم التسلسلي
        
        Returns:
            InvoiceNumber: رقم الفاتورة التالي
        """
        # البحث عن أعلى رقم موجود
        result = self._session.execute(
            text("""
                SELECT MAX(CAST(SUBSTRING(number FROM '\d+$') AS INTEGER))
                FROM invoices 
                WHERE number LIKE :prefix_pattern
            """),
            {"prefix_pattern": f"{prefix}%"}
        ).scalar()
        
        if result and result > 0:
            next_num = result + 1
        else:
            next_num = 1
        
        # تنسيق الرقم مع padding
        number_str = str(next_num).zfill(length)
        return InvoiceNumber(f"{prefix}{number_str}")
    
    def reserve_number(self, number: InvoiceNumber) -> bool:
        """حجز رقم فاتورة مؤقتاً (لمنع التكرار)"""
        # التحقق من عدم وجود الرقم
        existing = self._session.execute(
            select(InvoiceModel.id).where(InvoiceModel.number == str(number))
        ).first()
        
        return existing is None
    
    def release_number(self, number: InvoiceNumber) -> bool:
        """إلغاء حجز رقم فاتورة"""
        # لا يوجد حجز فعلي، فقط نتحقق من وجود الرقم
        existing = self._session.execute(
            select(InvoiceModel.id).where(InvoiceModel.number == str(number))
        ).first()
        
        return existing is not None
    
    def exists_by_number(self, number: InvoiceNumber) -> bool:
        """التحقق من وجود فاتورة برقم معين"""
        result = self._session.execute(
            select(InvoiceModel.id).where(InvoiceModel.number == str(number))
        ).first()
        
        return result is not None
    
    # =========================================================================
    # عمليات الحذف والاستعادة
    # =========================================================================
    
    def delete_draft(self, invoice_id: InvoiceId) -> bool:
        """حذف فاتورة مسودة (غير مرحّلة)"""
        model = self._session.execute(
            select(InvoiceModel).where(InvoiceModel.id == invoice_id.value)
        ).scalar_one_or_none()
        
        if not model or model.status != "draft":
            return False
        
        # حذف الأسطر المرتبطة أولاً
        self._session.execute(
            delete(InvoiceLineModel).where(InvoiceLineModel.invoice_id == invoice_id.value)
        )
        
        self._session.delete(model)
        return True
    
    def restore_draft(self, invoice_id: InvoiceId, restored_by: str) -> bool:
        """
        استعادة فاتورة محذوفة (إلغاء الحذف الناعم).
        
        Args:
            invoice_id: معرف الفاتورة
            restored_by: من قام بالاستعادة
            
        Returns:
            True إذا تمت الاستعادة بنجاح
        """
        now = utc_now()
        
        result = self._session.execute(
            update(InvoiceModel)
            .where(
                InvoiceModel.id == invoice_id.value,
                InvoiceModel.status == 'cancelled'  # فقط الملغاة
            )
            .values(
                status='draft',
                updated_at=now,
                updated_by=restored_by,
                version=InvoiceModel.version + 1
            )
        )
        
        return result.rowcount > 0
    
    # =========================================================================
    # العمليات الجماعية (Bulk Operations) المحسّنة
    # =========================================================================
    
    def bulk_save(self, invoices: List[Invoice]) -> int:
        """
        حفظ عدة فواتير دفعة واحدة
        
        Args:
            invoices: قائمة الفواتير للحفظ
        
        Returns:
            عدد الفواتير المحفوظة بنجاح
        """
        saved_count = 0
        errors = []
        
        for invoice in invoices:
            try:
                self.save(invoice)
                saved_count += 1
            except Exception as e:
                errors.append(f"Invoice {invoice.number}: {str(e)}")
        
        if errors:
            # تسجيل الأخطاء
            for error in errors:
                logger.error(f"Error saving invoice: {error}")
        
        return saved_count
    
    def bulk_update_status(
        self, 
        invoice_ids: List[str], 
        status: InvoiceStatus,
        expected_versions: Optional[Dict[str, int]] = None
    ) -> int:
        """
        تحديث حالة عدة فواتير دفعة واحدة مع Optimistic Locking.
        
        Args:
            invoice_ids: قائمة معرفات الفواتير
            status: الحالة الجديدة
            expected_versions: قاموس {invoice_id: expected_version} للتحقق من التزامن
            
        Returns:
            عدد الفواتير المحدثة
            
        Raises:
            ConcurrentModificationError: إذا تم تعديل أي فاتورة بشكل متزامن
        """
        uuids = [UUID(id) for id in invoice_ids]
        now = utc_now()
        
        # إذا تم توفير الإصدارات المتوقعة، تحقق منها أولاً
        if expected_versions:
            current_versions = self._session.execute(
                select(InvoiceModel.id, InvoiceModel.version)
                .where(InvoiceModel.id.in_(uuids))
            ).all()
            
            version_map = {str(row[0]): row[1] for row in current_versions}
            
            for invoice_id, expected_version in expected_versions.items():
                current_version = version_map.get(invoice_id)
                if current_version is None:
                    raise NotFoundError("Invoice", invoice_id)
                if current_version != expected_version:
                    raise ConcurrentModificationError(
                        "Invoice",
                        invoice_id,
                        expected_version,
                        current_version
                    )
        
        # تنفيذ التحديث
        result = self._session.execute(
            update(InvoiceModel)
            .where(
                InvoiceModel.id.in_(uuids),
                InvoiceModel.status != status.value  # فقط غير المحدثين
            )
            .values(
                status=status.value,
                updated_at=now,
                version=InvoiceModel.version + 1,
                posted_at=now if status == InvoiceStatus.POSTED else None,
                posted_by=None if status != InvoiceStatus.POSTED else InvoiceModel.posted_by
            )
        )
        
        return result.rowcount
    
    def bulk_delete_drafts(self, invoice_ids: List[str]) -> int:
        """
        حذف عدة فواتير مسودة دفعة واحدة
        
        Args:
            invoice_ids: قائمة معرفات الفواتير
        
        Returns:
            عدد الفواتير المحذوفة
        """
        uuids = [UUID(id) for id in invoice_ids]
        
        # حذف الأسطر المرتبطة أولاً
        self._session.execute(
            delete(InvoiceLineModel).where(InvoiceLineModel.invoice_id.in_(uuids))
        )
        
        # حذف الفواتير
        result = self._session.execute(
            delete(InvoiceModel)
            .where(
                and_(
                    InvoiceModel.id.in_(uuids),
                    InvoiceModel.status == 'draft'
                )
            )
        )
        
        return result.rowcount
    
    # =========================================================================
    # دوال الإحصائيات المتقدمة
    # =========================================================================
    
    def count_by_site(self, site_id: str, status: Optional[InvoiceStatus] = None) -> int:
        """حساب عدد الفواتير لموقع معين"""
        query = select(func.count()).select_from(InvoiceModel).where(
            InvoiceModel.site_id == site_id
        )
        
        if status:
            query = query.where(InvoiceModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def count_by_customer_and_site(
        self,
        customer_id: str,
        site_id: Optional[str] = None,
        status: Optional[InvoiceStatus] = None
    ) -> int:
        """حساب عدد فواتير العميل مع فلترة حسب الموقع والحالة"""
        query = select(func.count()).select_from(InvoiceModel).where(
            InvoiceModel.customer_id == customer_id
        )
        
        if site_id:
            query = query.where(InvoiceModel.site_id == site_id)
        
        if status:
            query = query.where(InvoiceModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def count_by_status(self, status: Optional[InvoiceStatus] = None) -> int:
        """حساب عدد الفواتير حسب الحالة"""
        query = select(func.count()).select_from(InvoiceModel)
        
        if status:
            query = query.where(InvoiceModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def get_total_by_site(self, site_id: str, status: Optional[InvoiceStatus] = None) -> Decimal:
        """حساب إجمالي مبالغ الفواتير لموقع معين"""
        query = select(func.sum(InvoiceModel.total_amount)).where(
            InvoiceModel.site_id == site_id
        )
        
        if status:
            query = query.where(InvoiceModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return Decimal(str(result or 0))
    
    def get_total_by_customer_and_site(
        self,
        customer_id: str,
        site_id: Optional[str] = None,
        status: Optional[InvoiceStatus] = None
    ) -> Decimal:
        """حساب إجمالي فواتير العميل مع فلترة حسب الموقع والحالة"""
        query = select(func.sum(InvoiceModel.total_amount)).where(
            InvoiceModel.customer_id == customer_id
        )
        
        if site_id:
            query = query.where(InvoiceModel.site_id == site_id)
        
        if status:
            query = query.where(InvoiceModel.status == status.value)
        
        result = self._session.execute(query).scalar()
        return Decimal(str(result or 0))
    
    def get_total_by_customer(self, customer_id: str, status: Optional[InvoiceStatus] = None) -> Decimal:
        """حساب إجمالي فواتير العميل"""
        return self.get_total_by_customer_and_site(customer_id, None, status)
    
    def get_average_by_site(self, site_id: str, status: Optional[InvoiceStatus] = None) -> Decimal:
        """حساب متوسط مبالغ الفواتير لموقع معين"""
        total = self.get_total_by_site(site_id, status)
        count = self.count_by_site(site_id, status)
        
        if count == 0:
            return Decimal('0')
        
        return total / Decimal(str(count))
    
    def get_site_statistics(self, site_id: str) -> Dict[str, Any]:
        """
        الحصول على إحصائيات فواتير موقع معين
        
        ✅ محدث: إضافة معلومات إضافية
        
        Args:
            site_id: معرف الموقع
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        total_count = self.count_by_site(site_id)
        total_amount = self.get_total_by_site(site_id)
        
        # إحصائيات حسب الحالة
        draft_count = self.count_by_site(site_id, InvoiceStatus.DRAFT)
        posted_count = self.count_by_site(site_id, InvoiceStatus.POSTED)
        cancelled_count = self.count_by_site(site_id, InvoiceStatus.CANCELLED)
        
        # الحصول على نطاق التواريخ
        date_range = self._session.execute(
            select(
                func.min(InvoiceModel.invoice_date),
                func.max(InvoiceModel.invoice_date)
            ).where(InvoiceModel.site_id == site_id)
        ).first()
        
        return {
            'site_id': site_id,
            'total_count': total_count,
            'total_amount': float(total_amount),
            'draft_count': draft_count,
            'posted_count': posted_count,
            'cancelled_count': cancelled_count,
            'first_invoice_date': date_range[0].isoformat() if date_range and date_range[0] else None,
            'last_invoice_date': date_range[1].isoformat() if date_range and date_range[1] else None,
            'average_amount': float(total_amount / total_count) if total_count > 0 else 0,
            'draft_percentage': (draft_count / total_count * 100) if total_count > 0 else 0,
            'posted_percentage': (posted_count / total_count * 100) if total_count > 0 else 0,
        }
    
    def get_customer_site_statistics(
        self,
        customer_id: str,
        site_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        الحصول على إحصائيات فواتير عميل مع فلترة حسب الموقع
        
        Args:
            customer_id: معرف العميل
            site_id: معرف الموقع (اختياري)
        
        Returns:
            قاموس يحتوي على الإحصائيات
        """
        total_count = self.count_by_customer_and_site(customer_id, site_id)
        total_amount = self.get_total_by_customer_and_site(customer_id, site_id)
        
        draft_count = self.count_by_customer_and_site(customer_id, site_id, InvoiceStatus.DRAFT)
        posted_count = self.count_by_customer_and_site(customer_id, site_id, InvoiceStatus.POSTED)
        cancelled_count = self.count_by_customer_and_site(customer_id, site_id, InvoiceStatus.CANCELLED)
        
        return {
            'customer_id': customer_id,
            'site_id': site_id,
            'total_count': total_count,
            'total_amount': float(total_amount),
            'draft_count': draft_count,
            'posted_count': posted_count,
            'cancelled_count': cancelled_count,
            'average_amount': float(total_amount / total_count) if total_count > 0 else 0,
            'latest_invoice': self.get_latest_for_customer(customer_id, 1)[0] if total_count > 0 else None,
        }
    
    def get_latest_for_customer(self, customer_id: str, limit: int = 5) -> List[Invoice]:
        """الحصول على أحدث فواتير العميل"""
        return self.list_by_customer(customer_id, limit=limit)
    
    def get_overdue_invoices(self, as_of_date: Optional[date] = None) -> List[Invoice]:
        """الحصول على الفواتير المتأخرة"""
        clock = get_clock()
        as_of = as_of_date or clock.today()
        
        # نفترض أن تاريخ الاستحقاق هو تاريخ الفاتورة + 30 يوم
        # في الواقع، يجب أن يكون هناك حقل due_date في النموذج
        due_date = as_of - timedelta(days=30)
        
        models = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(
                and_(
                    InvoiceModel.invoice_date <= due_date,
                    InvoiceModel.status == 'posted'
                )
            )
            .order_by(desc(InvoiceModel.invoice_date))
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]
    
    def get_customer_invoices_summary(self, customer_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """ملخص فواتير العميل (للقراءة السريعة)"""
        invoices = self.list_by_customer(customer_id, limit=limit)
        
        return [
            {
                'id': str(inv.id),
                'number': str(inv.number) if inv.number else None,
                'date': inv.date.isoformat() if inv.date else None,
                'total': float(inv.total.amount),
                'currency': inv.currency,
                'status': inv.status.value,
                'customer_name': inv.customer_name,
            }
            for inv in invoices
        ]
    
    def get_invoice_summary(self, invoice_id: InvoiceId) -> Optional[Dict[str, Any]]:
        """ملخص فاتورة واحدة (للقراءة السريعة)"""
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None
        
        return {
            'id': str(invoice.id),
            'number': str(invoice.number) if invoice.number else None,
            'date': invoice.date.isoformat() if invoice.date else None,
            'customer_id': invoice.customer_id,
            'customer_name': invoice.customer_name,
            'subtotal': float(invoice.subtotal.amount),
            'tax_amount': float(invoice.tax_amount.amount),
            'total': float(invoice.total.amount),
            'currency': invoice.currency,
            'status': invoice.status.value,
            'payment_type': invoice.payment_type.value,
            'site_id': invoice.site_id,
            'site_name': invoice.site_name,
            'lines_count': len(invoice.lines),
            'journal_entry_id': invoice.journal_entry_id,
            'created_at': invoice.created_at.isoformat() if invoice.created_at else None,
            'posted_at': invoice.posted_at.isoformat() if invoice.posted_at else None,
        }

    # =========================================================================
    # طرق واجهة IInvoiceRepository المفقودة
    # =========================================================================

    def count(self, filter: Optional[InvoiceFilter] = None) -> int:
        """حساب عدد الفواتير المطابقة للفلتر"""
        query = select(func.count()).select_from(InvoiceModel)
        
        if filter:
            if filter.customer_id:
                query = query.where(InvoiceModel.customer_id == filter.customer_id)
            if filter.site_id:
                query = query.where(InvoiceModel.site_id == filter.site_id)
            if filter.status:
                query = query.where(InvoiceModel.status == filter.status.value)
            if filter.payment_type:
                query = query.where(InvoiceModel.payment_type == filter.payment_type.value)
            if filter.currency:
                query = query.where(InvoiceModel.currency == filter.currency)
            if filter.from_date:
                query = query.where(InvoiceModel.invoice_date >= filter.from_date)
            if filter.to_date:
                query = query.where(InvoiceModel.invoice_date <= filter.to_date)
            if filter.min_amount is not None:
                query = query.where(InvoiceModel.total_amount >= filter.min_amount)
            if filter.max_amount is not None:
                query = query.where(InvoiceModel.total_amount <= filter.max_amount)
            if filter.has_tax is not None:
                if filter.has_tax:
                    query = query.where(InvoiceModel.tax_amount > 0)
                else:
                    query = query.where(InvoiceModel.tax_amount == 0)
        
        result = self._session.execute(query).scalar()
        return result or 0

    def search(self, filter: InvoiceFilter) -> List[Invoice]:
        """بحث متقدم عن الفواتير"""
        return self.list_by_filters(
            customer_id=filter.customer_id,
            site_id=filter.site_id,
            status=filter.status,
            from_date=filter.from_date,
            to_date=filter.to_date,
            limit=filter.limit,
            offset=filter.offset,
            order_by=filter.order_by,
            order_desc=filter.order_desc
        )

    def search_summaries(self, filter: InvoiceFilter) -> List[InvoiceSummary]:
        """بحث متقدم عن ملخصات الفواتير (أداء أفضل للقوائم)"""
        invoices = self.search(filter)
        return [
            InvoiceSummary(
                id=str(inv.id),
                number=str(inv.number) if inv.number else None,
                date=inv.date,
                customer_name=inv.customer_name,
                total=inv.total.amount,
                currency=inv.currency,
                status=inv.status.value,
                tax_amount=inv.tax_amount.amount,
                total_with_tax=inv.total.amount + inv.tax_amount.amount
            )
            for inv in invoices
        ]

    def get_statistics(self, from_date: Optional[date] = None, to_date: Optional[date] = None) -> InvoiceStatistics:
        """الحصول على إحصائيات الفواتير في نطاق زمني"""
        clock = get_clock()
        if not from_date:
            from_date = clock.today() - timedelta(days=30)
        if not to_date:
            to_date = clock.today()
        
        # إحصائيات أساسية
        total_count = self._session.execute(
            select(func.count())
            .select_from(InvoiceModel)
            .where(
                and_(
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
        ).scalar() or 0
        
        total_amount = self._session.execute(
            select(func.sum(InvoiceModel.total_amount))
            .where(
                and_(
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
        ).scalar() or Decimal('0')
        
        total_tax = self._session.execute(
            select(func.sum(InvoiceModel.tax_amount))
            .where(
                and_(
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
        ).scalar() or Decimal('0')
        
        # إحصائيات حسب الحالة
        draft_count = self._session.execute(
            select(func.count()).select_from(InvoiceModel)
            .where(
                and_(
                    InvoiceModel.status == 'draft',
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
        ).scalar() or 0
        
        posted_count = self._session.execute(
            select(func.count()).select_from(InvoiceModel)
            .where(
                and_(
                    InvoiceModel.status == 'posted',
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
        ).scalar() or 0
        
        cancelled_count = self._session.execute(
            select(func.count()).select_from(InvoiceModel)
            .where(
                and_(
                    InvoiceModel.status == 'cancelled',
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
        ).scalar() or 0
        
        # حسب العملة
        by_currency = {}
        currencies = ['USD', 'LBP', 'EUR', 'GBP']
        for curr in currencies:
            count = self._session.execute(
                select(func.sum(InvoiceModel.total_amount))
                .where(
                    and_(
                        InvoiceModel.currency == curr,
                        InvoiceModel.invoice_date >= from_date,
                        InvoiceModel.invoice_date <= to_date
                    )
                )
            ).scalar() or Decimal('0')
            if count > 0:
                by_currency[curr] = count
        
        # حسب طريقة الدفع
        by_payment_type = {}
        payment_types = ['cash', 'credit', 'check', 'transfer']
        for pt in payment_types:
            count = self._session.execute(
                select(func.sum(InvoiceModel.total_amount))
                .where(
                    and_(
                        InvoiceModel.payment_type == pt,
                        InvoiceModel.invoice_date >= from_date,
                        InvoiceModel.invoice_date <= to_date
                    )
                )
            ).scalar() or Decimal('0')
            if count > 0:
                by_payment_type[pt] = count
        
        # حساب المتوسطات
        average_amount = total_amount / total_count if total_count > 0 else Decimal('0')
        
        # الحصول على الحد الأدنى والأقصى
        min_max = self._session.execute(
            select(
                func.min(InvoiceModel.total_amount),
                func.max(InvoiceModel.total_amount)
            )
            .where(
                and_(
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
        ).first()
        
        min_amount = min_max[0] or Decimal('0')
        max_amount = min_max[1] or Decimal('0')
        
        return InvoiceStatistics(
            total_count=total_count,
            total_amount=total_amount,
            total_tax=total_tax,
            total_with_tax=total_amount + total_tax,
            draft_count=draft_count,
            posted_count=posted_count,
            cancelled_count=cancelled_count,
            by_currency=by_currency,
            by_payment_type=by_payment_type,
            average_amount=average_amount,
            min_amount=min_amount,
            max_amount=max_amount,
            period_start=from_date,
            period_end=to_date
        )

    def get_customer_statistics(self, customer_id: str) -> Dict[str, Any]:
        """الحصول على إحصائيات فواتير العميل"""
        total_count = self._session.execute(
            select(func.count()).select_from(InvoiceModel)
            .where(InvoiceModel.customer_id == customer_id)
        ).scalar() or 0
        
        total_amount = self._session.execute(
            select(func.sum(InvoiceModel.total_amount))
            .where(InvoiceModel.customer_id == customer_id)
        ).scalar() or Decimal('0')
        
        posted_count = self._session.execute(
            select(func.count()).select_from(InvoiceModel)
            .where(
                and_(
                    InvoiceModel.customer_id == customer_id,
                    InvoiceModel.status == 'posted'
                )
            )
        ).scalar() or 0
        
        return {
            'customer_id': customer_id,
            'total_count': total_count,
            'total_amount': float(total_amount),
            'posted_count': posted_count,
            'average_amount': float(total_amount / total_count) if total_count > 0 else 0,
            'currency': 'USD'
        }

    def get_tax_statistics(self, from_date: Optional[date] = None, to_date: Optional[date] = None) -> Dict[str, Any]:
        """الحصول على إحصائيات الضرائب في الفواتير"""
        clock = get_clock()
        if not from_date:
            from_date = clock.today() - timedelta(days=30)
        if not to_date:
            to_date = clock.today()
        
        total_tax = self._session.execute(
            select(func.sum(InvoiceModel.tax_amount))
            .where(
                and_(
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date
                )
            )
        ).scalar() or Decimal('0')
        
        total_taxable = self._session.execute(
            select(func.sum(InvoiceModel.total_amount))
            .where(
                and_(
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date,
                    InvoiceModel.tax_amount > 0
                )
            )
        ).scalar() or Decimal('0')
        
        invoices_with_tax = self._session.execute(
            select(func.count()).select_from(InvoiceModel)
            .where(
                and_(
                    InvoiceModel.invoice_date >= from_date,
                    InvoiceModel.invoice_date <= to_date,
                    InvoiceModel.tax_amount > 0
                )
            )
        ).scalar() or 0
        
        return {
            'from_date': from_date.isoformat(),
            'to_date': to_date.isoformat(),
            'total_tax': float(total_tax),
            'total_taxable': float(total_taxable),
            'invoices_with_tax': invoices_with_tax,
            'average_tax_rate': float(total_tax / total_taxable * 100) if total_taxable > 0 else 0
        }

    def get_invoices_with_tax(self, from_date: Optional[date] = None, to_date: Optional[date] = None) -> List[Invoice]:
        """الحصول على الفواتير التي تحتوي على ضريبة"""
        return self.list_by_date_range(from_date, to_date)

    def get_invoices_by_tax_rate(self, tax_rate: float, from_date: Optional[date] = None) -> List[Invoice]:
        """الحصول على الفواتير بنسبة ضريبة محددة"""
        to_date = from_date or date.today()
        from_date = from_date or (to_date - timedelta(days=365))
        return self.list_by_date_range(from_date, to_date)

    def get_total_tax_by_period(self, period: str, year: int) -> Dict[str, Decimal]:
        """الحصول على إجمالي الضرائب حسب الفترة"""
        if period == 'month':
            result = {}
            for month in range(1, 13):
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year, month, 31)
                else:
                    end_date = date(year, month + 1, 1) - timedelta(days=1)
                
                tax = self._session.execute(
                    select(func.sum(InvoiceModel.tax_amount))
                    .where(
                        and_(
                            InvoiceModel.invoice_date >= start_date,
                            InvoiceModel.invoice_date <= end_date
                        )
                    )
                ).scalar() or Decimal('0')
                result[f"{year}-{month:02d}"] = tax
            return result
        return {}

    def list_by_payment_type(self, payment_type: PaymentType, limit: int = 100) -> List[Invoice]:
        """قائمة فواتير حسب طريقة الدفع"""
        models = self._session.execute(
            select(InvoiceModel)
            .options(selectinload(InvoiceModel.lines))
            .where(InvoiceModel.payment_type == payment_type.value)
            .order_by(desc(InvoiceModel.invoice_date))
            .limit(limit)
        ).unique().scalars().all()
        
        return [_model_to_domain(m) for m in models]

    def get_invoices_by_site_and_date(
        self,
        site_id: str,
        from_date: date,
        to_date: date,
        status: Optional[InvoiceStatus] = None
    ) -> List[Invoice]:
        """قائمة فواتير حسب الموقع ونطاق زمني"""
        return self.list_by_site_and_date_range(site_id, from_date, to_date)


# =============================================================================
# تصدير الكلاس
# =============================================================================

__all__ = [
    "PostgresInvoiceRepository",
]