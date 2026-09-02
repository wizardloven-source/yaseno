# core/domain/rules/entities.py
"""
Accounting Rules Entities - كيانات محرك القواعد المحاسبية
✅ يدعم: PostingRule (القاعدة الأساسية)
✅ يدعم: RuleGroup (مجموعة قواعد)
✅ يدعم: RuleExecutionLog (سجل تنفيذ القواعد)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from decimal import Decimal

from .value_objects import (
    RuleId, RuleCode, RuleOrder, RuleType, RulePriority,
    RuleCondition, RuleAction, JournalTemplate,
    RuleConditionType, RuleOperator, RuleActionType
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# PostingRule - القاعدة المحاسبية (AGGREGATE ROOT)
# =============================================================================

@dataclass
class PostingRule:
    """
    AGGREGATE ROOT - القاعدة المحاسبية
    
    تحدد كيفية إنشاء القيود المحاسبية تلقائياً بناءً على شروط محددة.
    
    الميزات:
        1. يدعم أنواع متعددة من المعاملات (فواتير، مدفوعات، صناديق، إلخ)
        2. يدعم شروط متقدمة (مبلغ، عملة، عميل، منتج، موقع، إلخ)
        3. يدعم قوالب قيود محاسبية قابلة للتخصيص
        4. يدعم أولويات التنفيذ
        5. يدعم التفعيل والتعطيل
        6. يدعم سجل تنفيذ كامل
    """

    # ========== معلومات أساسية ==========
    id: RuleId = field(default_factory=RuleId.generate)
    code: RuleCode = field(default_factory=lambda: RuleCode(""))
    name: str = ""
    description: Optional[str] = None

    # ========== نوع القاعدة ==========
    rule_type: RuleType = RuleType.CUSTOM

    # ========== الأولوية ==========
    priority: RulePriority = RulePriority.NORMAL
    order: RuleOrder = field(default_factory=lambda: RuleOrder(0))

    # ========== الشروط ==========
    conditions: List[RuleCondition] = field(default_factory=list)
    condition_logic: str = "AND"  # AND, OR

    # ========== الإجراءات ==========
    actions: List[RuleAction] = field(default_factory=list)

    # ========== قالب القيد المحاسبي ==========
    journal_template: Optional[JournalTemplate] = None

    # ========== الحالة ==========
    is_active: bool = True
    is_default: bool = False
    is_mandatory: bool = False

    # ========== تقييد التكرار ==========
    prevent_duplicate: bool = True
    duplicate_check_fields: List[str] = field(default_factory=list)

    # ========== بيانات التدقيق ==========
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    version: int = 1

    # ========== أحداث المجال ==========
    _events: List[Any] = field(default_factory=list, repr=False)

    # =========================================================================
    # الخصائص المحسوبة
    # =========================================================================

    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"

    @property
    def condition_count(self) -> int:
        return len(self.conditions)

    @property
    def action_count(self) -> int:
        return len(self.actions)

    @property
    def has_journal_template(self) -> bool:
        return self.journal_template is not None

    # =========================================================================
    # دوال المصنع
    # =========================================================================

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        rule_type: RuleType,
        conditions: Optional[List[RuleCondition]] = None,
        actions: Optional[List[RuleAction]] = None,
        journal_template: Optional[JournalTemplate] = None,
        priority: RulePriority = RulePriority.NORMAL,
        description: Optional[str] = None,
        is_default: bool = False,
        is_mandatory: bool = False,
        created_by: str = "system"
    ) -> 'PostingRule':
        """إنشاء قاعدة محاسبية جديدة"""
        rule = cls(
            code=RuleCode(code),
            name=name,
            description=description,
            rule_type=rule_type,
            priority=priority,
            conditions=conditions or [],
            actions=actions or [],
            journal_template=journal_template,
            is_default=is_default,
            is_mandatory=is_mandatory,
            created_by=created_by,
            updated_by=created_by
        )

        from .events import RuleCreatedEvent
        rule._events.append(RuleCreatedEvent(
            rule_id=rule.id,
            rule_code=rule.code,
            rule_name=rule.name,
            rule_type=rule.rule_type,
            created_by=created_by
        ))

        return rule

    @classmethod
    def create_from_template(
        cls,
        template_name: str,
        rule_type: RuleType,
        template_data: Dict[str, Any],
        created_by: str = "system"
    ) -> 'PostingRule':
        """إنشاء قاعدة من قالب مسبق"""
        # قوالب مدمجة
        templates = cls._get_builtin_templates()

        if template_name not in templates:
            raise ValueError(f"Template '{template_name}' not found")

        template = templates[template_name]
        template['rule_type'] = rule_type
        template['created_by'] = created_by

        return cls.create(**template)

    @classmethod
    def _get_builtin_templates(cls) -> Dict[str, Dict[str, Any]]:
        """الحصول على القوالب المدمجة"""
        return {
            "invoice_cash_sale": {
                "code": "INV-CASH",
                "name": "فاتورة بيع نقدي",
                "description": "إنشاء قيد محاسبي لفاتورة بيع نقدي",
                "conditions": [
                    RuleCondition(
                        field="invoice.payment_type",
                        operator=RuleOperator.EQUALS,
                        value="cash",
                        condition_type=RuleConditionType.STATUS_EQUALS
                    ),
                    RuleCondition(
                        field="invoice.status",
                        operator=RuleOperator.EQUALS,
                        value="posted",
                        condition_type=RuleConditionType.STATUS_EQUALS
                    )
                ],
                "actions": [
                    RuleAction(
                        action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
                        parameters={"post_automatically": True}
                    )
                ],
                "journal_template": JournalTemplate(
                    id="template_invoice_cash",
                    name="فاتورة بيع نقدي",
                    lines=[
                        JournalLineTemplate(
                            account_code="1010",  # الصندوق
                            side="debit",
                            amount_source="total"
                        ),
                        JournalLineTemplate(
                            account_code="4010",  # إيرادات المبيعات
                            side="credit",
                            amount_source="subtotal"
                        ),
                        JournalLineTemplate(
                            account_code="2100",  # ضريبة مستحقة
                            side="credit",
                            amount_source="tax"
                        )
                    ]
                )
            },

            "invoice_credit_sale": {
                "code": "INV-CREDIT",
                "name": "فاتورة بيع آجل",
                "description": "إنشاء قيد محاسبي لفاتورة بيع آجل",
                "conditions": [
                    RuleCondition(
                        field="invoice.payment_type",
                        operator=RuleOperator.EQUALS,
                        value="credit",
                        condition_type=RuleConditionType.STATUS_EQUALS
                    ),
                    RuleCondition(
                        field="invoice.status",
                        operator=RuleOperator.EQUALS,
                        value="posted",
                        condition_type=RuleConditionType.STATUS_EQUALS
                    )
                ],
                "actions": [
                    RuleAction(
                        action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
                        parameters={"post_automatically": True}
                    )
                ],
                "journal_template": JournalTemplate(
                    id="template_invoice_credit",
                    name="فاتورة بيع آجل",
                    lines=[
                        JournalLineTemplate(
                            account_code="1020",  # المدينون
                            side="debit",
                            amount_source="total"
                        ),
                        JournalLineTemplate(
                            account_code="4010",  # إيرادات المبيعات
                            side="credit",
                            amount_source="subtotal"
                        ),
                        JournalLineTemplate(
                            account_code="2100",  # ضريبة مستحقة
                            side="credit",
                            amount_source="tax"
                        )
                    ]
                )
            },

            "payment_receive_cash": {
                "code": "PAY-RECV",
                "name": "قبض نقدي",
                "description": "إنشاء قيد محاسبي لقبض نقدي",
                "conditions": [
                    RuleCondition(
                        field="payment.payment_type",
                        operator=RuleOperator.EQUALS,
                        value="receive",
                        condition_type=RuleConditionType.STATUS_EQUALS
                    ),
                    RuleCondition(
                        field="payment.payment_method",
                        operator=RuleOperator.EQUALS,
                        value="cash",
                        condition_type=RuleConditionType.STATUS_EQUALS
                    )
                ],
                "actions": [
                    RuleAction(
                        action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
                        parameters={"post_automatically": True}
                    )
                ],
                "journal_template": JournalTemplate(
                    id="template_payment_receive",
                    name="قبض نقدي",
                    lines=[
                        JournalLineTemplate(
                            account_code="1010",  # الصندوق
                            side="debit",
                            amount_source="amount"
                        ),
                        JournalLineTemplate(
                            account_code="1020",  # المدينون
                            side="credit",
                            amount_source="amount"
                        )
                    ]
                )
            },

            "fund_transfer": {
                "code": "FUND-TRF",
                "name": "تحويل بين الصناديق",
                "description": "إنشاء قيد محاسبي لتحويل بين الصناديق",
                "conditions": [
                    RuleCondition(
                        field="transfer.status",
                        operator=RuleOperator.EQUALS,
                        value="completed",
                        condition_type=RuleConditionType.STATUS_EQUALS
                    )
                ],
                "actions": [
                    RuleAction(
                        action_type=RuleActionType.CREATE_JOURNAL_ENTRY,
                        parameters={"post_automatically": True}
                    )
                ],
                "journal_template": JournalTemplate(
                    id="template_fund_transfer",
                    name="تحويل بين الصناديق",
                    lines=[
                        JournalLineTemplate(
                            account_code="1010",  # الصندوق المستلم
                            side="debit",
                            amount_source="amount"
                        ),
                        JournalLineTemplate(
                            account_code="1010",  # الصندوق المرسل
                            side="credit",
                            amount_source="amount"
                        )
                    ]
                )
            }
        }

    # =========================================================================
    # العمليات الأساسية
    # =========================================================================

    def add_condition(self, condition: RuleCondition) -> None:
        """إضافة شرط للقاعدة"""
        self.conditions.append(condition)
        self.updated_at = utc_now()
        self.version += 1

    def remove_condition(self, condition_index: int) -> bool:
        """إزالة شرط من القاعدة"""
        if 0 <= condition_index < len(self.conditions):
            self.conditions.pop(condition_index)
            self.updated_at = utc_now()
            self.version += 1
            return True
        return False

    def add_action(self, action: RuleAction) -> None:
        """إضافة إجراء للقاعدة"""
        self.actions.append(action)
        self.updated_at = utc_now()
        self.version += 1

    def remove_action(self, action_index: int) -> bool:
        """إزالة إجراء من القاعدة"""
        if 0 <= action_index < len(self.actions):
            self.actions.pop(action_index)
            self.updated_at = utc_now()
            self.version += 1
            return True
        return False

    def set_journal_template(self, template: JournalTemplate) -> None:
        """تعيين قالب القيد المحاسبي"""
        self.journal_template = template
        self.updated_at = utc_now()
        self.version += 1

    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        priority: Optional[RulePriority] = None,
        is_active: Optional[bool] = None,
        updated_by: str = "system"
    ) -> None:
        """تحديث بيانات القاعدة"""
        changes = {}

        if name is not None and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name

        if description is not None and description != self.description:
            changes['description'] = {'old': self.description, 'new': description}
            self.description = description

        if priority is not None and priority != self.priority:
            changes['priority'] = {'old': self.priority.value, 'new': priority.value}
            self.priority = priority

        if is_active is not None and is_active != self.is_active:
            changes['is_active'] = {'old': self.is_active, 'new': is_active}
            self.is_active = is_active

        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            self.version += 1

            from .events import RuleUpdatedEvent
            self._events.append(RuleUpdatedEvent(
                rule_id=self.id,
                rule_code=self.code,
                changes=changes,
                updated_by=updated_by
            ))

    def activate(self, activated_by: str) -> None:
        """تفعيل القاعدة"""
        if self.is_active:
            return
        self.update(is_active=True, updated_by=activated_by)

        from .events import RuleActivatedEvent
        self._events.append(RuleActivatedEvent(
            rule_id=self.id,
            rule_code=self.code,
            activated_by=activated_by
        ))

    def deactivate(self, deactivated_by: str) -> None:
        """تعطيل القاعدة"""
        if not self.is_active:
            return
        self.update(is_active=False, updated_by=deactivated_by)

        from .events import RuleDeactivatedEvent
        self._events.append(RuleDeactivatedEvent(
            rule_id=self.id,
            rule_code=self.code,
            deactivated_by=deactivated_by
        ))

    # =========================================================================
    # تقييم القاعدة
    # =========================================================================

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        تقييم القاعدة في سياق معين
        
        Args:
            context: سياق التقييم (يحتوي على جميع البيانات المطلوبة)
        
        Returns:
            bool: True إذا تحققت جميع الشروط
        """
        if not self.is_active:
            return False

        if not self.conditions:
            return True

        results = []
        for condition in self.conditions:
            results.append(condition.evaluate(context))

        if self.condition_logic == "AND":
            return all(results)
        else:  # OR
            return any(results)

    def can_execute(self, context: Dict[str, Any]) -> bool:
        """
        التحقق من إمكانية تنفيذ القاعدة
        
        Args:
            context: سياق التنفيذ
        
        Returns:
            bool: True إذا يمكن تنفيذ القاعدة
        """
        if not self.evaluate(context):
            return False

        # التحقق من التكرار
        if self.prevent_duplicate:
            # سيتم التحقق في الـ Repository
            pass

        return True

    # =========================================================================
    # أحداث المجال
    # =========================================================================

    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة"""
        events = self._events.copy()
        self._events.clear()
        return events

    def add_event(self, event: Any) -> None:
        """إضافة حدث"""
        self._events.append(event)

    # =========================================================================
    # التسلسل
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': str(self.id),
            'code': str(self.code),
            'name': self.name,
            'description': self.description,
            'rule_type': self.rule_type.value,
            'priority': self.priority.value,
            'order': self.order.value,
            'conditions': [c.to_dict() for c in self.conditions],
            'condition_logic': self.condition_logic,
            'actions': [a.to_dict() for a in self.actions],
            'journal_template': self.journal_template.to_dict() if self.journal_template else None,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'is_mandatory': self.is_mandatory,
            'prevent_duplicate': self.prevent_duplicate,
            'duplicate_check_fields': self.duplicate_check_fields,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat(),
            'updated_by': self.updated_by,
            'version': self.version
        }

    def to_summary(self) -> Dict[str, Any]:
        """ملخص سريع للقاعدة"""
        return {
            'id': str(self.id),
            'code': str(self.code),
            'name': self.name,
            'rule_type': self.rule_type.value,
            'priority': self.priority.value,
            'is_active': self.is_active,
            'condition_count': len(self.conditions),
            'action_count': len(self.actions),
            'has_template': self.has_journal_template
        }

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"PostingRule(id={self.id}, code={self.code}, type={self.rule_type}, status={status})"


# =============================================================================
# RuleGroup - مجموعة قواعد
# =============================================================================

@dataclass
class RuleGroup:
    """
    مجموعة قواعد - لتجميع القواعد ذات الصلة
    
    مفيد لتنظيم القواعد حسب نوع المعاملة أو القسم
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    code: str = ""
    name: str = ""
    description: Optional[str] = None

    rules: List[PostingRule] = field(default_factory=list)

    is_active: bool = True
    is_default: bool = False

    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    version: int = 1

    _events: List[Any] = field(default_factory=list, repr=False)

    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"

    @property
    def rule_count(self) -> int:
        return len(self.rules)

    @property
    def active_rules(self) -> List[PostingRule]:
        return [r for r in self.rules if r.is_active]

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        rules: Optional[List[PostingRule]] = None,
        description: Optional[str] = None,
        is_default: bool = False,
        created_by: str = "system"
    ) -> 'RuleGroup':
        """إنشاء مجموعة قواعد جديدة"""
        group = cls(
            code=code,
            name=name,
            description=description,
            rules=rules or [],
            is_default=is_default,
            created_by=created_by,
            updated_by=created_by
        )

        from .events import RuleGroupCreatedEvent
        group._events.append(RuleGroupCreatedEvent(
            group_id=group.id,
            group_code=group.code,
            group_name=group.name,
            rule_count=len(group.rules),
            created_by=created_by
        ))

        return group

    def add_rule(self, rule: PostingRule) -> None:
        """إضافة قاعدة للمجموعة"""
        if rule not in self.rules:
            self.rules.append(rule)
            self.updated_at = utc_now()
            self.version += 1

    def remove_rule(self, rule_id: str) -> bool:
        """إزالة قاعدة من المجموعة"""
        for i, rule in enumerate(self.rules):
            if str(rule.id) == rule_id:
                self.rules.pop(i)
                self.updated_at = utc_now()
                self.version += 1
                return True
        return False

    def get_rules_for_type(self, rule_type: RuleType) -> List[PostingRule]:
        """الحصول على القواعد من نوع معين"""
        return [r for r in self.rules if r.rule_type == rule_type]

    def get_active_rules_for_type(self, rule_type: RuleType) -> List[PostingRule]:
        """الحصول على القواعد النشطة من نوع معين"""
        return [r for r in self.rules if r.is_active and r.rule_type == rule_type]

    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'rule_count': len(self.rules),
            'is_active': self.is_active,
            'is_default': self.is_default,
            'rules': [r.to_summary() for r in self.rules],
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'version': self.version
        }


