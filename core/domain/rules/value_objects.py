# core/domain/rules/value_objects.py
"""
Accounting Rules Value Objects - كائنات القيمة لمحرك القواعد المحاسبية
✅ يدعم: أنواع القواعد المختلفة
✅ يدعم: شروط القواعد
✅ يدعم: أولوية التنفيذ
✅ يدعم: العملات المتعددة
"""

from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable
from uuid import UUID, uuid4


# =============================================================================
# Enums الرئيسية
# =============================================================================

class RuleType(str, Enum):
    """نوع القاعدة المحاسبية"""
    # قواعد الفواتير
    INVOICE_CASH_SALE = "invoice_cash_sale"          # فاتورة بيع نقدي
    INVOICE_CREDIT_SALE = "invoice_credit_sale"      # فاتورة بيع آجل
    INVOICE_CASH_PURCHASE = "invoice_cash_purchase"  # فاتورة شراء نقدي
    INVOICE_CREDIT_PURCHASE = "invoice_credit_purchase"  # فاتورة شراء آجل
    INVOICE_RETURN = "invoice_return"                # مرتجع مبيعات
    INVOICE_REFUND = "invoice_refund"                # استرداد نقدي
    INVOICE_DISCOUNT = "invoice_discount"            # خصم فاتورة

    # قواعد المدفوعات
    PAYMENT_RECEIVE = "payment_receive"              # قبض نقدي
    PAYMENT_PAY = "payment_pay"                      # دفع نقدي
    PAYMENT_TRANSFER = "payment_transfer"            # تحويل بنكي
    PAYMENT_RECEIVE_INVOICE = "payment_receive_invoice"  # قبض مقابل فاتورة
    PAYMENT_PAY_INVOICE = "payment_pay_invoice"      # دفع مقابل فاتورة

    # قواعد الصناديق
    FUND_DEPOSIT = "fund_deposit"                    # إيداع صندوق
    FUND_WITHDRAW = "fund_withdraw"                  # سحب صندوق
    FUND_TRANSFER = "fund_transfer"                  # تحويل بين الصناديق

    # قواعد المخزون
    STOCK_IN = "stock_in"                            # زيادة مخزون
    STOCK_OUT = "stock_out"                          # نقص مخزون
    STOCK_ADJUST = "stock_adjust"                    # تعديل مخزون
    STOCK_TRANSFER = "stock_transfer"                # تحويل مخزون

    # قواعد الأصول
    ASSET_PURCHASE = "asset_purchase"                # شراء أصل
    ASSET_DEPRECIATION = "asset_depreciation"        # إهلاك أصل
    ASSET_SALE = "asset_sale"                        # بيع أصل
    ASSET_WRITE_OFF = "asset_write_off"              # شطب أصل

    # قواعد أخرى
    SALARY = "salary"                                # رواتب
    EXPENSE = "expense"                              # مصروفات
    REVENUE = "revenue"                              # إيرادات
    ADJUSTMENT = "adjustment"                        # تسوية
    REVERSAL = "reversal"                            # عكس قيد
    CLOSING = "closing"                              # إقفال
    OPENING = "opening"                              # رصيد افتتاحي
    CUSTOM = "custom"                                # قاعدة مخصصة


class RulePriority(str, Enum):
    """أولوية القاعدة"""
    CRITICAL = "critical"    # حرجة (تنفذ أولاً)
    HIGH = "high"            # عالية
    NORMAL = "normal"        # عادية
    LOW = "low"              # منخفضة
    LOWEST = "lowest"        # أقل أولوية


