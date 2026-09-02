# tests/unit/domain/test_tax_engine.py
"""
Unit Tests for TaxEngine - اختبارات محرك الضرائب الشامل

هذه الاختبارات تتحقق من:
    1. إنشاء القواعد الضريبية (Tax Rules)
    2. أنواع الضرائب المختلفة (VAT, GST, Sales Tax, Excise, Customs, Withholding)
    3. أنماط الحساب (Inclusive, Exclusive, Compound, Zero Rated, Exempt)
    4. حساب الضرائب البسيطة والمركبة
    5. الإعفاءات الضريبية (Exemptions)
    6. مجموعات الضرائب (Tax Groups)
    7. حسابات الفواتير متعددة البنود
    8. التحقق من صحة القواعد
    9. التخزين المؤقت (Caching)
    10. الفترات الضريبية (Tax Periods)
"""

import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from unittest.mock import Mock, MagicMock, call
from typing import List, Optional, Dict, Any

from core.domain.tax.entities import (
    TaxRule, TaxGroup, TaxExemption, TaxPeriod
)
from core.domain.tax.value_objects import (
    TaxId, TaxCode, TaxRate, TaxType, TaxCalculationType,
    TaxJurisdiction, TaxApplicationScope, TaxContext,
    TaxCalculationResult, TaxRuleSummary
)
from core.domain.tax.services import (
    TaxEngine, TaxCalculator, TaxValidator
)
from core.domain.tax.interfaces import (
    ITaxRepository, ITaxGroupRepository, 
    ITaxExemptionRepository, ITaxPeriodRepository
)


# =============================================================================
# FIXTURES (الإعدادات المشتركة للاختبارات)
# =============================================================================

@pytest.fixture
def mock_tax_repo():
    """مستودع ضرائب وهمي"""
    repo = Mock(spec=ITaxRepository)
    repo.get_active_rules = Mock(return_value=[])
    repo.get_default_rule = Mock(return_value=None)
    repo.get_by_code = Mock(return_value=None)
    repo.get_by_id = Mock(return_value=None)
    repo.get_all = Mock(return_value=[])
    repo.save = Mock()
    repo.delete = Mock(return_value=True)
    repo.count_active = Mock(return_value=0)
    return repo


@pytest.fixture
def mock_group_repo():
    """مستودع مجموعات ضرائب وهمي"""
    repo = Mock(spec=ITaxGroupRepository)
    repo.get_default_group = Mock(return_value=None)
    repo.get_by_code = Mock(return_value=None)
    repo.get_all = Mock(return_value=[])
    repo.save = Mock()
    repo.delete = Mock(return_value=True)
    return repo


@pytest.fixture
def mock_exemption_repo():
    """مستودع إعفاءات ضريبية وهمي"""
    repo = Mock(spec=ITaxExemptionRepository)
    repo.get_active_exemptions = Mock(return_value=[])
    repo.get_by_code = Mock(return_value=None)
    repo.get_all = Mock(return_value=[])
    repo.save = Mock()
    repo.delete = Mock(return_value=True)
    return repo


@pytest.fixture
def tax_engine(mock_tax_repo, mock_group_repo, mock_exemption_repo):
    """محرك ضرائب مع مستودعات وهمية"""
    return TaxEngine(
        tax_repository=mock_tax_repo,
        group_repository=mock_group_repo,
        exemption_repository=mock_exemption_repo
    )


@pytest.fixture
def vat_rule():
    """قاعدة ضريبية VAT 15%"""
    return TaxRule.create(
        code="VAT-15",
        name="ضريبة القيمة المضافة 15%",
        rate=Decimal("15"),
        tax_type=TaxType.VAT,
        calculation_type=TaxCalculationType.EXCLUSIVE,
        jurisdiction=TaxJurisdiction.FEDERAL,
        description="ضريبة القيمة المضافة 15%",
        is_default=True
    )


@pytest.fixture
def gst_rule():
    """قاعدة ضريبية GST 10%"""
    return TaxRule.create(
        code="GST-10",
        name="ضريبة السلع والخدمات 10%",
        rate=Decimal("10"),
        tax_type=TaxType.GST,
        calculation_type=TaxCalculationType.EXCLUSIVE
    )


