# core/domain/tax/entities.py
"""
Tax Entities - كيانات الضرائب
✅ يدعم: TaxRule (القاعدة الضريبية الأساسية)
✅ يدعم: TaxGroup (مجموعة ضرائب)
✅ يدعم: TaxExemption (إعفاء ضريبي)
✅ يدعم: TaxPeriod (فترة ضريبية)
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any, Set
from uuid import UUID, uuid4

from .value_objects import (
    TaxId, TaxCode, TaxRate, TaxAmount,
    TaxType, TaxCalculationType, TaxJurisdiction,
    TaxApplicationScope, TaxCalculationResult, TaxContext
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# TaxRule - القاعدة الضريبية (AGGREGATE ROOT)
# =============================================================================

@dataclass
class TaxRule:
    """
    AGGREGATE ROOT - القاعدة الضريبية
    
    تحدد كيفية حساب الضريبة لمنتج أو خدمة معينة في سياق معين.
    
    الميزات:
        1. يدعم أنواع متعددة من الضرائب (VAT, GST, إلخ)
        2. يدعم حساب Inclusive و Exclusive
        3. يدعم الضرائب المركبة (Compound)
        4. يدعم نطاقات تطبيق متعددة
        5. يدعم صلاحية زمنية
        6. يدعم الإعفاءات (Exemptions)
    """

    # ========== معلومات أساسية ==========
    id: TaxId = field(default_factory=TaxId.generate)
    code: TaxCode = field(default_factory=lambda: TaxCode(""))
    name: str = ""
    description: Optional[str] = None

    # ========== نوع الضريبة ==========
    tax_type: TaxType = TaxType.VAT
    calculation_type: TaxCalculationType = TaxCalculationType.EXCLUSIVE

    # ========== النسبة ==========
    rate: TaxRate = field(default_factory=lambda: TaxRate(Decimal('0')))

    # ========== الجهة المختصة ==========
    jurisdiction: TaxJurisdiction = TaxJurisdiction.FEDERAL
    jurisdiction_code: Optional[str] = None

    # ========== نطاق التطبيق ==========
    application_scope: TaxApplicationScope = TaxApplicationScope.ALL_PRODUCTS
    applies_to: List[str] = field(default_factory=list)  # أكواد المنتجات أو التصنيفات

    # ========== صلاحية القاعدة ==========
    valid_from: date = field(default_factory=date.today)
    valid_to: Optional[date] = None

    # ========== للضرائب المركبة ==========
    is_compound: bool = False
    parent_tax_id: Optional[TaxId] = None
    compound_calculation_order: int = 0

    # ========== الإعفاءات ==========
    exempt_customer_groups: List[str] = field(default_factory=list)
    exempt_product_categories: List[str] = field(default_factory=list)
    exempt_countries: List[str] = field(default_factory=list)
    exempt_threshold_amount: Optional[Decimal] = None

    # ========== الحالة ==========
    is_active: bool = True
    is_default: bool = False
    is_mandatory: bool = False

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
        return f"{self.code} - {self.name} ({self.rate})"

    @property
    def rate_as_decimal(self) -> Decimal:
        return self.rate.as_decimal()

    @property
    def is_valid(self) -> bool:
        """هل القاعدة صالحة حالياً؟"""
        if not self.is_active:
            return False
        today = date.today()
        if self.valid_to and today > self.valid_to:
            return False
        return today >= self.valid_from

    @property
    def is_exempt(self) -> bool:
        return self.calculation_type == TaxCalculationType.EXEMPT

    @property
    def is_zero_rated(self) -> bool:
        return self.calculation_type == TaxCalculationType.ZERO_RATED

    @property
    def applies_to_all(self) -> bool:
        return self.application_scope == TaxApplicationScope.ALL_PRODUCTS

    # =========================================================================
    # دوال المصنع
    # =========================================================================

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        rate: Decimal,
        tax_type: TaxType = TaxType.VAT,
        calculation_type: TaxCalculationType = TaxCalculationType.EXCLUSIVE,
        jurisdiction: TaxJurisdiction = TaxJurisdiction.FEDERAL,
        description: Optional[str] = None,
        is_default: bool = False,
        is_mandatory: bool = False,
        valid_from: Optional[date] = None,
        valid_to: Optional[date] = None,
        created_by: str = "system"
    ) -> 'TaxRule':
        """إنشاء قاعدة ضريبية جديدة"""
        rule = cls(
            code=TaxCode(code),
            name=name,
            description=description,
            tax_type=tax_type,
            calculation_type=calculation_type,
            rate=TaxRate(rate),
            jurisdiction=jurisdiction,
            valid_from=valid_from or date.today(),
            valid_to=valid_to,
            is_default=is_default,
            is_mandatory=is_mandatory,
            created_by=created_by,
            updated_by=created_by
        )

        # إضافة حدث الإنشاء
        from .events import TaxRuleCreatedEvent
        rule._events.append(TaxRuleCreatedEvent(
            tax_id=rule.id,
            tax_code=rule.code,
            tax_name=rule.name,
            rate=rule.rate,
            created_by=created_by
        ))

        return rule

    @classmethod
    def create_compound(
        cls,
        code: str,
        name: str,
        rate: Decimal,
        parent_tax_id: TaxId,
        calculation_order: int = 1,
        tax_type: TaxType = TaxType.VAT,
        jurisdiction: TaxJurisdiction = TaxJurisdiction.FEDERAL,
        description: Optional[str] = None,
        created_by: str = "system"
    ) -> 'TaxRule':
        """إنشاء قاعدة ضريبية مركبة"""
        rule = cls(
            code=TaxCode(code),
            name=name,
            description=description,
            tax_type=tax_type,
            calculation_type=TaxCalculationType.COMPOUND,
            rate=TaxRate(rate),
            jurisdiction=jurisdiction,
            is_compound=True,
            parent_tax_id=parent_tax_id,
            compound_calculation_order=calculation_order,
            created_by=created_by,
            updated_by=created_by
        )

        from .events import TaxRuleCreatedEvent
        rule._events.append(TaxRuleCreatedEvent(
            tax_id=rule.id,
            tax_code=rule.code,
            tax_name=rule.name,
            rate=rule.rate,
            is_compound=True,
            created_by=created_by
        ))

        return rule

    @classmethod
    def create_exempt(
        cls,
        code: str,
        name: str,
        jurisdiction: TaxJurisdiction = TaxJurisdiction.FEDERAL,
        description: Optional[str] = None,
        created_by: str = "system"
    ) -> 'TaxRule':
        """إنشاء قاعدة إعفاء ضريبي"""
        return cls.create(
            code=code,
            name=name,
            rate=Decimal('0'),
            tax_type=TaxType.VAT,
            calculation_type=TaxCalculationType.EXEMPT,
            jurisdiction=jurisdiction,
            description=description,
            created_by=created_by
        )

    # =========================================================================
    # العمليات الأساسية
    # =========================================================================

    def applies_to_product(self, product_code: str, product_category: str) -> bool:
        """التحقق مما إذا كانت القاعدة تنطبق على منتج"""
        if self.applies_to_all:
            return True

        if self.application_scope == TaxApplicationScope.PRODUCT_CATEGORY:
            return product_category in self.applies_to

        if self.application_scope == TaxApplicationScope.SPECIFIC_PRODUCT:
            return product_code in self.applies_to

        return False

    def applies_to_customer(self, customer_id: str, customer_group: str) -> bool:
        """التحقق مما إذا كانت القاعدة تنطبق على عميل"""
        # التحقق من الإعفاءات
        if customer_group in self.exempt_customer_groups:
            return False

        if self.application_scope == TaxApplicationScope.ALL_CUSTOMERS:
            return True

        if self.application_scope == TaxApplicationScope.CUSTOMER_GROUP:
            return customer_group in self.applies_to

        if self.application_scope == TaxApplicationScope.SPECIFIC_CUSTOMER:
            return customer_id in self.applies_to

        return True

    def is_exempt_for(self, context: TaxContext) -> bool:
        """التحقق مما إذا كانت القاعدة معفية للسياق المحدد"""
        # إعفاء حسب مجموعة العميل
        if context.customer_group and context.customer_group in self.exempt_customer_groups:
            return True

        # إعفاء حسب تصنيف المنتج
        if context.product_category and context.product_category in self.exempt_product_categories:
            return True

        # إعفاء حسب الدولة
        if context.customer_country and context.customer_country in self.exempt_countries:
            return True

        # إعفاء حسب المبلغ (للمعاملات الصغيرة)
        if self.exempt_threshold_amount and context.amount <= self.exempt_threshold_amount:
            return True

        return False

    def calculate_tax(self, amount: Decimal, context: Optional[TaxContext] = None) -> Decimal:
        """
        حساب مبلغ الضريبة
        
        Args:
            amount: المبلغ الخاضع للضريبة
            context: سياق الحساب (للتطبيقات الشرطية)
        
        Returns:
            Decimal: مبلغ الضريبة
        """
        # التحقق من الإعفاء
        if context and self.is_exempt_for(context):
            return Decimal('0')

        # الضريبة صفرية أو معفاة
        if self.calculation_type in [TaxCalculationType.ZERO_RATED, TaxCalculationType.EXEMPT]:
            return Decimal('0')

        # الضريبة المركبة
        if self.is_compound:
            return self.rate.apply_to(amount)

        # الضريبة العادية
        return self.rate.apply_to(amount)

    def calculate_tax_with_context(self, amount: Decimal, context: TaxContext) -> TaxCalculationResult:
        """
        حساب الضريبة مع سياق كامل
        
        Args:
            amount: المبلغ الخاضع للضريبة
            context: سياق الحساب
        
        Returns:
            TaxCalculationResult: نتيجة الحساب
        """
        tax_amount = self.calculate_tax(amount, context)

        return TaxCalculationResult(
            taxable_amount=amount,
            tax_amount=tax_amount,
            total_amount=amount + tax_amount,
            breakdown={str(self.code): tax_amount},
            applied_rules=[self],
            calculation_type=self.calculation_type
        )

    # =========================================================================
    # عمليات إدارة القاعدة
    # =========================================================================

    def update(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        rate: Optional[Decimal] = None,
        calculation_type: Optional[TaxCalculationType] = None,
        valid_to: Optional[date] = None,
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

        if rate is not None and rate != self.rate.rate:
            old_rate = self.rate
            self.rate = TaxRate(rate)
            changes['rate'] = {'old': str(old_rate), 'new': str(self.rate)}

        if calculation_type is not None and calculation_type != self.calculation_type:
            changes['calculation_type'] = {'old': self.calculation_type.value, 'new': calculation_type.value}
            self.calculation_type = calculation_type

        if valid_to is not None and valid_to != self.valid_to:
            changes['valid_to'] = {'old': self.valid_to, 'new': valid_to}
            self.valid_to = valid_to

        if is_active is not None and is_active != self.is_active:
            changes['is_active'] = {'old': self.is_active, 'new': is_active}
            self.is_active = is_active

        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            self.version += 1

            from .events import TaxRuleUpdatedEvent
            self._events.append(TaxRuleUpdatedEvent(
                tax_id=self.id,
                tax_code=self.code,
                changes=changes,
                updated_by=updated_by
            ))

    def deactivate(self, deactivated_by: str) -> None:
        """تعطيل القاعدة"""
        if not self.is_active:
            return
        self.update(is_active=False, updated_by=deactivated_by)

    def activate(self, activated_by: str) -> None:
        """تفعيل القاعدة"""
        if self.is_active:
            return
        self.update(is_active=True, updated_by=activated_by)

    def add_exemption(self, customer_group: Optional[str] = None, product_category: Optional[str] = None) -> None:
        """إضافة إعفاء"""
        if customer_group and customer_group not in self.exempt_customer_groups:
            self.exempt_customer_groups.append(customer_group)

        if product_category and product_category not in self.exempt_product_categories:
            self.exempt_product_categories.append(product_category)

        self.updated_at = utc_now()
        self.version += 1

    def remove_exemption(self, customer_group: Optional[str] = None, product_category: Optional[str] = None) -> None:
        """إزالة إعفاء"""
        if customer_group and customer_group in self.exempt_customer_groups:
            self.exempt_customer_groups.remove(customer_group)

        if product_category and product_category in self.exempt_product_categories:
            self.exempt_product_categories.remove(product_category)

        self.updated_at = utc_now()
        self.version += 1

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
            'tax_type': self.tax_type.value,
            'calculation_type': self.calculation_type.value,
            'rate': str(self.rate.rate),
            'jurisdiction': self.jurisdiction.value,
            'jurisdiction_code': self.jurisdiction_code,
            'application_scope': self.application_scope.value,
            'applies_to': self.applies_to,
            'valid_from': self.valid_from.isoformat(),
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'is_compound': self.is_compound,
            'parent_tax_id': str(self.parent_tax_id) if self.parent_tax_id else None,
            'compound_calculation_order': self.compound_calculation_order,
            'exempt_customer_groups': self.exempt_customer_groups,
            'exempt_product_categories': self.exempt_product_categories,
            'exempt_countries': self.exempt_countries,
            'exempt_threshold_amount': str(self.exempt_threshold_amount) if self.exempt_threshold_amount else None,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'is_mandatory': self.is_mandatory,
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
            'rate': str(self.rate.rate),
            'rate_display': str(self.rate),
            'tax_type': self.tax_type.value,
            'calculation_type': self.calculation_type.value,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'is_valid': self.is_valid,
            'valid_from': self.valid_from.isoformat(),
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
        }

    def __repr__(self) -> str:
        status = "ACTIVE" if self.is_active else "INACTIVE"
        return f"TaxRule(id={self.id}, code={self.code}, rate={self.rate}, status={status})"


# =============================================================================
# TaxGroup - مجموعة ضرائب
# =============================================================================

@dataclass
class TaxGroup:
    """
    مجموعة ضرائب - لتجميع عدة ضرائب معاً
    
    مفيد للفواتير التي تطبق عليها ضرائب متعددة (مثل VAT + GST)
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    code: str = ""
    name: str = ""
    description: Optional[str] = None
    tax_rules: List[TaxRule] = field(default_factory=list)
    is_active: bool = True
    is_default: bool = False

    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    version: int = 1

    _events: List[Any] = field(default_factory=list, repr=False)

    @property
    def total_rate(self) -> Decimal:
        """إجمالي نسبة الضرائب في المجموعة"""
        return sum(rule.rate.rate for rule in self.tax_rules)

    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"

    @property
    def rule_count(self) -> int:
        return len(self.tax_rules)

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        tax_rules: Optional[List[TaxRule]] = None,
        description: Optional[str] = None,
        is_default: bool = False,
        created_by: str = "system"
    ) -> 'TaxGroup':
        """إنشاء مجموعة ضرائب جديدة"""
        group = cls(
            code=code,
            name=name,
            description=description,
            tax_rules=tax_rules or [],
            is_default=is_default,
            created_by=created_by,
            updated_by=created_by
        )

        from .events import TaxGroupCreatedEvent
        group._events.append(TaxGroupCreatedEvent(
            group_id=group.id,
            group_code=group.code,
            group_name=group.name,
            rule_count=len(group.tax_rules),
            created_by=created_by
        ))

        return group

    def add_rule(self, rule: TaxRule) -> None:
        """إضافة قاعدة ضريبية للمجموعة"""
        if rule not in self.tax_rules:
            self.tax_rules.append(rule)
            self.updated_at = utc_now()
            self.version += 1

    def remove_rule(self, rule_id: str) -> bool:
        """إزالة قاعدة ضريبية من المجموعة"""
        for i, rule in enumerate(self.tax_rules):
            if str(rule.id) == rule_id:
                self.tax_rules.pop(i)
                self.updated_at = utc_now()
                self.version += 1
                return True
        return False

    def calculate_tax(self, amount: Decimal, context: Optional[TaxContext] = None) -> TaxCalculationResult:
        """
        حساب الضريبة باستخدام جميع القواعد في المجموعة
        
        Args:
            amount: المبلغ الخاضع للضريبة
            context: سياق الحساب
        
        Returns:
            TaxCalculationResult: نتيجة الحساب
        """
        total_tax = Decimal('0')
        breakdown = {}
        applied_rules = []
        calc_type = TaxCalculationType.EXCLUSIVE

        # حساب الضرائب الأساسية
        for rule in self.tax_rules:
            if not rule.is_valid:
                continue

            if context and rule.is_exempt_for(context):
                continue

            tax = rule.calculate_tax(amount, context)
            if tax > 0:
                total_tax += tax
                breakdown[str(rule.code)] = tax
                applied_rules.append(rule)

                if rule.calculation_type == TaxCalculationType.INCLUSIVE:
                    calc_type = TaxCalculationType.INCLUSIVE

        # حساب الضرائب المركبة (تعتمد على الضرائب الأخرى)
        compound_rules = [r for r in self.tax_rules if r.is_compound and r.is_valid]
        compound_rules.sort(key=lambda r: r.compound_calculation_order)

        for rule in compound_rules:
            if context and rule.is_exempt_for(context):
                continue

            base = amount + total_tax
            tax = rule.calculate_tax(base, context)
            if tax > 0:
                total_tax += tax
                breakdown[f"{rule.code}_compound"] = tax
                applied_rules.append(rule)

        return TaxCalculationResult(
            taxable_amount=amount,
            tax_amount=total_tax,
            total_amount=amount + total_tax,
            breakdown=breakdown,
            applied_rules=applied_rules,
            calculation_type=calc_type
        )

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
            'rule_count': len(self.tax_rules),
            'total_rate': str(self.total_rate),
            'is_active': self.is_active,
            'is_default': self.is_default,
            'rules': [r.to_summary() for r in self.tax_rules],
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'version': self.version
        }


