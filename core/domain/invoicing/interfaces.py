# core/domain/invoicing/interfaces.py
"""
Repository Interfaces for Invoicing Context
✅ محدث: دعم البحث المتقدم بالضرائب
✅ محدث: دعم إحصائيات الفواتير
✅ محدث: دعم الفلترة المتقدمة
✅ محدث: دعم التحديث الجماعي
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from .value_objects import InvoiceId, InvoiceNumber, InvoiceStatus, PaymentType
from .entities import Invoice


# =============================================================================
# DTOs للإحصائيات والتقارير
# =============================================================================

class InvoiceSummary:
    """ملخص فاتورة - للقراءة السريعة"""
    def __init__(
        self,
        id: str,
        number: str,
        date: datetime,
        customer_name: str,
        total: Decimal,
        currency: str,
        status: str,
        tax_amount: Decimal = Decimal('0'),
        total_with_tax: Decimal = Decimal('0')
    ):
        self.id = id
        self.number = number
        self.date = date
        self.customer_name = customer_name
        self.total = total
        self.currency = currency
        self.status = status
        self.tax_amount = tax_amount
        self.total_with_tax = total_with_tax


class InvoiceStatistics:
    """إحصائيات الفواتير"""
    def __init__(
        self,
        total_count: int,
        total_amount: Decimal,
        total_tax: Decimal,
        total_with_tax: Decimal,
        draft_count: int,
        posted_count: int,
        cancelled_count: int,
        by_currency: Dict[str, Decimal],
        by_payment_type: Dict[str, Decimal],
        average_amount: Decimal,
        min_amount: Decimal,
        max_amount: Decimal,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ):
        self.total_count = total_count
        self.total_amount = total_amount
        self.total_tax = total_tax
        self.total_with_tax = total_with_tax
        self.draft_count = draft_count
        self.posted_count = posted_count
        self.cancelled_count = cancelled_count
        self.by_currency = by_currency
        self.by_payment_type = by_payment_type
        self.average_amount = average_amount
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.period_start = period_start
        self.period_end = period_end


class InvoiceFilter:
    """فلتر البحث عن الفواتير"""
    def __init__(
        self,
        customer_id: Optional[str] = None,
        site_id: Optional[str] = None,
        status: Optional[InvoiceStatus] = None,
        payment_type: Optional[PaymentType] = None,
        currency: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        has_tax: Optional[bool] = None,
        search_text: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "date",
        order_desc: bool = True
    ):
        self.customer_id = customer_id
        self.site_id = site_id
        self.status = status
        self.payment_type = payment_type
        self.currency = currency
        self.from_date = from_date
        self.to_date = to_date
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.has_tax = has_tax
        self.search_text = search_text
        self.limit = limit
        self.offset = offset
        self.order_by = order_by
        self.order_desc = order_desc


# =============================================================================
# واجهة المستودع الرئيسية
# =============================================================================

class IInvoiceRepository(ABC):
    """
    Repository Interface for Invoice Aggregate
    ✅ محدث: دعم البحث المتقدم والضرائب والإحصائيات
    """

    # =========================================================================
    # العمليات الأساسية
    # =========================================================================

    @abstractmethod
    def save(self, invoice: Invoice) -> None:
        """حفظ الفاتورة (جديدة أو محدثة)"""
        pass

    @abstractmethod
    def get_by_id(self, invoice_id: InvoiceId) -> Optional[Invoice]:
        """الحصول على فاتورة بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_number(self, number: InvoiceNumber) -> Optional[Invoice]:
        """الحصول على فاتورة بواسطة الرقم"""
        pass

    @abstractmethod
    def get_by_journal_entry_id(self, journal_entry_id: str) -> Optional[Invoice]:
        """الحصول على فاتورة بواسطة معرف القيد المحاسبي"""
        pass

    @abstractmethod
    def delete_draft(self, invoice_id: InvoiceId) -> bool:
        """حذف فاتورة مسودة (غير مرحّلة)"""
        pass

    # =========================================================================
    # القوائم والبحث
    # =========================================================================

    @abstractmethod
    def list_by_customer(self, customer_id: str, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """قائمة فواتير العميل"""
        pass

    @abstractmethod
    def list_by_status(self, status: InvoiceStatus, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """قائمة فواتير حسب الحالة"""
        pass

    @abstractmethod
    def list_by_date_range(
        self, 
        from_date: date, 
        to_date: date, 
        limit: int = 100,
        offset: int = 0
    ) -> List[Invoice]:
        """قائمة فواتير في نطاق زمني"""
        pass

    @abstractmethod
    def list_by_site(self, site_id: str, limit: int = 100, offset: int = 0) -> List[Invoice]:
        """قائمة فواتير حسب الموقع"""
        pass

    @abstractmethod
    def list_by_payment_type(self, payment_type: PaymentType, limit: int = 100) -> List[Invoice]:
        """قائمة فواتير حسب طريقة الدفع"""
        pass

    @abstractmethod
    def search(self, filter: InvoiceFilter) -> List[Invoice]:
        """
        بحث متقدم عن الفواتير باستخدام InvoiceFilter
        
        Args:
            filter: كائن الفلتر
        
        Returns:
            قائمة الفواتير المطابقة للبحث
        """
        pass

    @abstractmethod
    def search_summaries(self, filter: InvoiceFilter) -> List[InvoiceSummary]:
        """
        بحث متقدم عن ملخصات الفواتير (أداء أفضل للقوائم)
        
        Args:
            filter: كائن الفلتر
        
        Returns:
            قائمة ملخصات الفواتير
        """
        pass

    @abstractmethod
    def count(self, filter: Optional[InvoiceFilter] = None) -> int:
        """
        حساب عدد الفواتير المطابقة للفلتر
        
        Args:
            filter: كائن الفلتر (اختياري)
        
        Returns:
            عدد الفواتير
        """
        pass

    # =========================================================================
    # إحصائيات وتقارير
    # =========================================================================

    @abstractmethod
    def get_statistics(self, from_date: Optional[date] = None, to_date: Optional[date] = None) -> InvoiceStatistics:
        """
        الحصول على إحصائيات الفواتير في نطاق زمني
        
        Args:
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
        
        Returns:
            كائن InvoiceStatistics
        """
        pass

    @abstractmethod
    def get_customer_statistics(self, customer_id: str) -> Dict[str, Any]:
        """
        الحصول على إحصائيات فواتير العميل
        
        Args:
            customer_id: معرف العميل
        
        Returns:
            قاموس بالإحصائيات
        """
        pass

    @abstractmethod
    def get_site_statistics(self, site_id: str) -> Dict[str, Any]:
        """
        الحصول على إحصائيات فواتير الموقع
        
        Args:
            site_id: معرف الموقع
        
        Returns:
            قاموس بالإحصائيات
        """
        pass

    @abstractmethod
    def get_tax_statistics(self, from_date: Optional[date] = None, to_date: Optional[date] = None) -> Dict[str, Any]:
        """
        الحصول على إحصائيات الضرائب في الفواتير
        
        Args:
            from_date: تاريخ البداية (اختياري)
            to_date: تاريخ النهاية (اختياري)
        
        Returns:
            قاموس بإحصائيات الضرائب
        """
        pass

    # =========================================================================
    # عمليات خاصة بالضرائب
    # =========================================================================

    @abstractmethod
    def get_invoices_with_tax(self, from_date: Optional[date] = None, to_date: Optional[date] = None) -> List[Invoice]:
        """الحصول على الفواتير التي تحتوي على ضريبة"""
        pass

    @abstractmethod
    def get_invoices_by_tax_rate(self, tax_rate: float, from_date: Optional[date] = None) -> List[Invoice]:
        """الحصول على الفواتير بنسبة ضريبة محددة"""
        pass

    @abstractmethod
    def get_total_tax_by_period(self, period: str, year: int) -> Dict[str, Decimal]:
        """
        الحصول على إجمالي الضرائب حسب الفترة
        
        Args:
            period: 'month', 'quarter', 'year'
            year: السنة
        
        Returns:
            قاموس {period: total_tax}
        """
        pass

    # =========================================================================
    # العمليات الجماعية
    # =========================================================================

    @abstractmethod
    def bulk_save(self, invoices: List[Invoice]) -> int:
        """
        حفظ عدة فواتير دفعة واحدة
        
        Args:
            invoices: قائمة الفواتير
        
        Returns:
            عدد الفواتير المحفوظة
        """
        pass

    @abstractmethod
    def bulk_update_status(self, invoice_ids: List[str], status: InvoiceStatus) -> int:
        """
        تحديث حالة عدة فواتير دفعة واحدة
        
        Args:
            invoice_ids: قائمة معرفات الفواتير
            status: الحالة الجديدة
        
        Returns:
            عدد الفواتير المحدثة
        """
        pass

    @abstractmethod
    def bulk_delete_drafts(self, invoice_ids: List[str]) -> int:
        """
        حذف عدة فواتير مسودة دفعة واحدة
        
        Args:
            invoice_ids: قائمة معرفات الفواتير
        
        Returns:
            عدد الفواتير المحذوفة
        """
        pass

    # =========================================================================
    # عمليات ترقيم الفواتير
    # =========================================================================

    @abstractmethod
    def get_next_number(self, prefix: Optional[str] = None, length: Optional[int] = None) -> InvoiceNumber:
        """
        الحصول على رقم الفاتورة التالي
        
        Args:
            prefix: بادئة الرقم (اختياري)
            length: طول الرقم التسلسلي (اختياري)
        
        Returns:
            InvoiceNumber: رقم الفاتورة التالي
        """
        pass

    @abstractmethod
    def reserve_number(self, number: InvoiceNumber) -> bool:
        """
        حجز رقم فاتورة مؤقتاً (لمنع التكرار)
        
        Args:
            number: رقم الفاتورة
        
        Returns:
            True إذا تم الحجز بنجاح
        """
        pass

    @abstractmethod
    def release_number(self, number: InvoiceNumber) -> bool:
        """
        إلغاء حجز رقم فاتورة
        
        Args:
            number: رقم الفاتورة
        
        Returns:
            True إذا تم الإلغاء بنجاح
        """
        pass

    # =========================================================================
    # عمليات إضافية
    # =========================================================================

    @abstractmethod
    def exists_by_number(self, number: InvoiceNumber) -> bool:
        """التحقق من وجود فاتورة برقم معين"""
        pass

    @abstractmethod
    def get_latest_for_customer(self, customer_id: str, limit: int = 5) -> List[Invoice]:
        """الحصول على أحدث فواتير العميل"""
        pass

    @abstractmethod
    def get_overdue_invoices(self, as_of_date: Optional[date] = None) -> List[Invoice]:
        """الحصول على الفواتير المتأخرة"""
        pass

    @abstractmethod
    def get_invoices_by_site_and_date(
        self,
        site_id: str,
        from_date: date,
        to_date: date,
        status: Optional[InvoiceStatus] = None
    ) -> List[Invoice]:
        """قائمة فواتير حسب الموقع ونطاق زمني"""
        pass

    @abstractmethod
    def get_customer_invoices_summary(self, customer_id: str, limit: int = 10) -> List[InvoiceSummary]:
        """ملخص فواتير العميل (للقراءة السريعة)"""
        pass


# =============================================================================
# واجهة إضافية: خدمة التقارير
# =============================================================================

class IInvoiceReportingService(ABC):
    """
    خدمة تقارير الفواتير - منفصلة عن المستودع للوضوح
    """
    
    @abstractmethod
    def generate_sales_report(
        self,
        from_date: date,
        to_date: date,
        customer_id: Optional[str] = None,
        site_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """توليد تقرير المبيعات"""
        pass

    @abstractmethod
    def generate_tax_report(
        self,
        from_date: date,
        to_date: date,
        tax_rate: Optional[float] = None
    ) -> Dict[str, Any]:
        """توليد تقرير الضرائب"""
        pass

    @abstractmethod
    def generate_customer_statement(
        self,
        customer_id: str,
        from_date: date,
        to_date: date
    ) -> Dict[str, Any]:
        """توليد كشف حساب عميل"""
        pass


# =============================================================================
# تصدير جميع الكلاسات
# =============================================================================

__all__ = [
    # DTOs
    "InvoiceSummary",
    "InvoiceStatistics",
    "InvoiceFilter",
    
    # الواجهة الرئيسية
    "IInvoiceRepository",
    
    # واجهة التقارير
    "IInvoiceReportingService",
]