@pytest.fixture
def inclusive_vat_rule():
    """قاعدة ضريبية VAT شاملة 15%"""
    return TaxRule.create(
        code="VAT-15-INCL",
        name="ضريبة القيمة المضافة 15% (شاملة)",
        rate=Decimal("15"),
        calculation_type=TaxCalculationType.INCLUSIVE,
        tax_type=TaxType.VAT
    )


@pytest.fixture
def compound_vat_rule():
    """قاعدة ضريبية مركبة 5%"""
    return TaxRule.create_compound(
        code="VAT-COMPOUND",
        name="ضريبة مركبة 5%",
        rate=Decimal("5"),
        parent_tax_id=TaxId.generate(),
        calculation_order=1
    )


@pytest.fixture
def exempt_rule():
    """قاعدة إعفاء ضريبي"""
    return TaxRule.create_exempt(
        code="EXEMPT",
        name="معفى من الضريبة",
        jurisdiction=TaxJurisdiction.FEDERAL
    )


@pytest.fixture
def zero_rated_rule():
    """قاعدة ضريبة صفرية"""
    return TaxRule.create(
        code="ZERO",
        name="ضريبة صفرية",
        rate=Decimal("0"),
        calculation_type=TaxCalculationType.ZERO_RATED
    )


@pytest.fixture
def tax_group(vat_rule, gst_rule):
    """مجموعة ضرائب تحتوي VAT و GST"""
    return TaxGroup.create(
        code="VAT-GST",
        name="مجموعة VAT و GST",
        tax_rules=[vat_rule, gst_rule],
        is_default=True
    )


# =============================================================================
# TEST CLASS 1: إنشاء القواعد الضريبية (Tax Rules Creation)
# =============================================================================

class TestTaxRuleCreation:
    """اختبارات إنشاء القواعد الضريبية"""
    
    def test_create_vat_rule(self):
        """إنشاء قاعدة VAT"""
        rule = TaxRule.create(
            code="VAT-15",
            name="ضريبة القيمة المضافة 15%",
            rate=Decimal("15"),
            tax_type=TaxType.VAT
        )
        
        assert rule.code.value == "VAT-15"
        assert rule.name == "ضريبة القيمة المضافة 15%"
        assert rule.rate.rate == Decimal("15")
        assert rule.tax_type == TaxType.VAT
        assert rule.calculation_type == TaxCalculationType.EXCLUSIVE
        assert rule.is_active is True
    
    def test_create_gst_rule(self):
        """إنشاء قاعدة GST"""
        rule = TaxRule.create(
            code="GST-10",
            name="ضريبة السلع والخدمات 10%",
            rate=Decimal("10"),
            tax_type=TaxType.GST,
            calculation_type=TaxCalculationType.INCLUSIVE
        )
        
        assert rule.tax_type == TaxType.GST
        assert rule.calculation_type == TaxCalculationType.INCLUSIVE
        assert rule.rate.rate == Decimal("10")
    
    def test_create_sales_tax_rule(self):
        """إنشاء قاعدة ضريبة مبيعات"""
        rule = TaxRule.create(
            code="SALES-8",
            name="ضريبة المبيعات 8%",
            rate=Decimal("8"),
            tax_type=TaxType.SALES_TAX,
            jurisdiction=TaxJurisdiction.STATE
        )
        
        assert rule.tax_type == TaxType.SALES_TAX
        assert rule.jurisdiction == TaxJurisdiction.STATE
    
    def test_create_excise_rule(self):
        """إنشاء قاعدة ضريبة مكوس"""
        rule = TaxRule.create(
            code="EXCISE-20",
            name="ضريبة المكوس 20%",
            rate=Decimal("20"),
            tax_type=TaxType.EXCISE
        )
        
        assert rule.tax_type == TaxType.EXCISE
    
    def test_create_customs_rule(self):
        """إنشاء قاعدة ضريبة جمركية"""
        rule = TaxRule.create(
            code="CUSTOMS-5",
            name="ضريبة جمركية 5%",
            rate=Decimal("5"),
            tax_type=TaxType.CUSTOMS,
            jurisdiction=TaxJurisdiction.INTERNATIONAL
        )
        
        assert rule.tax_type == TaxType.CUSTOMS
        assert rule.jurisdiction == TaxJurisdiction.INTERNATIONAL
    
    def test_create_withholding_rule(self):
        """إنشاء قاعدة ضريبة استقطاع"""
        rule = TaxRule.create(
            code="WITHHOLD-10",
            name="ضريبة الاستقطاع 10%",
            rate=Decimal("10"),
            tax_type=TaxType.WITHHOLDING
        )
        
        assert rule.tax_type == TaxType.WITHHOLDING
    
    def test_create_exempt_rule(self):
        """إنشاء قاعدة إعفاء"""
        rule = TaxRule.create_exempt(
            code="EXEMPT-001",
            name="إعفاء ضريبي"
        )
        
        assert rule.calculation_type == TaxCalculationType.EXEMPT
        assert rule.rate.rate == Decimal("0")
    
    def test_create_compound_rule(self):
        """إنشاء قاعدة ضريبة مركبة"""
        parent_id = TaxId.generate()
        rule = TaxRule.create_compound(
            code="COMPOUND-5",
            name="ضريبة مركبة 5%",
            rate=Decimal("5"),
            parent_tax_id=parent_id,
            calculation_order=2
        )
        
        assert rule.is_compound is True
        assert rule.parent_tax_id == parent_id
        assert rule.compound_calculation_order == 2
    
    def test_rule_generates_events(self):
        """يجب توليد حدث عند إنشاء القاعدة"""
        rule = TaxRule.create(
            code="VAT-15",
            name="VAT 15%",
            rate=Decimal("15")
        )
        
        events = rule.pull_events()
        assert len(events) == 1
        from core.domain.tax.events import TaxRuleCreatedEvent
        assert isinstance(events[0], TaxRuleCreatedEvent)