# =============================================================================
# RuleExecutionLog - سجل تنفيذ القواعد
# =============================================================================

@dataclass
class RuleExecutionLog:
    """
    سجل تنفيذ القاعدة - لتتبع تنفيذ القواعد وتشخيص الأخطاء
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    rule_id: str = ""
    rule_code: str = ""
    rule_name: str = ""

    # سياق التنفيذ
    entity_type: str = ""  # invoice, payment, fund, etc.
    entity_id: str = ""
    context_snapshot: Dict[str, Any] = field(default_factory=dict)

    # نتيجة التنفيذ
    success: bool = False
    message: str = ""
    journal_entry_id: Optional[str] = None
    actions_executed: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # معلومات التنفيذ
    execution_time_ms: float = 0.0
    executed_by: str = "system"
    executed_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'rule_id': self.rule_id,
            'rule_code': self.rule_code,
            'rule_name': self.rule_name,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'success': self.success,
            'message': self.message,
            'journal_entry_id': self.journal_entry_id,
            'actions_executed': self.actions_executed,
            'errors': self.errors,
            'execution_time_ms': self.execution_time_ms,
            'executed_by': self.executed_by,
            'executed_at': self.executed_at.isoformat()
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PostingRule',
    'RuleGroup',
    'RuleExecutionLog',
]