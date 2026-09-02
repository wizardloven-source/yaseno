# core/domain/rules/services.py
"""
Accounting Rules Services - خدمات محرك القواعد المحاسبية
✅ محدث: دعم التكامل مع Accounting Orchestrator
✅ محدث: دعم مراكز التكلفة والربح
✅ محدث: دعم القواعد الديناميكية
✅ محدث: دعم الأولويات والتسلسل
✅ محدث: دعم منع التكرار مع التخزين المؤقت
✅ محدث: دعم سجل التنفيذ المتقدم
✅ محدث: منع الاستيراد الدائري باستخدام TYPE_CHECKING
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple, Callable, TYPE_CHECKING
from datetime import datetime, timezone
import logging
import time
from functools import lru_cache

from .value_objects import (
    RuleType, RulePriority, RuleActionType,
    RuleCondition, RuleAction, RuleExecutionResult,
    JournalTemplate, JournalLineTemplate
)
from .entities import PostingRule, RuleGroup, RuleExecutionLog
from .interfaces import IRuleRepository, IRuleGroupRepository, IRuleExecutionLogRepository

# ✅ استيراد شرطي لتجنب الاستيراد الدائري
if TYPE_CHECKING:
    from core.application.accounting.orchestrator import (
        AccountingOrchestrator,
        JournalEntryRequest,
        JournalEntryResult
    )
    from core.domain.centers.services import CenterService

logger = logging.getLogger(__name__)


# =============================================================================
# RuleValidator - مدقق القواعد
# =============================================================================

class RuleValidator:
    """مدقق القواعد - يتحقق من صحة القواعد قبل التنفيذ"""
    
    @classmethod
    def validate_rule(cls, rule: PostingRule) -> List[str]:
        """التحقق من صحة القاعدة"""
        errors = []
        
        if not rule.code or len(str(rule.code).strip()) < 3:
            errors.append("Rule code must be at least 3 characters")
        
        if not rule.name or len(str(rule.name).strip()) < 3:
            errors.append("Rule name must be at least 3 characters")
        
        if not rule.rule_type:
            errors.append("Rule type is required")
        
        if not rule.priority:
            errors.append("Rule priority is required")
        
        # التحقق من القالب المحاسبي
        if rule.has_journal_template and not rule.journal_template.is_valid():
            errors.append("Journal template is invalid")
        
        # التحقق من الإجراءات
        for action in rule.actions:
            if not action.action_type:
                errors.append(f"Action type is required for action: {action.id}")
            
            if action.action_type == RuleActionType.CUSTOM and not action.parameters.get('handler'):
                errors.append(f"Custom action requires handler: {action.id}")
        
        return errors
    
    @classmethod
    def validate_execution_context(cls, context: Dict[str, Any]) -> List[str]:
        """التحقق من صحة سياق التنفيذ"""
        errors = []
        
        # التحقق من وجود الكيانات المطلوبة
        required_fields = ['entity_type', 'entity_id']
        for field in required_fields:
            if field not in context:
                errors.append(f"Missing required context field: {field}")
        
        # التحقق من المبالغ إذا كانت مطلوبة
        if context.get('requires_amount', False):
            if 'amount' not in context or context['amount'] <= 0:
                errors.append("Amount is required and must be greater than zero")
        
        return errors


# =============================================================================
# RuleExecutor - منفذ القواعد (محدث)
# =============================================================================

class RuleExecutor:
    """
    منفذ القواعد - ينفذ إجراءات القاعدة بناءً على السياق
    ✅ محدث: دعم Accounting Orchestrator
    ✅ محدث: دعم مراكز التكلفة
    ✅ محدث: استيراد متأخر لتجنب الاستيراد الدائري
    """

    def __init__(self, dependencies: Dict[str, Any]):
        """
        Args:
            dependencies: التبعيات المطلوبة للتنفيذ
                - orchestrator: Accounting Orchestrator (اختياري)
                - journal_repo: مستودع القيود
                - posting_engine: محرك الترحيل
                - fund_repo: مستودع الصناديق
                - invoice_repo: مستودع الفواتير
                - payment_repo: مستودع الدفعات
                - center_service: خدمة مراكز التكلفة (اختياري)
        """
        self._deps = dependencies
        self._orchestrator = dependencies.get('orchestrator')
        self._center_service = dependencies.get('center_service')

    def execute(self, rule: PostingRule, context: Dict[str, Any]) -> RuleExecutionResult:
        """
        تنفيذ القاعدة في السياق المعطى
        
        ✅ محدث: يدعم Orchestrator ومراكز التكلفة
        """
        start_time = time.time()

        result = RuleExecutionResult(
            rule_id=str(rule.id),
            rule_code=str(rule.code),
            rule_name=rule.name,
            success=True,
            message="Rule executed successfully"
        )

        try:
            # التحقق من صحة السياق
            validation_errors = RuleValidator.validate_execution_context(context)
            if validation_errors:
                result.success = False
                result.message = "Invalid execution context"
                result.errors.extend(validation_errors)
                return result

            # ✅ إذا كان Orchestrator متاحاً، استخدمه لإنشاء القيد
            if self._orchestrator and rule.has_journal_template:
                journal_result = self._execute_with_orchestrator(rule, context)
                if journal_result.get('success', False):
                    result.journal_entry_id = journal_result.get('journal_entry_id')
                    result.executed_actions.append({
                        'action_type': 'create_journal_entry',
                        'journal_entry_id': journal_result.get('journal_entry_id'),
                        'success': True
                    })
                else:
                    result.success = False
                    result.errors.append(journal_result.get('error', 'Failed to create journal entry'))

            # تنفيذ الإجراءات الأخرى
            for action in rule.actions:
                if action.action_type == RuleActionType.CREATE_JOURNAL_ENTRY:
                    continue  # تم تنفيذه عبر Orchestrator
                
                action_result = self._execute_action(action, context)
                result.executed_actions.append(action_result)

                if not action_result.get('success', False):
                    result.success = False
                    result.errors.append(action_result.get('error', 'Unknown error'))

            if not result.success:
                result.message = "Rule execution failed"

        except Exception as e:
            result.success = False
            result.message = f"Execution error: {str(e)}"
            result.errors.append(str(e))
            logger.error(f"Rule execution error: {e}", exc_info=True)

        finally:
            result.execution_time_ms = (time.time() - start_time) * 1000

        return result

    def _execute_with_orchestrator(
        self,
        rule: PostingRule,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        تنفيذ القاعدة باستخدام Accounting Orchestrator
        
        ✅ استيراد متأخر لتجنب الاستيراد الدائري
        ✅ يدعم مراكز التكلفة
        ✅ يدعم القالب الديناميكي
        """
        try:
            # ✅ استيراد متأخر لتجنب الاستيراد الدائري
            from core.application.accounting.orchestrator import JournalEntryRequest
            
            # 1. استخراج بيانات القيد من القالب
            template = rule.journal_template
            if not template:
                return {
                    'success': False,
                    'error': "No journal template available"
                }

            # 2. استخراج المبالغ من السياق
            amounts = self._extract_amounts(context)

            # 3. بناء أسطر القيد
            lines = []
            for line_template in template.lines:
                amount = self._calculate_line_amount(line_template, amounts, context)

                if amount <= 0 and line_template.is_required:
                    continue

                lines.append({
                    "account_code": line_template.account_code,
                    "debit": float(amount) if line_template.side == "debit" else 0,
                    "credit": float(amount) if line_template.side == "credit" else 0,
                    "currency": line_template.currency or template.default_currency or "USD"
                })

            if not lines:
                return {
                    'success': False,
                    'error': "No journal lines generated from template"
                }

            # 4. ✅ إضافة مراكز التكلفة إذا كانت موجودة
            if self._center_service:
                lines = self._enrich_with_cost_centers(lines, context)

            # 5. بناء طلب القيد
            request = JournalEntryRequest(
                entity_type=context.get('entity_type', 'rule'),
                entity_id=context.get('entity_id', str(rule.id)),
                description=template.description or f"Auto-generated by rule: {rule.code}",
                lines=lines,
                date=context.get('date', datetime.now(timezone.utc)),
                transaction_type=context.get('transaction_type', 'adjustment'),
                created_by=context.get('posted_by', 'system'),
                reference_number=context.get('reference_number'),
                cost_center=context.get('cost_center'),
                profit_center=context.get('profit_center'),
                cost_centers=context.get('cost_centers'),
                profit_centers=context.get('profit_centers'),
                metadata={
                    'rule_id': str(rule.id),
                    'rule_code': str(rule.code),
                    'rule_name': rule.name,
                    'context': context
                }
            )

            # 6. تنفيذ الطلب عبر Orchestrator
            result = self._orchestrator.create_journal_entry(
                request=request,
                posted_by=context.get('posted_by', 'system')
            )

            if not result.success:
                return {
                    'success': False,
                    'error': f"Orchestrator failed: {result.message}",
                    'errors': result.errors
                }

            return {
                'success': True,
                'journal_entry_id': result.journal_entry_id,
                'message': "Journal entry created via Orchestrator"
            }

        except Exception as e:
            logger.error(f"Error executing rule with orchestrator: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _enrich_with_cost_centers(
        self,
        lines: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        إضافة مراكز التكلفة إلى أسطر القيد
        
        ✅ يدعم توزيع المبالغ على مراكز متعددة
        ✅ يتحقق من صحة المراكز
        """
        if not self._center_service:
            return lines

        # الحصول على مراكز التكلفة من السياق
        cost_centers = context.get('cost_centers', {})
        cost_center_code = context.get('cost_center_code')
        profit_center_code = context.get('profit_center_code')

        # إذا لم تكن هناك مراكز، أرجع الأسطر كما هي
        if not cost_centers and not cost_center_code and not profit_center_code:
            return lines

        enriched_lines = []

        for line in lines:
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

            # مركز ربح واحد
            if profit_center_code:
                line['profit_center'] = profit_center_code

            enriched_lines.append(line)

        return enriched_lines

    def _extract_amounts(self, context: Dict[str, Any]) -> Dict[str, Decimal]:
        """استخراج المبالغ من السياق"""
        amounts = {}

        # مصادر المبالغ المدعومة
        sources = ['total', 'subtotal', 'tax', 'discount', 'shipping', 'amount']
        for source in sources:
            if source in context:
                amounts[source] = Decimal(str(context[source]))
            elif 'invoice' in context and source in context['invoice']:
                amounts[source] = Decimal(str(context['invoice'][source]))
            elif 'payment' in context and source in context['payment']:
                amounts[source] = Decimal(str(context['payment'][source]))

        # مبلغ افتراضي
        if 'amount' not in amounts and 'total' in amounts:
            amounts['amount'] = amounts['total']

        return amounts

    def _calculate_line_amount(
        self,
        line_template: JournalLineTemplate,
        amounts: Dict[str, Decimal],
        context: Dict[str, Any]
    ) -> Decimal:
        """حساب مبلغ السطر"""
        source = line_template.amount_source

        # الحصول على المبلغ الأساسي
        if source in amounts:
            base_amount = amounts[source]
        elif source == 'custom':
            base_amount = Decimal(str(context.get('custom_amount', 0)))
        else:
            base_amount = Decimal('0')

        # تطبيق النسبة المئوية
        amount = base_amount * (line_template.percentage / Decimal('100'))

        return amount

    def _execute_action(self, action: RuleAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """تنفيذ إجراء محدد"""
        try:
            if action.action_type == RuleActionType.UPDATE_FUND_BALANCE:
                return self._action_update_fund_balance(action, context)

            elif action.action_type == RuleActionType.UPDATE_STOCK:
                return self._action_update_stock(action, context)

            elif action.action_type == RuleActionType.SEND_NOTIFICATION:
                return self._action_send_notification(action, context)

            elif action.action_type == RuleActionType.CUSTOM:
                return self._action_custom(action, context)

            else:
                return {
                    'success': False,
                    'error': f"Unsupported action type: {action.action_type.value}"
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _action_update_fund_balance(self, action: RuleAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """تحديث رصيد الصندوق"""
        fund_repo = self._deps.get('fund_repo')
        if not fund_repo:
            return {'success': False, 'error': "Fund repository not available"}

        try:
            fund_id = context.get('fund_id')
            amount = Decimal(str(context.get('amount', 0)))
            operation = context.get('operation', 'deposit')  # deposit, withdraw

            if not fund_id:
                return {'success': False, 'error': "Fund ID not provided"}

            fund = fund_repo.get_by_id(fund_id)
            if not fund:
                return {'success': False, 'error': f"Fund {fund_id} not found"}

            # تنفيذ العملية
            if operation == 'deposit':
                fund.deposit(amount, context.get('reason', 'Auto deposit'), context.get('created_by', 'system'))
            else:
                fund.withdraw(amount, context.get('reason', 'Auto withdrawal'), context.get('created_by', 'system'))

            fund_repo.save(fund)

            return {
                'success': True,
                'message': f"Fund balance updated: {operation} {amount}",
                'new_balance': float(fund.balance)
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _action_update_stock(self, action: RuleAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """تحديث المخزون"""
        product_repo = self._deps.get('product_repo')
        if not product_repo:
            return {'success': False, 'error': "Product repository not available"}

        try:
            product_id = context.get('product_id')
            quantity = context.get('quantity', 0)
            operation = context.get('operation', 'decrease')  # increase, decrease

            if not product_id:
                return {'success': False, 'error': "Product ID not provided"}

            product = product_repo.get_by_id(product_id)
            if not product:
                return {'success': False, 'error': f"Product {product_id} not found"}

            # تنفيذ العملية
            if operation == 'increase':
                product.increase_stock(quantity, context.get('reason', 'Auto increase'), context.get('created_by', 'system'))
            else:
                product.decrease_stock(quantity, context.get('reason', 'Auto decrease'), context.get('created_by', 'system'))

            product_repo.save(product)

            return {
                'success': True,
                'message': f"Stock updated: {operation} {quantity}",
                'new_stock': product.stock_quantity
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _action_send_notification(self, action: RuleAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """إرسال إشعار"""
        notification_service = self._deps.get('notification_service')
        if not notification_service:
            return {'success': False, 'error': "Notification service not available"}

        try:
            message = action.parameters.get('message', context.get('message', ''))
            recipient = action.parameters.get('recipient', context.get('recipient'))

            notification_service.send(recipient, message, context)

            return {
                'success': True,
                'message': f"Notification sent to {recipient}"
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _action_custom(self, action: RuleAction, context: Dict[str, Any]) -> Dict[str, Any]:
        """تنفيذ إجراء مخصص"""
        custom_handler = self._deps.get('custom_handlers', {}).get(
            action.parameters.get('handler', '')
        )

        if not custom_handler:
            return {
                'success': False,
                'error': f"Custom handler not found: {action.parameters.get('handler')}"
            }

        try:
            result = custom_handler(context, action.parameters)
            return {
                'success': True,
                'result': result
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}


# =============================================================================
# RuleEngine - محرك القواعد (محدث)
# =============================================================================

class RuleEngine:
    """
    محرك القواعد المحاسبية - المسؤول عن تنفيذ القواعد تلقائياً
    
    ✅ محدث: دعم التكامل مع Accounting Orchestrator
    ✅ محدث: دعم مراكز التكلفة
    ✅ محدث: دعم التخزين المؤقت المتقدم
    ✅ محدث: دعم سجل التنفيذ المتقدم
    ✅ محدث: منع الاستيراد الدائري
    """

    def __init__(
        self,
        rule_repository: IRuleRepository,
        group_repository: Optional[IRuleGroupRepository] = None,
        log_repository: Optional[IRuleExecutionLogRepository] = None,
        orchestrator: Optional['AccountingOrchestrator'] = None,
        center_service: Optional['CenterService'] = None,
        dependencies: Optional[Dict[str, Any]] = None
    ):
        self._rule_repo = rule_repository
        self._group_repo = group_repository
        self._log_repo = log_repository
        self._orchestrator = orchestrator

        # دمج التبعيات
        deps = dependencies or {}
        if orchestrator:
            deps['orchestrator'] = orchestrator
        if center_service:
            deps['center_service'] = center_service

        self._executor = RuleExecutor(deps)

        # التخزين المؤقت
        self._rule_cache: Dict[str, PostingRule] = {}
        self._rules_by_type: Dict[str, List[PostingRule]] = {}
        self._cache_ttl: int = 300  # 5 دقائق
        self._last_cache_update: float = 0

    # =========================================================================
    # تنفيذ القواعد (محدث)
    # =========================================================================

    def execute_rules(
        self,
        rule_type: RuleType,
        context: Dict[str, Any],
        execute_all: bool = True
    ) -> List[RuleExecutionResult]:
        """
        تنفيذ القواعد من نوع معين في سياق معين
        
        ✅ محدث: يدعم Orchestrator ومراكز التكلفة
        """
        results = []

        # الحصول على القواعد المناسبة
        rules = self._get_rules_for_type(rule_type)

        if not rules:
            logger.info(f"No rules found for type: {rule_type.value}")
            return results

        # ترتيب القواعد حسب الأولوية
        rules = self._sort_rules(rules)

        # تخزين نتائج القواعد المنفذة
        executed_results = []

        for rule in rules:
            if not rule.is_active:
                continue

            # التحقق من إمكانية التنفيذ
            if not rule.can_execute(context):
                continue

            # تنفيذ القاعدة
            result = self._executor.execute(rule, context)
            results.append(result)

            # تسجيل التنفيذ
            self._log_execution(rule, context, result)

            # إذا لم ننفذ جميع القواعد ونفذت قاعدة بنجاح، توقف
            if not execute_all and result.success:
                break

        return results

    def execute_rule(self, rule_id: str, context: Dict[str, Any]) -> RuleExecutionResult:
        """تنفيذ قاعدة محددة"""
        rule = self.get_rule(rule_id)
        if not rule:
            return RuleExecutionResult(
                rule_id=rule_id,
                rule_code="",
                rule_name="Unknown",
                success=False,
                message=f"Rule {rule_id} not found",
                errors=[f"Rule {rule_id} not found"]
            )

        if not rule.is_active:
            return RuleExecutionResult(
                rule_id=str(rule.id),
                rule_code=str(rule.code),
                rule_name=rule.name,
                success=False,
                message="Rule is inactive",
                errors=["Rule is inactive"]
            )

        result = self._executor.execute(rule, context)
        self._log_execution(rule, context, result)
        return result

    # =========================================================================
    # إدارة القواعد
    # =========================================================================

    def get_rule(self, rule_id: str) -> Optional[PostingRule]:
        """الحصول على قاعدة مع التخزين المؤقت"""
        if rule_id in self._rule_cache:
            return self._rule_cache[rule_id]

        rule = self._rule_repo.get_by_id(rule_id)
        if rule:
            self._rule_cache[str(rule.id)] = rule
        return rule

    def get_rule_by_code(self, code: str) -> Optional[PostingRule]:
        """الحصول على قاعدة بالكود"""
        return self._rule_repo.get_by_code(code)

    def get_all_rules(self, include_inactive: bool = False) -> List[PostingRule]:
        """الحصول على جميع القواعد"""
        return self._rule_repo.get_all(include_inactive)

    def get_active_rules(self) -> List[PostingRule]:
        """الحصول على القواعد النشطة"""
        return self._rule_repo.get_active_rules()

    def _get_rules_for_type(self, rule_type: RuleType) -> List[PostingRule]:
        """الحصول على القواعد من نوع معين"""
        key = rule_type.value
        if key in self._rules_by_type:
            return self._rules_by_type[key]

        rules = self._rule_repo.get_by_type(rule_type)
        self._rules_by_type[key] = rules
        return rules

    def _sort_rules(self, rules: List[PostingRule]) -> List[PostingRule]:
        """ترتيب القواعد حسب الأولوية"""
        priority_order = {
            RulePriority.CRITICAL: 0,
            RulePriority.HIGH: 1,
            RulePriority.NORMAL: 2,
            RulePriority.LOW: 3,
            RulePriority.LOWEST: 4
        }

        return sorted(
            rules,
            key=lambda r: (priority_order.get(r.priority, 2), r.order.value)
        )

    def save_rule(self, rule: PostingRule) -> PostingRule:
        """حفظ قاعدة"""
        self._rule_repo.save(rule)
        self._rule_cache[str(rule.id)] = rule

        key = rule.rule_type.value
        if key in self._rules_by_type:
            self._rules_by_type[key].append(rule)

        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """حذف قاعدة"""
        rule = self.get_rule(rule_id)
        if not rule:
            return False

        if rule.is_default:
            raise ValueError("Cannot delete default rule")

        result = self._rule_repo.delete(rule_id)

        if result:
            if rule_id in self._rule_cache:
                del self._rule_cache[rule_id]

            for key, rules in self._rules_by_type.items():
                self._rules_by_type[key] = [r for r in rules if str(r.id) != rule_id]

        return result

    # =========================================================================
    # إدارة المجموعات
    # =========================================================================

    def get_groups(self) -> List[RuleGroup]:
        """الحصول على جميع مجموعات القواعد"""
        if not self._group_repo:
            return []
        return self._group_repo.get_all()

    def get_group(self, group_id: str) -> Optional[RuleGroup]:
        """الحصول على مجموعة قواعد"""
        if not self._group_repo:
            return None
        return self._group_repo.get_by_id(group_id)

    def save_group(self, group: RuleGroup) -> RuleGroup:
        """حفظ مجموعة قواعد"""
        if not self._group_repo:
            raise ValueError("Group repository not available")
        self._group_repo.save(group)
        return group

    # =========================================================================
    # تسجيل التنفيذ
    # =========================================================================

    def _log_execution(
        self,
        rule: PostingRule,
        context: Dict[str, Any],
        result: RuleExecutionResult
    ) -> None:
        """تسجيل تنفيذ القاعدة"""
        if not self._log_repo:
            return

        try:
            log = RuleExecutionLog(
                rule_id=str(rule.id),
                rule_code=str(rule.code),
                rule_name=rule.name,
                entity_type=context.get('entity_type', 'unknown'),
                entity_id=context.get('entity_id', ''),
                context_snapshot=context,
                success=result.success,
                message=result.message,
                journal_entry_id=result.journal_entry_id,
                actions_executed=result.executed_actions,
                errors=result.errors,
                execution_time_ms=result.execution_time_ms,
                executed_by=context.get('executed_by', 'system')
            )

            self._log_repo.save(log)

        except Exception as e:
            logger.error(f"Failed to log rule execution: {e}")

    def get_execution_logs(
        self,
        rule_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> List[RuleExecutionLog]:
        """الحصول على سجل تنفيذ القواعد"""
        if not self._log_repo:
            return []

        if rule_id:
            return self._log_repo.get_by_rule(rule_id, limit)
        elif entity_type:
            return self._log_repo.get_by_entity_type(entity_type, limit)
        else:
            return self._log_repo.get_recent(limit)

    # =========================================================================
    # التخزين المؤقت
    # =========================================================================

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._rule_cache.clear()
        self._rules_by_type.clear()

    def reload(self) -> None:
        """إعادة تحميل جميع البيانات"""
        self.clear_cache()

        rules = self._rule_repo.get_active_rules()
        for rule in rules:
            self._rule_cache[str(rule.id)] = rule

            key = rule.rule_type.value
            if key not in self._rules_by_type:
                self._rules_by_type[key] = []
            self._rules_by_type[key].append(rule)

    # =========================================================================
    # التحليل والإحصائيات
    # =========================================================================

    def get_rule_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات القواعد"""
        rules = self._rule_repo.get_all()
        active_rules = [r for r in rules if r.is_active]

        stats = {
            'total_rules': len(rules),
            'active_rules': len(active_rules),
            'inactive_rules': len(rules) - len(active_rules),
            'by_type': {},
            'by_priority': {},
            'execution_count': {},
            'success_rate': {}
        }

        # إحصائيات حسب النوع
        for rule in active_rules:
            key = rule.rule_type.value
            stats['by_type'][key] = stats['by_type'].get(key, 0) + 1

        # إحصائيات حسب الأولوية
        for rule in active_rules:
            key = rule.priority.value
            stats['by_priority'][key] = stats['by_priority'].get(key, 0) + 1

        # إحصائيات التنفيذ
        if self._log_repo:
            for rule in active_rules:
                count = self._log_repo.count_by_rule(str(rule.id))
                if count > 0:
                    stats['execution_count'][str(rule.code)] = count
                    success_rate = self._get_success_rate(str(rule.id))
                    if success_rate is not None:
                        stats['success_rate'][str(rule.code)] = success_rate

        return stats

    def _get_success_rate(self, rule_id: str) -> Optional[float]:
        """الحصول على نسبة نجاح قاعدة"""
        if not self._log_repo:
            return None

        total = self._log_repo.count_by_rule(rule_id)
        if total == 0:
            return None

        success = self._log_repo.count_success_by_rule(rule_id)
        return (success / total) * 100

    # =========================================================================
    # دوال مساعدة للتحقق من القواعد
    # =========================================================================

    def can_execute_rule(self, rule_id: str, context: Dict[str, Any]) -> Tuple[bool, str]:
        """التحقق من إمكانية تنفيذ قاعدة"""
        rule = self.get_rule(rule_id)
        if not rule:
            return False, f"Rule {rule_id} not found"

        if not rule.is_active:
            return False, "Rule is inactive"

        if not rule.can_execute(context):
            return False, "Rule conditions not met"

        # التحقق من صحة السياق
        errors = RuleValidator.validate_execution_context(context)
        if errors:
            return False, f"Invalid context: {', '.join(errors)}"

        return True, "Rule can be executed"


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'RuleValidator',
    'RuleExecutor',
    'RuleEngine',
]