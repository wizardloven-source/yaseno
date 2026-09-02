# core/application/reports/dtos.py
"""
Reports Data Transfer Objects - كائنات نقل البيانات للتقارير
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from decimal import Decimal


# =============================================================================
# DTOs الأساسية للتقارير
# =============================================================================

@dataclass(frozen=True)
class ReportParameterDTO:
    """
    معلمة تقرير - DTO
    
    Attributes:
        name: اسم المعلمة
        type: نوع المعلمة (string, number, date, boolean, list)
        value: القيمة
        label: التسمية المعروضة
        options: الخيارات المتاحة (للقوائم المنسدلة)
        required: هل المعلمة إجبارية؟
    """
    name: str
    type: str
    value: Any = None
    label: Optional[str] = None
    options: Optional[List[Dict[str, Any]]] = None
    required: bool = False


@dataclass(frozen=True)
class ReportDTO:
    """
    تقرير - DTO كامل
    
    Attributes:
        id: معرف التقرير
        name: اسم التقرير
        description: وصف التقرير
        report_type: نوع التقرير
        category: تصنيف التقرير
        format: صيغة التقرير
        parameters: قائمة المعلمات
        data: بيانات التقرير
        metadata: بيانات وصفية إضافية
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
        version: الإصدار
    """
    id: str
    name: str
    report_type: str
    category: str
    format: str = "pdf"
    description: Optional[str] = None
    parameters: List[ReportParameterDTO] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    version: int = 1
    
    @property
    def display_name(self) -> str:
        """الاسم المعروض للتقرير"""
        return f"{self.name} ({self.report_type})"
    
    @property
    def type_display(self) -> str:
        """نوع التقرير معروضاً"""
        types = {
            "trial_balance": "ميزان المراجعة",
            "balance_sheet": "الميزانية العمومية",
            "income_statement": "قائمة الدخل",
            "cash_flow": "قائمة التدفقات النقدية",
            "general_ledger": "دفتر الأستاذ العام",
            "subsidiary_ledger": "دفتر الأستاذ المساعد",
            "sales": "تقرير المبيعات",
            "purchases": "تقرير المشتريات",
            "inventory": "تقرير المخزون",
            "inventory_valuation": "تقييم المخزون",
            "low_stock": "المخزون المنخفض",
            "tax": "تقرير الضرائب",
            "profitability": "الربحية",
            "kpi": "مؤشرات الأداء",
            "customer_statement": "كشف حساب عميل",
            "supplier_statement": "كشف حساب مورد",
            "aging": "تقرير الأعمار",
        }
        return types.get(self.report_type, self.report_type)
    
    @property
    def category_display(self) -> str:
        """تصنيف التقرير معروضاً"""
        categories = {
            "financial": "مالي",
            "sales": "مبيعات",
            "purchasing": "مشتريات",
            "inventory": "مخزون",
            "tax": "ضرائب",
            "performance": "أداء",
            "customer": "عملاء",
            "supplier": "موردين",
        }
        return categories.get(self.category, self.category)
    
    @property
    def generated_at_formatted(self) -> str:
        """وقت التوليد منسقاً"""
        return self.generated_at.strftime("%Y-%m-%d %H:%M:%S")


# =============================================================================
# DTOs للتقارير المالية
# =============================================================================

@dataclass(frozen=True)
class TrialBalanceReportDTO:
    """
    تقرير ميزان المراجعة - DTO
    
    Attributes:
        as_of_date: التاريخ
        currency: العملة
        accounts: قائمة الحسابات
        total_debits: إجمالي المدين
        total_credits: إجمالي الدائن
        is_balanced: هل متوازن؟
        difference: الفرق
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    as_of_date: date
    currency: str = "USD"
    accounts: List[Dict[str, Any]] = field(default_factory=list)
    total_debits: Decimal = Decimal('0')
    total_credits: Decimal = Decimal('0')
    is_balanced: bool = True
    difference: Decimal = Decimal('0')
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def total_debits_formatted(self) -> str:
        return f"{self.total_debits:,.2f} {self.currency}"
    
    @property
    def total_credits_formatted(self) -> str:
        return f"{self.total_credits:,.2f} {self.currency}"
    
    @property
    def account_count(self) -> int:
        return len(self.accounts)