class RuleConditionType(str, Enum):
    """نوع شرط القاعدة"""
    # شروط المبلغ
    AMOUNT_EQUALS = "amount_equals"
    AMOUNT_GREATER_THAN = "amount_greater_than"
    AMOUNT_LESS_THAN = "amount_less_than"
    AMOUNT_BETWEEN = "amount_between"
    AMOUNT_ZERO = "amount_zero"

    # شروط العملة
    CURRENCY_EQUALS = "currency_equals"
    CURRENCY_IN = "currency_in"

    # شروط العميل/المورد
    CUSTOMER_ID_EQUALS = "customer_id_equals"
    CUSTOMER_ID_IN = "customer_id_in"
    CUSTOMER_GROUP_IN = "customer_group_in"
    SUPPLIER_ID_EQUALS = "supplier_id_equals"
    SUPPLIER_ID_IN = "supplier_id_in"

    # شروط المنتج
    PRODUCT_ID_EQUALS = "product_id_equals"
    PRODUCT_ID_IN = "product_id_in"
    PRODUCT_CATEGORY_IN = "product_category_in"

    # شروط الموقع
    SITE_ID_EQUALS = "site_id_equals"
    SITE_ID_IN = "site_id_in"

    # شروط الفترة
    PERIOD_EQUALS = "period_equals"
    PERIOD_IN = "period_in"
    DATE_BETWEEN = "date_between"

    # شروط الحالة
    STATUS_EQUALS = "status_equals"
    STATUS_IN = "status_in"

    # شروط مخصصة
    CUSTOM = "custom"


class RuleOperator(str, Enum):
    """مشغل الشرط"""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUALS = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUALS = "<="
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    BETWEEN = "between"


class RuleActionType(str, Enum):
    """نوع إجراء القاعدة"""
    CREATE_JOURNAL_ENTRY = "create_journal_entry"    # إنشاء قيد محاسبي
    CREATE_INVOICE = "create_invoice"                # إنشاء فاتورة
    CREATE_PAYMENT = "create_payment"                # إنشاء دفعة
    UPDATE_FUND_BALANCE = "update_fund_balance"      # تحديث رصيد صندوق
    UPDATE_STOCK = "update_stock"                    # تحديث مخزون
    SEND_NOTIFICATION = "send_notification"          # إرسال إشعار
    CALL_WEBHOOK = "call_webhook"                    # استدعاء Webhook
    CUSTOM = "custom"                                # إجراء مخصص


# =============================================================================
# Value Objects الأساسية
# =============================================================================

@dataclass(frozen=True)
class RuleId:
    """معرف القاعدة"""
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("RuleId cannot be empty")
        try:
            UUID(self.value)
        except ValueError:
            pass  # قد يكون معرفاً مخصصاً

    def __str__(self) -> str:
        return self.value

    @classmethod
    def generate(cls) -> 'RuleId':
        return cls(str(uuid4()))

    @classmethod
    def from_string(cls, value: str) -> 'RuleId':
        return cls(value)


@dataclass(frozen=True)
class RuleCode:
    """كود القاعدة (فريد)"""
    value: str

    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("RuleCode cannot be empty")
        cleaned = self.value.strip().upper()
        object.__setattr__(self, 'value', cleaned)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RuleOrder:
    """ترتيب تنفيذ القاعدة"""
    value: int

    def __post_init__(self):
        if self.value < 0:
            raise ValueError(f"Rule order cannot be negative: {self.value}")

    def __str__(self) -> str:
        return str(self.value)


# =============================================================================
# RuleCondition - شرط القاعدة
# =============================================================================