# =============================================================================
# TEST CLASS 2: حساب الضرائب (Tax Calculations)
# =============================================================================

class TestTaxCalculations:
    """اختبارات حساب الضرائب"""
    
    def test_vat_exclusive_calculation(self, vat_rule):
        """حساب VAT بطريقة Exclusive"""
        tax = vat_rule.calculate_tax(Decimal("1000"))
        assert tax == Decimal("150")  # 15% من 1000
    
    def test_vat_inclusive_calculation(self, inclusive_vat_rule):
        """حساب VAT بطريقة Inclusive"""
        tax = inclusive_vat_rule.calculate_tax(Decimal("1150"))
        assert tax == Decimal("150")  # 1150 * (15/115)
    
    def test_gst_exclusive_calculation(self, gst_rule):
        """حساب GST بطريقة Exclusive"""
        tax = gst_rule.calculate_tax(Decimal("1000"))
        assert tax == Decimal("100")  # 10% من 1000
    
    def test_zero_rated_calculation(self, zero_rated_rule):
        """حساب ضريبة صفرية"""
        tax = zero_rated_rule.calculate_tax(Decimal("1000"))
        assert tax == Decimal("0")
    
    def test_exempt_calculation(self, exempt_rule):
        """حساب إعفاء ضريبي"""
        tax = exempt_rule.calculate_tax(Decimal("1000"))
        assert tax == Decimal("0")
    
    def test_compound_calculation(self, compound_vat_rule):
        """حساب ضريبة مركبة"""
        tax = compound_vat_rule.calculate_tax(Decimal("1000"))
        assert tax == Decimal("50")  # 5% من 1000
    
    def test_calculation_with_rounding(self, vat_rule):
        """حساب مع تقريب"""
        tax = vat_rule.calculate_tax(Decimal("100.33"))
        # 100.33 * 0.15 = 15.0495 -> مقرب إلى 15.05
        assert tax == Decimal("15.05")
    
    def test_calculation_with_context_and_exemption(self, vat_rule):
        """حساب مع سياق وإعفاء"""
        # إضافة إعفاء لمجموعة عميل
        vat_rule.exempt_customer_groups = ["wholesale"]
        
        context = TaxContext(
            amount=Decimal("1000"),
            customer_group="wholesale"
        )
        
        tax = vat_rule.calculate_tax(Decimal("1000"), context)
        assert tax == Decimal("0")  # معفى


# =============================================================================
# TEST CLASS 3: محرك الضرائب (TaxEngine)
# =============================================================================