@dataclass(frozen=True)
class BalanceSheetReportDTO:
    """
    تقرير الميزانية العمومية - DTO
    
    Attributes:
        as_of_date: التاريخ
        currency: العملة
        assets: الأصول
        liabilities: الخصوم
        equity: حقوق الملكية
        ratios: النسب المالية
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    as_of_date: date
    currency: str = "USD"
    assets: Dict[str, Any] = field(default_factory=dict)
    liabilities: Dict[str, Any] = field(default_factory=dict)
    equity: Dict[str, Any] = field(default_factory=dict)
    ratios: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def total_assets(self) -> Decimal:
        return Decimal(str(self.assets.get('total', 0)))
    
    @property
    def total_liabilities(self) -> Decimal:
        return Decimal(str(self.liabilities.get('total', 0)))
    
    @property
    def total_equity(self) -> Decimal:
        return Decimal(str(self.equity.get('total', 0)))
    
    @property
    def is_balanced(self) -> bool:
        return abs(self.total_assets - (self.total_liabilities + self.total_equity)) < 0.01


@dataclass(frozen=True)
class IncomeStatementReportDTO:
    """
    تقرير قائمة الدخل - DTO
    
    Attributes:
        period_start: بداية الفترة
        period_end: نهاية الفترة
        currency: العملة
        revenue: الإيرادات
        cogs: تكلفة البضاعة المباعة
        gross_profit: إجمالي الربح
        operating_expenses: مصروفات التشغيل
        operating_profit: الربح التشغيلي
        other_income: إيرادات أخرى
        other_expenses: مصروفات أخرى
        net_income_before_tax: صافي الدخل قبل الضريبة
        income_tax: ضريبة الدخل
        net_income: صافي الدخل
        margins: هوامش الربح
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    period_start: date
    period_end: date
    currency: str = "USD"
    revenue: Decimal = Decimal('0')
    cogs: Decimal = Decimal('0')
    gross_profit: Decimal = Decimal('0')
    operating_expenses: Decimal = Decimal('0')
    operating_profit: Decimal = Decimal('0')
    other_income: Decimal = Decimal('0')
    other_expenses: Decimal = Decimal('0')
    net_income_before_tax: Decimal = Decimal('0')
    income_tax: Decimal = Decimal('0')
    net_income: Decimal = Decimal('0')
    margins: Dict[str, Decimal] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def period_display(self) -> str:
        return f"{self.period_start} إلى {self.period_end}"
    
    @property
    def is_profit(self) -> bool:
        return self.net_income > 0
    
    @property
    def is_loss(self) -> bool:
        return self.net_income < 0


# =============================================================================
# DTOs لتقارير المبيعات والمشتريات
# =============================================================================

@dataclass(frozen=True)
class SalesReportDTO:
    """
    تقرير المبيعات - DTO
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        total_sales: إجمالي المبيعات
        total_invoices: عدد الفواتير
        average_invoice: متوسط الفاتورة
        by_customer: تفصيل حسب العميل
        by_product: تفصيل حسب المنتج
        by_category: تفصيل حسب التصنيف
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    total_sales: Decimal = Decimal('0')
    total_invoices: int = 0
    average_invoice: Decimal = Decimal('0')
    by_customer: List[Dict[str, Any]] = field(default_factory=list)
    by_product: List[Dict[str, Any]] = field(default_factory=list)
    by_category: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def total_sales_formatted(self) -> str:
        return f"{self.total_sales:,.2f} {self.currency}"
    
    @property
    def average_invoice_formatted(self) -> str:
        return f"{self.average_invoice:,.2f} {self.currency}"


@dataclass(frozen=True)
class PurchasesReportDTO:
    """
    تقرير المشتريات - DTO
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        total_purchases: إجمالي المشتريات
        total_orders: عدد الطلبيات
        average_order: متوسط الطلبية
        by_supplier: تفصيل حسب المورد
        by_product: تفصيل حسب المنتج
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    total_purchases: Decimal = Decimal('0')
    total_orders: int = 0
    average_order: Decimal = Decimal('0')
    by_supplier: List[Dict[str, Any]] = field(default_factory=list)
    by_product: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def total_purchases_formatted(self) -> str:
        return f"{self.total_purchases:,.2f} {self.currency}"
    
    @property
    def average_order_formatted(self) -> str:
        return f"{self.average_order:,.2f} {self.currency}"


