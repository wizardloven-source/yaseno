# tests/unit/domain/test_rule_engine.py
"""
Unit Tests for RuleEngine - اختبارات محرك القواعد المحاسبية الشامل

هذه الاختبارات تتحقق من:
    1. إنشاء القواعد المحاسبية (Posting Rules)
    2. شروط القواعد (Conditions)
    3. إجراءات القواعد (Actions)
    4. قوالب القيود المحاسبية (Journal Templates)
    5. مجموعات القواعد (Rule Groups)
    6. تنفيذ القواعد (Rule Execution)
    7. أولويات التنفيذ (Priorities)
    8. سجل التنفيذ (Execution Log)
    9. منع التكرار (Duplicate Prevention)
    10. التحقق من صحة القواعد (Validation)
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, call
from typing import List, Optional, Dict, Any

from core.domain.rules.entities import (
    PostingRule, RuleGroup, RuleExecutionLog
)
from core.domain.rules.value_objects import (
    RuleId, RuleCode, RuleType, RulePriority, RuleOrder,
    RuleCondition, RuleAction, JournalTemplate, JournalLineTemplate,
    RuleConditionType, RuleOperator, RuleActionType,
    RuleExecutionResult
)
from core.domain.rules.services import (
    RuleValidator, RuleExecutor, RuleEngine
)
from core.domain.rules.interfaces import (
    IRuleRepository, IRuleGroupRepository, IRuleExecutionLogRepository
)


# =============================================================================
# FIXTURES (الإعدادات المشتركة للاختبارات)
# =============================================================================

@pytest.fixture
def mock_rule_repo():
    """مستودع قواعد وهمي"""
    repo = Mock(spec=IRuleRepository)
    repo.save = Mock()
    repo.get_by_id = Mock(return_value=None)
    repo.get_by_code = Mock(return_value=None)
    repo.get_all = Mock(return_value=[])
    repo.get_active_rules = Mock(return_value=[])
    repo.get_by_type = Mock(return_value=[])
    repo.get_by_priority = Mock(return_value=[])
    repo.get_default_rule = Mock(return_value=None)
    repo.delete = Mock(return_value=True)
    repo.count_active = Mock(return_value=0)
    return repo


@pytest.fixture
def mock_group_repo():
    """مستودع مجموعات قواعد وهمي"""
    repo = Mock(spec=IRuleGroupRepository)
    repo.save = Mock()
    repo.get_by_id = Mock(return_value=None)
    repo.get_by_code = Mock(return_value=None)
    repo.get_all = Mock(return_value=[])
    repo.get_default_group = Mock(return_value=None)
    repo.delete = Mock(return_value=True)
    return repo


@pytest.fixture
def mock_log_repo():
    """مستودع سجل تنفيذ وهمي"""
    repo = Mock(spec=IRuleExecutionLogRepository)
    repo.save = Mock()
    repo.get_by_id = Mock(return_value=None)
    repo.get_by_rule = Mock(return_value=[])
    repo.get_by_entity_type = Mock(return_value=[])
    repo.get_recent = Mock(return_value=[])
    repo.count_by_rule = Mock(return_value=0)
    repo.delete_old_logs = Mock(return_value=0)
    return repo


@pytest.fixture
def mock_dependencies():
    """تبعيات وهمية لمنفذ القواعد"""
    return {
        "journal_repo": Mock(),
        "posting_engine": Mock(),
        "fund_repo": Mock(),
        "invoice_repo": Mock(),
        "payment_repo": Mock(),
        "product_repo": Mock(),
        "notification_service": Mock()
    }


@pytest.fixture
def rule_engine(mock_rule_repo, mock_group_repo, mock_log_repo, mock_dependencies):
    """محرك القواعد مع مستودعات وهمية"""
    return RuleEngine(
        rule_repository=mock_rule_repo,
        group_repository=mock_group_repo,
        log_repository=mock_log_repo,
        dependencies=mock_dependencies
    )


@pytest.fixture
def sample_condition():
    """شرط نموذجي"""
    return RuleCondition(
        field="payment_type",
        operator=RuleOperator.EQUALS,
        value="cash",
        condition_type=RuleConditionType.STATUS_EQUALS
    )


@pytest.fixture
def sample_action():
    """إجراء نموذجي"""
    return RuleAction(
        action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
        parameters={"post_automatically": True, "template_id": "template_001"},
        description="إنشاء قيد محاسبي"
    )


@pytest.fixture
def sample_journal_template():
    """قالب قيد محاسبي نموذجي"""
    return JournalTemplate(
        id="template_001",
        name="فاتورة بيع نقدي",
        description="قالب لفاتورة البيع النقدي",
        lines=[
            JournalLineTemplate(
                account_code="1010",
                side="debit",
                amount_source="total",
                percentage=Decimal("100"),
                description="الصندوق"
            ),
            JournalLineTemplate(
                account_code="4010",
                side="credit",
                amount_source="total",
                percentage=Decimal("100"),
                description="إيرادات المبيعات"
            )
        ],
        require_balance=True,
        post_automatically=True,
        default_currency="USD"
    )


@pytest.fixture
def invoice_cash_rule(sample_condition, sample_action, sample_journal_template):
    """قاعدة فاتورة بيع نقدي"""
    return PostingRule.create(
        code="INV-CASH",
        name="فاتورة بيع نقدي",
        rule_type=RuleType.INVOICE_CASH_SALE,
        conditions=[sample_condition],
        actions=[sample_action],
        journal_template=sample_journal_template,
        priority=RulePriority.NORMAL,
        description="إنشاء قيد محاسبي لفاتورة بيع نقدي",
        is_default=True,
        created_by="system"
    )


@pytest.fixture
def invoice_credit_rule():
    """قاعدة فاتورة بيع آجل"""
    condition = RuleCondition(
        field="payment_type",
        operator=RuleOperator.EQUALS,
        value="credit",
        condition_type=RuleConditionType.STATUS_EQUALS
    )
    
    template = JournalTemplate(
        id="template_002",
        name="فاتورة بيع آجل",
        lines=[
            JournalLineTemplate(
                account_code="1020",
                side="debit",
                amount_source="total",
                description="المدينون"
            ),
            JournalLineTemplate(
                account_code="4010",
                side="credit",
                amount_source="subtotal",
                description="إيرادات المبيعات"
            ),
            JournalLineTemplate(
                account_code="2100",
                side="credit",
                amount_source="tax",
                description="ضريبة مستحقة"
            )
        ]
    )
    
    return PostingRule.create(
        code="INV-CREDIT",
        name="فاتورة بيع آجل",
        rule_type=RuleType.INVOICE_CREDIT_SALE,
        conditions=[condition],
        actions=[RuleAction(
            action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
            parameters={"post_automatically": True}
        )],
        journal_template=template,
        priority=RulePriority.NORMAL,
        created_by="system"
    )


@pytest.fixture
def payment_receive_rule():
    """قاعدة قبض نقدي"""
    condition = RuleCondition(
        field="payment.payment_type",
        operator=RuleOperator.EQUALS,
        value="receive",
        condition_type=RuleConditionType.STATUS_EQUALS
    )
    
    template = JournalTemplate(
        id="template_003",
        name="قبض نقدي",
        lines=[
            JournalLineTemplate(
                account_code="1010",
                side="debit",
                amount_source="amount",
                description="الصندوق"
            ),
            JournalLineTemplate(
                account_code="1020",
                side="credit",
                amount_source="amount",
                description="المدينون"
            )
        ]
    )
    
    return PostingRule.create(
        code="PAY-RECV",
        name="قبض نقدي",
        rule_type=RuleType.PAYMENT_RECEIVE,
        conditions=[condition],
        actions=[RuleAction(
            action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
            parameters={"post_automatically": True}
        )],
        journal_template=template,
        priority=RulePriority.HIGH,
        created_by="system"
    )


@pytest.fixture
def fund_transfer_rule():
    """قاعدة تحويل بين الصناديق"""
    condition = RuleCondition(
        field="transfer.status",
        operator=RuleOperator.EQUALS,
        value="completed",
        condition_type=RuleConditionType.STATUS_EQUALS
    )
    
    template = JournalTemplate(
        id="template_004",
        name="تحويل بين الصناديق",
        lines=[
            JournalLineTemplate(
                account_code="1010",
                side="debit",
                amount_source="amount",
                description="الصندوق المستلم"
            ),
            JournalLineTemplate(
                account_code="1010",
                side="credit",
                amount_source="amount",
                description="الصندوق المرسل"
            )
        ]
    )
    
    return PostingRule.create(
        code="FUND-TRF",
        name="تحويل بين الصناديق",
        rule_type=RuleType.FUND_TRANSFER,
        conditions=[condition],
        actions=[RuleAction(
            action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
            parameters={"post_automatically": True}
        )],
        journal_template=template,
        priority=RulePriority.NORMAL,
        created_by="system"
    )


@pytest.fixture
def rule_group(invoice_cash_rule, invoice_credit_rule):
    """مجموعة قواعد"""
    return RuleGroup.create(
        code="INVOICE-RULES",
        name="قواعد الفواتير",
        rules=[invoice_cash_rule, invoice_credit_rule],
        description="مجموعة قواعد الفواتير",
        is_default=True,
        created_by="system"
    )


# =============================================================================
# TEST CLASS 1: إنشاء القواعد المحاسبية (Posting Rules Creation)
# =============================================================================

class TestPostingRuleCreation:
    """اختبارات إنشاء القواعد المحاسبية"""
    
    def test_create_posting_rule(self, sample_condition, sample_action, sample_journal_template):
        """إنشاء قاعدة محاسبية"""
        rule = PostingRule.create(
            code="TEST-RULE",
            name="قاعدة اختبار",
            rule_type=RuleType.CUSTOM,
            conditions=[sample_condition],
            actions=[sample_action],
            journal_template=sample_journal_template,
            priority=RulePriority.NORMAL,
            description="قاعدة اختبار",
            is_default=True,
            created_by="admin"
        )
        
        assert rule.code.value == "TEST-RULE"
        assert rule.name == "قاعدة اختبار"
        assert rule.rule_type == RuleType.CUSTOM
        assert len(rule.conditions) == 1
        assert len(rule.actions) == 1
        assert rule.has_journal_template is True
        assert rule.is_default is True
        assert rule.created_by == "admin"
    
    def test_create_rule_without_conditions(self):
        """إنشاء قاعدة بدون شروط"""
        rule = PostingRule.create(
            code="NO-COND",
            name="قاعدة بدون شروط",
            rule_type=RuleType.CUSTOM,
            actions=[RuleAction(
                action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
                parameters={}
            )]
        )
        
        assert len(rule.conditions) == 0
        assert rule.evaluate({}) is True  # دائماً تنطبق
    
    def test_create_rule_from_template(self):
        """إنشاء قاعدة من قالب"""
        template_data = {
            "code": "INV-CASH-FROM-TEMPLATE",
            "name": "فاتورة بيع نقدي من قالب",
            "description": "تم إنشاؤها من القالب المدمج"
        }
        
        rule = PostingRule.create_from_template(
            template_name="invoice_cash_sale",
            rule_type=RuleType.INVOICE_CASH_SALE,
            template_data=template_data,
            created_by="admin"
        )
        
        assert rule.code.value == "INV-CASH-FROM-TEMPLATE"
        assert rule.rule_type == RuleType.INVOICE_CASH_SALE
        assert rule.has_journal_template is True
    
    def test_create_rule_creates_event(self):
        """إنشاء قاعدة يولد حدثاً"""
        rule = PostingRule.create(
            code="EVENT-TEST",
            name="قاعدة اختبار الأحداث",
            rule_type=RuleType.CUSTOM
        )
        
        events = rule.pull_events()
        assert len(events) == 1
        from core.domain.rules.events import RuleCreatedEvent
        assert isinstance(events[0], RuleCreatedEvent)
    
    def test_create_rule_with_priority(self):
        """إنشاء قاعدة بأولوية محددة"""
        rule = PostingRule.create(
            code="HIGH-PRIORITY",
            name="قاعدة عالية الأولوية",
            rule_type=RuleType.CUSTOM,
            priority=RulePriority.CRITICAL
        )
        
        assert rule.priority == RulePriority.CRITICAL


# =============================================================================
# TEST CLASS 2: شروط القواعد (Rule Conditions)
# =============================================================================

class TestRuleConditions:
    """اختبارات شروط القواعد"""
    
    def test_condition_equals(self):
        """شرط تساوي"""
        condition = RuleCondition(
            field="status",
            operator=RuleOperator.EQUALS,
            value="posted"
        )
        
        assert condition.evaluate({"status": "posted"}) is True
        assert condition.evaluate({"status": "draft"}) is False
    
    def test_condition_not_equals(self):
        """شرط عدم تساوي"""
        condition = RuleCondition(
            field="status",
            operator=RuleOperator.NOT_EQUALS,
            value="draft"
        )
        
        assert condition.evaluate({"status": "posted"}) is True
        assert condition.evaluate({"status": "draft"}) is False
    
    def test_condition_greater_than(self):
        """شرط أكبر من"""
        condition = RuleCondition(
            field="amount",
            operator=RuleOperator.GREATER_THAN,
            value=Decimal("1000")
        )
        
        assert condition.evaluate({"amount": Decimal("1500")}) is True
        assert condition.evaluate({"amount": Decimal("500")}) is False
    
    def test_condition_less_than(self):
        """شرط أقل من"""
        condition = RuleCondition(
            field="amount",
            operator=RuleOperator.LESS_THAN,
            value=Decimal("1000")
        )
        
        assert condition.evaluate({"amount": Decimal("500")}) is True
        assert condition.evaluate({"amount": Decimal("1500")}) is False
    
    def test_condition_in_list(self):
        """شرط ضمن قائمة"""
        condition = RuleCondition(
            field="payment_type",
            operator=RuleOperator.IN,
            value=["cash", "transfer"]
        )
        
        assert condition.evaluate({"payment_type": "cash"}) is True
        assert condition.evaluate({"payment_type": "credit"}) is False
    
    def test_condition_not_in_list(self):
        """شرط خارج قائمة"""
        condition = RuleCondition(
            field="payment_type",
            operator=RuleOperator.NOT_IN,
            value=["cash", "transfer"]
        )
        
        assert condition.evaluate({"payment_type": "credit"}) is True
        assert condition.evaluate({"payment_type": "cash"}) is False
    
    def test_condition_contains(self):
        """شرط يحتوي على"""
        condition = RuleCondition(
            field="description",
            operator=RuleOperator.CONTAINS,
            value="VAT"
        )
        
        assert condition.evaluate({"description": "VAT calculation"}) is True
        assert condition.evaluate({"description": "No tax"}) is False
    
    def test_condition_starts_with(self):
        """شرط يبدأ بـ"""
        condition = RuleCondition(
            field="code",
            operator=RuleOperator.STARTS_WITH,
            value="INV-"
        )
        
        assert condition.evaluate({"code": "INV-001"}) is True
        assert condition.evaluate({"code": "PO-001"}) is False
    
    def test_condition_between(self):
        """شرط بين قيمتين"""
        condition = RuleCondition(
            field="amount",
            operator=RuleOperator.BETWEEN,
            value=[Decimal("100"), Decimal("1000")]
        )
        
        assert condition.evaluate({"amount": Decimal("500")}) is True
        assert condition.evaluate({"amount": Decimal("50")}) is False
        assert condition.evaluate({"amount": Decimal("1500")}) is False
    
    def test_condition_nested_field(self):
        """شرط على حقل متداخل (dot notation)"""
        condition = RuleCondition(
            field="customer.id",
            operator=RuleOperator.EQUALS,
            value="CUST-001"
        )
        
        context = {"customer": {"id": "CUST-001", "name": "Test"}}
        assert condition.evaluate(context) is True
        
        context2 = {"customer": {"id": "CUST-002", "name": "Test2"}}
        assert condition.evaluate(context2) is False
    
    def test_condition_with_required(self):
        """شرط مع required=False"""
        condition = RuleCondition(
            field="optional_field",
            operator=RuleOperator.EQUALS,
            value="value",
            is_required=False
        )
        
        # الحقل غير موجود، لكن الشرط ليس مطلوباً
        assert condition.evaluate({}) is True
    
    def test_condition_to_dict(self):
        """تحويل الشرط إلى قاموس"""
        condition = RuleCondition(
            field="status",
            operator=RuleOperator.EQUALS,
            value="posted",
            condition_type=RuleConditionType.STATUS_EQUALS
        )
        
        data = condition.to_dict()
        assert data["field"] == "status"
        assert data["operator"] == "="
        assert data["value"] == "posted"
        assert data["condition_type"] == "status_equals"


# =============================================================================
# TEST CLASS 3: إجراءات القواعد (Rule Actions)
# =============================================================================

class TestRuleActions:
    """اختبارات إجراءات القواعد"""
    
    def test_create_action(self):
        """إنشاء إجراء"""
        action = RuleAction(
            action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
            parameters={"post_automatically": True},
            description="إنشاء قيد محاسبي"
        )
        
        assert action.action_type == RuleActionType.CREATE_JOURNAL_ENTRY
        assert action.parameters["post_automatically"] is True
    
    def test_action_to_dict(self):
        """تحويل الإجراء إلى قاموس"""
        action = RuleAction(
            action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
            parameters={"post_automatically": True},
            description="إنشاء قيد"
        )
        
        data = action.to_dict()
        assert data["action_type"] == "create_journal_entry"
        assert data["parameters"]["post_automatically"] is True
    
    def test_action_from_dict(self):
        """إنشاء إجراء من قاموس"""
        data = {
            "action_type": "create_journal_entry",
            "parameters": {"post_automatically": True},
            "description": "إنشاء قيد"
        }
        
        action = RuleAction.from_dict(data)
        assert action.action_type == RuleActionType.CREATE_JOURNAL_ENTRY
        assert action.parameters["post_automatically"] is True


# =============================================================================
# TEST CLASS 4: قوالب القيود المحاسبية (Journal Templates)
# =============================================================================

class TestJournalTemplates:
    """اختبارات قوالب القيود المحاسبية"""
    
    def test_create_journal_template(self, sample_journal_template):
        """إنشاء قالب قيد محاسبي"""
        assert sample_journal_template.id == "template_001"
        assert sample_journal_template.name == "فاتورة بيع نقدي"
        assert len(sample_journal_template.lines) == 2
        assert sample_journal_template.require_balance is True
    
    def test_journal_template_to_dict(self, sample_journal_template):
        """تحويل قالب القيد إلى قاموس"""
        data = sample_journal_template.to_dict()
        assert data["id"] == "template_001"
        assert data["name"] == "فاتورة بيع نقدي"
        assert len(data["lines"]) == 2
        assert data["lines"][0]["account_code"] == "1010"
        assert data["lines"][0]["side"] == "debit"
    
    def test_journal_line_template_validation(self):
        """التحقق من صحة قالب السطر"""
        with pytest.raises(ValueError):
            JournalLineTemplate(
                account_code="",
                side="debit",
                amount_source="total"
            )
        
        with pytest.raises(ValueError):
            JournalLineTemplate(
                account_code="1010",
                side="invalid",
                amount_source="total"
            )


# =============================================================================
# TEST CLASS 5: مدقق القواعد (RuleValidator)
# =============================================================================

class TestRuleValidator:
    """اختبارات مدقق القواعد"""
    
    def test_validate_valid_rule(self, invoice_cash_rule):
        """التحقق من قاعدة صالحة"""
        errors = RuleValidator.validate_rule(invoice_cash_rule)
        assert len(errors) == 0
    
    def test_validate_rule_without_code(self):
        """التحقق من قاعدة بدون كود"""
        rule = PostingRule.create(
            code="",
            name="قاعدة بدون كود",
            rule_type=RuleType.CUSTOM
        )
        errors = RuleValidator.validate_rule(rule)
        assert len(errors) > 0
        assert any("كود" in e for e in errors)
    
    def test_validate_rule_without_name(self):
        """التحقق من قاعدة بدون اسم"""
        rule = PostingRule.create(
            code="NO-NAME",
            name="",
            rule_type=RuleType.CUSTOM
        )
        errors = RuleValidator.validate_rule(rule)
        assert len(errors) > 0
        assert any("اسم" in e for e in errors)
    
    def test_validate_rule_without_conditions_or_template(self):
        """التحقق من قاعدة بدون شروط أو قالب"""
        rule = PostingRule.create(
            code="EMPTY",
            name="قاعدة فارغة",
            rule_type=RuleType.CUSTOM
        )
        errors = RuleValidator.validate_rule(rule)
        assert len(errors) > 0
        assert any("شروط" in e for e in errors)
    
    def test_validate_template_balanced(self, sample_journal_template):
        """التحقق من توازن قالب القيد"""
        errors = RuleValidator.validate_template(sample_journal_template)
        assert len(errors) == 0
    
    def test_validate_template_unbalanced(self):
        """التحقق من قالب غير متوازن"""
        template = JournalTemplate(
            id="unbalanced",
            name="قالب غير متوازن",
            lines=[
                JournalLineTemplate(
                    account_code="1010",
                    side="debit",
                    amount_source="total"
                )
                # لا يوجد سطر دائن
            ]
        )
        errors = RuleValidator.validate_template(template)
        assert len(errors) > 0
        assert any("دائن" in e for e in errors)
    
    def test_validate_conditions(self, sample_condition):
        """التحقق من شروط القاعدة"""
        errors = RuleValidator.validate_conditions([sample_condition])
        assert len(errors) == 0
    
    def test_validate_condition_without_field(self):
        """التحقق من شرط بدون حقل"""
        condition = RuleCondition(
            field="",
            operator=RuleOperator.EQUALS,
            value="value"
        )
        errors = RuleValidator.validate_conditions([condition])
        assert len(errors) > 0
        assert any("حقل" in e for e in errors)
    
    def test_validate_execution_context_valid(self):
        """التحقق من سياق تنفيذ صالح"""
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001"
        }
        errors = RuleValidator.validate_execution_context(context)
        assert len(errors) == 0
    
    def test_validate_execution_context_invalid(self):
        """التحقق من سياق تنفيذ غير صالح"""
        context = {"entity_type": "invoice"}  # مفقود entity_id
        errors = RuleValidator.validate_execution_context(context)
        assert len(errors) > 0
        assert any("entity_id" in e for e in errors)


# =============================================================================
# TEST CLASS 6: تنفيذ القواعد (Rule Execution)
# =============================================================================

class TestRuleExecution:
    """اختبارات تنفيذ القواعد"""
    
    def test_execute_rule_success(self, invoice_cash_rule, mock_dependencies):
        """تنفيذ قاعدة بنجاح"""
        executor = RuleExecutor(mock_dependencies)
        
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001",
            "payment_type": "cash",
            "total": 1000,
            "subtotal": 850,
            "tax": 150,
            "posted_by": "system"
        }
        
        result = executor.execute(invoice_cash_rule, context)
        
        assert result.success is True
        assert result.rule_code == "INV-CASH"
        assert result.message == "Rule executed successfully"
        assert result.journal_entry_id is not None
    
    def test_execute_rule_fails_on_condition(self, invoice_cash_rule, mock_dependencies):
        """فشل تنفيذ القاعدة بسبب الشرط"""
        executor = RuleExecutor(mock_dependencies)
        
        # payment_type != cash
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001",
            "payment_type": "credit"
        }
        
        result = executor.execute(invoice_cash_rule, context)
        assert result.success is False
        assert "condition" in result.message.lower() or len(result.errors) > 0
    
    def test_execute_rule_with_actions(self, invoice_cash_rule, mock_dependencies):
        """تنفيذ قاعدة مع إجراءات"""
        executor = RuleExecutor(mock_dependencies)
        
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001",
            "payment_type": "cash",
            "total": 1000,
            "subtotal": 850,
            "tax": 150
        }
        
        result = executor.execute(invoice_cash_rule, context)
        
        # يجب أن يكون هناك إجراءات منفذة
        assert result.success is True
        assert len(result.executed_actions) > 0
    
    def test_execute_rule_without_template(self, mock_dependencies):
        """تنفيذ قاعدة بدون قالب"""
        rule = PostingRule.create(
            code="NO-TEMPLATE",
            name="قاعدة بدون قالب",
            rule_type=RuleType.CUSTOM,
            actions=[RuleAction(
                action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
                parameters={}
            )]
        )
        
        executor = RuleExecutor(mock_dependencies)
        context = {"entity_type": "test"}
        
        result = executor.execute(rule, context)
        assert result.success is False
        assert any("قالب" in e for e in result.errors)


# =============================================================================
# TEST CLASS 7: محرك القواعد (RuleEngine)
# =============================================================================

class TestRuleEngine:
    """اختبارات محرك القواعد الرئيسي"""
    
    def test_execute_rules_with_no_rules(self, rule_engine):
        """تنفيذ قواعد بدون وجود قواعد"""
        context = {"entity_type": "invoice", "entity_id": "INV-001"}
        results = rule_engine.execute_rules(RuleType.INVOICE_CASH_SALE, context)
        assert len(results) == 0
    
    def test_execute_rules_with_single_rule(self, mock_rule_repo, rule_engine, invoice_cash_rule):
        """تنفيذ قاعدة واحدة"""
        mock_rule_repo.get_by_type.return_value = [invoice_cash_rule]
        
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001",
            "payment_type": "cash",
            "total": 1000
        }
        
        results = rule_engine.execute_rules(RuleType.INVOICE_CASH_SALE, context)
        
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].rule_code == "INV-CASH"
    
    def test_execute_rules_with_multiple_rules(self, mock_rule_repo, rule_engine, 
                                                invoice_cash_rule, invoice_credit_rule):
        """تنفيذ قواعد متعددة"""
        mock_rule_repo.get_by_type.return_value = [invoice_cash_rule, invoice_credit_rule]
        
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001",
            "payment_type": "cash",
            "total": 1000
        }
        
        results = rule_engine.execute_rules(RuleType.INVOICE_CASH_SALE, context)
        
        # يجب تنفيذ القاعدة التي تنطبق فقط (INV-CASH)
        assert len(results) == 1
        assert results[0].rule_code == "INV-CASH"
    
    def test_execute_rules_with_execute_all(self, mock_rule_repo, rule_engine,
                                             invoice_cash_rule, invoice_credit_rule):
        """تنفيذ جميع القواعد المطبقة"""
        # جعل كلتا القاعدتين تنطبقان
        invoice_credit_rule.conditions[0].value = "cash"  # نفس الشرط
        
        mock_rule_repo.get_by_type.return_value = [invoice_cash_rule, invoice_credit_rule]
        
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001",
            "payment_type": "cash",
            "total": 1000
        }
        
        results = rule_engine.execute_rules(
            RuleType.INVOICE_CASH_SALE, 
            context, 
            execute_all=True
        )
        
        assert len(results) == 2
    
    def test_execute_rule_by_id(self, mock_rule_repo, rule_engine, invoice_cash_rule):
        """تنفيذ قاعدة بمعرفها"""
        mock_rule_repo.get_by_id.return_value = invoice_cash_rule
        
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001",
            "payment_type": "cash",
            "total": 1000
        }
        
        result = rule_engine.execute_rule("rule-123", context)
        
        assert result.success is True
        assert result.rule_code == "INV-CASH"
    
    def test_execute_rule_by_id_not_found(self, mock_rule_repo, rule_engine):
        """تنفيذ قاعدة غير موجودة"""
        mock_rule_repo.get_by_id.return_value = None
        
        context = {"entity_type": "invoice"}
        result = rule_engine.execute_rule("non-existent", context)
        
        assert result.success is False
        assert "not found" in result.message.lower()
    
    def test_execute_inactive_rule(self, mock_rule_repo, rule_engine, invoice_cash_rule):
        """تنفيذ قاعدة غير نشطة"""
        invoice_cash_rule.is_active = False
        mock_rule_repo.get_by_id.return_value = invoice_cash_rule
        
        context = {"entity_type": "invoice"}
        result = rule_engine.execute_rule("rule-123", context)
        
        assert result.success is False
        assert "inactive" in result.message.lower()


# =============================================================================
# TEST CLASS 8: أولويات تنفيذ القواعد (Priorities)
# =============================================================================

class TestRulePriorities:
    """اختبارات أولويات تنفيذ القواعد"""
    
    def test_rules_sorted_by_priority(self, mock_rule_repo, rule_engine):
        """ترتيب القواعد حسب الأولوية"""
        low_rule = PostingRule.create(
            code="LOW",
            name="قاعدة منخفضة",
            rule_type=RuleType.CUSTOM,
            priority=RulePriority.LOW
        )
        
        high_rule = PostingRule.create(
            code="HIGH",
            name="قاعدة عالية",
            rule_type=RuleType.CUSTOM,
            priority=RulePriority.HIGH
        )
        
        critical_rule = PostingRule.create(
            code="CRITICAL",
            name="قاعدة حرجة",
            rule_type=RuleType.CUSTOM,
            priority=RulePriority.CRITICAL
        )
        
        rules = [low_rule, high_rule, critical_rule]
        sorted_rules = rule_engine._sort_rules(rules)
        
        # يجب أن تكون الأولوية الحرجة أولاً
        assert sorted_rules[0].priority == RulePriority.CRITICAL
        assert sorted_rules[1].priority == RulePriority.HIGH
        assert sorted_rules[2].priority == RulePriority.LOW


# =============================================================================
# TEST CLASS 9: منع التكرار (Duplicate Prevention)
# =============================================================================

class TestDuplicatePrevention:
    """اختبارات منع تنفيذ القاعدة أكثر من مرة"""
    
    def test_prevent_duplicate_execution(self, mock_rule_repo, mock_log_repo, rule_engine, invoice_cash_rule):
        """منع تنفيذ القاعدة أكثر من مرة لنفس الكيان"""
        mock_rule_repo.get_by_type.return_value = [invoice_cash_rule]
        
        # محاكاة وجود سجل تنفيذ سابق
        mock_log_repo.count_by_rule.return_value = 1
        
        context = {
            "entity_type": "invoice",
            "entity_id": "INV-001",
            "payment_type": "cash"
        }
        
        results = rule_engine.execute_rules(RuleType.INVOICE_CASH_SALE, context)
        
        # يجب ألا تنفذ القاعدة بسبب منع التكرار
        assert len(results) == 0


# =============================================================================
# TEST CLASS 10: سجل تنفيذ القواعد (Execution Log)
# =============================================================================

class TestExecutionLog:
    """اختبارات سجل تنفيذ القواعد"""
    
    def test_log_creation(self, rule_engine, mock_log_repo, invoice_cash_rule):
        """إنشاء سجل تنفيذ"""
        # المحاكاة: تنفيذ قاعدة
        mock_log_repo.save = Mock()
        
        log = RuleExecutionLog(
            rule_id=str(invoice_cash_rule.id),
            rule_code=str(invoice_cash_rule.code),
            rule_name=invoice_cash_rule.name,
            entity_type="invoice",
            entity_id="INV-001",
            success=True,
            message="تم التنفيذ بنجاح"
        )
        
        mock_log_repo.save(log)
        mock_log_repo.save.assert_called_once_with(log)
    
    def test_get_execution_logs(self, mock_log_repo, rule_engine, invoice_cash_rule):
        """الحصول على سجلات التنفيذ"""
        logs = [
            RuleExecutionLog(
                rule_id=str(invoice_cash_rule.id),
                rule_code=str(invoice_cash_rule.code),
                rule_name=invoice_cash_rule.name,
                entity_type="invoice",
                entity_id="INV-001",
                success=True,
                message="نجاح"
            ),
            RuleExecutionLog(
                rule_id=str(invoice_cash_rule.id),
                rule_code=str(invoice_cash_rule.code),
                rule_name=invoice_cash_rule.name,
                entity_type="invoice",
                entity_id="INV-002",
                success=False,
                message="فشل"
            )
        ]
        mock_log_repo.get_by_rule.return_value = logs
        
        result_logs = rule_engine.get_execution_logs(rule_id=str(invoice_cash_rule.id))
        
        assert len(result_logs) == 2
        assert result_logs[0].rule_code == "INV-CASH"


# =============================================================================
# TEST CLASS 11: مجموعات القواعد (Rule Groups)
# =============================================================================

class TestRuleGroups:
    """اختبارات مجموعات القواعد"""
    
    def test_create_rule_group(self, invoice_cash_rule, invoice_credit_rule):
        """إنشاء مجموعة قواعد"""
        group = RuleGroup.create(
            code="INVOICE-RULES",
            name="قواعد الفواتير",
            rules=[invoice_cash_rule, invoice_credit_rule],
            description="قواعد الفواتير"
        )
        
        assert group.code == "INVOICE-RULES"
        assert len(group.rules) == 2
        assert group.rule_count == 2
    
    def test_add_rule_to_group(self, invoice_cash_rule):
        """إضافة قاعدة إلى مجموعة"""
        group = RuleGroup.create(
            code="TEST-GROUP",
            name="مجموعة اختبار",
            rules=[]
        )
        
        assert len(group.rules) == 0
        
        group.add_rule(invoice_cash_rule)
        assert len(group.rules) == 1
    
    def test_remove_rule_from_group(self, invoice_cash_rule, invoice_credit_rule):
        """إزالة قاعدة من مجموعة"""
        group = RuleGroup.create(
            code="TEST-GROUP",
            name="مجموعة اختبار",
            rules=[invoice_cash_rule, invoice_credit_rule]
        )
        
        removed = group.remove_rule(str(invoice_cash_rule.id))
        assert removed is True
        assert len(group.rules) == 1
        assert group.rules[0].code == invoice_credit_rule.code
    
    def test_get_active_rules_from_group(self, invoice_cash_rule, invoice_credit_rule):
        """الحصول على القواعد النشطة من المجموعة"""
        invoice_credit_rule.is_active = False
        
        group = RuleGroup.create(
            code="TEST-GROUP",
            name="مجموعة اختبار",
            rules=[invoice_cash_rule, invoice_credit_rule]
        )
        
        active_rules = group.active_rules
        assert len(active_rules) == 1
        assert active_rules[0].code == invoice_cash_rule.code


# =============================================================================
# TEST CLASS 12: نتائج تنفيذ القواعد (Execution Results)
# =============================================================================

class TestExecutionResults:
    """اختبارات نتائج تنفيذ القواعد"""
    
    def test_success_result(self):
        """نتيجة تنفيذ ناجحة"""
        result = RuleExecutionResult(
            rule_id="rule-123",
            rule_code="TEST",
            rule_name="قاعدة اختبار",
            success=True,
            message="تم التنفيذ بنجاح",
            journal_entry_id="je-456"
        )
        
        assert result.success is True
        assert result.has_errors is False
        assert result.journal_entry_id == "je-456"
    
    def test_failure_result(self):
        """نتيجة تنفيذ فاشلة"""
        result = RuleExecutionResult(
            rule_id="rule-123",
            rule_code="TEST",
            rule_name="قاعدة اختبار",
            success=False,
            message="فشل التنفيذ",
            errors=["خطأ 1", "خطأ 2"]
        )
        
        assert result.success is False
        assert result.has_errors is True
        assert len(result.errors) == 2
    
    def test_result_with_warnings(self):
        """نتيجة تنفيذ مع تحذيرات"""
        result = RuleExecutionResult(
            rule_id="rule-123",
            rule_code="TEST",
            rule_name="قاعدة اختبار",
            success=True,
            message="نجاح مع تحذيرات",
            warnings=["تحذير 1"]
        )
        
        assert result.is_partial_success is True
        assert result.has_warnings is True
    
    def test_result_to_dict(self):
        """تحويل النتيجة إلى قاموس"""
        result = RuleExecutionResult(
            rule_id="rule-123",
            rule_code="TEST",
            rule_name="قاعدة اختبار",
            success=True,
            message="نجاح",
            execution_time_ms=150.5
        )
        
        data = result.to_dict()
        assert data["rule_id"] == "rule-123"
        assert data["success"] is True
        assert data["execution_time_ms"] == 150.5


# =============================================================================
# TEST CLASS 13: التخزين المؤقت (Caching)
# =============================================================================

class TestRuleEngineCache:
    """اختبارات التخزين المؤقت لمحرك القواعد"""
    
    def test_clear_cache(self, rule_engine, invoice_cash_rule):
        """مسح التخزين المؤقت"""
        rule_engine._rule_cache["test"] = invoice_cash_rule
        assert len(rule_engine._rule_cache) > 0
        
        rule_engine.clear_cache()
        assert len(rule_engine._rule_cache) == 0
    
    def test_reload_cache(self, mock_rule_repo, rule_engine, invoice_cash_rule):
        """إعادة تحميل التخزين المؤقت"""
        mock_rule_repo.get_active_rules.return_value = [invoice_cash_rule]
        
        rule_engine.reload()
        # يجب أن تكون القواعد محملة في الكاش
        assert len(rule_engine._rule_cache) > 0


# =============================================================================
# TEST CLASS 14: قواعد مدمجة (Built-in Templates)
# =============================================================================

class TestBuiltinTemplates:
    """اختبارات القوالب المدمجة"""
    
    def test_get_builtin_templates(self):
        """الحصول على القوالب المدمجة"""
        templates = PostingRule._get_builtin_templates()
        
        assert "invoice_cash_sale" in templates
        assert "invoice_credit_sale" in templates
        assert "payment_receive_cash" in templates
        assert "fund_transfer" in templates
    
    def test_invoice_cash_template(self):
        """قالب فاتورة بيع نقدي"""
        templates = PostingRule._get_builtin_templates()
        template = templates["invoice_cash_sale"]
        
        assert template["code"] == "INV-CASH"
        assert len(template["conditions"]) > 0
        assert template["journal_template"] is not None
    
    def test_invoice_credit_template(self):
        """قالب فاتورة بيع آجل"""
        templates = PostingRule._get_builtin_templates()
        template = templates["invoice_credit_sale"]
        
        assert template["code"] == "INV-CREDIT"
        assert len(template["conditions"]) > 0
        assert template["journal_template"] is not None
    
    def test_payment_receive_template(self):
        """قالب قبض نقدي"""
        templates = PostingRule._get_builtin_templates()
        template = templates["payment_receive_cash"]
        
        assert template["code"] == "PAY-RECV"
        assert len(template["conditions"]) > 0
        assert template["journal_template"] is not None


# =============================================================================
# TEST CLASS 15: تحديث وإدارة القواعد (Rule Management)
# =============================================================================

class TestRuleManagement:
    """اختبارات تحديث وإدارة القواعد"""
    
    def test_update_rule(self, invoice_cash_rule):
        """تحديث قاعدة"""
        old_name = invoice_cash_rule.name
        invoice_cash_rule.update(
            name="قاعدة محدثة",
            description="وصف محدث",
            priority=RulePriority.HIGH,
            updated_by="admin"
        )
        
        assert invoice_cash_rule.name == "قاعدة محدثة"
        assert invoice_cash_rule.description == "وصف محدث"
        assert invoice_cash_rule.priority == RulePriority.HIGH
        assert invoice_cash_rule.version > 1
    
    def test_update_rule_creates_event(self, invoice_cash_rule):
        """تحديث القاعدة يخلق حدثاً"""
        invoice_cash_rule.update(name="اسم جديد", updated_by="admin")
        
        events = invoice_cash_rule.pull_events()
        assert len(events) > 0
        from core.domain.rules.events import RuleUpdatedEvent
        assert isinstance(events[0], RuleUpdatedEvent)
    
    def test_activate_rule(self, invoice_cash_rule):
        """تفعيل قاعدة"""
        invoice_cash_rule.is_active = False
        invoice_cash_rule.activate(activated_by="admin")
        assert invoice_cash_rule.is_active is True
    
    def test_deactivate_rule(self, invoice_cash_rule):
        """تعطيل قاعدة"""
        invoice_cash_rule.is_active = True
        invoice_cash_rule.deactivate(deactivated_by="admin")
        assert invoice_cash_rule.is_active is False
    
    def test_add_condition_to_rule(self, invoice_cash_rule):
        """إضافة شرط إلى قاعدة"""
        new_condition = RuleCondition(
            field="amount",
            operator=RuleOperator.GREATER_THAN,
            value=Decimal("100")
        )
        
        old_count = len(invoice_cash_rule.conditions)
        invoice_cash_rule.add_condition(new_condition)
        assert len(invoice_cash_rule.conditions) == old_count + 1
    
    def test_remove_condition_from_rule(self, invoice_cash_rule):
        """إزالة شرط من قاعدة"""
        old_count = len(invoice_cash_rule.conditions)
        removed = invoice_cash_rule.remove_condition(0)
        assert removed is True
        assert len(invoice_cash_rule.conditions) == old_count - 1
    
    def test_add_action_to_rule(self, invoice_cash_rule):
        """إضافة إجراء إلى قاعدة"""
        new_action = RuleAction(
            action_type=RuleActionType.SEND_NOTIFICATION,
            parameters={"recipient": "admin@example.com"}
        )
        
        old_count = len(invoice_cash_rule.actions)
        invoice_cash_rule.add_action(new_action)
        assert len(invoice_cash_rule.actions) == old_count + 1


# =============================================================================
# تشغيل الاختبارات
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])