@dataclass(frozen=True)
class RuleCondition:
    """
    شرط القاعدة - يحدد متى يتم تنفيذ القاعدة
    
    مثال:
        RuleCondition(
            field="amount",
            operator=RuleOperator.GREATER_THAN,
            value=Decimal("1000")
        )
    """
    field: str
    operator: RuleOperator
    value: Any
    condition_type: RuleConditionType = RuleConditionType.CUSTOM
    is_required: bool = True

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        تقييم الشرط في سياق معين
        
        Args:
            context: قاموس يحتوي على البيانات المطلوبة
        
        Returns:
            bool: True إذا تحقق الشرط
        """
        # الحصول على قيمة الحقل من السياق
        actual_value = self._get_value_from_context(context)

        if actual_value is None:
            return not self.is_required

        # تقييم الشرط حسب المشغل
        return self._compare(actual_value)

    def _get_value_from_context(self, context: Dict[str, Any]) -> Any:
        """استخراج القيمة من السياق باستخدام مسار الحقل"""
        if '.' in self.field:
            # دعم المسارات المتداخلة (مثل "customer.id")
            parts = self.field.split('.')
            value = context
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part)
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            return value
        else:
            return context.get(self.field)

    def _compare(self, actual_value: Any) -> bool:
        """مقارنة القيمة الفعلية مع القيمة المطلوبة"""
        try:
            if self.operator == RuleOperator.EQUALS:
                return actual_value == self.value
            elif self.operator == RuleOperator.NOT_EQUALS:
                return actual_value != self.value
            elif self.operator == RuleOperator.GREATER_THAN:
                return actual_value > self.value
            elif self.operator == RuleOperator.GREATER_THAN_OR_EQUALS:
                return actual_value >= self.value
            elif self.operator == RuleOperator.LESS_THAN:
                return actual_value < self.value
            elif self.operator == RuleOperator.LESS_THAN_OR_EQUALS:
                return actual_value <= self.value
            elif self.operator == RuleOperator.IN:
                return actual_value in self.value
            elif self.operator == RuleOperator.NOT_IN:
                return actual_value not in self.value
            elif self.operator == RuleOperator.CONTAINS:
                return self.value in actual_value
            elif self.operator == RuleOperator.STARTS_WITH:
                return str(actual_value).startswith(str(self.value))
            elif self.operator == RuleOperator.ENDS_WITH:
                return str(actual_value).endswith(str(self.value))
            elif self.operator == RuleOperator.BETWEEN:
                if isinstance(self.value, (list, tuple)) and len(self.value) == 2:
                    return self.value[0] <= actual_value <= self.value[1]
                return False
            else:
                return False
        except (TypeError, ValueError):
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'field': self.field,
            'operator': self.operator.value,
            'value': self.value,
            'condition_type': self.condition_type.value,
            'is_required': self.is_required
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleCondition':
        return cls(
            field=data['field'],
            operator=RuleOperator(data['operator']),
            value=data['value'],
            condition_type=RuleConditionType(data.get('condition_type', 'custom')),
            is_required=data.get('is_required', True)
        )


# =============================================================================
# RuleAction - إجراء القاعدة
# =============================================================================

@dataclass(frozen=True)
class RuleAction:
    """
    إجراء القاعدة - ما يحدث عند تنفيذ القاعدة
    
    مثال:
        RuleAction(
            action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
            parameters={
                "template_id": "journal_template_001",
                "post_automatically": True
            }
        )
    """
    action_type: RuleActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None

    def execute(self, engine: Any, context: Dict[str, Any]) -> Any:
        """
        تنفيذ الإجراء
        
        Args:
            engine: محرك القواعد (RuleEngine)
            context: سياق التنفيذ
        
        Returns:
            Any: نتيجة تنفيذ الإجراء
        """
        from .services import RuleEngine
        if isinstance(engine, RuleEngine):
            return engine.execute_action(self, context)
        raise ValueError("Invalid engine provided")

    def to_dict(self) -> Dict[str, Any]:
        return {
            'action_type': self.action_type.value,
            'parameters': self.parameters,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleAction':
        return cls(
            action_type=RuleActionType(data['action_type']),
            parameters=data.get('parameters', {}),
            description=data.get('description')
        )


# =============================================================================
# RuleTemplate - قالب القيد المحاسبي
# =============================================================================

@dataclass(frozen=True)
class JournalLineTemplate:
    """قالب سطر قيد محاسبي"""
    account_code: str
    side: str  # "debit" or "credit"
    amount_source: str  # مصدر المبلغ (مثل "total", "subtotal", "tax", "discount")
    percentage: Decimal = Decimal('100')
    currency: Optional[str] = None
    description: Optional[str] = None
    is_required: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            'account_code': self.account_code,
            'side': self.side,
            'amount_source': self.amount_source,
            'percentage': str(self.percentage),
            'currency': self.currency,
            'description': self.description,
            'is_required': self.is_required
        }


@dataclass(frozen=True)
class JournalTemplate:
    """قالب قيد محاسبي كامل"""
    id: str
    name: str
    description: Optional[str] = None
    lines: List[JournalLineTemplate] = field(default_factory=list)
    require_balance: bool = True
    post_automatically: bool = False
    default_currency: str = "USD"

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'lines': [line.to_dict() for line in self.lines],
            'require_balance': self.require_balance,
            'post_automatically': self.post_automatically,
            'default_currency': self.default_currency
        }


# =============================================================================
# RuleExecutionResult - نتيجة تنفيذ القاعدة
# =============================================================================

@dataclass
class RuleExecutionResult:
    """نتيجة تنفيذ القاعدة"""
    rule_id: str
    rule_code: str
    rule_name: str
    success: bool
    message: str
    executed_actions: List[Dict[str, Any]] = field(default_factory=list)
    journal_entry_id: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    @property
    def is_partial_success(self) -> bool:
        return self.success and self.has_warnings

    def to_dict(self) -> Dict[str, Any]:
        return {
            'rule_id': self.rule_id,
            'rule_code': self.rule_code,
            'rule_name': self.rule_name,
            'success': self.success,
            'message': self.message,
            'executed_actions': self.executed_actions,
            'journal_entry_id': self.journal_entry_id,
            'errors': self.errors,
            'warnings': self.warnings,
            'execution_time_ms': self.execution_time_ms
        }

@dataclass(frozen=True)
class RuleContext:
    """
    سياق تنفيذ القاعدة - يحتوي على جميع البيانات اللازمة لتقييم القاعدة
    
    مثال:
        context = RuleContext(
            entity_type="invoice",
            entity_id="INV-001",
            action="post",
            user_id="user123",
            amount=Decimal("1000.00"),
            currency="USD",
            customer_id="CUST001"
        )
    """
    entity_type: str
    entity_id: str
    action: str
    user_id: Optional[str] = None
    amount: Decimal = Decimal('0')
    currency: str = "USD"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # بيانات إضافية حسب نوع الكيان
    customer_id: Optional[str] = None
    supplier_id: Optional[str] = None
    product_id: Optional[str] = None
    fund_id: Optional[str] = None
    site_id: Optional[str] = None
    invoice_id: Optional[str] = None
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        الحصول على قيمة من السياق
        
        Args:
            key: مفتاح القيمة
            default: القيمة الافتراضية إذا لم يتم العثور على المفتاح
        
        Returns:
            Any: القيمة المطلوبة
        """
        if hasattr(self, key):
            return getattr(self, key)
        return self.metadata.get(key, default)
    
    def with_metadata(self, key: str, value: Any) -> 'RuleContext':
        """إضافة بيانات وصفية جديدة (تعيد نسخة جديدة)"""
        new_metadata = self.metadata.copy()
        new_metadata[key] = value
        return RuleContext(
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            action=self.action,
            user_id=self.user_id,
            amount=self.amount,
            currency=self.currency,
            metadata=new_metadata,
            customer_id=self.customer_id,
            supplier_id=self.supplier_id,
            product_id=self.product_id,
            fund_id=self.fund_id,
            site_id=self.site_id,
            invoice_id=self.invoice_id,
            payment_id=self.payment_id,
            order_id=self.order_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل السياق إلى قاموس"""
        return {
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'action': self.action,
            'user_id': self.user_id,
            'amount': str(self.amount),
            'currency': self.currency,
            'metadata': self.metadata,
            'customer_id': self.customer_id,
            'supplier_id': self.supplier_id,
            'product_id': self.product_id,
            'fund_id': self.fund_id,
            'site_id': self.site_id,
            'invoice_id': self.invoice_id,
            'payment_id': self.payment_id,
            'order_id': self.order_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleContext':
        """إنشاء سياق من قاموس"""
        return cls(
            entity_type=data.get('entity_type', ''),
            entity_id=data.get('entity_id', ''),
            action=data.get('action', ''),
            user_id=data.get('user_id'),
            amount=Decimal(str(data.get('amount', 0))),
            currency=data.get('currency', 'USD'),
            metadata=data.get('metadata', {}),
            customer_id=data.get('customer_id'),
            supplier_id=data.get('supplier_id'),
            product_id=data.get('product_id'),
            fund_id=data.get('fund_id'),
            site_id=data.get('site_id'),
            invoice_id=data.get('invoice_id'),
            payment_id=data.get('payment_id'),
            order_id=data.get('order_id'),
        )
# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    'RuleType',
    'RulePriority',
    'RuleConditionType',
    'RuleOperator',
    'RuleActionType',

    # Value Objects
    'RuleId',
    'RuleCode',
    'RuleOrder',

    # Core Classes
    'RuleCondition',
    'RuleAction',
    'JournalLineTemplate',
    'JournalTemplate',
    
    # Result
    'RuleExecutionResult',
    
    # ✅ إضافة RuleContext
    'RuleContext',
]