# =============================================================================
# DTOs لتقارير المخزون
# =============================================================================

@dataclass(frozen=True)
class InventoryReportDTO:
    """
    تقرير المخزون - DTO
    
    Attributes:
        as_of_date: التاريخ
        currency: العملة
        items: قائمة المنتجات
        total_items: عدد المنتجات
        total_value: القيمة الإجمالية
        low_stock_items: المنتجات منخفضة المخزون
        out_of_stock_items: المنتجات نافدة
        by_category: تفصيل حسب التصنيف
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    as_of_date: date
    currency: str = "USD"
    items: List[Dict[str, Any]] = field(default_factory=list)
    total_items: int = 0
    total_value: Decimal = Decimal('0')
    low_stock_items: int = 0
    out_of_stock_items: int = 0
    by_category: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def total_value_formatted(self) -> str:
        return f"{self.total_value:,.2f} {self.currency}"


# =============================================================================
# DTOs لتقارير العملاء والموردين
# =============================================================================

@dataclass(frozen=True)
class CustomerStatementReportDTO:
    """
    كشف حساب عميل - DTO
    
    Attributes:
        customer_id: معرف العميل
        customer_name: اسم العميل
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        opening_balance: الرصيد الافتتاحي
        closing_balance: الرصيد الختامي
        transactions: الحركات
        summary: الملخص
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    customer_id: str
    customer_name: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    currency: str = "USD"
    opening_balance: Decimal = Decimal('0')
    closing_balance: Decimal = Decimal('0')
    transactions: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def opening_balance_formatted(self) -> str:
        return f"{self.opening_balance:,.2f} {self.currency}"
    
    @property
    def closing_balance_formatted(self) -> str:
        return f"{self.closing_balance:,.2f} {self.currency}"


@dataclass(frozen=True)
class SupplierStatementReportDTO:
    """
    كشف حساب مورد - DTO
    
    Attributes:
        supplier_id: معرف المورد
        supplier_name: اسم المورد
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        opening_balance: الرصيد الافتتاحي
        closing_balance: الرصيد الختامي
        transactions: الحركات
        summary: الملخص
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    supplier_id: str
    supplier_name: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    currency: str = "USD"
    opening_balance: Decimal = Decimal('0')
    closing_balance: Decimal = Decimal('0')
    transactions: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def opening_balance_formatted(self) -> str:
        return f"{self.opening_balance:,.2f} {self.currency}"
    
    @property
    def closing_balance_formatted(self) -> str:
        return f"{self.closing_balance:,.2f} {self.currency}"


# =============================================================================
# DTOs لتقارير الأداء والتحليل
# =============================================================================

@dataclass(frozen=True)
class KPIReportDTO:
    """
    تقرير مؤشرات الأداء - DTO
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        sales: مؤشرات المبيعات
        purchases: مؤشرات المشتريات
        inventory: مؤشرات المخزون
        customers: مؤشرات العملاء
        ratios: النسب المالية
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    sales: Dict[str, Any] = field(default_factory=dict)
    purchases: Dict[str, Any] = field(default_factory=dict)
    inventory: Dict[str, Any] = field(default_factory=dict)
    customers: Dict[str, Any] = field(default_factory=dict)
    ratios: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"


@dataclass(frozen=True)
class ProfitabilityReportDTO:
    """
    تقرير الربحية - DTO
    
    Attributes:
        from_date: بداية الفترة
        to_date: نهاية الفترة
        currency: العملة
        group_by: التجميع حسب
        total_revenue: إجمالي الإيرادات
        total_cost: إجمالي التكاليف
        total_profit: إجمالي الربح
        total_margin: هامش الربح الإجمالي
        items: تفصيل البنود
        generated_at: وقت التوليد
        generated_by: من قام بالتوليد
    """
    from_date: date
    to_date: date
    currency: str = "USD"
    group_by: str = "product"  # product, customer, category, site
    total_revenue: Decimal = Decimal('0')
    total_cost: Decimal = Decimal('0')
    total_profit: Decimal = Decimal('0')
    total_margin: Decimal = Decimal('0')
    items: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    generated_by: str = "system"
    
    @property
    def total_revenue_formatted(self) -> str:
        return f"{self.total_revenue:,.2f} {self.currency}"
    
    @property
    def total_cost_formatted(self) -> str:
        return f"{self.total_cost:,.2f} {self.currency}"
    
    @property
    def total_profit_formatted(self) -> str:
        return f"{self.total_profit:,.2f} {self.currency}"
    
    @property
    def total_margin_formatted(self) -> str:
        return f"{self.total_margin:.2f}%"


