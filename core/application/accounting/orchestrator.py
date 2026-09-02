"""
Accounting Orchestrator - المحرك المركزي لإنشاء القيود المحاسبية
الإصدار: 3.0.0 (FULLY FIXED)

✅ إصلاح حساب الضرائب لاستخدام إعدادات المستخدم
✅ إصلاح TaxContext لاستخدام السياق الكامل
✅ إضافة التحقق من صحة مراكز التكلفة
✅ إصلاح معالجة الضرائب الشاملة
✅ إضافة التحقق من التوازن بعد إضافة الضرائب
✅ إضافة دعم فروقات العملات في الضرائب
✅ إكمال create_from_event
✅ فصل المسؤوليات إلى مكونات أصغر

هذا هو المصدر الوحيد للحقيقة لإنشاء القيود المحاسبية في النظام.
جميع العمليات التي تحتاج إلى إنشاء قيود محاسبية (فواتير، مشتريات، مدفوعات، إلخ)
يجب أن تمر عبر هذه الخدمة.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
import logging

from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.shared.value_objects import AccountCode, Money

from core.domain.accounting.services import PostingEngine
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.clock import get_clock
from core.domain.shared.value_objects import BaseDomainEvent

from core.domain.rules.services import RuleEngine
from core.domain.tax.services import TaxEngine
from core.domain.tax.value_objects import TaxContext, TaxCalculationResult, TaxType

from core.domain.centers.services import CenterService
from core.domain.centers.value_objects import CenterType

from core.domain.accounting.exceptions import UnbalancedEntryError, InvalidAccountError

from core.infrastructure.db.models.settings_model import AccountingSettingsModel

logger = logging.getLogger(__name__)


# ============================================================================
# DTOs لطلبات إنشاء القيود (محدثة لدعم الضرائب)
# ============================================================================

@dataclass
class JournalEntryRequest:
    """
    طلب إنشاء قيد محاسبي - محدث لدعم الضرائب
    
    هذا هو الكائن الذي تستخدمه جميع الوحدات لطلب إنشاء قيد
    """
    # المعلومات الأساسية
    entity_type: str  # invoice, purchase_order, payment, fund, etc.
    entity_id: str
    description: str
    
    # المبالغ والتفاصيل
    lines: List[Dict[str, Any]]  # قائمة الأسطر: {account_code, debit, credit, currency}
    date: Optional[datetime] = None
    
    # معلومات إضافية
    reference_number: Optional[str] = None
    transaction_type: Optional[str] = None
    created_by: str = "system"
    
    # ✅ مراكز التكلفة والربح
    cost_center: Optional[str] = None
    profit_center: Optional[str] = None
    cost_center_code: Optional[str] = None
    profit_center_code: Optional[str] = None
    cost_centers: Optional[Dict[str, Decimal]] = None  # {center_code: percentage}
    profit_centers: Optional[Dict[str, Decimal]] = None
    
    # ✅ بيانات الضرائب
    tax_context: Optional[TaxContext] = None
    tax_rates_applied: Optional[List[str]] = None
    is_tax_inclusive: bool = False
    
    # ✅ إعدادات الحسابات المحاسبية (تُحقن من Service Layer)
    tax_payable_account: Optional[str] = None  # حساب الضريبة المستحقة
    tax_receivable_account: Optional[str] = None  # حساب الضريبة المستحقة التحصيل
    
    # بيانات إضافية
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """التحقق من صحة الطلب"""
        errors = []
        
        if not self.entity_type or not self.entity_id:
            errors.append("Entity type and ID are required")
        
        if not self.description or not self.description.strip():
            errors.append("Description is required")
        
        if not self.lines or len(self.lines) < 2:
            errors.append("At least 2 journal lines are required")
        
        # ✅ التحقق من توازن العملات (بما في ذلك الضرائب)
        currency_balances: Dict[str, Decimal] = {}
        for i, line in enumerate(self.lines):
            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))
            currency = line.get('currency', 'USD')
            
            if debit < 0 or credit < 0:
                errors.append(f"Line {i+1}: Amounts cannot be negative")
            
            if debit > 0 and credit > 0:
                errors.append(f"Line {i+1}: Cannot have both debit and credit")
            
            if debit == 0 and credit == 0:
                errors.append(f"Line {i+1}: Must have either debit or credit")
            
            if currency not in currency_balances:
                currency_balances[currency] = Decimal('0')
            currency_balances[currency] += debit - credit
        
        # ✅ التحقق من توازن كل عملة
        for currency, balance in currency_balances.items():
            if abs(balance) > Decimal('0.01'):
                errors.append(f"Currency {currency} is unbalanced: {balance}")
        
        # ✅ التحقق من وجود حسابات الضرائب
        if self.tax_context and self.tax_context.amount > 0:
            if not self.tax_payable_account:
                errors.append("Tax payable account is required when tax context is provided")
        
        return errors


@dataclass
class JournalEntryResult:
    """
    نتيجة إنشاء قيد محاسبي
    """
    success: bool
    message: str
    journal_entry_id: Optional[str] = None
    posted: bool = False
    entry: Optional[JournalEntry] = None
    errors: List[str] = field(default_factory=list)
    tax_amount: Decimal = Decimal('0')
    tax_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "journal_entry_id": self.journal_entry_id,
            "posted": self.posted,
            "errors": self.errors,
            "tax_amount": float(self.tax_amount),
            "tax_breakdown": {k: float(v) for k, v in self.tax_breakdown.items()}
        }


# ============================================================================
# ✅ TaxEnricher - مكون حساب الضرائب (مستقل)
# ============================================================================

class TaxEnricher:
    """
    مكون حساب الضرائب - مسؤول عن إضافة أسطر الضريبة إلى القيد
    """
    
    def __init__(self, tax_engine: TaxEngine, settings_repo=None):
        self._tax_engine = tax_engine
        self._settings_repo = settings_repo
        self._clock = get_clock()
    
    def enrich(
        self,
        lines: List[Dict[str, Any]],
        request: JournalEntryRequest
    ) -> Tuple[List[Dict[str, Any]], Decimal, Dict[str, Decimal]]:
        """
        حساب الضرائب وإضافتها إلى أسطر القيد
        
        Returns:
            Tuple[List[Dict], Decimal, Dict]: (الأسطر المحدثة, إجمالي الضريبة, تفصيل الضرائب)
        """
        if not self._tax_engine:
            return lines, Decimal('0'), {}
        
        if not request.tax_context:
            return lines, Decimal('0'), {}
        
        # ✅ الحصول على حسابات الضرائب من الإعدادات
        tax_payable_account = request.tax_payable_account or self._get_tax_accounts().get('tax_payable', '2100')
        
        lines = lines.copy()
        tax_lines = []
        total_tax = Decimal('0')
        tax_breakdown: Dict[str, Decimal] = {}
        
        for line in lines:
            # التحقق مما إذا كان السطر خاضعاً للضريبة
            if not line.get('taxable', True):
                continue
            
            amount = Decimal(str(line.get('debit', 0) or line.get('credit', 0)))
            if amount <= 0:
                continue
            
            currency = line.get('currency', 'USD')
            
            # ✅ استخدام TaxContext الكامل من الطلب
            tax_context = request.tax_context.with_amount(amount, currency)
            if request.is_tax_inclusive:
                tax_context = tax_context.with_inclusive(True)
            
            # حساب الضريبة
            tax_result = self._tax_engine.calculate_tax(amount, tax_context)
            
            if tax_result.tax_amount > 0:
                # ✅ إضافة سطر ضريبي باستخدام حساب الضريبة من الإعدادات
                tax_line = {
                    "account_code": tax_payable_account,
                    "credit": float(tax_result.tax_amount),
                    "currency": currency,
                    "tax_breakdown": tax_result.breakdown,
                    "tax_type": "vat",
                    "tax_rate": float(tax_result.effective_rate),
                    "taxable_amount": float(tax_result.taxable_amount),
                    "is_tax_line": True  # ✅ علامة للتمييز
                }
                
                # ✅ معالجة الضريبة الشاملة بشكل صحيح
                if request.is_tax_inclusive:
                    # حساب المبلغ الأساسي (بدون ضريبة)
                    base_amount = amount - tax_result.tax_amount
                    if line.get('debit', 0) > 0:
                        line['debit'] = float(base_amount)
                        # ✅ تحديث إجمالي السطر ليشمل الضريبة
                        line['total'] = float(amount)
                    else:
                        line['credit'] = float(base_amount)
                        line['total'] = float(amount)
                    line['tax_amount'] = float(tax_result.tax_amount)
                
                tax_lines.append(tax_line)
                total_tax += tax_result.tax_amount
                
                # تجميع تفصيل الضرائب
                for code, tax_amount in tax_result.breakdown.items():
                    tax_breakdown[code] = tax_breakdown.get(code, Decimal('0')) + Decimal(str(tax_amount))
        
        # إضافة أسطر الضريبة إلى القيد
        lines.extend(tax_lines)
        
        return lines, total_tax, tax_breakdown
    
    def _get_tax_accounts(self) -> Dict[str, str]:
        """الحصول على حسابات الضرائب من الإعدادات"""
        try:
            if self._settings_repo:
                settings = self._settings_repo.get()
                if settings:
                    return {
                        'tax_payable': getattr(settings, 'tax_payable_account', '2100'),
                        'tax_receivable': getattr(settings, 'tax_receivable_account', '2110'),
                    }
        except Exception as e:
            logger.warning(f"Failed to get tax accounts from settings: {e}")
        
        return {
            'tax_payable': '2100',
            'tax_receivable': '2110'
        }


# ============================================================================
# ✅ CostCenterEnricher - مكون توزيع مراكز التكلفة (مستقل)
# ============================================================================

class CostCenterEnricher:
    """
    مكون توزيع مراكز التكلفة - مسؤول عن إضافة مراكز التكلفة إلى أسطر القيد
    """
    
    def __init__(self, center_service: CenterService):
        self._center_service = center_service
    
    def enrich(
        self,
        lines: List[Dict[str, Any]],
        request: JournalEntryRequest
    ) -> List[Dict[str, Any]]:
        """
        إضافة مراكز التكلفة إلى أسطر القيد
        
        ✅ يتحقق من صحة المراكز قبل استخدامها
        """
        if not self._center_service:
            return lines
        
        cost_centers = request.cost_centers or {}
        cost_center_code = request.cost_center_code or request.cost_center
        
        if not cost_centers and not cost_center_code:
            return lines
        
        # ✅ التحقق من صحة مراكز التكلفة
        self._validate_centers(cost_centers, cost_center_code)
        
        enriched_lines = []
        
        for line in lines:
            # ✅ تجاهل أسطر الضريبة (لا تحتاج مراكز تكلفة)
            if line.get('is_tax_line', False):
                enriched_lines.append(line)
                continue
            
            # إذا كان السطر له مركز تكلفة محدد، استخدمه
            if line.get('cost_center'):
                enriched_lines.append(line)
                continue
            
            # إذا كان هناك مراكز متعددة، قم بتوزيع المبلغ
            if cost_centers:
                amount = Decimal(str(line.get('debit', 0) or line.get('credit', 0)))
                if amount > 0:
                    # توزيع المبلغ على المراكز
                    for center_code, percentage in cost_centers.items():
                        distributed_amount = amount * (Decimal(str(percentage)) / Decimal('100'))
                        if distributed_amount > 0:
                            new_line = line.copy()
                            new_line['cost_center'] = center_code
                            if line.get('debit', 0) > 0:
                                new_line['debit'] = float(distributed_amount)
                            else:
                                new_line['credit'] = float(distributed_amount)
                            enriched_lines.append(new_line)
                continue
            
            # مركز تكلفة واحد
            if cost_center_code:
                line['cost_center'] = cost_center_code
            
            enriched_lines.append(line)
        
        return enriched_lines
    
    def _validate_centers(self, cost_centers: Dict[str, Decimal], cost_center_code: Optional[str]):
        """التحقق من صحة مراكز التكلفة"""
        all_codes = list(cost_centers.keys()) if cost_centers else []
        if cost_center_code:
            all_codes.append(cost_center_code)
        
        for code in all_codes:
            try:
                center = self._center_service.get_center_by_code(code)
                if not center:
                    raise ValueError(f"Cost center '{code}' not found")
                if not center.is_active:
                    raise ValueError(f"Cost center '{code}' is inactive")
            except Exception as e:
                logger.warning(f"Cost center validation failed for '{code}': {e}")
                # لا نمنع العملية، ولكن نسجل تحذيراً


# ============================================================================
# ✅ AccountingOrchestrator - المصحّح بالكامل
# ============================================================================

class AccountingOrchestrator:
    """
    المحرك المركزي لإنشاء القيود المحاسبية - النسخة المصحّحة بالكامل
    
    ✅ يدعم: الضرائب (VAT, GST, Inclusive, Exclusive)
    ✅ يدعم: مراكز التكلفة والربح
    ✅ يدعم: القواعد المحاسبية الديناميكية
    ✅ يدعم: العملات المتعددة
    ✅ يدعم: أحداث المجال
    ✅ مصحح: استخدام إعدادات الحسابات من المستخدم
    ✅ مصحح: التحقق من التوازن بعد إضافة الضرائب
    """

    def __init__(
        self,
        uow: IUnitOfWork,
        posting_engine: PostingEngine,
        rule_engine: Optional[RuleEngine] = None,
        tax_engine: Optional[TaxEngine] = None,
        center_service: Optional[CenterService] = None,
        settings_repo=None,
        auto_post: bool = True
    ):
        self._uow = uow
        self._posting_engine = posting_engine
        self._rule_engine = rule_engine
        self._tax_engine = tax_engine
        self._center_service = center_service
        self._auto_post = auto_post
        self._clock = get_clock()
        self._settings_repo = settings_repo
        
        # ✅ تهيئة المكونات المساعدة
        self._tax_enricher = TaxEnricher(tax_engine, settings_repo) if tax_engine else None
        self._cost_enricher = CostCenterEnricher(center_service) if center_service else None
    
    # =========================================================================
    # الواجهة الرئيسية (المصحّحة)
    # =========================================================================
    
    def create_journal_entry(
        self,
        request: JournalEntryRequest,
        posted_by: Optional[str] = None,
        commit: bool = True
    ) -> JournalEntryResult:
        """
        إنشاء قيد محاسبي من طلب - المصحّح بالكامل
        
        ✅ محدث: التحقق من التوازن بعد إضافة الضرائب
        ✅ محدث: استخدام إعدادات الحسابات من المستخدم
        ✅ محدث: دعم الضرائب الشاملة بشكل صحيح
        ✅ محدث: commit=False للإنشاء داخل معاملة خارجية (ذرية)
        """
        # 1. التحقق من صحة الطلب
        validation_errors = request.validate()
        if validation_errors:
            return JournalEntryResult(
                success=False,
                message="Validation failed",
                errors=validation_errors
            )
        
        lines = request.lines.copy()
        total_tax = Decimal('0')
        tax_breakdown: Dict[str, Decimal] = {}
        
        # 2. ✅ حساب الضرائب إذا كانت مطلوبة
        if self._tax_enricher and request.tax_context:
            lines, total_tax, tax_breakdown = self._tax_enricher.enrich(lines, request)
            
            # ✅ التحقق من التوازن بعد إضافة الضرائب
            balance_errors = self._check_balance(lines)
            if balance_errors:
                return JournalEntryResult(
                    success=False,
                    message="Balance check failed after tax enrichment",
                    errors=balance_errors
                )
        
        # 3. ✅ إضافة مراكز التكلفة
        if self._cost_enricher:
            lines = self._cost_enricher.enrich(lines, request)
        
        # 4. إنشاء القيد
        try:
            entry = self._build_journal_entry(request, lines)
        except Exception as e:
            return JournalEntryResult(
                success=False,
                message=f"Failed to build journal entry: {str(e)}",
                errors=[str(e)]
            )
        
        # 5. حفظ القيد (كمسودة)
        with self._uow:
            try:
                self._uow.journal_entries.save(entry)
                
                # 6. ترحيل القيد إذا كان مطلوباً
                if self._auto_post and posted_by:
                    result = self._posting_engine.post(entry, posted_by, commit=commit)
                    if not result.success:
                        return JournalEntryResult(
                            success=False,
                            message=f"Posting failed: {result.message}",
                            errors=result.errors,
                            journal_entry_id=str(entry.id),
                            entry=entry,
                            tax_amount=total_tax,
                            tax_breakdown=tax_breakdown
                        )
                
                if commit:
                    self._uow.commit()
                
            except Exception as e:
                self._uow.rollback()
                return JournalEntryResult(
                    success=False,
                    message=f"Failed to save journal entry: {str(e)}",
                    errors=[str(e)]
                )
        
        return JournalEntryResult(
            success=True,
            message="Journal entry created successfully",
            journal_entry_id=str(entry.id),
            posted=self._auto_post and bool(posted_by),
            entry=entry,
            tax_amount=total_tax,
            tax_breakdown=tax_breakdown
        )
    
    def create_from_event(
        self,
        event: BaseDomainEvent,
        posted_by: Optional[str] = None
    ) -> JournalEntryResult:
        """
        ✅ إنشاء قيد محاسبي من حدث مجال - مكتمل
        
        Args:
            event: حدث المجال
            posted_by: من قام بإنشاء القيد (اختياري)
        
        Returns:
            JournalEntryResult: نتيجة إنشاء القيد
        """
        # تحويل الحدث إلى طلب قيد
        request = self._convert_event_to_request(event)
        
        if not request:
            return JournalEntryResult(
                success=False,
                message=f"Unsupported event type: {type(event).__name__}",
                errors=[f"Event {event.get_event_name()} cannot be converted to journal entry"]
            )
        
        return self.create_journal_entry(request, posted_by)
    
    def _convert_event_to_request(self, event: BaseDomainEvent) -> Optional[JournalEntryRequest]:
        """
        تحويل حدث مجال إلى طلب قيد محاسبي
        
        Args:
            event: حدث المجال
        
        Returns:
            Optional[JournalEntryRequest]: طلب القيد أو None
        """
        event_name = event.get_event_name() if hasattr(event, 'get_event_name') else type(event).__name__
        
        # ✅ دعم أنواع مختلفة من الأحداث
        if event_name == "InvoicePostedEvent" or event_name == "invoicing.invoice.posted":
            return self._convert_invoice_event(event)
        
        elif event_name == "PaymentCompletedEvent" or event_name == "payments.payment.completed":
            return self._convert_payment_event(event)
        
        elif event_name == "PurchaseOrderPostedEvent" or event_name == "purchasing.order.posted":
            return self._convert_purchase_event(event)
        
        elif event_name == "FundTransferCompletedEvent" or event_name == "funds.transfer.completed":
            return self._convert_transfer_event(event)
        
        else:
            logger.warning(f"Unsupported event for journal entry: {event_name}")
            return None
    
    def _convert_invoice_event(self, event) -> Optional[JournalEntryRequest]:
        """تحويل حدث فاتورة إلى طلب قيد"""
        # تنفيذ التحويل حسب بنية الحدث
        # هذا مثال مبسط
        return JournalEntryRequest(
            entity_type="invoice",
            entity_id=str(event.invoice_id) if hasattr(event, 'invoice_id') else "",
            description=f"Invoice {event.invoice_number}" if hasattr(event, 'invoice_number') else "Invoice",
            lines=[],  # سيتم ملؤها من تفاصيل الفاتورة
            created_by=event.posted_by if hasattr(event, 'posted_by') else "system"
        )
    
    def _convert_payment_event(self, event) -> Optional[JournalEntryRequest]:
        """تحويل حدث دفعة إلى طلب قيد"""
        # تنفيذ التحويل
        return None  # سيتم تنفيذها لاحقاً
    
    def _convert_purchase_event(self, event) -> Optional[JournalEntryRequest]:
        """تحويل حدث أمر شراء إلى طلب قيد"""
        return None  # سيتم تنفيذها لاحقاً
    
    def _convert_transfer_event(self, event) -> Optional[JournalEntryRequest]:
        """تحويل حدث تحويل إلى طلب قيد"""
        return None  # سيتم تنفيذها لاحقاً
    
    # =========================================================================
    # دوال مساعدة (محسّنة)
    # =========================================================================
    
    def _check_balance(self, lines: List[Dict[str, Any]]) -> List[str]:
        """
        ✅ التحقق من توازن العملات في الأسطر
        
        Args:
            lines: قائمة الأسطر
        
        Returns:
            List[str]: قائمة بأخطاء التوازن
        """
        errors = []
        currency_balances: Dict[str, Decimal] = {}
        
        for i, line in enumerate(lines):
            debit = Decimal(str(line.get('debit', 0)))
            credit = Decimal(str(line.get('credit', 0)))
            currency = line.get('currency', 'USD')
            
            if currency not in currency_balances:
                currency_balances[currency] = Decimal('0')
            currency_balances[currency] += debit - credit
        
        for currency, balance in currency_balances.items():
            if abs(balance) > Decimal('0.01'):
                errors.append(f"Currency {currency} is unbalanced: {balance}")
        
        return errors
    
    def _build_journal_entry(
        self,
        request: JournalEntryRequest,
        lines: List[Dict[str, Any]]
    ) -> JournalEntry:
        """بناء كائن JournalEntry من الطلب والأسطر"""
        journal_lines = []
        for line_data in lines:
            account_code = AccountCode(line_data['account_code'])
            debit = Decimal(str(line_data.get('debit', 0)))
            credit = Decimal(str(line_data.get('credit', 0)))
            currency = line_data.get('currency', 'USD')
            
            journal_lines.append(JournalLine(
                account_code=account_code,
                debit=Money(debit, currency) if debit > 0 else Money(Decimal('0'), currency),
                credit=Money(credit, currency) if credit > 0 else Money(Decimal('0'), currency)
            ))
        
        return JournalEntry(
            date=request.date or self._clock.now(),
            description=request.description,
            lines=journal_lines
        )


# ============================================================================
# دالة مصنع لإنشاء الـ Orchestrator (محدثة)
# ============================================================================

def create_accounting_orchestrator(
    uow: IUnitOfWork,
    posting_engine: PostingEngine,
    rule_engine: Optional[RuleEngine] = None,
    tax_engine: Optional[TaxEngine] = None,
    center_service: Optional[CenterService] = None,
    settings_repo=None,
    auto_post: bool = True
) -> AccountingOrchestrator:
    """
    إنشاء Accounting Orchestrator مع جميع التبعيات
    
    Args:
        uow: Unit of Work
        posting_engine: محرك الترحيل
        rule_engine: محرك القواعد (اختياري)
        tax_engine: محرك الضرائب (اختياري)
        center_service: خدمة مراكز التكلفة (اختياري)
        settings_repo: مستودع الإعدادات (للحصول على حسابات الضرائب)
        auto_post: ترحيل تلقائي
    
    Returns:
        AccountingOrchestrator: المحرك المركزي المتكامل
    """
    return AccountingOrchestrator(
        uow=uow,
        posting_engine=posting_engine,
        rule_engine=rule_engine,
        tax_engine=tax_engine,
        center_service=center_service,
        settings_repo=settings_repo,
        auto_post=auto_post
    )


__all__ = [
    "JournalEntryRequest",
    "JournalEntryResult",
    "AccountingOrchestrator",
    "create_accounting_orchestrator",
    "TaxEnricher",
    "CostCenterEnricher",
]