class TestTaxEngine:
    """اختبارات محرك الضرائب الرئيسي"""
    
    def test_calculate_tax_with_no_rules(self, tax_engine):
        """حساب الضريبة بدون قواعد"""
        context = TaxContext(amount=Decimal("1000"))
        result = tax_engine.calculate_tax(Decimal("1000"), context)
        
        assert result.tax_amount == Decimal("0")
        assert result.total_amount == Decimal("1000")
        assert len(result.applied_rules) == 0
    
    def test_calculate_tax_with_single_rule(self, mock_tax_repo, tax_engine, vat_rule):
        """حساب الضريبة بقاعدة واحدة"""
        mock_tax_repo.get_active_rules.return_value = [vat_rule]
        
        context = TaxContext(amount=Decimal("1000"))
        result = tax_engine.calculate_tax(Decimal("1000"), context)
        
        assert result.tax_amount == Decimal("150")
        assert result.total_amount == Decimal("1150")
        assert len(result.applied_rules) == 1
        assert str(vat_rule.code) in result.breakdown
    
    def test_calculate_tax_with_multiple_rules(self, mock_tax_repo, tax_engine, vat_rule, gst_rule):
        """حساب الضريبة بقواعد متعددة"""
        mock_tax_repo.get_active_rules.return_value = [vat_rule, gst_rule]
        
        context = TaxContext(amount=Decimal("1000"))
        result = tax_engine.calculate_tax(Decimal("1000"), context)
        
        # VAT 15% + GST 10% = 250
        assert result.tax_amount == Decimal("250")
        assert result.total_amount == Decimal("1250")
        assert len(result.applied_rules) == 2
    
    def test_calculate_tax_with_exemption(self, mock_tax_repo, mock_exemption_repo, tax_engine, vat_rule):
        """حساب الضريبة مع إعفاء"""
        mock_tax_repo.get_active_rules.return_value = [vat_rule]
        
        # إنشاء إعفاء
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء عميل VIP",
            customer_ids=["VIP-001"],
            valid_from=date.today()
        )
        mock_exemption_repo.get_active_exemptions.return_value = [exemption]
        
        context = TaxContext(
            amount=Decimal("1000"),
            customer_id="VIP-001"
        )
        result = tax_engine.calculate_tax(Decimal("1000"), context)
        
        # معفى من الضريبة
        assert result.tax_amount == Decimal("0")
        assert result.total_amount == Decimal("1000")
    
    def test_calculate_tax_for_invoice(self, mock_tax_repo, tax_engine, vat_rule):
        """حساب ضريبة لفواتير متعددة البنود"""
        mock_tax_repo.get_active_rules.return_value = [vat_rule]
        
        items = [
            {"product_code": "P1", "product_category": "electronics", "amount": 100},
            {"product_code": "P2", "product_category": "clothing", "amount": 200},
            {"product_code": "P3", "product_category": "food", "amount": 50}
        ]
        context = TaxContext(amount=Decimal("350"))
        
        result = tax_engine.calculate_tax_for_invoice(items, context)
        
        # 15% على 350 = 52.5
        assert result.tax_amount == Decimal("52.5")
        assert result.total_amount == Decimal("402.5")
    
    def test_calculate_tax_with_compound_rules(self, mock_tax_repo, tax_engine, vat_rule, compound_vat_rule):
        """حساب الضريبة مع قواعد مركبة"""
        mock_tax_repo.get_active_rules.return_value = [vat_rule, compound_vat_rule]
        
        context = TaxContext(amount=Decimal("1000"))
        result = tax_engine.calculate_tax(Decimal("1000"), context)
        
        # VAT 15% على 1000 = 150
        # مركبة 5% على (1000 + 150) = 57.5
        # المجموع = 207.5
        assert result.tax_amount == Decimal("207.5")
    
    def test_calculate_tax_respects_rule_priority(self, mock_tax_repo, tax_engine, vat_rule, gst_rule):
        """يجب احترام ترتيب القواعد"""
        # جعل vat_rule إلزامية أولاً
        vat_rule.is_default = True
        mock_tax_repo.get_active_rules.return_value = [gst_rule, vat_rule]
        
        context = TaxContext(amount=Decimal("1000"))
        result = tax_engine.calculate_tax(Decimal("1000"), context)
        
        # يجب أن تكون VAT مطبقة (لأنها default)
        # ولكن كلتا القاعدتين تطبقان
        assert result.tax_amount == Decimal("250")
    
    def test_calculate_tax_with_application_scope(self, mock_tax_repo, tax_engine, vat_rule):
        """حساب الضريبة مع نطاق تطبيق"""
        # قاعدة تنطبق فقط على الإلكترونيات
        vat_rule.application_scope = TaxApplicationScope.PRODUCT_CATEGORY
        vat_rule.applies_to = ["electronics"]
        mock_tax_repo.get_active_rules.return_value = [vat_rule]
        
        # منتج إلكترونيات - يجب أن تطبق الضريبة
        context = TaxContext(
            amount=Decimal("1000"),
            product_category="electronics"
        )
        result = tax_engine.calculate_tax(Decimal("1000"), context)
        assert result.tax_amount == Decimal("150")
        
        # منتج غير إلكترونيات - لا تطبق الضريبة
        context2 = TaxContext(
            amount=Decimal("1000"),
            product_category="clothing"
        )
        result2 = tax_engine.calculate_tax(Decimal("1000"), context2)
        assert result2.tax_amount == Decimal("0")


