# core/domain/invoicing/entities.py
"""
Invoice Aggregate Root - The Heart of Invoicing Module
✅ محدث: دعم الضرائب المتكامل (Tax Engine)
✅ محدث: دعم العملات المتعددة في الضرائب
✅ محدث: دعم تفصيل الضرائب (Tax Breakdown)
✅ محدث: دعم فروع العملاء (Customer Branches)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Any, Dict, TYPE_CHECKING
import uuid

from ..shared.value_objects import Money, AccountCode
from .value_objects import InvoiceId, InvoiceNumber, InvoiceStatus, PaymentType

if TYPE_CHECKING:
    from core.domain.tax.services import TaxEngine
    from core.domain.tax.value_objects import TaxCalculationResult, TaxRule


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class InvoiceLine:
    """سطر في الفاتورة - محدث لدعم الضرائب لكل سطر"""
    
    product_code: str
    product_name: str
    quantity: Decimal
    unit_price: Money
    notes: str = ""
    line_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # ✅ حقول الضريبة لكل سطر
    tax_rate: Decimal = Decimal('0')
    tax_amount: Money = field(default_factory=lambda: Money.zero())
    tax_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    is_tax_inclusive: bool = False
    
    # الحساب المحاسبي للإيراد (يُحقن من Service Layer)
    _revenue_account: Optional[AccountCode] = None
    
    @property
    def total(self) -> Money:
        """الإجمالي = الكمية × سعر الوحدة"""
        return Money(self.quantity * self.unit_price.amount, self.unit_price.currency)
    
    @property
    def total_with_tax(self) -> Money:
        """الإجمالي شامل الضريبة (إذا كانت الضريبة شاملة)"""
        if self.is_tax_inclusive:
            return self.total
        return Money(self.total.amount + self.tax_amount.amount, self.currency)
    
    @property
    def revenue_account(self) -> AccountCode:
        """الحساب المحاسبي للإيراد"""
        if self._revenue_account is None:
            return AccountCode("4010")  # قيمة افتراضية
        return self._revenue_account
    
    def set_revenue_account(self, account_code: AccountCode) -> None:
        """تعيين حساب الإيرادات (يستخدم من Service Layer)"""
        self._revenue_account = account_code
    
    @property
    def currency(self) -> str:
        """عملة السطر"""
        return self.unit_price.currency
    
    @property
    def tax_amount_formatted(self) -> str:
        """مبلغ الضريبة منسقاً"""
        return f"{self.tax_amount.amount:,.2f} {self.currency}"
    
    @property
    def total_formatted(self) -> str:
        """الإجمالي منسقاً"""
        return f"{self.total.amount:,.2f} {self.currency}"
    
    def calculate_tax(self, tax_engine: 'TaxEngine', customer_id: Optional[str] = None) -> 'TaxCalculationResult':
        """
        حساب الضريبة لهذا السطر باستخدام TaxEngine
        
        Args:
            tax_engine: محرك الضرائب
            customer_id: معرف العميل (للقواعد الخاصة بالعميل)
        
        Returns:
            TaxCalculationResult: نتيجة حساب الضريبة
        """
        from core.domain.tax.services import TaxContext
        
        context = TaxContext(
            product_code=self.product_code,
            amount=self.total.amount,
            customer_id=customer_id,
            date=datetime.now().date()
        )
        
        result = tax_engine.calculate_tax(self.total.amount, context)
        
        # تحديث السطر بنتائج الضريبة
        self.tax_rate = result.effective_rate
        self.tax_amount = Money(result.tax_amount, self.currency)
        self.tax_breakdown = {
            k: Decimal(str(v)) for k, v in result.breakdown.items()
        }
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل السطر إلى قاموس"""
        return {
            'line_id': self.line_id,
            'product_code': self.product_code,
            'product_name': self.product_name,
            'quantity': float(self.quantity),
            'unit_price': float(self.unit_price.amount),
            'currency': self.currency,
            'total': float(self.total.amount),
            'tax_rate': float(self.tax_rate),
            'tax_amount': float(self.tax_amount.amount),
            'tax_breakdown': {k: float(v) for k, v in self.tax_breakdown.items()},
            'is_tax_inclusive': self.is_tax_inclusive,
            'total_with_tax': float(self.total_with_tax.amount),
            'notes': self.notes
        }


