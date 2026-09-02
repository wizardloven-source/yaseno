# core/infrastructure/db/postgres/tax_repository.py
"""
PostgreSQL Repository for Tax - مستودع الضرائب
✅ يدعم: TaxRule, TaxGroup, TaxExemption, TaxPeriod
✅ يدعم: Optimistic Locking عبر الـ version
✅ يدعم: البحث المتقدم حسب النوع والجهة والحالة
✅ يدعم: Pagination للقوائم الكبيرة
✅ يدعم: التخزين المؤقت (Caching)
"""

import logging
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import select, update, func, and_, or_, desc, asc
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError

from core.domain.tax.entities import TaxRule, TaxGroup, TaxExemption, TaxPeriod
from core.domain.tax.value_objects import (
    TaxId, TaxCode, TaxRate, TaxType, TaxCalculationType,
    TaxJurisdiction, TaxApplicationScope, TaxCalculationResult
)
from core.domain.tax.interfaces import (
    ITaxRepository, ITaxGroupRepository, ITaxExemptionRepository, ITaxPeriodRepository
)
from core.shared.exceptions import ConcurrentModificationError

from ..models.tax_model import (
    TaxRuleModel, TaxGroupModel, TaxGroupRulesModel,
    TaxExemptionModel, TaxPeriodModel, TaxCalculationLogModel
)


logger = logging.getLogger(__name__)


# =============================================================================
# دوال التحويل بين Domain و ORM - TaxRule
# =============================================================================

def _domain_to_model_tax_rule(rule: TaxRule) -> TaxRuleModel:
    """تحويل Domain Entity إلى ORM Model - TaxRule"""
    return TaxRuleModel(
        id=UUID(str(rule.id)),
        code=str(rule.code),
        name=rule.name,
        description=rule.description,
        tax_type=rule.tax_type.value,
        calculation_type=rule.calculation_type.value,
        rate=rule.rate.rate,
        jurisdiction=rule.jurisdiction.value,
        jurisdiction_code=rule.jurisdiction_code,
        application_scope=rule.application_scope.value,
        applies_to=rule.applies_to,
        valid_from=rule.valid_from,
        valid_to=rule.valid_to,
        is_compound=rule.is_compound,
        parent_tax_id=UUID(str(rule.parent_tax_id)) if rule.parent_tax_id else None,
        compound_calculation_order=rule.compound_calculation_order,
        exempt_customer_groups=rule.exempt_customer_groups,
        exempt_product_categories=rule.exempt_product_categories,
        exempt_countries=rule.exempt_countries,
        exempt_threshold_amount=rule.exempt_threshold_amount,
        is_active=rule.is_active,
        is_default=rule.is_default,
        is_mandatory=rule.is_mandatory,
        created_at=rule.created_at,
        created_by=rule.created_by,
        updated_at=rule.updated_at,
        updated_by=rule.updated_by,
        version=rule.version
    )


def _model_to_domain_tax_rule(model: TaxRuleModel) -> TaxRule:
    """تحويل ORM Model إلى Domain Entity - TaxRule"""
    if not model:
        return None

    rule = TaxRule(
        id=TaxId(str(model.id)),
        code=TaxCode(model.code),
        name=model.name,
        description=model.description,
        tax_type=TaxType(model.tax_type),
        calculation_type=TaxCalculationType(model.calculation_type),
        rate=TaxRate(model.rate),
        jurisdiction=TaxJurisdiction(model.jurisdiction),
        jurisdiction_code=model.jurisdiction_code,
        application_scope=TaxApplicationScope(model.application_scope),
        applies_to=model.applies_to or [],
        valid_from=model.valid_from,
        valid_to=model.valid_to,
        is_compound=model.is_compound,
        parent_tax_id=TaxId(str(model.parent_tax_id)) if model.parent_tax_id else None,
        compound_calculation_order=model.compound_calculation_order,
        exempt_customer_groups=model.exempt_customer_groups or [],
        exempt_product_categories=model.exempt_product_categories or [],
        exempt_countries=model.exempt_countries or [],
        exempt_threshold_amount=model.exempt_threshold_amount,
        is_active=model.is_active,
        is_default=model.is_default,
        is_mandatory=model.is_mandatory,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )

    return rule


# =============================================================================
# دوال التحويل - TaxGroup
# =============================================================================