# =============================================================================
# TEST CLASS 4: الإعفاءات الضريبية (Tax Exemptions)
# =============================================================================

class TestTaxExemptions:
    """اختبارات الإعفاءات الضريبية"""
    
    def test_create_exemption(self):
        """إنشاء إعفاء ضريبي"""
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء عملاء VIP",
            customer_ids=["VIP-001", "VIP-002"],
            valid_from=date.today(),
            valid_to=date.today() + timedelta(days=365)
        )
        
        assert exemption.code == "EXEMPT-001"
        assert len(exemption.customer_ids) == 2
        assert "VIP-001" in exemption.customer_ids
        assert exemption.is_valid is True
    
    def test_exemption_applies_to_customer(self):
        """التحقق من تطبيق الإعفاء على عميل"""
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء عملاء VIP",
            customer_ids=["VIP-001"]
        )
        
        assert exemption.applies_to_customer("VIP-001", "") is True
        assert exemption.applies_to_customer("VIP-002", "") is False
    
    def test_exemption_applies_to_customer_group(self):
        """التحقق من تطبيق الإعفاء على مجموعة عملاء"""
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء عملاء الجملة",
            customer_groups=["wholesale"]
        )
        
        assert exemption.applies_to_customer("", "wholesale") is True
        assert exemption.applies_to_customer("", "retail") is False
    
    def test_exemption_applies_to_product(self):
        """التحقق من تطبيق الإعفاء على منتج"""
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء المنتجات الغذائية",
            product_categories=["food"]
        )
        
        assert exemption.applies_to_product("", "food") is True
        assert exemption.applies_to_product("", "electronics") is False
    
    def test_exemption_applies_to_amount(self):
        """التحقق من تطبيق الإعفاء على المبلغ"""
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء المعاملات الصغيرة",
            threshold_amount=Decimal("100")
        )
        
        assert exemption.applies_to_amount(Decimal("50")) is True
        assert exemption.applies_to_amount(Decimal("150")) is False
    
    def test_exemption_expiry(self):
        """التحقق من انتهاء صلاحية الإعفاء"""
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء منتهي",
            valid_from=date.today() - timedelta(days=30),
            valid_to=date.today() - timedelta(days=1)
        )
        
        assert exemption.is_valid is False
    
    def test_exemption_can_apply_full(self):
        """التحقق الشامل من إمكانية تطبيق الإعفاء"""
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء شامل",
            customer_ids=["VIP-001"],
            product_categories=["food"],
            threshold_amount=Decimal("500")
        )
        
        context = TaxContext(
            customer_id="VIP-001",
            product_category="food",
            amount=Decimal("100")
        )
        
        assert exemption.can_apply(context) is True
        
        # عميل غير VIP
        context2 = TaxContext(
            customer_id="REG-001",
            product_category="food",
            amount=Decimal("100")
        )
        assert exemption.can_apply(context2) is False
        
        # منتج غير غذائي
        context3 = TaxContext(
            customer_id="VIP-001",
            product_category="electronics",
            amount=Decimal("100")
        )
        assert exemption.can_apply(context3) is False


# =============================================================================
# TEST CLASS 5: مجموعات الضرائب (Tax Groups)
# =============================================================================