# =============================================================================
# TaxExemption - الإعفاء الضريبي
# =============================================================================

@dataclass
class TaxExemption:
    """
    إعفاء ضريبي - يسمح بإعفاء معاملة معينة من الضريبة
    
    يدعم:
        - إعفاءات دائمة أو مؤقتة
        - إعفاءات مرتبطة بعميل معين
        - إعفاءات مرتبطة بمنتج معين
        - إعفاءات مرتبطة بفترة زمنية
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    code: str = ""
    name: str = ""
    description: Optional[str] = None

    # الكيانات المعفاة
    customer_ids: List[str] = field(default_factory=list)
    customer_groups: List[str] = field(default_factory=list)
    product_codes: List[str] = field(default_factory=list)
    product_categories: List[str] = field(default_factory=list)
    countries: List[str] = field(default_factory=list)

    # صلاحية الإعفاء
    valid_from: date = field(default_factory=date.today)
    valid_to: Optional[date] = None

    # حد المبلغ (للمعاملات الصغيرة)
    threshold_amount: Optional[Decimal] = None
    threshold_currency: str = "USD"

    # الحالة
    is_active: bool = True
    is_automatic: bool = False

    created_at: datetime = field(default_factory=utc_now)
    created_by: str = "system"
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = "system"
    version: int = 1

    _events: List[Any] = field(default_factory=list, repr=False)

    @property
    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        today = date.today()
        if self.valid_to and today > self.valid_to:
            return False
        return today >= self.valid_from

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        description: Optional[str] = None,
        customer_ids: Optional[List[str]] = None,
        customer_groups: Optional[List[str]] = None,
        valid_from: Optional[date] = None,
        valid_to: Optional[date] = None,
        created_by: str = "system"
    ) -> 'TaxExemption':
        """إنشاء إعفاء ضريبي جديد"""
        exemption = cls(
            code=code,
            name=name,
            description=description,
            customer_ids=customer_ids or [],
            customer_groups=customer_groups or [],
            valid_from=valid_from or date.today(),
            valid_to=valid_to,
            created_by=created_by,
            updated_by=created_by
        )

        from .events import TaxExemptionCreatedEvent
        exemption._events.append(TaxExemptionCreatedEvent(
            exemption_id=exemption.id,
            exemption_code=exemption.code,
            exemption_name=exemption.name,
            created_by=created_by
        ))

        return exemption

    def applies_to_customer(self, customer_id: str, customer_group: str) -> bool:
        """التحقق مما إذا كان الإعفاء ينطبق على عميل"""
        if customer_id and customer_id in self.customer_ids:
            return True
        if customer_group and customer_group in self.customer_groups:
            return True
        return False

    def applies_to_product(self, product_code: str, product_category: str) -> bool:
        """التحقق مما إذا كان الإعفاء ينطبق على منتج"""
        if product_code and product_code in self.product_codes:
            return True
        if product_category and product_category in self.product_categories:
            return True
        return False

    def applies_to_amount(self, amount: Decimal) -> bool:
        """التحقق مما إذا كان الإعفاء ينطبق على المبلغ"""
        if self.threshold_amount is None:
            return True
        return amount <= self.threshold_amount

    def applies_to_country(self, country: str) -> bool:
        """التحقق مما إذا كان الإعفاء ينطبق على دولة"""
        if not self.countries:
            return True
        return country in self.countries

    def can_apply(self, context: TaxContext) -> bool:
        """التحقق من إمكانية تطبيق الإعفاء"""
        if not self.is_valid:
            return False

        # التحقق من العميل
        if not self.applies_to_customer(
            context.customer_id or "",
            context.customer_group or ""
        ):
            return False

        # التحقق من المنتج
        if not self.applies_to_product(
            context.product_code or "",
            context.product_category or ""
        ):
            return False

        # التحقق من المبلغ
        if not self.applies_to_amount(context.amount):
            return False

        # التحقق من الدولة
        if not self.applies_to_country(context.customer_country or ""):
            return False

        return True

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
            'customer_ids': self.customer_ids,
            'customer_groups': self.customer_groups,
            'product_codes': self.product_codes,
            'product_categories': self.product_categories,
            'countries': self.countries,
            'valid_from': self.valid_from.isoformat(),
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'threshold_amount': str(self.threshold_amount) if self.threshold_amount else None,
            'threshold_currency': self.threshold_currency,
            'is_active': self.is_active,
            'is_automatic': self.is_automatic,
            'is_valid': self.is_valid,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'version': self.version
        }


# =============================================================================
# TaxPeriod - الفترة الضريبية
# =============================================================================

@dataclass
class TaxPeriod:
    """
    الفترة الضريبية - لتتبع الضرائب حسب الفترات الزمنية
    
    يستخدم لتقارير الضرائب الشهرية والربع سنوية والسنوية
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    code: str = ""

    start_date: date = field(default_factory=date.today)
    end_date: date = field(default_factory=date.today)

    # نوع الفترة (شهرية، ربع سنوية، سنوية)
    period_type: str = "monthly"  # monthly, quarterly, yearly

    # حالة الفترة
    status: str = "open"  # open, closed, locked

    # إجماليات الضرائب
    total_taxable_sales: Decimal = Decimal('0')
    total_tax_collected: Decimal = Decimal('0')
    total_tax_paid: Decimal = Decimal('0')
    total_tax_due: Decimal = Decimal('0')
    total_tax_credit: Decimal = Decimal('0')
    net_tax_due: Decimal = Decimal('0')

    currency: str = "USD"

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
    def is_closed(self) -> bool:
        return self.status in ["closed", "locked"]

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        start_date: date,
        end_date: date,
        period_type: str = "monthly",
        created_by: str = "system"
    ) -> 'TaxPeriod':
        """إنشاء فترة ضريبية جديدة"""
        period = cls(
            code=code,
            name=name,
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            created_by=created_by,
            updated_by=created_by
        )

        from .events import TaxPeriodCreatedEvent
        period._events.append(TaxPeriodCreatedEvent(
            period_id=period.id,
            period_code=period.code,
            period_name=period.name,
            start_date=period.start_date,
            end_date=period.end_date,
            created_by=created_by
        ))

        return period

    def close(self, closed_by: str) -> None:
        """إغلاق الفترة الضريبية"""
        if self.is_closed:
            return

        self.status = "closed"
        self.updated_at = utc_now()
        self.updated_by = closed_by
        self.version += 1

        from .events import TaxPeriodClosedEvent
        self._events.append(TaxPeriodClosedEvent(
            period_id=self.id,
            period_code=self.code,
            period_name=self.name,
            closed_by=closed_by
        ))

    def reopen(self, reopened_by: str) -> None:
        """إعادة فتح فترة ضريبية"""
        if self.status == "open":
            return

        self.status = "open"
        self.updated_at = utc_now()
        self.updated_by = reopened_by
        self.version += 1

        from .events import TaxPeriodReopenedEvent
        self._events.append(TaxPeriodReopenedEvent(
            period_id=self.id,
            period_code=self.code,
            period_name=self.name,
            reopened_by=reopened_by
        ))

    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'period_type': self.period_type,
            'status': self.status,
            'currency': self.currency,
            'total_taxable_sales': str(self.total_taxable_sales),
            'total_tax_collected': str(self.total_tax_collected),
            'total_tax_paid': str(self.total_tax_paid),
            'total_tax_due': str(self.total_tax_due),
            'total_tax_credit': str(self.total_tax_credit),
            'net_tax_due': str(self.net_tax_due),
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'version': self.version
        }


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'TaxRule',
    'TaxGroup',
    'TaxExemption',
    'TaxPeriod',
]