def _domain_to_model_tax_group(group: TaxGroup) -> TaxGroupModel:
    """تحويل Domain Entity إلى ORM Model - TaxGroup"""
    return TaxGroupModel(
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


def _model_to_domain_tax_group(model: TaxGroupModel, include_rules: bool = True) -> TaxGroup:
    """تحويل ORM Model إلى Domain Entity - TaxGroup"""
    if not model:
        return None

    rules = []
    if include_rules and model.tax_rules:
        rules = [_model_to_domain_tax_rule(r) for r in model.tax_rules]

    return TaxGroup(
        id=str(model.id),
        code=model.code,
        name=model.name,
        description=model.description,
        tax_rules=rules,
        is_active=model.is_active,
        is_default=model.is_default,
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )


# =============================================================================
# PostgresTaxRepository - مستودع القواعد الضريبية
# =============================================================================

class PostgresTaxRepository(ITaxRepository):
    """
    PostgreSQL implementation of ITaxRepository
    """

    def __init__(self, session: Session):
        self._session = session
        self._cache: Dict[str, TaxRule] = {}

    # ========== العمليات الأساسية ==========

    def save(self, rule: TaxRule) -> None:
        """حفظ القاعدة الضريبية مع Optimistic Locking"""
        existing = self._session.execute(
            select(TaxRuleModel).where(TaxRuleModel.id == UUID(str(rule.id)))
        ).scalar_one_or_none()

        if existing:
            # تحديث مع التحقق من الإصدار
            now = utc_now()
            new_version = existing.version + 1

            result = self._session.execute(
                update(TaxRuleModel)
                .where(
                    TaxRuleModel.id == UUID(str(rule.id)),
                    TaxRuleModel.version == rule.version
                )
                .values(
                    code=str(rule.code),
                    name=rule.name,
                    description=rule.description,
                    tax_type=rule.tax_type.value,
                    calculation_type=rule.calculation_type.value,
                    rate=rule.rate.rate,
                    jurisdiction=rule.jurisdiction.value,
                    jurisdiction_code=rule.jurisdiction_code,
                    application_scope=rule.application_scope.value,
                    applies_to=rule.applies_to,
                    valid_from=rule.valid_from,
                    valid_to=rule.valid_to,
                    is_compound=rule.is_compound,
                    parent_tax_id=UUID(str(rule.parent_tax_id)) if rule.parent_tax_id else None,
                    compound_calculation_order=rule.compound_calculation_order,
                    exempt_customer_groups=rule.exempt_customer_groups,
                    exempt_product_categories=rule.exempt_product_categories,
                    exempt_countries=rule.exempt_countries,
                    exempt_threshold_amount=rule.exempt_threshold_amount,
                    is_active=rule.is_active,
                    is_default=rule.is_default,
                    is_mandatory=rule.is_mandatory,
                    updated_at=now,
                    updated_by=rule.updated_by,
                    version=new_version
                )
            )

            if result.rowcount == 0:
                raise ConcurrentModificationError(
                    "TaxRule",
                    str(rule.id),
                    rule.version,
                    existing.version
                )

            rule.version = new_version
            rule.updated_at = now

        else:
            # إنشاء قاعدة جديدة
            model = _domain_to_model_tax_rule(rule)
            self._session.add(model)
            self._session.flush()
            rule.version = 1

        self._cache[str(rule.id)] = rule

    def get_by_id(self, rule_id: str) -> Optional[TaxRule]:
        """الحصول على قاعدة ضريبية بواسطة المعرف"""
        if rule_id in self._cache:
            return self._cache[rule_id]

        model = self._session.execute(
            select(TaxRuleModel).where(TaxRuleModel.id == UUID(rule_id))
        ).scalar_one_or_none()

        if not model:
            return None

        rule = _model_to_domain_tax_rule(model)
        self._cache[rule_id] = rule
        return rule

    def get_by_code(self, code: str) -> Optional[TaxRule]:
        """الحصول على قاعدة ضريبية بواسطة الكود"""
        for rule in self._cache.values():
            if str(rule.code) == code:
                return rule

        model = self._session.execute(
            select(TaxRuleModel).where(TaxRuleModel.code == code)
        ).scalar_one_or_none()

        if not model:
            return None

        rule = _model_to_domain_tax_rule(model)
        self._cache[str(rule.id)] = rule
        return rule

    def get_all(self, include_inactive: bool = False) -> List[TaxRule]:
        """الحصول على جميع القواعد الضريبية"""
        query = select(TaxRuleModel)

        if not include_inactive:
            query = query.where(TaxRuleModel.is_active == True)

        query = query.order_by(TaxRuleModel.code)

        models = self._session.execute(query).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_tax_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def get_active_rules(self) -> List[TaxRule]:
        """الحصول على القواعد النشطة فقط"""
        return self.get_all(include_inactive=False)

    def get_default_rule(self) -> Optional[TaxRule]:
        """الحصول على القاعدة الافتراضية"""
        model = self._session.execute(
            select(TaxRuleModel)
            .where(
                and_(
                    TaxRuleModel.is_default == True,
                    TaxRuleModel.is_active == True
                )
            )
        ).scalar_one_or_none()

        if not model:
            return None

        rule = _model_to_domain_tax_rule(model)
        self._cache[str(rule.id)] = rule
        return rule

    def get_by_date_range(self, start_date: date, end_date: date) -> List[TaxRule]:
        """الحصول على القواعد في نطاق زمني"""
        models = self._session.execute(
            select(TaxRuleModel)
            .where(
                and_(
                    TaxRuleModel.valid_from <= end_date,
                    or_(
                        TaxRuleModel.valid_to >= start_date,
                        TaxRuleModel.valid_to.is_(None)
                    ),
                    TaxRuleModel.is_active == True
                )
            )
            .order_by(TaxRuleModel.code)
        ).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_tax_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def get_by_tax_type(self, tax_type: TaxType) -> List[TaxRule]:
        """الحصول على القواعد حسب نوع الضريبة"""
        models = self._session.execute(
            select(TaxRuleModel)
            .where(
                and_(
                    TaxRuleModel.tax_type == tax_type.value,
                    TaxRuleModel.is_active == True
                )
            )
            .order_by(TaxRuleModel.code)
        ).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_tax_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def get_by_jurisdiction(self, jurisdiction: TaxJurisdiction) -> List[TaxRule]:
        """الحصول على القواعد حسب الجهة المختصة"""
        models = self._session.execute(
            select(TaxRuleModel)
            .where(
                and_(
                    TaxRuleModel.jurisdiction == jurisdiction.value,
                    TaxRuleModel.is_active == True
                )
            )
            .order_by(TaxRuleModel.code)
        ).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_tax_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def search_rules(self, search_text: str, limit: int = 50) -> List[TaxRule]:
        """البحث عن القواعد الضريبية"""
        search_pattern = f"%{search_text}%"

        models = self._session.execute(
            select(TaxRuleModel)
            .where(
                and_(
                    TaxRuleModel.is_active == True,
                    or_(
                        TaxRuleModel.code.ilike(search_pattern),
                        TaxRuleModel.name.ilike(search_pattern),
                        TaxRuleModel.description.ilike(search_pattern)
                    )
                )
            )
            .limit(limit)
        ).scalars().all()

        rules = []
        for model in models:
            rule = _model_to_domain_tax_rule(model)
            self._cache[str(rule.id)] = rule
            rules.append(rule)

        return rules

    def delete(self, rule_id: str) -> bool:
        """حذف قاعدة ضريبية"""
        model = self._session.execute(
            select(TaxRuleModel).where(TaxRuleModel.id == UUID(rule_id))
        ).scalar_one_or_none()

        if not model:
            return False

        if model.is_default:
            raise ValueError("Cannot delete default tax rule")

        self._session.delete(model)

        if rule_id in self._cache:
            del self._cache[rule_id]

        return True

    def count_active(self) -> int:
        """حساب عدد القواعد النشطة"""
        result = self._session.execute(
            select(func.count()).select_from(TaxRuleModel)
            .where(TaxRuleModel.is_active == True)
        ).scalar()

        return result or 0

    def count_by_type(self, tax_type: TaxType) -> int:
        """حساب عدد القواعد من نوع معين"""
        result = self._session.execute(
            select(func.count()).select_from(TaxRuleModel)
            .where(
                and_(
                    TaxRuleModel.tax_type == tax_type.value,
                    TaxRuleModel.is_active == True
                )
            )
        ).scalar()

        return result or 0

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._cache.clear()


# =============================================================================
# PostgresTaxGroupRepository - مستودع مجموعات الضرائب
# =============================================================================

class PostgresTaxGroupRepository(ITaxGroupRepository):
    """
    PostgreSQL implementation of ITaxGroupRepository
    """

    def __init__(self, session: Session):
        self._session = session
        self._cache: Dict[str, TaxGroup] = {}

    def save(self, group: TaxGroup) -> None:
        """حفظ مجموعة ضرائب"""
        existing = self._session.execute(
            select(TaxGroupModel).where(TaxGroupModel.id == UUID(group.id))
        ).scalar_one_or_none()

        if existing:
            now = utc_now()
            new_version = existing.version + 1

            self._session.execute(
                update(TaxGroupModel)
                .where(
                    TaxGroupModel.id == UUID(group.id),
                    TaxGroupModel.version == group.version
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

            # تحديث العلاقات (Many-to-Many)
            existing.tax_rules = []
            for rule in group.tax_rules:
                rule_model = self._session.execute(
                    select(TaxRuleModel).where(TaxRuleModel.id == UUID(str(rule.id)))
                ).scalar_one_or_none()
                if rule_model:
                    existing.tax_rules.append(rule_model)

        else:
            model = _domain_to_model_tax_group(group)
            self._session.add(model)
            self._session.flush()
            group.version = 1

            # إضافة العلاقات
            for rule in group.tax_rules:
                rule_model = self._session.execute(
                    select(TaxRuleModel).where(TaxRuleModel.id == UUID(str(rule.id)))
                ).scalar_one_or_none()
                if rule_model:
                    model.tax_rules.append(rule_model)

        self._cache[group.id] = group

    def get_by_id(self, group_id: str) -> Optional[TaxGroup]:
        """الحصول على مجموعة ضرائب بواسطة المعرف"""
        if group_id in self._cache:
            return self._cache[group_id]

        model = self._session.execute(
            select(TaxGroupModel)
            .options(selectinload(TaxGroupModel.tax_rules))
            .where(TaxGroupModel.id == UUID(group_id))
        ).unique().scalar_one_or_none()

        if not model:
            return None

        group = _model_to_domain_tax_group(model)
        self._cache[group_id] = group
        return group

    def get_by_code(self, code: str) -> Optional[TaxGroup]:
        """الحصول على مجموعة ضرائب بواسطة الكود"""
        model = self._session.execute(
            select(TaxGroupModel)
            .options(selectinload(TaxGroupModel.tax_rules))
            .where(TaxGroupModel.code == code)
        ).unique().scalar_one_or_none()

        if not model:
            return None

        group = _model_to_domain_tax_group(model)
        self._cache[group.id] = group
        return group

    def get_all(self, include_inactive: bool = False) -> List[TaxGroup]:
        """الحصول على جميع مجموعات الضرائب"""
        query = select(TaxGroupModel).options(selectinload(TaxGroupModel.tax_rules))

        if not include_inactive:
            query = query.where(TaxGroupModel.is_active == True)

        query = query.order_by(TaxGroupModel.code)

        models = self._session.execute(query).unique().scalars().all()

        groups = []
        for model in models:
            group = _model_to_domain_tax_group(model)
            self._cache[group.id] = group
            groups.append(group)

        return groups

    def get_default_group(self) -> Optional[TaxGroup]:
        """الحصول على المجموعة الافتراضية"""
        model = self._session.execute(
            select(TaxGroupModel)
            .options(selectinload(TaxGroupModel.tax_rules))
            .where(
                and_(
                    TaxGroupModel.is_default == True,
                    TaxGroupModel.is_active == True
                )
            )
        ).unique().scalar_one_or_none()

        if not model:
            return None

        group = _model_to_domain_tax_group(model)
        self._cache[group.id] = group
        return group

    def delete(self, group_id: str) -> bool:
        """حذف مجموعة ضرائب"""
        model = self._session.execute(
            select(TaxGroupModel).where(TaxGroupModel.id == UUID(group_id))
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
# PostgresTaxExemptionRepository - مستودع الإعفاءات الضريبية
# =============================================================================

class PostgresTaxExemptionRepository(ITaxExemptionRepository):
    """
    PostgreSQL implementation of ITaxExemptionRepository
    """

    def __init__(self, session: Session):
        self._session = session
        self._cache: Dict[str, TaxExemption] = {}

    def save(self, exemption: TaxExemption) -> None:
        """حفظ إعفاء ضريبي"""
        existing = self._session.execute(
            select(TaxExemptionModel).where(TaxExemptionModel.id == UUID(exemption.id))
        ).scalar_one_or_none()

        if existing:
            now = utc_now()
            new_version = existing.version + 1

            self._session.execute(
                update(TaxExemptionModel)
                .where(
                    TaxExemptionModel.id == UUID(exemption.id),
                    TaxExemptionModel.version == exemption.version
                )
                .values(
                    code=exemption.code,
                    name=exemption.name,
                    description=exemption.description,
                    customer_ids=exemption.customer_ids,
                    customer_groups=exemption.customer_groups,
                    product_codes=exemption.product_codes,
                    product_categories=exemption.product_categories,
                    countries=exemption.countries,
                    valid_from=exemption.valid_from,
                    valid_to=exemption.valid_to,
                    threshold_amount=exemption.threshold_amount,
                    threshold_currency=exemption.threshold_currency,
                    is_active=exemption.is_active,
                    is_automatic=exemption.is_automatic,
                    updated_at=now,
                    updated_by=exemption.updated_by,
                    version=new_version
                )
            )

            exemption.version = new_version

        else:
            model = TaxExemptionModel(
                id=UUID(exemption.id),
                code=exemption.code,
                name=exemption.name,
                description=exemption.description,
                customer_ids=exemption.customer_ids,
                customer_groups=exemption.customer_groups,
                product_codes=exemption.product_codes,
                product_categories=exemption.product_categories,
                countries=exemption.countries,
                valid_from=exemption.valid_from,
                valid_to=exemption.valid_to,
                threshold_amount=exemption.threshold_amount,
                threshold_currency=exemption.threshold_currency,
                is_active=exemption.is_active,
                is_automatic=exemption.is_automatic,
                created_at=exemption.created_at,
                created_by=exemption.created_by,
                updated_at=exemption.updated_at,
                updated_by=exemption.updated_by,
                version=exemption.version
            )
            self._session.add(model)
            self._session.flush()
            exemption.version = 1

        self._cache[exemption.id] = exemption

    def get_by_id(self, exemption_id: str) -> Optional[TaxExemption]:
        """الحصول على إعفاء ضريبي بواسطة المعرف"""
        if exemption_id in self._cache:
            return self._cache[exemption_id]

        model = self._session.execute(
            select(TaxExemptionModel).where(TaxExemptionModel.id == UUID(exemption_id))
        ).scalar_one_or_none()

        if not model:
            return None

        exemption = TaxExemption(
            id=str(model.id),
            code=model.code,
            name=model.name,
            description=model.description,
            customer_ids=model.customer_ids or [],
            customer_groups=model.customer_groups or [],
            product_codes=model.product_codes or [],
            product_categories=model.product_categories or [],
            countries=model.countries or [],
            valid_from=model.valid_from,
            valid_to=model.valid_to,
            threshold_amount=model.threshold_amount,
            threshold_currency=model.threshold_currency,
            is_active=model.is_active,
            is_automatic=model.is_automatic,
            created_at=model.created_at,
            created_by=model.created_by,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
            version=model.version
        )

        self._cache[exemption_id] = exemption
        return exemption

    def get_by_code(self, code: str) -> Optional[TaxExemption]:
        """الحصول على إعفاء ضريبي بواسطة الكود"""
        model = self._session.execute(
            select(TaxExemptionModel).where(TaxExemptionModel.code == code)
        ).scalar_one_or_none()

        if not model:
            return None

        return self.get_by_id(str(model.id))

    def get_all(self, include_inactive: bool = False) -> List[TaxExemption]:
        """الحصول على جميع الإعفاءات الضريبية"""
        query = select(TaxExemptionModel)

        if not include_inactive:
            query = query.where(TaxExemptionModel.is_active == True)

        query = query.order_by(TaxExemptionModel.code)

        models = self._session.execute(query).scalars().all()

        exemptions = []
        for model in models:
            exemption = TaxExemption(
                id=str(model.id),
                code=model.code,
                name=model.name,
                description=model.description,
                customer_ids=model.customer_ids or [],
                customer_groups=model.customer_groups or [],
                product_codes=model.product_codes or [],
                product_categories=model.product_categories or [],
                countries=model.countries or [],
                valid_from=model.valid_from,
                valid_to=model.valid_to,
                threshold_amount=model.threshold_amount,
                threshold_currency=model.threshold_currency,
                is_active=model.is_active,
                is_automatic=model.is_automatic,
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                version=model.version
            )
            self._cache[exemption.id] = exemption
            exemptions.append(exemption)

        return exemptions

    def get_active_exemptions(self) -> List[TaxExemption]:
        """الحصول على الإعفاءات النشطة"""
        today = date.today()

        models = self._session.execute(
            select(TaxExemptionModel)
            .where(
                and_(
                    TaxExemptionModel.is_active == True,
                    TaxExemptionModel.valid_from <= today,
                    or_(
                        TaxExemptionModel.valid_to >= today,
                        TaxExemptionModel.valid_to.is_(None)
                    )
                )
            )
            .order_by(TaxExemptionModel.code)
        ).scalars().all()

        exemptions = []
        for model in models:
            exemption = TaxExemption(
                id=str(model.id),
                code=model.code,
                name=model.name,
                description=model.description,
                customer_ids=model.customer_ids or [],
                customer_groups=model.customer_groups or [],
                product_codes=model.product_codes or [],
                product_categories=model.product_categories or [],
                countries=model.countries or [],
                valid_from=model.valid_from,
                valid_to=model.valid_to,
                threshold_amount=model.threshold_amount,
                threshold_currency=model.threshold_currency,
                is_active=model.is_active,
                is_automatic=model.is_automatic,
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                version=model.version
            )
            self._cache[exemption.id] = exemption
            exemptions.append(exemption)

        return exemptions

    def get_by_customer(self, customer_id: str) -> List[TaxExemption]:
        """الحصول على إعفاءات عميل معين"""
        models = self._session.execute(
            select(TaxExemptionModel)
            .where(
                and_(
                    TaxExemptionModel.is_active == True,
                    TaxExemptionModel.customer_ids.contains([customer_id])
                )
            )
        ).scalars().all()

        exemptions = []
        for model in models:
            exemption = TaxExemption(
                id=str(model.id),
                code=model.code,
                name=model.name,
                description=model.description,
                customer_ids=model.customer_ids or [],
                customer_groups=model.customer_groups or [],
                product_codes=model.product_codes or [],
                product_categories=model.product_categories or [],
                countries=model.countries or [],
                valid_from=model.valid_from,
                valid_to=model.valid_to,
                threshold_amount=model.threshold_amount,
                threshold_currency=model.threshold_currency,
                is_active=model.is_active,
                is_automatic=model.is_automatic,
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                version=model.version
            )
            self._cache[exemption.id] = exemption
            exemptions.append(exemption)

        return exemptions

    def get_by_product(self, product_code: str) -> List[TaxExemption]:
        """الحصول على إعفاءات منتج معين"""
        models = self._session.execute(
            select(TaxExemptionModel)
            .where(
                and_(
                    TaxExemptionModel.is_active == True,
                    TaxExemptionModel.product_codes.contains([product_code])
                )
            )
        ).scalars().all()

        exemptions = []
        for model in models:
            exemption = TaxExemption(
                id=str(model.id),
                code=model.code,
                name=model.name,
                description=model.description,
                customer_ids=model.customer_ids or [],
                customer_groups=model.customer_groups or [],
                product_codes=model.product_codes or [],
                product_categories=model.product_categories or [],
                countries=model.countries or [],
                valid_from=model.valid_from,
                valid_to=model.valid_to,
                threshold_amount=model.threshold_amount,
                threshold_currency=model.threshold_currency,
                is_active=model.is_active,
                is_automatic=model.is_automatic,
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                version=model.version
            )
            self._cache[exemption.id] = exemption
            exemptions.append(exemption)

        return exemptions

    def delete(self, exemption_id: str) -> bool:
        """حذف إعفاء ضريبي"""
        model = self._session.execute(
            select(TaxExemptionModel).where(TaxExemptionModel.id == UUID(exemption_id))
        ).scalar_one_or_none()

        if not model:
            return False

        self._session.delete(model)

        if exemption_id in self._cache:
            del self._cache[exemption_id]

        return True

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._cache.clear()


# =============================================================================
# PostgresTaxPeriodRepository - مستودع الفترات الضريبية
# =============================================================================

class PostgresTaxPeriodRepository(ITaxPeriodRepository):
    """
    PostgreSQL implementation of ITaxPeriodRepository
    """

    def __init__(self, session: Session):
        self._session = session
        self._cache: Dict[str, TaxPeriod] = {}

    def save(self, period: TaxPeriod) -> None:
        """حفظ فترة ضريبية"""
        existing = self._session.execute(
            select(TaxPeriodModel).where(TaxPeriodModel.id == UUID(period.id))
        ).scalar_one_or_none()

        if existing:
            now = utc_now()
            new_version = existing.version + 1

            self._session.execute(
                update(TaxPeriodModel)
                .where(
                    TaxPeriodModel.id == UUID(period.id),
                    TaxPeriodModel.version == period.version
                )
                .values(
                    code=period.code,
                    name=period.name,
                    start_date=period.start_date,
                    end_date=period.end_date,
                    period_type=period.period_type,
                    status=period.status,
                    total_taxable_sales=period.total_taxable_sales,
                    total_tax_collected=period.total_tax_collected,
                    total_tax_paid=period.total_tax_paid,
                    total_tax_due=period.total_tax_due,
                    total_tax_credit=period.total_tax_credit,
                    net_tax_due=period.net_tax_due,
                    currency=period.currency,
                    metadata=period.metadata,
                    updated_at=now,
                    updated_by=period.updated_by,
                    version=new_version
                )
            )

            period.version = new_version

        else:
            model = TaxPeriodModel(
                id=UUID(period.id),
                code=period.code,
                name=period.name,
                start_date=period.start_date,
                end_date=period.end_date,
                period_type=period.period_type,
                status=period.status,
                total_taxable_sales=period.total_taxable_sales,
                total_tax_collected=period.total_tax_collected,
                total_tax_paid=period.total_tax_paid,
                total_tax_due=period.total_tax_due,
                total_tax_credit=period.total_tax_credit,
                net_tax_due=period.net_tax_due,
                currency=period.currency,
                metadata=period.metadata,
                created_at=period.created_at,
                created_by=period.created_by,
                updated_at=period.updated_at,
                updated_by=period.updated_by,
                version=period.version
            )
            self._session.add(model)
            self._session.flush()
            period.version = 1

        self._cache[period.id] = period

    def get_by_id(self, period_id: str) -> Optional[TaxPeriod]:
        """الحصول على فترة ضريبية بواسطة المعرف"""
        if period_id in self._cache:
            return self._cache[period_id]

        model = self._session.execute(
            select(TaxPeriodModel).where(TaxPeriodModel.id == UUID(period_id))
        ).scalar_one_or_none()

        if not model:
            return None

        period = TaxPeriod(
            id=str(model.id),
            code=model.code,
            name=model.name,
            start_date=model.start_date,
            end_date=model.end_date,
            period_type=model.period_type,
            status=model.status,
            total_taxable_sales=model.total_taxable_sales,
            total_tax_collected=model.total_tax_collected,
            total_tax_paid=model.total_tax_paid,
            total_tax_due=model.total_tax_due,
            total_tax_credit=model.total_tax_credit,
            net_tax_due=model.net_tax_due,
            currency=model.currency,
            metadata=model.metadata or {},
            created_at=model.created_at,
            created_by=model.created_by,
            updated_at=model.updated_at,
            updated_by=model.updated_by,
            version=model.version
        )

        self._cache[period_id] = period
        return period

    def get_by_code(self, code: str) -> Optional[TaxPeriod]:
        """الحصول على فترة ضريبية بواسطة الكود"""
        model = self._session.execute(
            select(TaxPeriodModel).where(TaxPeriodModel.code == code)
        ).scalar_one_or_none()

        if not model:
            return None

        return self.get_by_id(str(model.id))

    def get_current_period(self) -> Optional[TaxPeriod]:
        """الحصول على الفترة الحالية"""
        today = date.today()

        model = self._session.execute(
            select(TaxPeriodModel)
            .where(
                and_(
                    TaxPeriodModel.start_date <= today,
                    TaxPeriodModel.end_date >= today,
                    TaxPeriodModel.status == 'open'
                )
            )
            .order_by(desc(TaxPeriodModel.start_date))
            .limit(1)
        ).scalar_one_or_none()

        if not model:
            return None

        return self.get_by_id(str(model.id))

    def get_by_date(self, dt: date) -> Optional[TaxPeriod]:
        """الحصول على الفترة التي تحتوي على تاريخ معين"""
        model = self._session.execute(
            select(TaxPeriodModel)
            .where(
                and_(
                    TaxPeriodModel.start_date <= dt,
                    TaxPeriodModel.end_date >= dt
                )
            )
            .limit(1)
        ).scalar_one_or_none()

        if not model:
            return None

        return self.get_by_id(str(model.id))

    def get_by_year(self, year: int) -> List[TaxPeriod]:
        """الحصول على فترات سنة معينة"""
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        models = self._session.execute(
            select(TaxPeriodModel)
            .where(
                and_(
                    TaxPeriodModel.start_date >= start_date,
                    TaxPeriodModel.end_date <= end_date
                )
            )
            .order_by(TaxPeriodModel.start_date)
        ).scalars().all()

        periods = []
        for model in models:
            period = TaxPeriod(
                id=str(model.id),
                code=model.code,
                name=model.name,
                start_date=model.start_date,
                end_date=model.end_date,
                period_type=model.period_type,
                status=model.status,
                total_taxable_sales=model.total_taxable_sales,
                total_tax_collected=model.total_tax_collected,
                total_tax_paid=model.total_tax_paid,
                total_tax_due=model.total_tax_due,
                total_tax_credit=model.total_tax_credit,
                net_tax_due=model.net_tax_due,
                currency=model.currency,
                metadata=model.metadata or {},
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                version=model.version
            )
            self._cache[period.id] = period
            periods.append(period)

        return periods

    def get_open_periods(self) -> List[TaxPeriod]:
        """الحصول على الفترات المفتوحة"""
        models = self._session.execute(
            select(TaxPeriodModel)
            .where(TaxPeriodModel.status == 'open')
            .order_by(TaxPeriodModel.start_date)
        ).scalars().all()

        periods = []
        for model in models:
            period = TaxPeriod(
                id=str(model.id),
                code=model.code,
                name=model.name,
                start_date=model.start_date,
                end_date=model.end_date,
                period_type=model.period_type,
                status=model.status,
                total_taxable_sales=model.total_taxable_sales,
                total_tax_collected=model.total_tax_collected,
                total_tax_paid=model.total_tax_paid,
                total_tax_due=model.total_tax_due,
                total_tax_credit=model.total_tax_credit,
                net_tax_due=model.net_tax_due,
                currency=model.currency,
                metadata=model.metadata or {},
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                version=model.version
            )
            self._cache[period.id] = period
            periods.append(period)

        return periods

    def get_closed_periods(self) -> List[TaxPeriod]:
        """الحصول على الفترات المغلقة"""
        models = self._session.execute(
            select(TaxPeriodModel)
            .where(TaxPeriodModel.status.in_(['closed', 'locked']))
            .order_by(desc(TaxPeriodModel.end_date))
        ).scalars().all()

        periods = []
        for model in models:
            period = TaxPeriod(
                id=str(model.id),
                code=model.code,
                name=model.name,
                start_date=model.start_date,
                end_date=model.end_date,
                period_type=model.period_type,
                status=model.status,
                total_taxable_sales=model.total_taxable_sales,
                total_tax_collected=model.total_tax_collected,
                total_tax_paid=model.total_tax_paid,
                total_tax_due=model.total_tax_due,
                total_tax_credit=model.total_tax_credit,
                net_tax_due=model.net_tax_due,
                currency=model.currency,
                metadata=model.metadata or {},
                created_at=model.created_at,
                created_by=model.created_by,
                updated_at=model.updated_at,
                updated_by=model.updated_by,
                version=model.version
            )
            self._cache[period.id] = period
            periods.append(period)

        return periods

    def delete(self, period_id: str) -> bool:
        """حذف فترة ضريبية"""
        period = self.get_by_id(period_id)
        if not period:
            return False

        if period.status != 'open':
            raise ValueError(f"Cannot delete period with status '{period.status}'")

        model = self._session.execute(
            select(TaxPeriodModel).where(TaxPeriodModel.id == UUID(period_id))
        ).scalar_one_or_none()

        if not model:
            return False

        self._session.delete(model)

        if period_id in self._cache:
            del self._cache[period_id]

        return True

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._cache.clear()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PostgresTaxRepository',
    'PostgresTaxGroupRepository',
    'PostgresTaxExemptionRepository',
    'PostgresTaxPeriodRepository',
]