class TestTaxGroups:
    """اختبارات مجموعات الضرائب"""
    
    def test_create_tax_group(self, vat_rule, gst_rule):
        """إنشاء مجموعة ضرائب"""
        group = TaxGroup.create(
            code="VAT-GST",
            name="مجموعة VAT و GST",
            tax_rules=[vat_rule, gst_rule],
            is_default=True
        )
        
        assert group.code == "VAT-GST"
        assert len(group.tax_rules) == 2
        assert group.is_default is True
    
    def test_calculate_tax_from_group(self, vat_rule, gst_rule):
        """حساب الضريبة من مجموعة"""
        group = TaxGroup.create(
            code="VAT-GST",
            name="مجموعة VAT و GST",
            tax_rules=[vat_rule, gst_rule]
        )
        
        result = group.calculate_tax(Decimal("1000"))
        
        # VAT 15% = 150, GST 10% = 100, المجموع = 250
        assert result.tax_amount == Decimal("250")
        assert result.total_amount == Decimal("1250")
    
    def test_add_rule_to_group(self, vat_rule):
        """إضافة قاعدة إلى مجموعة"""
        group = TaxGroup.create(
            code="VAT-ONLY",
            name="مجموعة VAT فقط",
            tax_rules=[vat_rule]
        )
        
        assert len(group.tax_rules) == 1
        
        new_rule = TaxRule.create(
            code="GST-10",
            name="GST 10%",
            rate=Decimal("10"),
            tax_type=TaxType.GST
        )
        
        group.add_rule(new_rule)
        assert len(group.tax_rules) == 2
    
    def test_remove_rule_from_group(self, vat_rule, gst_rule):
        """إزالة قاعدة من مجموعة"""
        group = TaxGroup.create(
            code="VAT-GST",
            name="مجموعة VAT و GST",
            tax_rules=[vat_rule, gst_rule]
        )
        
        removed = group.remove_rule(str(vat_rule.id))
        assert removed is True
        assert len(group.tax_rules) == 1
        assert group.tax_rules[0].code == gst_rule.code


# =============================================================================
# TEST CLASS 6: حاسبة الضرائب المساعدة (TaxCalculator)
# =============================================================================

class TestTaxCalculator:
    """اختبارات حاسبة الضرائب المساعدة"""
    
    def test_calculate_exclusive(self):
        """حساب الضريبة بطريقة Exclusive"""
        calculator = TaxCalculator(None)
        tax = calculator.calculate_exclusive(Decimal("1000"), Decimal("15"))
        assert tax == Decimal("150")
    
    def test_calculate_inclusive(self):
        """حساب الضريبة بطريقة Inclusive"""
        calculator = TaxCalculator(None)
        tax = calculator.calculate_inclusive(Decimal("1150"), Decimal("15"))
        assert tax == Decimal("150")
    
    def test_calculate_total_exclusive(self):
        """حساب الإجمالي بطريقة Exclusive"""
        calculator = TaxCalculator(None)
        total = calculator.calculate_total_exclusive(Decimal("1000"), Decimal("15"))
        assert total == Decimal("1150")
    
    def test_calculate_total_inclusive(self):
        """حساب الإجمالي بطريقة Inclusive"""
        calculator = TaxCalculator(None)
        total = calculator.calculate_total_inclusive(Decimal("1150"), Decimal("15"))
        assert total == Decimal("1150")
    
    def test_calculate_with_zero_rate(self):
        """حساب الضريبة بنسبة صفر"""
        calculator = TaxCalculator(None)
        tax = calculator.calculate_exclusive(Decimal("1000"), Decimal("0"))
        assert tax == Decimal("0")
    
    def test_calculate_with_negative_amount(self):
        """حساب الضريبة بمبلغ سالب (يجب أن يرفض)"""
        # ملاحظة: هذا يعتمد على تنفيذ TaxEngine
        # يجب أن تكون هناك معالجة للمبالغ السالبة
        pass


# =============================================================================
# TEST CLASS 7: مدقق الضرائب (TaxValidator)
# =============================================================================