# =============================================================================
# DTOs للجدولة والتصدير
# =============================================================================

@dataclass(frozen=True)
class ReportScheduleDTO:
    """
    جدولة تقرير - DTO
    
    Attributes:
        id: معرف الجدولة
        report_type: نوع التقرير
        frequency: التكرار (daily, weekly, monthly, quarterly, yearly)
        parameters: المعلمات
        format: صيغة التصدير
        recipients: المستلمون
        start_date: تاريخ البدء
        end_date: تاريخ الانتهاء
        last_run: آخر تنفيذ
        is_active: هل الجدولة نشطة؟
        created_at: وقت الإنشاء
        created_by: من قام بالإنشاء
    """
    id: str
    report_type: str
    frequency: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    format: str = "pdf"
    recipients: List[str] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    last_run: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    
    @property
    def frequency_display(self) -> str:
        frequencies = {
            "daily": "يومي",
            "weekly": "أسبوعي",
            "monthly": "شهري",
            "quarterly": "ربع سنوي",
            "yearly": "سنوي",
        }
        return frequencies.get(self.frequency, self.frequency)
    
    @property
    def next_run(self) -> Optional[datetime]:
        """حساب وقت التشغيل التالي"""
        if not self.is_active or not self.start_date:
            return None
        # يمكن إضافة منطق حساب الوقت التالي هنا
        return None


@dataclass(frozen=True)
class ReportExportDTO:
    """
    نتيجة تصدير تقرير - DTO
    
    Attributes:
        success: هل نجحت العملية؟
        message: رسالة الحالة
        file_path: مسار الملف
        format: صيغة الملف
        report_id: معرف التقرير
        rows_exported: عدد الصفوف المصدرة
        exported_at: وقت التصدير
        exported_by: من قام بالتصدير
    """
    success: bool
    message: str
    format: str
    report_id: str
    file_path: Optional[str] = None
    rows_exported: int = 0
    exported_at: datetime = field(default_factory=datetime.now)
    exported_by: str = "system"
    
    @property
    def is_success(self) -> bool:
        return self.success
    
    @property
    def file_name(self) -> str:
        if self.file_path:
            return self.file_path.split('/')[-1].split('\\')[-1]
        return ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message': self.message,
            'file_path': self.file_path,
            'format': self.format,
            'report_id': self.report_id,
            'rows_exported': self.rows_exported,
            'exported_at': self.exported_at.isoformat(),
            'exported_by': self.exported_by,
        }


# =============================================================================
# DTOs للفلاتر والبحث
# =============================================================================

@dataclass(frozen=True)
class ReportFilterDTO:
    """
    فلتر تقرير - DTO
    
    Attributes:
        from_date: تاريخ البداية
        to_date: تاريخ النهاية
        currency: العملة
        account_code: كود الحساب
        customer_id: معرف العميل
        supplier_id: معرف المورد
        product_code: كود المنتج
        category: التصنيف
        status: الحالة
        limit: الحد الأقصى للنتائج
        offset: الإزاحة للصفحات
    """
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    currency: str = "USD"
    account_code: Optional[str] = None
    customer_id: Optional[str] = None
    supplier_id: Optional[str] = None
    product_code: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    limit: int = 100
    offset: int = 0


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # الأساسية
    "ReportParameterDTO",
    "ReportDTO",
    
    # المالية
    "TrialBalanceReportDTO",
    "BalanceSheetReportDTO",
    "IncomeStatementReportDTO",
    
    # المبيعات والمشتريات
    "SalesReportDTO",
    "PurchasesReportDTO",
    
    # المخزون
    "InventoryReportDTO",
    
    # العملاء والموردين
    "CustomerStatementReportDTO",
    "SupplierStatementReportDTO",
    
    # الأداء والتحليل
    "KPIReportDTO",
    "ProfitabilityReportDTO",
    
    # الجدولة والتصدير
    "ReportScheduleDTO",
    "ReportExportDTO",
    
    # الفلاتر
    "ReportFilterDTO",
]