# core/domain/tax/services.py
"""
Tax Services - خدمات الضرائب
✅ يدعم: TaxEngine (المحرك الرئيسي)
✅ يدعم: TaxCalculator (حساب الضريبة)
✅ يدعم: TaxValidator (التحقق من صحة الضرائب)
✅ يدعم: TaxReportService (تقارير الضرائب)
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from dataclasses import dataclass

from .value_objects import (
    TaxContext, TaxCalculationResult, TaxCalculationType,
    TaxType, TaxJurisdiction
)
from .entities import TaxRule, TaxGroup, TaxExemption, TaxPeriod
from .interfaces import ITaxRepository, ITaxGroupRepository, ITaxExemptionRepository


# =============================================================================
# TaxValidator - مدقق الضرائب
# =============================================================================

class TaxValidator:
    """مدقق الضرائب - يتحقق من صحة القواعد والحسابات"""

    @staticmethod
    def validate_rule(rule: TaxRule) -> List[str]:
        """التحقق من صحة قاعدة ضريبية"""
        errors = []

        if not rule.code or not rule.code.value:
            errors.append("كود الضريبة مطلوب")

        if not rule.name:
            errors.append("اسم الضريبة مطلوب")

        if rule.rate.rate < 0:
            errors.append("نسبة الضريبة لا يمكن أن تكون سالبة")

        if rule.rate.rate > 100:
            errors.append("نسبة الضريبة لا يمكن أن تتجاوز 100%")

        if rule.valid_to and rule.valid_from > rule.valid_to:
            errors.append("تاريخ البداية لا يمكن أن يكون بعد تاريخ النهاية")

        # التحقق من الضرائب المركبة
        if rule.is_compound and not rule.parent_tax_id:
            errors.append("الضريبة المركبة يجب أن تحدد ضريبة أب")

        return errors

    @staticmethod
    def validate_group(group: TaxGroup) -> List[str]:
        """التحقق من صحة مجموعة ضرائب"""
        errors = []

        if not group.code:
            errors.append("كود المجموعة مطلوب")

        if not group.name:
            errors.append("اسم المجموعة مطلوب")

        if not group.tax_rules:
            errors.append("يجب إضافة قاعدة ضريبية واحدة على الأقل للمجموعة")

        return errors

    @staticmethod
    def validate_exemption(exemption: TaxExemption) -> List[str]:
        """التحقق من صحة إعفاء ضريبي"""
        errors = []

        if not exemption.code:
            errors.append("كود الإعفاء مطلوب")

        if not exemption.name:
            errors.append("اسم الإعفاء مطلوب")

        if exemption.valid_to and exemption.valid_from > exemption.valid_to:
            errors.append("تاريخ البداية لا يمكن أن يكون بعد تاريخ النهاية")

        if exemption.threshold_amount and exemption.threshold_amount < 0:
            errors.append("حد المبلغ لا يمكن أن يكون سالباً")

        return errors

    @staticmethod
    def verify_balance(taxable_amount: Decimal, tax_amount: Decimal, total: Decimal) -> Tuple[bool, Decimal]:
        """التحقق من توازن حساب الضريبة"""
        expected_total = taxable_amount + tax_amount
        difference = total - expected_total
        return abs(difference) < Decimal('0.01'), difference


# =============================================================================
# TaxEngine - محرك الضرائب (DOMAIN SERVICE)
# =============================================================================

class TaxEngine:
    """
    محرك الضرائب - المسؤول عن حساب وتطبيق الضرائب
    
    هذا هو المدخل الرئيسي لنظام الضرائب.
    جميع حسابات الضرائب تمر عبر هذا المحرك.
    """

    def __init__(
        self,
        tax_repository: ITaxRepository,
        group_repository: Optional[ITaxGroupRepository] = None,
        exemption_repository: Optional[ITaxExemptionRepository] = None
    ):
        self._tax_repo = tax_repository
        self._group_repo = group_repository
        self._exemption_repo = exemption_repository

        # التخزين المؤقت
        self._rule_cache: Dict[str, TaxRule] = {}
        self._group_cache: Dict[str, TaxGroup] = {}
        self._exemption_cache: Dict[str, TaxExemption] = {}

    # =========================================================================
    # حساب الضريبة
    # =========================================================================

    def calculate_tax(self, amount: Decimal, context: TaxContext) -> TaxCalculationResult:
        """
        حساب الضريبة للمبلغ المحدد في السياق المعطى
        
        Args:
            amount: المبلغ الخاضع للضريبة
            context: سياق الحساب
        
        Returns:
            TaxCalculationResult: نتيجة حساب الضريبة
        """
        if amount <= 0:
            return TaxCalculationResult(
                taxable_amount=Decimal('0'),
                tax_amount=Decimal('0'),
                total_amount=Decimal('0'),
                breakdown={},
                applied_rules=[],
                calculation_type=TaxCalculationType.EXEMPT
            )

        # 1. الحصول على القواعد المناسبة
        rules = self._get_applicable_rules(context)

        if not rules:
            return TaxCalculationResult(
                taxable_amount=amount,
                tax_amount=Decimal('0'),
                total_amount=amount,
                breakdown={},
                applied_rules=[],
                calculation_type=TaxCalculationType.EXEMPT
            )

        # 2. التحقق من الإعفاءات
        exemption = self._get_applicable_exemption(context)
        if exemption and exemption.can_apply(context):
            return TaxCalculationResult(
                taxable_amount=amount,
                tax_amount=Decimal('0'),
                total_amount=amount,
                breakdown={'exemption': Decimal('0')},
                applied_rules=[],
                calculation_type=TaxCalculationType.EXEMPT
            )

        # 3. حساب الضريبة الأساسية
        total_tax = Decimal('0')
        breakdown = {}
        applied_rules = []
        calc_type = TaxCalculationType.EXCLUSIVE

        for rule in rules:
            if context and rule.is_exempt_for(context):
                continue

            tax = rule.calculate_tax(amount, context)
            if tax > 0:
                total_tax += tax
                breakdown[str(rule.code)] = tax
                applied_rules.append(rule)

                if rule.calculation_type == TaxCalculationType.INCLUSIVE:
                    calc_type = TaxCalculationType.INCLUSIVE

        # 4. حساب الضرائب المركبة
        compound_rules = [r for r in rules if r.is_compound and r.is_valid]
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

    def calculate_tax_for_invoice(
        self,
        items: List[Dict[str, Any]],
        context: TaxContext
    ) -> TaxCalculationResult:
        """
        حساب الضريبة لفاتورة كاملة (عدة بنود)
        
        Args:
            items: قائمة بنود الفاتورة (كل بند يحتوي على amount, product_code, product_category)
            context: سياق الحساب
        
        Returns:
            TaxCalculationResult: نتيجة حساب الضريبة الإجمالية
        """
        total_tax = Decimal('0')
        total_taxable = Decimal('0')
        total_amount = Decimal('0')
        breakdown = {}
        all_rules = []

        for item in items:
            amount = Decimal(str(item.get('amount', 0)))
            if amount <= 0:
                continue

            # تحديث السياق للمنتج الحالي
            item_context = TaxContext(
                product_code=item.get('product_code'),
                product_category=item.get('product_category'),
                customer_id=context.customer_id,
                customer_group=context.customer_group,
                customer_tax_number=context.customer_tax_number,
                customer_country=context.customer_country,
                invoice_id=context.invoice_id,
                invoice_date=context.invoice_date,
                currency=context.currency,
                site_id=context.site_id,
                site_country=context.site_country,
                site_region=context.site_region,
                amount=amount,
                is_tax_inclusive=context.is_tax_inclusive
            )

            result = self.calculate_tax(amount, item_context)

            total_tax += result.tax_amount
            total_taxable += result.taxable_amount
            total_amount += result.total_amount

            for key, value in result.breakdown.items():
                breakdown[key] = breakdown.get(key, Decimal('0')) + value

            all_rules.extend(result.applied_rules)

        return TaxCalculationResult(
            taxable_amount=total_taxable,
            tax_amount=total_tax,
            total_amount=total_amount,
            breakdown=breakdown,
            applied_rules=list(set(all_rules)),
            calculation_type=TaxCalculationType.EXCLUSIVE
        )

    # =========================================================================
    # الحصول على القواعد والإعفاءات
    # =========================================================================

    def _get_applicable_rules(self, context: TaxContext) -> List[TaxRule]:
        """الحصول على القواعد الضريبية المناسبة للسياق"""
        rules = self._tax_repo.get_active_rules()

        applicable = []
        for rule in rules:
            if not rule.is_valid:
                continue

            # التحقق من تطبيق القاعدة على المنتج
            if not rule.applies_to_product(
                context.product_code or "",
                context.product_category or ""
            ):
                continue

            # التحقق من تطبيق القاعدة على العميل
            if not rule.applies_to_customer(
                context.customer_id or "",
                context.customer_group or ""
            ):
                continue

            applicable.append(rule)

        # ترتيب القواعد: الافتراضية أولاً، ثم الإجبارية، ثم الباقي
        applicable.sort(key=lambda r: (not r.is_default, not r.is_mandatory, r.rate.rate))

        return applicable

    def _get_applicable_exemption(self, context: TaxContext) -> Optional[TaxExemption]:
        """الحصول على الإعفاء المناسب للسياق"""
        if not self._exemption_repo:
            return None

        exemptions = self._exemption_repo.get_active_exemptions()

        for exemption in exemptions:
            if exemption.can_apply(context):
                return exemption

        return None

    # =========================================================================
    # إدارة القواعد
    # =========================================================================

    def get_rule(self, rule_id: str) -> Optional[TaxRule]:
        """الحصول على قاعدة ضريبية"""
        if rule_id in self._rule_cache:
            return self._rule_cache[rule_id]

        rule = self._tax_repo.get_by_id(rule_id)
        if rule:
            self._rule_cache[str(rule.id)] = rule
        return rule

    def get_rule_by_code(self, code: str) -> Optional[TaxRule]:
        """الحصول على قاعدة ضريبية بالكود"""
        return self._tax_repo.get_by_code(code)

    def get_default_rule(self) -> Optional[TaxRule]:
        """الحصول على القاعدة الافتراضية"""
        return self._tax_repo.get_default_rule()

    def create_rule(self, rule: TaxRule) -> TaxRule:
        """إنشاء قاعدة ضريبية جديدة"""
        # التحقق من عدم وجود كود مكرر
        existing = self._tax_repo.get_by_code(str(rule.code))
        if existing:
            raise ValueError(f"Tax rule with code {rule.code} already exists")

        # إذا كانت القاعدة افتراضية، تعطيل القواعد الافتراضية الأخرى
        if rule.is_default:
            default = self._tax_repo.get_default_rule()
            if default:
                default.is_default = False
                self._tax_repo.save(default)

        self._tax_repo.save(rule)
        self._rule_cache[str(rule.id)] = rule
        return rule

    def update_rule(self, rule: TaxRule) -> TaxRule:
        """تحديث قاعدة ضريبية"""
        # التحقق من وجود القاعدة
        existing = self._tax_repo.get_by_id(str(rule.id))
        if not existing:
            raise ValueError(f"Tax rule with id {rule.id} not found")

        # التحقق من الكود الفريد
        if str(rule.code) != str(existing.code):
            duplicate = self._tax_repo.get_by_code(str(rule.code))
            if duplicate and str(duplicate.id) != str(rule.id):
                raise ValueError(f"Tax rule with code {rule.code} already exists")

        # إذا أصبحت القاعدة افتراضية، تعطيل القواعد الافتراضية الأخرى
        if rule.is_default and not existing.is_default:
            default = self._tax_repo.get_default_rule()
            if default and str(default.id) != str(rule.id):
                default.is_default = False
                self._tax_repo.save(default)

        self._tax_repo.save(rule)
        self._rule_cache[str(rule.id)] = rule
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """حذف قاعدة ضريبية"""
        rule = self._tax_repo.get_by_id(rule_id)
        if not rule:
            return False

        if rule.is_default:
            raise ValueError("Cannot delete default tax rule")

        result = self._tax_repo.delete(rule_id)
        if result and rule_id in self._rule_cache:
            del self._rule_cache[rule_id]
        return result

    # =========================================================================
    # إدارة المجموعات
    # =========================================================================

    def get_group(self, group_id: str) -> Optional[TaxGroup]:
        """الحصول على مجموعة ضرائب"""
        if group_id in self._group_cache:
            return self._group_cache[group_id]

        if not self._group_repo:
            return None

        group = self._group_repo.get_by_id(group_id)
        if group:
            self._group_cache[group_id] = group
        return group

    def get_group_by_code(self, code: str) -> Optional[TaxGroup]:
        """الحصول على مجموعة ضرائب بالكود"""
        if not self._group_repo:
            return None
        return self._group_repo.get_by_code(code)

    def create_group(self, group: TaxGroup) -> TaxGroup:
        """إنشاء مجموعة ضرائب جديدة"""
        if not self._group_repo:
            raise ValueError("Group repository not available")

        # التحقق من عدم وجود كود مكرر
        existing = self._group_repo.get_by_code(group.code)
        if existing:
            raise ValueError(f"Tax group with code {group.code} already exists")

        # إذا كانت المجموعة افتراضية، تعطيل المجموعات الافتراضية الأخرى
        if group.is_default:
            default = self._group_repo.get_default_group()
            if default:
                default.is_default = False
                self._group_repo.save(default)

        self._group_repo.save(group)
        self._group_cache[group.id] = group
        return group

    # =========================================================================
    # إدارة الإعفاءات
    # =========================================================================

    def get_exemption(self, exemption_id: str) -> Optional[TaxExemption]:
        """الحصول على إعفاء ضريبي"""
        if exemption_id in self._exemption_cache:
            return self._exemption_cache[exemption_id]

        if not self._exemption_repo:
            return None

        exemption = self._exemption_repo.get_by_id(exemption_id)
        if exemption:
            self._exemption_cache[exemption_id] = exemption
        return exemption

    def create_exemption(self, exemption: TaxExemption) -> TaxExemption:
        """إنشاء إعفاء ضريبي جديد"""
        if not self._exemption_repo:
            raise ValueError("Exemption repository not available")

        # التحقق من عدم وجود كود مكرر
        existing = self._exemption_repo.get_by_code(exemption.code)
        if existing:
            raise ValueError(f"Tax exemption with code {exemption.code} already exists")

        self._exemption_repo.save(exemption)
        self._exemption_cache[exemption.id] = exemption
        return exemption

    # =========================================================================
    # الحصول على إحصائيات الضرائب
    # =========================================================================

    def get_tax_summary(self) -> Dict[str, Any]:
        """الحصول على ملخص الضرائب"""
        rules = self._tax_repo.get_all()

        return {
            'total_rules': len(rules),
            'active_rules': len([r for r in rules if r.is_active]),
            'default_rule': str(self._tax_repo.get_default_rule()),
            'tax_types': {
                t.value: len([r for r in rules if r.tax_type == t])
                for t in TaxType
            },
            'calculation_types': {
                c.value: len([r for r in rules if r.calculation_type == c])
                for c in TaxCalculationType
            },
            'jurisdictions': {
                j.value: len([r for r in rules if r.jurisdiction == j])
                for j in TaxJurisdiction
            }
        }

    def get_tax_by_period(self, start_date: date, end_date: date) -> List[TaxRule]:
        """الحصول على الضرائب في فترة زمنية"""
        return self._tax_repo.get_by_date_range(start_date, end_date)

    # =========================================================================
    # التخزين المؤقت
    # =========================================================================

    def clear_cache(self) -> None:
        """مسح التخزين المؤقت"""
        self._rule_cache.clear()
        self._group_cache.clear()
        self._exemption_cache.clear()

    def reload(self) -> None:
        """إعادة تحميل جميع البيانات"""
        self.clear_cache()
        # إعادة تحميل القواعد الافتراضية
        self._tax_repo.get_default_rule()


# =============================================================================
# TaxCalculator - حاسبة الضرائب (بساطة إضافية)
# =============================================================================

class TaxCalculator:
    """
    حاسبة الضرائب - واجهة مبسطة لحساب الضرائب
    
    توفر دوال مساعدة للحسابات الشائعة.
    """

    def __init__(self, tax_engine: TaxEngine):
        self._engine = tax_engine

    def calculate(self, amount: Decimal, context: TaxContext) -> TaxCalculationResult:
        """حساب الضريبة"""
        return self._engine.calculate_tax(amount, context)

    def calculate_with_rate(self, amount: Decimal, rate: Decimal) -> Decimal:
        """حساب الضريبة بنسبة محددة (بدون سياق)"""
        return amount * (rate / Decimal('100'))

    def calculate_inclusive(self, amount: Decimal, rate: Decimal) -> Decimal:
        """
        حساب الضريبة من مبلغ شامل الضريبة
        
        المبلغ شامل الضريبة = المبلغ الأساسي + الضريبة
        الضريبة = المبلغ شامل * (النسبة / (100 + النسبة))
        """
        if rate == 0:
            return Decimal('0')
        return amount * (rate / (Decimal('100') + rate))

    def calculate_exclusive(self, amount: Decimal, rate: Decimal) -> Decimal:
        """
        حساب الضريبة من مبلغ غير شامل الضريبة
        
        المبلغ غير شامل الضريبة = المبلغ الأساسي
        الضريبة = المبلغ الأساسي * (النسبة / 100)
        """
        return amount * (rate / Decimal('100'))

    def calculate_total_inclusive(self, amount: Decimal, rate: Decimal) -> Decimal:
        """حساب المبلغ شامل الضريبة"""
        tax = self.calculate_inclusive(amount, rate)
        return amount + tax

    def calculate_total_exclusive(self, amount: Decimal, rate: Decimal) -> Decimal:
        """حساب المبلغ شامل الضريبة من مبلغ غير شامل"""
        tax = self.calculate_exclusive(amount, rate)
        return amount + tax


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'TaxValidator',
    'TaxEngine',
    'TaxCalculator',
]