class TestTaxValidator:
    """اختبارات مدقق الضرائب"""
    
    def test_validate_valid_rule(self, vat_rule):
        """التحقق من قاعدة صالحة"""
        errors = TaxValidator.validate_rule(vat_rule)
        assert len(errors) == 0
    
    def test_validate_rule_without_code(self):
        """التحقق من قاعدة بدون كود"""
        rule = TaxRule.create(
            code="",
            name="VAT 15%",
            rate=Decimal("15")
        )
        errors = TaxValidator.validate_rule(rule)
        assert len(errors) > 0
        assert any("كود" in e for e in errors)
    
    def test_validate_rule_without_name(self):
        """التحقق من قاعدة بدون اسم"""
        rule = TaxRule.create(
            code="VAT-15",
            name="",
            rate=Decimal("15")
        )
        errors = TaxValidator.validate_rule(rule)
        assert len(errors) > 0
        assert any("اسم" in e for e in errors)
    
    def test_validate_rule_with_negative_rate(self):
        """التحقق من قاعدة بنسبة سالبة"""
        rule = TaxRule.create(
            code="VAT-NEG",
            name="VAT سالبة",
            rate=Decimal("-15")
        )
        errors = TaxValidator.validate_rule(rule)
        assert len(errors) > 0
        assert any("سالبة" in e for e in errors)
    
    def test_validate_rule_with_rate_over_100(self):
        """التحقق من قاعدة بنسبة تتجاوز 100%"""
        rule = TaxRule.create(
            code="VAT-150",
            name="VAT 150%",
            rate=Decimal("150")
        )
        errors = TaxValidator.validate_rule(rule)
        assert len(errors) > 0
        assert any("تتجاوز" in e for e in errors)
    
    def test_validate_valid_group(self, vat_rule, gst_rule):
        """التحقق من مجموعة صالحة"""
        group = TaxGroup.create(
            code="VAT-GST",
            name="VAT و GST",
            tax_rules=[vat_rule, gst_rule]
        )
        errors = TaxValidator.validate_group(group)
        assert len(errors) == 0
    
    def test_validate_group_without_rules(self):
        """التحقق من مجموعة بدون قواعد"""
        group = TaxGroup.create(
            code="EMPTY",
            name="مجموعة فارغة",
            tax_rules=[]
        )
        errors = TaxValidator.validate_group(group)
        assert len(errors) > 0
        assert any("قاعدة" in e for e in errors)
    
    def test_validate_valid_exemption(self):
        """التحقق من إعفاء صالح"""
        exemption = TaxExemption.create(
            code="EXEMPT-001",
            name="إعفاء VIP"
        )
        errors = TaxValidator.validate_exemption(exemption)
        assert len(errors) == 0
    
    def test_validate_exemption_without_code(self):
        """التحقق من إعفاء بدون كود"""
        exemption = TaxExemption.create(
            code="",
            name="إعفاء VIP"
        )
        errors = TaxValidator.validate_exemption(exemption)
        assert len(errors) > 0
        assert any("كود" in e for e in errors)
    
    def test_verify_balance_correct(self):
        """التحقق من توازن صحيح"""
        is_balanced, difference = TaxValidator.verify_balance(
            taxable_amount=Decimal("1000"),
            tax_amount=Decimal("150"),
            total=Decimal("1150")
        )
        assert is_balanced is True
        assert difference < Decimal("0.01")
    
    def test_verify_balance_incorrect(self):
        """التحقق من توازن خاطئ"""
        is_balanced, difference = TaxValidator.verify_balance(
            taxable_amount=Decimal("1000"),
            tax_amount=Decimal("150"),
            total=Decimal("1200")
        )
        assert is_balanced is False
        assert difference == Decimal("50")


# =============================================================================
# TEST CLASS 8: إدارة القواعد الضريبية (Rule Management)
# =============================================================================

class TestTaxRuleManagement:
    """اختبارات إدارة القواعد الضريبية"""
    
    def test_activate_rule(self, vat_rule):
        """تفعيل قاعدة"""
        vat_rule.is_active = False
        vat_rule.activate(activated_by="admin")
        assert vat_rule.is_active is True
    
    def test_deactivate_rule(self, vat_rule):
        """تعطيل قاعدة"""
        vat_rule.is_active = True
        vat_rule.deactivate(deactivated_by="admin")
        assert vat_rule.is_active is False
    
    def test_update_rule(self, vat_rule):
        """تحديث قاعدة"""
        old_name = vat_rule.name
        vat_rule.update(
            name="VAT 15% جديد",
            rate=Decimal("16"),
            updated_by="admin"
        )
        
        assert vat_rule.name == "VAT 15% جديد"
        assert vat_rule.rate.rate == Decimal("16")
        assert vat_rule.version > 1
    
    def test_update_rule_creates_event(self, vat_rule):
        """تحديث القاعدة يخلق حدثاً"""
        vat_rule.update(name="VAT جديد", updated_by="admin")
        
        events = vat_rule.pull_events()
        assert len(events) > 0
        from core.domain.tax.events import TaxRuleUpdatedEvent
        assert isinstance(events[0], TaxRuleUpdatedEvent)
    
    def test_rule_is_valid(self, vat_rule):
        """التحقق من صلاحية القاعدة"""
        assert vat_rule.is_valid is True
    
    def test_rule_expired(self):
        """قاعدة منتهية الصلاحية"""
        rule = TaxRule.create(
            code="VAT-OLD",
            name="VAT قديم",
            rate=Decimal("15"),
            valid_from=date.today() - timedelta(days=30),
            valid_to=date.today() - timedelta(days=1)
        )
        assert rule.is_valid is False
    
    def test_rule_future(self):
        """قاعدة مستقبلية"""
        rule = TaxRule.create(
            code="VAT-FUTURE",
            name="VAT مستقبل",
            rate=Decimal("15"),
            valid_from=date.today() + timedelta(days=30)
        )
        assert rule.is_valid is False


