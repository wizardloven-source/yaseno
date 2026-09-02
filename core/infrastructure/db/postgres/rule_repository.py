# core/infrastructure/db/postgres/rule_repository.py
"""
PostgreSQL Repository for Accounting Rules - مستودع القواعد المحاسبية
✅ يدعم: PostingRule, RuleGroup, RuleExecutionLog
✅ يدعم: Optimistic Locking عبر الـ version
✅ يدعم: البحث المتقدم حسب النوع والأولوية والحالة
✅ يدعم: Pagination للقوائم الكبيرة
✅ يدعم: التخزين المؤقت (Caching)
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, func, and_, or_, desc, asc
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from core.domain.rules.entities import PostingRule, RuleGroup, RuleExecutionLog
from core.domain.rules.value_objects import (
    RuleId, RuleCode, RuleType, RulePriority,
    RuleCondition, RuleAction, JournalTemplate, JournalLineTemplate,
    RuleExecutionResult
)
from core.domain.rules.interfaces import (
    IRuleRepository, IRuleGroupRepository, IRuleExecutionLogRepository
)
from core.shared.exceptions import ConcurrentModificationError

from ..models.rule_model import PostingRuleModel, RuleGroupModel, RuleExecutionLogModel


logger = logging.getLogger(__name__)


# =============================================================================
# دوال التحويل بين Domain و ORM - PostingRule
# =============================================================================

def _domain_to_model_rule(rule: PostingRule) -> PostingRuleModel:
    """تحويل Domain Entity إلى ORM Model - PostingRule"""
    return PostingRuleModel(
        id=UUID(str(rule.id)),
        code=str(rule.code),
        name=rule.name,
        description=rule.description,
        rule_type=rule.rule_type.value,
        priority=rule.priority.value,
        order=rule.order.value,
        conditions=[c.to_dict() for c in rule.conditions],
        condition_logic=rule.condition_logic,
        actions=[a.to_dict() for a in rule.actions],
        journal_template=rule.journal_template.to_dict() if rule.journal_template else None,
        is_active=rule.is_active,
        is_default=rule.is_default,
        is_mandatory=rule.is_mandatory,
        prevent_duplicate=rule.prevent_duplicate,
        duplicate_check_fields=rule.duplicate_check_fields,
        created_at=rule.created_at,
        created_by=rule.created_by,
        updated_at=rule.updated_at,
        updated_by=rule.updated_by,
        version=rule.version
    )


def _model_to_domain_rule(model: PostingRuleModel) -> PostingRule:
    """تحويل ORM Model إلى Domain Entity - PostingRule"""
    if not model:
        return None

    # تحويل الشروط
    conditions = []
    for cond_data in model.conditions or []:
        conditions.append(RuleCondition.from_dict(cond_data))

    # تحويل الإجراءات
    actions = []
    for action_data in model.actions or []:
        actions.append(RuleAction.from_dict(action_data))

    # تحويل قالب القيد المحاسبي
    journal_template = None
    if model.journal_template:
        template_data = model.journal_template
        lines = []
        for line_data in template_data.get('lines', []):
            lines.append(JournalLineTemplate(
                account_code=line_data.get('account_code', ''),
                side=line_data.get('side', 'debit'),
                amount_source=line_data.get('amount_source', 'total'),
                percentage=Decimal(str(line_data.get('percentage', 100))),
                currency=line_data.get('currency'),
                description=line_data.get('description'),
                is_required=line_data.get('is_required', True)
            ))
        journal_template = JournalTemplate(
            id=template_data.get('id', ''),
            name=template_data.get('name', ''),
            description=template_data.get('description'),
            lines=lines,
            require_balance=template_data.get('require_balance', True),
            post_automatically=template_data.get('post_automatically', False),
            default_currency=template_data.get('default_currency', 'USD')
        )

    rule = PostingRule(
        id=RuleId(str(model.id)),
        code=RuleCode(model.code),
        name=model.name,
        description=model.description,
        rule_type=RuleType(model.rule_type),
        priority=RulePriority(model.priority),
        order=model.order,
        conditions=conditions,
        condition_logic=model.condition_logic,
        actions=actions,
        journal_template=journal_template,
        is_active=model.is_active,
        is_default=model.is_default,
        is_mandatory=model.is_mandatory,
        prevent_duplicate=model.prevent_duplicate,
        duplicate_check_fields=model.duplicate_check_fields or [],
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )

    return rule


# =============================================================================
# دوال التحويل - RuleGroup
# =============================================================================

def _domain_to_model_group(group: RuleGroup) -> RuleGroupModel:
    """تحويل Domain Entity إلى ORM Model - RuleGroup"""
    return RuleGroupModel(
        id=UUID(group.id),
        code=group.code,
        name=group.name,
        description=group.description,
        is_active=group.is_active,
        is_default=group.is_default,
        created_at=group.created_at,
        created_by=group.created_by,
        updated_at=group.updated_at,
        updated_by=group.updated_by,
        version=group.version
    )


def _model_to_domain_group(model: RuleGroupModel, include_rules: bool = True) -> RuleGroup:
    """تحويل ORM Model إلى Domain Entity - RuleGroup"""
    if not model:
        return None

    rules = []
    if include_rules and model.rules:
        rules = [_model_to_domain_rule(r) for r in model.rules]

    return RuleGroup(
        id=str(model.id),
        code=model.code,
        name=model.name,
        description=model.description,
        rules=rules,
        is_active=model.is_active,
        is_default=model.is_default,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )


# =============================================================================
# دوال التحويل - RuleExecutionLog
# =============================================================================

def _domain_to_model_log(log: RuleExecutionLog) -> RuleExecutionLogModel:
    """تحويل Domain Entity إلى ORM Model - RuleExecutionLog"""
    return RuleExecutionLogModel(
        rule_id=log.rule_id,
        rule_code=log.rule_code,
        rule_name=log.rule_name,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
        context_snapshot=log.context_snapshot,
        success=log.success,
        message=log.message,
        journal_entry_id=log.journal_entry_id,
        actions_executed=log.actions_executed,
        errors=log.errors,
        execution_time_ms=log.execution_time_ms,
        executed_by=log.executed_by,
        executed_at=log.executed_at
    )


def _model_to_domain_log(model: RuleExecutionLogModel) -> RuleExecutionLog:
    """تحويل ORM Model إلى Domain Entity - RuleExecutionLog"""
    if not model:
        return None

    return RuleExecutionLog(
        id=str(model.id),
        rule_id=model.rule_id,
        rule_code=model.rule_code,
        rule_name=model.rule_name,
        entity_type=model.entity_type,
        entity_id=model.entity_id,
        context_snapshot=model.context_snapshot or {},
        success=model.success,
        message=model.message,
        journal_entry_id=model.journal_entry_id,
        actions_executed=model.actions_executed or [],
        errors=model.errors or [],
        execution_time_ms=float(model.execution_time_ms) if model.execution_time_ms else 0.0,
        executed_by=model.executed_by,
        executed_at=model.executed_at
    )


# =============================================================================
# PostgresRuleRepository - مستودع القواعد
# =============================================================================

class PostgresRuleRepository(IRuleRepository):
    """
    PostgreSQL implementation of IRuleRepository
    """

    def __init__(self, session: Session):
        self._session = session
        self._cache: Dict[str, PostingRule] = {}

    # ========== العمليات الأساسية ==========

    def save(self, rule: PostingRule) -> None:
        """حفظ القاعدة مع Optimistic Locking"""
        existing = self._session.execute(
            select(PostingRuleModel).where(PostingRuleModel.id == UUID(str(rule.id)))
        ).scalar_one_or_none()

        if existing:
            # تحديث مع التحقق من الإصدار
            now = utc_now()
            new_version = existing.version + 1

            result = self._session.execute(
                update(PostingRuleModel)
                .where(
                    PostingRuleModel.id == UUID(str(rule.id)),
                    PostingRuleModel.version == rule.version
                )
                .values(
                    code=str(rule.code),
                    name=rule.name,
                    description=rule.description,
                    rule_type=rule.rule_type.value,
                    priority=rule.priority.value,
                    order=rule.order.value,
                    conditions=[c.to_dict() for c in rule.conditions],
                    condition_logic=rule.condition_logic,
                    actions=[a.to_dict() for a in rule.actions],
                    journal_template=rule.journal_template.to_dict() if rule.journal_template else None,
                    is_active=rule.is_active,
                    is_default=rule.is_default,
                    is_mandatory=rule.is_mandatory,
                    prevent_duplicate=rule.prevent_duplicate,
                    duplicate_check_fields=rule.duplicate_check_fields,
                    updated_at=now,
                    updated_by=rule.updated_by,
                    version=new_version
                )
            )

            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "PostingRule",
                    str(rule.id),
                    rule.version,
                    existing.version
                )

            rule.version = new_version
            rule.updated_at = now

        else:
            # إنشاء قاعدة جديدة
            model = _domain_to_model_rule(rule)
            self._session.add(model)
            self._session.flush()
            rule.version = 1

        # تحديث الكاش
        self._cache[str(rule.id)] = rule

    def get_by_id(self, rule_id: str) -> Optional[PostingRule]:
        """الحصول على قاعدة بواسطة المعرف"""
        # التحقق من الكاش
        if rule_id in self._cache:
            return self._cache[rule_id]

        model = self._session.execute(
            select(PostingRuleModel).where(PostingRuleModel.id == UUID(rule_id))
        ).scalar_one_or_none()

        if not model:
            return None

        rule = _model_to_domain_rule(model)
        self._cache[rule_id] = rule
        return rule

    def get_by_code(self, code: str) -> Optional[PostingRule]:
        """الحصول على قاعدة بواسطة الكود"""
        # البحث في الكاش أولاً
        for rule in self._cache.values():
            if str(rule.code) == code:
                return rule

        model = self._session.execute(
            select(PostingRuleModel).where(PostingRuleModel.code == code)
        ).scalar_one_or_none()

        if not model:
            return None

        rule = _model_to_domain_rule(model)
        self._cache[str(rule.id)] = rule
        return rule

    def get_all(self, include_inactive: bool = False) -> List[PostingRule]:
        """الحصول على جميع القواعد"""
        query = select(PostingRuleModel)

        if not include_inactive:
            query = query.where(PostingRuleModel.is_active == True)

        query = query.order_by(PostingRuleModel.priority, PostingRuleModel.order)

        models = self._session.execute(query).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def get_active_rules(self) -> List[PostingRule]:
        """الحصول على القواعد النشطة فقط"""
        return self.get_all(include_inactive=False)

    def get_by_type(self, rule_type: RuleType) -> List[PostingRule]:
        """الحصول على القواعد حسب النوع"""
        # البحث في الكاش أولاً
        cached_rules = [r for r in self._cache.values() if r.rule_type == rule_type]
        if cached_rules:
            return cached_rules

        models = self._session.execute(
            select(PostingRuleModel)
            .where(
                and_(
                    PostingRuleModel.rule_type == rule_type.value,
                    PostingRuleModel.is_active == True
                )
            )
            .order_by(PostingRuleModel.priority, PostingRuleModel.order)
        ).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def get_by_priority(self, priority: RulePriority) -> List[PostingRule]:
        """الحصول على القواعد حسب الأولوية"""
        models = self._session.execute(
            select(PostingRuleModel)
            .where(
                and_(
                    PostingRuleModel.priority == priority.value,
                    PostingRuleModel.is_active == True
                )
            )
            .order_by(PostingRuleModel.order)
        ).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def get_default_rule(self) -> Optional[PostingRule]:
        """الحصول على القاعدة الافتراضية"""
        model = self._session.execute(
            select(PostingRuleModel)
            .where(
                and_(
                    PostingRuleModel.is_default == True,
                    PostingRuleModel.is_active == True
                )
            )
        ).scalar_one_or_none()

        if not model:
            return None

        rule = _model_to_domain_rule(model)
        self._cache[str(rule.id)] = rule
        return rule

    def get_rules_by_group(self, group_id: str) -> List[PostingRule]:
        """الحصول على القواعد في مجموعة معينة"""
        models = self._session.execute(
            select(PostingRuleModel)
            .where(
                and_(
                    PostingRuleModel.group_id == UUID(group_id),
                    PostingRuleModel.is_active == True
                )
            )
            .order_by(PostingRuleModel.priority, PostingRuleModel.order)
        ).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def search_rules(self, search_text: str, limit: int = 50) -> List[PostingRule]:
        """البحث عن القواعد"""
        search_pattern = f"%{search_text}%"

        models = self._session.execute(
            select(PostingRuleModel)
            .where(
                and_(
                    PostingRuleModel.is_active == True,
                    or_(
                        PostingRuleModel.code.ilike(search_pattern),
                        PostingRuleModel.name.ilike(search_pattern),
                        PostingRuleModel.description.ilike(search_pattern)
                    )
                )
            )
            .limit(limit)
        ).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def delete(self, rule_id: str) -> bool:
        """حذف قاعدة"""
        model = self._session.execute(
            select(PostingRuleModel).where(PostingRuleModel.id == UUID(rule_id))
        ).scalar_one_or_none()

        if not model:
            return False

        self._session.delete(model)

        # تنظيف الكاش
        if rule_id in self._cache:
            del self._cache[rule_id]

        return True

    def count_active(self) -> int:
        """حساب عدد القواعد النشطة"""
        result = self._session.execute(
            select(func.count()).select_from(PostingRuleModel)
            .where(PostingRuleModel.is_active == True)
        ).scalar()

        return result or 0

    def count_by_type(self, rule_type: RuleType) -> int:
        """حساب عدد القواعد من نوع معين"""
        result = self._session.execute(
            select(func.count()).select_from(PostingRuleModel)
            .where(
                and_(
                    PostingRuleModel.rule_type == rule_type.value,
                    PostingRuleModel.is_active == True
                )
            )
        ).scalar()

        return result or 0

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._cache.clear()

    def get_cached_rule(self, rule_id: str) -> Optional[PostingRule]:
        """الحصول على قاعدة من الكاش"""
        return self._cache.get(rule_id)


# =============================================================================
# PostgresRuleGroupRepository - مستودع مجموعات القواعد
# =============================================================================

class PostgresRuleGroupRepository(IRuleGroupRepository):
    """
    PostgreSQL implementation of IRuleGroupRepository
    """

    def __init__(self, session: Session):
        self._session = session
        self._cache: Dict[str, RuleGroup] = {}

    def save(self, group: RuleGroup) -> None:
        """حفظ مجموعة قواعد"""
        existing = self._session.execute(
            select(RuleGroupModel).where(RuleGroupModel.id == UUID(group.id))
        ).scalar_one_or_none()

        if existing:
            # تحديث
            now = utc_now()
            new_version = existing.version + 1

            self._session.execute(
                update(RuleGroupModel)
                .where(
                    RuleGroupModel.id == UUID(group.id),
                    RuleGroupModel.version == group.version
                )
                .values(
                    code=group.code,
                    name=group.name,
                    description=group.description,
                    is_active=group.is_active,
                    is_default=group.is_default,
                    updated_at=now,
                    updated_by=group.updated_by,
                    version=new_version
                )
            )

            group.version = new_version

        else:
            # إنشاء جديد
            model = _domain_to_model_group(group)
            self._session.add(model)
            self._session.flush()
            group.version = 1

        self._cache[group.id] = group

    def get_by_id(self, group_id: str) -> Optional[RuleGroup]:
        """الحصول على مجموعة بواسطة المعرف"""
        if group_id in self._cache:
            return self._cache[group_id]

        model = self._session.execute(
            select(RuleGroupModel)
            .options(selectinload(RuleGroupModel.rules))
            .where(RuleGroupModel.id == UUID(group_id))
        ).unique().scalar_one_or_none()

        if not model:
            return None

        group = _model_to_domain_group(model)
        self._cache[group_id] = group
        return group

    def get_by_code(self, code: str) -> Optional[RuleGroup]:
        """الحصول على مجموعة بواسطة الكود"""
        model = self._session.execute(
            select(RuleGroupModel)
            .options(selectinload(RuleGroupModel.rules))
            .where(RuleGroupModel.code == code)
        ).unique().scalar_one_or_none()

        if not model:
            return None

        group = _model_to_domain_group(model)
        self._cache[group.id] = group
        return group

    def get_all(self, include_inactive: bool = False) -> List[RuleGroup]:
        """الحصول على جميع المجموعات"""
        query = select(RuleGroupModel).options(selectinload(RuleGroupModel.rules))

        if not include_inactive:
            query = query.where(RuleGroupModel.is_active == True)

        query = query.order_by(RuleGroupModel.code)

        models = self._session.execute(query).unique().scalars().all()

        groups = []
        for model in models:
            group = _model_to_domain_group(model)
            self._cache[group.id] = group
            groups.append(group)

        return groups

    def get_default_group(self) -> Optional[RuleGroup]:
        """الحصول على المجموعة الافتراضية"""
        model = self._session.execute(
            select(RuleGroupModel)
            .options(selectinload(RuleGroupModel.rules))
            .where(
                and_(
                    RuleGroupModel.is_default == True,
                    RuleGroupModel.is_active == True
                )
            )
        ).unique().scalar_one_or_none()

        if not model:
            return None

        group = _model_to_domain_group(model)
        self._cache[group.id] = group
        return group

    def delete(self, group_id: str) -> bool:
        """حذف مجموعة قواعد"""
        model = self._session.execute(
            select(RuleGroupModel).where(RuleGroupModel.id == UUID(group_id))
        ).scalar_one_or_none()

        if not model:
            return False

        self._session.delete(model)

        if group_id in self._cache:
            del self._cache[group_id]

        return True

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._cache.clear()


# =============================================================================
# PostgresRuleExecutionLogRepository - مستودع سجل التنفيذ
# =============================================================================

class PostgresRuleExecutionLogRepository(IRuleExecutionLogRepository):
    """
    PostgreSQL implementation of IRuleExecutionLogRepository
    """

    def __init__(self, session: Session):
        self._session = session

    def save(self, log: RuleExecutionLog) -> None:
        """حفظ سجل تنفيذ"""
        model = _domain_to_model_log(log)
        self._session.add(model)
        self._session.flush()

        # تحديث المعرف إذا كان جديداً
        if not log.id or log.id == "":
            log.id = str(model.id)

    def get_by_id(self, log_id: str) -> Optional[RuleExecutionLog]:
        """الحصول على سجل بواسطة المعرف"""
        model = self._session.execute(
            select(RuleExecutionLogModel).where(RuleExecutionLogModel.id == int(log_id))
        ).scalar_one_or_none()

        if not model:
            return None

        return _model_to_domain_log(model)

    def get_by_rule(self, rule_id: str, limit: int = 100) -> List[RuleExecutionLog]:
        """الحصول على سجلات قاعدة معينة"""
        models = self._session.execute(
            select(RuleExecutionLogModel)
            .where(RuleExecutionLogModel.rule_id == rule_id)
            .order_by(desc(RuleExecutionLogModel.executed_at))
            .limit(limit)
        ).scalars().all()

        return [_model_to_domain_log(m) for m in models]

    def get_by_entity_type(self, entity_type: str, limit: int = 100) -> List[RuleExecutionLog]:
        """الحصول على سجلات نوع كيان معين"""
        models = self._session.execute(
            select(RuleExecutionLogModel)
            .where(RuleExecutionLogModel.entity_type == entity_type)
            .order_by(desc(RuleExecutionLogModel.executed_at))
            .limit(limit)
        ).scalars().all()

        return [_model_to_domain_log(m) for m in models]

    def get_by_entity(self, entity_type: str, entity_id: str, limit: int = 100) -> List[RuleExecutionLog]:
        """الحصول على سجلات كيان معين"""
        models = self._session.execute(
            select(RuleExecutionLogModel)
            .where(
                and_(
                    RuleExecutionLogModel.entity_type == entity_type,
                    RuleExecutionLogModel.entity_id == entity_id
                )
            )
            .order_by(desc(RuleExecutionLogModel.executed_at))
            .limit(limit)
        ).scalars().all()

        return [_model_to_domain_log(m) for m in models]

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100
    ) -> List[RuleExecutionLog]:
        """الحصول على سجلات في نطاق زمني"""
        models = self._session.execute(
            select(RuleExecutionLogModel)
            .where(
                and_(
                    RuleExecutionLogModel.executed_at >= start_date,
                    RuleExecutionLogModel.executed_at <= end_date
                )
            )
            .order_by(desc(RuleExecutionLogModel.executed_at))
            .limit(limit)
        ).scalars().all()

        return [_model_to_domain_log(m) for m in models]

    def get_recent(self, limit: int = 100) -> List[RuleExecutionLog]:
        """الحصول على أحدث السجلات"""
        models = self._session.execute(
            select(RuleExecutionLogModel)
            .order_by(desc(RuleExecutionLogModel.executed_at))
            .limit(limit)
        ).scalars().all()

        return [_model_to_domain_log(m) for m in models]

    def get_by_success(self, success: bool, limit: int = 100) -> List[RuleExecutionLog]:
        """الحصول على السجلات حسب حالة النجاح"""
        models = self._session.execute(
            select(RuleExecutionLogModel)
            .where(RuleExecutionLogModel.success == success)
            .order_by(desc(RuleExecutionLogModel.executed_at))
            .limit(limit)
        ).scalars().all()

        return [_model_to_domain_log(m) for m in models]

    def count_by_rule(self, rule_id: str) -> int:
        """حساب عدد مرات تنفيذ قاعدة معينة"""
        result = self._session.execute(
            select(func.count()).select_from(RuleExecutionLogModel)
            .where(RuleExecutionLogModel.rule_id == rule_id)
        ).scalar()

        return result or 0

    def count_success_by_rule(self, rule_id: str) -> int:
        """حساب عدد مرات التنفيذ الناجحة لقاعدة معينة"""
        result = self._session.execute(
            select(func.count()).select_from(RuleExecutionLogModel)
            .where(
                and_(
                    RuleExecutionLogModel.rule_id == rule_id,
                    RuleExecutionLogModel.success == True
                )
            )
        ).scalar()

        return result or 0

    def get_success_rate(self, rule_id: str) -> float:
        """الحصول على نسبة نجاح قاعدة معينة"""
        total = self.count_by_rule(rule_id)
        if total == 0:
            return 0.0

        success = self.count_success_by_rule(rule_id)
        return (success / total) * 100

    def delete_old_logs(self, days: int) -> int:
        """حذف السجلات القديمة"""
        cutoff = utc_now() - timezone.timedelta(days=days)

        result = self._session.execute(
            select(RuleExecutionLogModel)
            .where(RuleExecutionLogModel.executed_at < cutoff)
        ).scalars().all()

        count = len(result)
        for model in result:
            self._session.delete(model)

        return count

    def delete_by_rule(self, rule_id: str) -> int:
        """حذف جميع سجلات قاعدة معينة"""
        result = self._session.execute(
            select(RuleExecutionLogModel)
            .where(RuleExecutionLogModel.rule_id == rule_id)
        ).scalars().all()

        count = len(result)
        for model in result:
            self._session.delete(model)

        return count


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PostgresRuleRepository',
    'PostgresRuleGroupRepository',
    'PostgresRuleExecutionLogRepository',
]