@dataclass
class Invoice:
    """
    AGGREGATE ROOT - الفاتورة
    كل فاتورة تولد قيداً محاسبياً عند ترحيلها
    
    ✅ محدث: دعم الضرائب المتكاملة
    ✅ محدث: دعم تفصيل الضرائب لكل سطر وللفاتورة ككل
    ✅ محدث: دعم العملات المتعددة في الضرائب
    ✅ محدث: دعم فروع العملاء (Customer Branches)
    """
    
    # ========== معلومات أساسية ==========
    id: InvoiceId = field(default_factory=InvoiceId.generate)
    number: Optional[InvoiceNumber] = None
    date: datetime = field(default_factory=utc_now)
    
    # ========== أطراف المعاملة ==========
    customer_id: str = ""
    customer_name: str = ""
    customer_tax_number: Optional[str] = None  # ✅ رقم ضريبي للعميل
    customer_tax_group: Optional[str] = None   # ✅ مجموعة ضريبية للعميل
    
    # ✅ فروع العميل (جديد)
    customer_branch_id: Optional[str] = None
    customer_branch_name: Optional[str] = None
    customer_branch_code: Optional[str] = None
    
    # موقع الشركة (مصدر الفاتورة)
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    
    # ========== معلومات مالية ==========
    currency: str = "USD"
    payment_currency: str = "USD"
    payment_type: PaymentType = PaymentType.CASH
    fund_id: Optional[str] = None
    
    # ========== إعدادات الحسابات المحاسبية ==========
    _cash_account: Optional[AccountCode] = None
    _receivables_account: Optional[AccountCode] = None
    _revenue_account: Optional[AccountCode] = None
    _tax_payable_account: Optional[AccountCode] = None      # ✅ حساب الضريبة المستحقة
    _tax_receivable_account: Optional[AccountCode] = None   # ✅ حساب الضريبة المستحقة التحصيل
    
    # ========== تفاصيل الفاتورة ==========
    lines: List[InvoiceLine] = field(default_factory=list)
    notes: str = ""
    
    # ========== الضرائب ==========
    tax_amount: Money = field(default_factory=lambda: Money.zero())
    tax_breakdown: Dict[str, Money] = field(default_factory=dict)  # {tax_code: amount}
    tax_rates_applied: List[str] = field(default_factory=list)      # قائمة أكواد الضرائب المطبقة
    is_tax_inclusive: bool = False  # هل الضريبة شاملة في السعر؟

    # ========== حالة الفاتورة ==========
    status: InvoiceStatus = InvoiceStatus.DRAFT
    
    # ========== ربط مع النواة المحاسبية ==========
    journal_entry_id: Optional[str] = None
    
    # ========== بيانات التدقيق ==========
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None
    
    # ========== أحداث المجال ==========
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # ========== التحكم في التزامن ==========
    version: int = 1
    
    # =========================================================================
    # ✅ خصائص فروع العملاء (جديدة)
    # =========================================================================
    
    @property
    def has_customer_branch(self) -> bool:
        """هل الفاتورة تحدد فرع عميل؟"""
        return bool(self.customer_branch_id)
    
    @property
    def customer_branch_display(self) -> str:
        """الاسم المعروض لفرع العميل"""
        if self.customer_branch_name:
            return self.customer_branch_name
        if self.customer_branch_code:
            return self.customer_branch_code
        return "بدون فرع"
    
    # =========================================================================
    # خصائص الحسابات المحاسبية (موجودة)
    # =========================================================================
    
    def set_accounting_settings(
        self, 
        cash_account: AccountCode,
        receivables_account: AccountCode,
        revenue_account: AccountCode,
        tax_payable_account: Optional[AccountCode] = None,
        tax_receivable_account: Optional[AccountCode] = None
    ) -> None:
        """
        تعيين إعدادات الحسابات المحاسبية للفاتورة
        يتم استدعاؤها من Service Layer قبل الترحيل
        """
        self._cash_account = cash_account
        self._receivables_account = receivables_account
        self._revenue_account = revenue_account
        self._tax_payable_account = tax_payable_account or AccountCode("2100")  # ضريبة مستحقة
        self._tax_receivable_account = tax_receivable_account or AccountCode("2110")  # ضريبة مستحقة التحصيل
        
        # تعيين حساب الإيرادات لجميع الأسطر
        for line in self.lines:
            line.set_revenue_account(revenue_account)
    
    # =========================================================================
    # حساب الإجماليات (موجودة)
    # =========================================================================
    
    @property
    def subtotal(self) -> Money:
        """المجموع الفرعي (بدون ضريبة)"""
        total = Decimal('0')
        for line in self.lines:
            total += line.total.amount
        return Money(total, self.currency)
    
    @property
    def total(self) -> Money:
        """الإجمالي النهائي (بدون ضريبة)"""
        return self.subtotal
    
    @property
    def total_with_tax(self) -> Money:
        """الإجمالي شامل الضريبة"""
        if self.is_tax_inclusive:
            return self.total
        return Money(self.total.amount + self.tax_amount.amount, self.currency)
    
    @property
    def total_with_tax_inclusive(self) -> Money:
        """الإجمالي شامل الضريبة"""
        if self.is_tax_inclusive:
            return self.total
        return Money(self.total.amount + self.tax_amount.amount, self.currency)
    
    @property
    def is_posted(self) -> bool:
        return self.status == InvoiceStatus.POSTED
    
    @property
    def is_draft(self) -> bool:
        return self.status == InvoiceStatus.DRAFT
    
    @property
    def has_tax(self) -> bool:
        """هل تحتوي الفاتورة على ضريبة؟"""
        return self.tax_amount.amount > 0
    
    @property
    def tax_summary(self) -> Dict[str, Any]:
        """ملخص الضرائب في الفاتورة"""
        return {
            'total_tax': str(self.tax_amount.amount),
            'currency': self.currency,
            'breakdown': {k: str(v.amount) for k, v in self.tax_breakdown.items()},
            'rates_applied': self.tax_rates_applied,
            'is_inclusive': self.is_tax_inclusive,
            'total_with_tax': str(self.total_with_tax.amount)
        }
    
    # =========================================================================
    # العمليات الأساسية (موجودة)
    # =========================================================================
    
    def add_line(self, line: InvoiceLine) -> None:
        """
        إضافة سطر إلى الفاتورة
        """
        if self.is_posted:
            from .exceptions import CannotModifyPostedInvoiceError
            raise CannotModifyPostedInvoiceError(str(self.id))
        
        if line.quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        
        # إذا تم تعيين حساب الإيرادات مسبقاً، نطبقه على السطر الجديد
        if self._revenue_account:
            line.set_revenue_account(self._revenue_account)
        
        self.lines.append(line)
    
    def remove_line(self, line_id: str) -> bool:
        """
        حذف سطر من الفاتورة
        """
        if self.is_posted:
            from .exceptions import CannotModifyPostedInvoiceError
            raise CannotModifyPostedInvoiceError(str(self.id))
        
        for i, line in enumerate(self.lines):
            if line.line_id == line_id:
                self.lines.pop(i)
                return True
        return False
    
    def clear_lines(self) -> None:
        """
        مسح جميع البنود
        """
        if self.is_posted:
            from .exceptions import CannotModifyPostedInvoiceError
            raise CannotModifyPostedInvoiceError(str(self.id))
        self.lines.clear()
    
    def update_line(self, line_id: str, quantity: Decimal, unit_price: Money, notes: str = "") -> None:
        """
        تحديث سطر موجود
        """
        if self.is_posted:
            from .exceptions import CannotModifyPostedInvoiceError
            raise CannotModifyPostedInvoiceError(str(self.id))
        
        for line in self.lines:
            if line.line_id == line_id:
                line.quantity = quantity
                line.unit_price = unit_price
                line.notes = notes
                return
        
        raise ValueError(f"Line {line_id} not found")
    
    # =========================================================================
    # ✅ تعيين فرع العميل (جديد)
    # =========================================================================
    
    def set_customer_branch(
        self,
        branch_id: str,
        branch_name: Optional[str] = None,
        branch_code: Optional[str] = None,
        updated_by: str = ""
    ) -> None:
        """
        تعيين فرع العميل للفاتورة
        
        Args:
            branch_id: معرف فرع العميل
            branch_name: اسم فرع العميل (اختياري)
            branch_code: كود فرع العميل (اختياري)
            updated_by: من قام بالتحديث
        """
        if self.is_posted:
            from .exceptions import CannotModifyPostedInvoiceError
            raise CannotModifyPostedInvoiceError(str(self.id))
        
        self.customer_branch_id = branch_id
        
        if branch_name:
            self.customer_branch_name = branch_name
        
        if branch_code:
            self.customer_branch_code = branch_code
        
        self.updated_at = utc_now()
        self.updated_by = updated_by
        self.version += 1
    
    def clear_customer_branch(self, updated_by: str = "") -> None:
        """
        إزالة فرع العميل من الفاتورة
        
        Args:
            updated_by: من قام بالتحديث
        """
        if self.is_posted:
            from .exceptions import CannotModifyPostedInvoiceError
            raise CannotModifyPostedInvoiceError(str(self.id))
        
        self.customer_branch_id = None
        self.customer_branch_name = None
        self.customer_branch_code = None
        
        self.updated_at = utc_now()
        self.updated_by = updated_by
        self.version += 1
    
    # =========================================================================
    # حساب الضرائب (موجود)
    # =========================================================================
    
    def calculate_tax(self, tax_engine: 'TaxEngine') -> 'TaxCalculationResult':
        """
        حساب الضريبة للفاتورة بأكملها باستخدام TaxEngine
        
        Args:
            tax_engine: محرك الضرائب
        
        Returns:
            TaxCalculationResult: نتيجة حساب الضريبة الإجمالية
        """
        from core.domain.tax.services import TaxContext
        
        total_tax = Decimal('0')
        breakdown: Dict[str, Decimal] = {}
        all_rates: List[str] = []
        total_amount = Decimal('0')
        
        # حساب الضريبة لكل سطر
        for line in self.lines:
            # حساب الضريبة للسطر
            context = TaxContext(
                product_code=line.product_code,
                amount=line.total.amount,
                customer_id=self.customer_id,
                customer_group=self.customer_tax_group,
                date=self.date.date()
            )
            
            result = tax_engine.calculate_tax(line.total.amount, context)
            
            # تحديث السطر بنتائج الضريبة
            line.tax_rate = result.effective_rate
            line.tax_amount = Money(result.tax_amount, line.currency)
            line.tax_breakdown = {
                k: Decimal(str(v)) for k, v in result.breakdown.items()
            }
            
            # تجميع النتائج الإجمالية
            total_tax += result.tax_amount
            total_amount += line.total.amount
            
            for code, amount in result.breakdown.items():
                if code not in breakdown:
                    breakdown[code] = Decimal('0')
                breakdown[code] += Decimal(str(amount))
            
            for rule in result.applied_rules:
                code = str(rule.code)
                if code not in all_rates:
                    all_rates.append(code)
        
        # تحديث الفاتورة بنتائج الضريبة
        self.tax_amount = Money(total_tax, self.currency)
        self.tax_breakdown = {
            code: Money(amount, self.currency) 
            for code, amount in breakdown.items()
        }
        self.tax_rates_applied = all_rates

        # إنشاء نتيجة إجمالية
        from core.domain.tax.value_objects import TaxCalculationResult, TaxCalculationType
        
        return TaxCalculationResult(
            taxable_amount=total_amount,
            tax_amount=total_tax,
            total_amount=total_amount + total_tax,
            breakdown=breakdown,
            applied_rules=[],  # سيتم ملؤها من الأسطر
            calculation_type=TaxCalculationType.EXCLUSIVE
        )
    
    def get_tax_breakdown_by_line(self) -> List[Dict[str, Any]]:
        """
        الحصول على تفصيل الضرائب لكل سطر
        """
        result = []
        for line in self.lines:
            result.append({
                'line_id': line.line_id,
                'product_code': line.product_code,
                'product_name': line.product_name,
                'taxable_amount': float(line.total.amount),
                'tax_amount': float(line.tax_amount.amount),
                'tax_rate': float(line.tax_rate),
                'breakdown': {k: float(v) for k, v in line.tax_breakdown.items()},
                'total_with_tax': float(line.total_with_tax.amount)
            })
        return result
    
    # =========================================================================
    # العمليات الأساسية (موجودة)
    # =========================================================================
    
    def post(self, posted_by: str, journal_entry_id: str) -> None:
        """
        ترحيل الفاتورة
        """
        if self.is_posted:
            from .exceptions import InvoiceAlreadyPostedError
            raise InvoiceAlreadyPostedError(str(self.id))
        
        if len(self.lines) == 0:
            raise ValueError("Cannot post invoice with no lines")
        
        # التحقق من تعيين الحسابات المحاسبية قبل الترحيل
        if not self._cash_account or not self._receivables_account or not self._revenue_account:
            raise ValueError(
                "Accounting settings not configured. "
                "Please call set_accounting_settings() before posting."
            )
        
        self.status = InvoiceStatus.POSTED
        self.posted_at = utc_now()
        self.posted_by = posted_by
        self.journal_entry_id = journal_entry_id
        
        # بث حدث ترحيل الفاتورة (محدث بدعم الضرائب)
        from .events import InvoicePostedEvent
        self._events.append(InvoicePostedEvent(
            invoice_id=self.id,
            invoice_number=str(self.number) if self.number else None,
            journal_entry_id=journal_entry_id,
            total_amount=self.total,
            tax_amount=self.tax_amount,
            total_with_tax=self.total_with_tax,
            customer_id=self.customer_id,
            customer_branch_id=self.customer_branch_id,  # ✅ إضافة فرع العميل
            customer_branch_name=self.customer_branch_name,  # ✅ إضافة
            posted_by=posted_by
        ))
    
    # =========================================================================
    # توليد القيد المحاسبي (موجود مع تحديث)
    # =========================================================================
    
    def to_journal_entry_lines(self) -> List[tuple]:
        """
        تحويل الفاتورة إلى أسطر قيد محاسبي
        ✅ محدث: يدعم حسابات الضريبة
        
        Returns: List of (account_code, debit, credit, currency)
        """
        if not self._cash_account or not self._receivables_account:
            raise ValueError(
                "Accounting settings not configured. "
                "Please call set_accounting_settings() before generating journal entry."
            )
        
        lines = []
        
        # ✅ سطر المدين: حساب الصندوق أو المدينين (من الإعدادات)
        if self.payment_type == PaymentType.CASH:
            debit_account = self._cash_account
        else:
            debit_account = self._receivables_account
        
        # المبلغ الإجمالي شامل الضريبة
        total_amount = self.total_with_tax.amount if self.has_tax else self.total.amount
        
        lines.append((
            debit_account,
            total_amount,
            Decimal('0'),
            self.currency
        ))
        
        # ✅ أسطر الدائن: حساب الإيرادات (من الإعدادات)
        for line in self.lines:
            # إذا كانت الضريبة شاملة، نخصم مبلغ الضريبة من الإيراد
            if self.is_tax_inclusive:
                revenue_amount = line.total.amount - line.tax_amount.amount
            else:
                revenue_amount = line.total.amount
            
            lines.append((
                line.revenue_account,
                Decimal('0'),
                revenue_amount,
                line.currency
            ))
        
        # ✅ سطر الضريبة: إذا كانت هناك ضريبة
        if self.has_tax:
            tax_account = self._tax_payable_account
            lines.append((
                tax_account,
                Decimal('0'),
                self.tax_amount.amount,
                self.currency
            ))
        
        return lines
    
    def generate_journal_entry_description(self) -> str:
        """
        توليد وصف للقيد المحاسبي
        ✅ محدث: يتضمن معلومات فرع العميل
        """
        item_count = len(self.lines)
        tax_info = f" (Tax: {self.tax_amount.amount} {self.currency})" if self.has_tax else ""
        branch_info = f" - Branch: {self.customer_branch_name or self.customer_branch_code or 'No Branch'}" if self.customer_branch_id else ""
        
        return f"INVOICE {self.number or 'DRAFT'} - Customer: {self.customer_name}{branch_info} ({item_count} items){tax_info}"
    
    # =========================================================================
    # Domain Events (موجودة)
    # =========================================================================
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events
    
    # =========================================================================
    # دالة المصنع (محدثة)
    # =========================================================================
    
    @classmethod
    def create(
        cls,
        customer_id: str,
        customer_name: str,
        currency: str = "USD",
        payment_type: PaymentType = PaymentType.CASH,
        payment_currency: str = "USD",
        site_id: Optional[str] = None,
        site_name: Optional[str] = None,
        fund_id: Optional[str] = None,
        customer_tax_number: Optional[str] = None,
        customer_tax_group: Optional[str] = None,
        is_tax_inclusive: bool = False,
        # ✅ إضافة معاملات فرع العميل
        customer_branch_id: Optional[str] = None,
        customer_branch_name: Optional[str] = None,
        customer_branch_code: Optional[str] = None,
        notes: str = "",
        created_by: str = ""
    ) -> 'Invoice':
        """
        إنشاء فاتورة جديدة مع دعم الضرائب وفروع العملاء
        """
        invoice = cls(
            customer_id=customer_id,
            customer_name=customer_name,
            site_id=site_id,
            site_name=site_name,
            currency=currency,
            payment_currency=payment_currency,
            payment_type=payment_type,
            fund_id=fund_id,
            customer_tax_number=customer_tax_number,
            customer_tax_group=customer_tax_group,
            is_tax_inclusive=is_tax_inclusive,
            # ✅ تعيين فرع العميل
            customer_branch_id=customer_branch_id,
            customer_branch_name=customer_branch_name,
            customer_branch_code=customer_branch_code,
            notes=notes,
            created_by=created_by,
            version=1
        )
        
        # بث حدث إنشاء الفاتورة (محدث)
        from .events import InvoiceCreatedEvent
        invoice._events.append(InvoiceCreatedEvent(
            invoice_id=invoice.id,
            customer_id=customer_id,
            customer_branch_id=customer_branch_id,  # ✅ إضافة
            customer_branch_name=customer_branch_name,  # ✅ إضافة
            total_amount=Money(Decimal('0'), currency),
            created_by=created_by
        ))
        
        return invoice
    
    # =========================================================================
    # التوثيق (محدث)
    # =========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الفاتورة إلى قاموس للتسلسل"""
        return {
            'id': str(self.id),
            'number': str(self.number) if self.number else None,
            'date': self.date.isoformat(),
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'customer_tax_number': self.customer_tax_number,
            'customer_tax_group': self.customer_tax_group,
            # ✅ إضافة فروع العملاء
            'customer_branch_id': self.customer_branch_id,
            'customer_branch_name': self.customer_branch_name,
            'customer_branch_code': self.customer_branch_code,
            'site_id': self.site_id,
            'site_name': self.site_name,
            'currency': self.currency,
            'payment_currency': self.payment_currency,
            'payment_type': self.payment_type.value,
            'fund_id': self.fund_id,
            'lines': [line.to_dict() for line in self.lines],
            'subtotal': float(self.subtotal.amount),
            'tax_amount': float(self.tax_amount.amount),
            'tax_breakdown': {k: float(v.amount) for k, v in self.tax_breakdown.items()},
            'tax_rates_applied': self.tax_rates_applied,
            'is_tax_inclusive': self.is_tax_inclusive,
            'total': float(self.total.amount),
            'total_with_tax': float(self.total_with_tax.amount),
            'status': self.status.value,
            'journal_entry_id': self.journal_entry_id,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'posted_at': self.posted_at.isoformat() if self.posted_at else None,
            'posted_by': self.posted_by,
            'version': self.version
        }
    
    def __repr__(self) -> str:
        branch_info = f", branch={self.customer_branch_name or self.customer_branch_id}" if self.customer_branch_id else ""
        return f"Invoice(id={self.id}, number={self.number}, customer={self.customer_name}{branch_info}, total={self.total}, tax={self.tax_amount}, status={self.status})"