# =============================================================================
# TEST CLASS 9: الفترات الضريبية (Tax Periods)
# =============================================================================

class TestTaxPeriods:
    """اختبارات الفترات الضريبية"""
    
    def test_create_tax_period(self):
        """إنشاء فترة ضريبية"""
        period = TaxPeriod.create(
            code="Q1-2024",
            name="الربع الأول 2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31),
            period_type="quarterly"
        )
        
        assert period.code == "Q1-2024"
        assert period.start_date == date(2024, 1, 1)
        assert period.end_date == date(2024, 3, 31)
        assert period.status == "open"
    
    def test_close_period(self):
        """إغلاق فترة ضريبية"""
        period = TaxPeriod.create(
            code="Q1-2024",
            name="الربع الأول 2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31)
        )
        
        period.close(closed_by="admin")
        assert period.status == "closed"
    
    def test_reopen_period(self):
        """إعادة فتح فترة ضريبية"""
        period = TaxPeriod.create(
            code="Q1-2024",
            name="الربع الأول 2024",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 3, 31)
        )
        
        period.close(closed_by="admin")
        period.reopen(reopened_by="admin")
        assert period.status == "open"


# =============================================================================
# TEST CLASS 10: التخزين المؤقت (Caching)
# =============================================================================

class TestTaxEngineCache:
    """اختبارات التخزين المؤقت لمحرك الضرائب"""
    
    def test_cache_clearing(self, tax_engine, vat_rule):
        """مسح التخزين المؤقت"""
        tax_engine._rule_cache["test"] = vat_rule
        assert len(tax_engine._rule_cache) > 0
        
        tax_engine.clear_cache()
        assert len(tax_engine._rule_cache) == 0
    
    def test_cache_reload(self, tax_engine, mock_tax_repo, vat_rule):
        """إعادة تحميل التخزين المؤقت"""
        mock_tax_repo.get_active_rules.return_value = [vat_rule]
        
        tax_engine.reload()
        # يجب أن تكون القواعد محملة في الكاش
        # يمكن التحقق من ذلك عبر استدعاء get_active_rules


# =============================================================================
# TEST CLASS 11: تكامل TaxEngine مع TaxGroupRepository
# =============================================================================

class TestTaxEngineWithGroupRepository:
    """اختبارات تكامل TaxEngine مع مستودع المجموعات"""
    
    def test_get_group(self, mock_group_repo, tax_engine, tax_group):
        """الحصول على مجموعة ضرائب"""
        mock_group_repo.get_by_id.return_value = tax_group
        
        group = tax_engine.get_group("test-id")
        assert group.code == "VAT-GST"
        assert len(group.tax_rules) == 2
    
    def test_get_group_by_code(self, mock_group_repo, tax_engine, tax_group):
        """الحصول على مجموعة ضرائب بالكود"""
        mock_group_repo.get_by_code.return_value = tax_group
        
        group = tax_engine.get_group_by_code("VAT-GST")
        assert group is not None
        assert group.code == "VAT-GST"
    
    def test_create_group(self, mock_group_repo, tax_engine, vat_rule, gst_rule):
        """إنشاء مجموعة ضرائب جديدة"""
        group = TaxGroup.create(
            code="VAT-GST",
            name="VAT و GST",
            tax_rules=[vat_rule, gst_rule]
        )
        
        mock_group_repo.save = Mock()
        tax_engine.create_group(group)
        mock_group_repo.save.assert_called_once_with(group)


# =============================================================================
# تشغيل الاختبارات
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])