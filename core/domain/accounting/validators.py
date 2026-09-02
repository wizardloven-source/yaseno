"""
Posting Validator - التحقق من صحة القيود المحاسبية
الإصدار المُصحَّح - v2.0.0

✅ إضافة التحقق من توازن القيد
✅ إضافة التحقق من العملات المتعددة
✅ إضافة التحقق من وجود الحسابات
✅ إضافة التحقق من نشاط الحسابات
✅ إضافة التحقق من نوع الحساب
✅ إضافة التحقق من صلاحية الفترة المالية
✅ إضافة التحقق من الحسابات الرئيسية
✅ إضافة التحقق من صحة العملة
✅ إضافة التحقق من مراكز التكلفة
✅ إضافة التحقق من الرموز الضريبية
"""

from typing import List, Optional, Dict, Any
from decimal import Decimal
import logging

from .entities import JournalEntry, JournalLine
from core.domain.shared.value_objects import AccountCode, Money
from core.domain.accounting.exceptions import InvalidAccountError

logger = logging.getLogger(__name__)


# =============================================================================
# إعدادات العملات المدعومة (يمكن حقنها من قاعدة البيانات)
# =============================================================================

SUPPORTED_CURRENCIES = {
    'USD', 'EUR', 'LBP', 'GBP', 'AED', 'SAR', 
    'JOD', 'KWD', 'BHD', 'IQD', 'LYD', 'TND', 'OMR'
}

CURRENCY_DECIMAL_PLACES = {
    'LBP': 0, 'USD': 2, 'EUR': 2, 'GBP': 2,
    'AED': 2, 'SAR': 2, 'JOD': 3, 'KWD': 3,
    'BHD': 3, 'IQD': 3, 'LYD': 3, 'TND': 3, 'OMR': 3,
}


# =============================================================================
# PostingValidator - المدقق المحسّن بالكامل
# =============================================================================

class PostingValidator:
    """
    مدقق صحة القيود المحاسبية - النسخة المتقدمة
    
    يقوم بالتحقق من:
        1. البيانات الأساسية (الوصف، عدد الأسطر)
        2. صحة المبالغ (غير سالبة، غير صفرية)
        3. توازن القيد (لكل عملة على حدة)
        4. وجود الحسابات وفعاليتها
        5. نوع الحساب (مدين/دائن)
        6. صلاحية الفترة المالية
        7. الحسابات الرئيسية
        8. صحة العملة
        9. مراكز التكلفة (اختياري)
        10. الرموز الضريبية (اختياري)
    """
    
    # =========================================================================
    # إعدادات قابلة للحقن
    # =========================================================================
    
    _account_repo = None
    _period_repo = None
    _fiscal_service = None
    _center_repo = None
    _tax_repo = None
    
    @classmethod
    def configure(
        cls,
        account_repo=None,
        period_repo=None,
        fiscal_service=None,
        center_repo=None,
        tax_repo=None
    ):
        """
        تهيئة المدقق بالتبعيات المطلوبة
        
        Args:
            account_repo: مستودع الحسابات
            period_repo: مستودع الفترات المالية
            fiscal_service: خدمة السنة المالية
            center_repo: مستودع مراكز التكلفة
            tax_repo: مستودع الضرائب
        """
        cls._account_repo = account_repo
        cls._period_repo = period_repo
        cls._fiscal_service = fiscal_service
        cls._center_repo = center_repo
        cls._tax_repo = tax_repo
        logger.info("PostingValidator configured successfully")
    
    # =========================================================================
    # الدالة الرئيسية للتحقق
    # =========================================================================
    
    @classmethod
    def validate_journal_entry(
        cls, 
        entry: JournalEntry,
        check_accounts: bool = True,
        check_period: bool = True,
        check_centers: bool = True,
        check_tax: bool = True
    ) -> List[str]:
        """
        التحقق من صحة القيد المحاسبي
        
        Args:
            entry: القيد المراد التحقق منه
            check_accounts: التحقق من الحسابات
            check_period: التحقق من الفترة المالية
            check_centers: التحقق من مراكز التكلفة
            check_tax: التحقق من الرموز الضريبية
        
        Returns:
            List[str]: قائمة بأخطاء التحقق (فارغة إذا كان صحيحاً)
        """
        errors = []
        
        # 1. التحقق من البيانات الأساسية
        errors.extend(cls._validate_basic(entry))
        
        if errors:
            return errors  # إذا فشلت التحققات الأساسية، لا نكمل
        
        # 2. التحقق من المبالغ
        errors.extend(cls._validate_amounts(entry))
        
        # 3. التحقق من التوازن (مع دعم العملات المتعددة)
        errors.extend(cls._validate_balance(entry))
        
        # 4. التحقق من العملات
        errors.extend(cls._validate_currencies(entry))
        
        # 5. التحقق من الحسابات (إذا كان مطلوباً)
        if check_accounts:
            errors.extend(cls._validate_accounts(entry))
        
        # 6. التحقق من الفترة المالية (إذا كان مطلوباً)
        if check_period:
            errors.extend(cls._validate_period(entry))
        
        # 7. التحقق من مراكز التكلفة (إذا كان مطلوباً)
        if check_centers:
            errors.extend(cls._validate_cost_centers(entry))
        
        # 8. التحقق من الرموز الضريبية (إذا كان مطلوباً)
        if check_tax:
            errors.extend(cls._validate_tax_codes(entry))
        
        return errors
    
    # =========================================================================
    # دوال التحقق الفردية
    # =========================================================================
    
    @classmethod
    def _validate_basic(cls, entry: JournalEntry) -> List[str]:
        """
        التحقق من البيانات الأساسية للقيد
        """
        errors = []
        
        # التحقق من الوصف
        if not entry.description or not entry.description.strip():
            errors.append("❌ Description is required for journal entry")
        elif len(entry.description) > 500:
            errors.append(f"❌ Description too long: {len(entry.description)} > 500 characters")
        
        # التحقق من عدد الأسطر
        if len(entry.lines) < 2:
            errors.append("❌ Entry requires at least 2 lines (double-entry accounting)")
        elif len(entry.lines) > 100:
            errors.append(f"❌ Too many lines: {len(entry.lines)} > 100")
        
        # التحقق من التاريخ
        if not entry.date:
            errors.append("❌ Entry date is required")
        
        return errors
    
    @classmethod
    def _validate_amounts(cls, entry: JournalEntry) -> List[str]:
        """
        التحقق من صحة المبالغ في الأسطر
        """
        errors = []
        
        for i, line in enumerate(entry.lines):
            line_num = i + 1
            
            # التحقق من المبالغ غير السالبة
            if line.debit.amount < 0:
                errors.append(f"❌ Line {line_num}: Debit amount cannot be negative ({line.debit.amount})")
            
            if line.credit.amount < 0:
                errors.append(f"❌ Line {line_num}: Credit amount cannot be negative ({line.credit.amount})")
            
            # التحقق من أن السطر يحتوي على مبلغ
            if line.debit.amount == 0 and line.credit.amount == 0:
                errors.append(f"❌ Line {line_num}: Line must have either debit or credit amount")
            
            # التحقق من أن السطر ليس مديناً ودائناً في نفس الوقت
            if line.debit.amount > 0 and line.credit.amount > 0:
                errors.append(f"❌ Line {line_num}: Line cannot have both debit and credit amounts")
            
            # التحقق من صحة المبلغ (ليس كبيراً جداً)
            max_amount = Decimal('9999999999.99')
            if line.debit.amount > max_amount or line.credit.amount > max_amount:
                errors.append(f"❌ Line {line_num}: Amount exceeds maximum allowed ({max_amount})")
        
        return errors
    
    @classmethod
    def _validate_balance(cls, entry: JournalEntry) -> List[str]:
        """
        ✅ التحقق من توازن القيد (لكل عملة على حدة)
        """
        errors = []
        
        # تجميع المبالغ حسب العملة
        currency_totals: Dict[str, Dict[str, Decimal]] = {}
        
        for line in entry.lines:
            currency = line.currency.upper().strip()
            
            if currency not in currency_totals:
                currency_totals[currency] = {
                    'debit': Decimal('0'),
                    'credit': Decimal('0'),
                    'balance': Decimal('0')
                }
            
            currency_totals[currency]['debit'] += line.debit.amount
            currency_totals[currency]['credit'] += line.credit.amount
            currency_totals[currency]['balance'] = (
                currency_totals[currency]['debit'] - currency_totals[currency]['credit']
            )
        
        # التحقق من توازن كل عملة
        for currency, totals in currency_totals.items():
            if abs(totals['balance']) > Decimal('0.01'):
                errors.append(
                    f"❌ Currency {currency} is unbalanced: "
                    f"Debit {totals['debit']} vs Credit {totals['credit']} "
                    f"(Difference: {abs(totals['balance'])})"
                )
        
        return errors
    
    @classmethod
    def _validate_currencies(cls, entry: JournalEntry) -> List[str]:
        """
        ✅ التحقق من صحة العملات المستخدمة
        """
        errors = []
        
        for i, line in enumerate(entry.lines):
            currency = line.currency.upper().strip()
            
            # التحقق من أن العملة مدعومة
            if currency not in SUPPORTED_CURRENCIES:
                errors.append(
                    f"❌ Line {i+1}: Unsupported currency '{currency}'. "
                    f"Supported: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
                )
            
            # التحقق من صحة العملة (3 أحرف)
            if len(currency) != 3:
                errors.append(f"❌ Line {i+1}: Currency code must be 3 characters, got '{currency}'")
        
        return errors
    
    @classmethod
    def _validate_accounts(cls, entry: JournalEntry) -> List[str]:
        """
        ✅ التحقق من وجود الحسابات وفعاليتها ونوعها
        """
        errors = []
        
        if not cls._account_repo:
            logger.warning("Account repository not configured, skipping account validation")
            return errors
        
        for i, line in enumerate(entry.lines):
            account_code = str(line.account_code)
            
            # التحقق من وجود الحساب
            account = cls._account_repo.get_by_code(line.account_code)
            if not account:
                errors.append(f"❌ Line {i+1}: Account '{account_code}' does not exist")
                continue
            
            # التحقق من أن الحساب نشط
            if not account.is_active:
                errors.append(f"❌ Line {i+1}: Account '{account_code}' is inactive")
            
            # ✅ التحقق من أن الحساب ليس حساباً رئيسياً (Parent Account)
            if getattr(account, 'is_parent', False) or getattr(account, 'can_post', True) is False:
                errors.append(
                    f"❌ Line {i+1}: Account '{account_code}' is a parent account. "
                    "Direct posting is only allowed on leaf accounts."
                )
            
            # ✅ التحقق من نوع الحساب يتناسب مع نوع الحركة
            if line.is_debit and not cls._can_be_debited(account):
                errors.append(
                    f"❌ Line {i+1}: Account '{account_code}' of type '{account.account_type}' "
                    "cannot be debited"
                )
            
            if line.is_credit and not cls._can_be_credited(account):
                errors.append(
                    f"❌ Line {i+1}: Account '{account_code}' of type '{account.account_type}' "
                    "cannot be credited"
                )
        
        return errors
    
    @classmethod
    def _can_be_debited(cls, account) -> bool:
        """
        التحقق مما إذا كان الحساب يمكن أن يكون مديناً
        """
        # الحسابات التي يمكن أن تكون مدينة: أصول، مصروفات
        account_type = getattr(account, 'account_type', '').lower()
        return account_type in ['asset', 'expense', 'cost_of_goods_sold']
    
    @classmethod
    def _can_be_credited(cls, account) -> bool:
        """
        التحقق مما إذا كان الحساب يمكن أن يكون دائناً
        """
        # الحسابات التي يمكن أن تكون دائنة: خصوم، حقوق ملكية، إيرادات
        account_type = getattr(account, 'account_type', '').lower()
        return account_type in ['liability', 'equity', 'revenue', 'income']
    
    @classmethod
    def _validate_period(cls, entry: JournalEntry) -> List[str]:
        """
        ✅ التحقق من صلاحية الفترة المالية
        """
        errors = []
        
        if not entry.date:
            return errors
        
        entry_date = entry.date.date()
        
        # 1. التحقق من أن التاريخ ليس في المستقبل
        from datetime import date
        if entry_date > date.today():
            errors.append(f"❌ Entry date '{entry_date}' cannot be in the future")
        
        # 2. التحقق من الفترة المالية
        if cls._fiscal_service:
            is_valid, error_msg = cls._fiscal_service.validate_date_for_posting(entry_date)
            if not is_valid:
                errors.append(f"❌ {error_msg}")
        
        # 3. التحقق من الفترة عبر المستودع (للتوافق)
        elif cls._period_repo:
            try:
                period = cls._period_repo.get_period_by_date(entry_date)
                if not period:
                    errors.append(f"❌ No fiscal period found for date '{entry_date}'")
                elif period.is_closed:
                    errors.append(f"❌ Cannot post to closed period: {period.name}")
            except Exception as e:
                errors.append(f"❌ Period validation error: {str(e)}")
        
        return errors
    
    @classmethod
    def _validate_cost_centers(cls, entry: JournalEntry) -> List[str]:
        """
        ✅ التحقق من صحة مراكز التكلفة
        """
        errors = []
        
        if not cls._center_repo:
            return errors
        
        for i, line in enumerate(entry.lines):
            # التحقق من مركز التكلفة إذا كان موجوداً
            if hasattr(line, 'cost_center') and line.cost_center:
                center = cls._center_repo.get_by_code(line.cost_center)
                if not center:
                    errors.append(
                        f"❌ Line {i+1}: Cost center '{line.cost_center}' does not exist"
                    )
                elif not center.is_active:
                    errors.append(
                        f"❌ Line {i+1}: Cost center '{line.cost_center}' is inactive"
                    )
            
            # التحقق من مركز الربح إذا كان موجوداً
            if hasattr(line, 'profit_center') and line.profit_center:
                center = cls._center_repo.get_by_code(line.profit_center)
                if not center:
                    errors.append(
                        f"❌ Line {i+1}: Profit center '{line.profit_center}' does not exist"
                    )
                elif not center.is_active:
                    errors.append(
                        f"❌ Line {i+1}: Profit center '{line.profit_center}' is inactive"
                    )
        
        return errors
    
    @classmethod
    def _validate_tax_codes(cls, entry: JournalEntry) -> List[str]:
        """
        ✅ التحقق من صحة الرموز الضريبية
        """
        errors = []
        
        if not cls._tax_repo:
            return errors
        
        for i, line in enumerate(entry.lines):
            if hasattr(line, 'tax_code') and line.tax_code:
                tax_rule = cls._tax_repo.get_by_code(line.tax_code)
                if not tax_rule:
                    errors.append(
                        f"❌ Line {i+1}: Tax code '{line.tax_code}' does not exist"
                    )
                elif not tax_rule.is_active:
                    errors.append(
                        f"❌ Line {i+1}: Tax code '{line.tax_code}' is inactive"
                    )
        
        return errors
    
    # =========================================================================
    # دوال مساعدة إضافية
    # =========================================================================
    
    @classmethod
    def is_valid_entry(cls, entry: JournalEntry) -> bool:
        """
        التحقق السريع من صحة القيد (بدون تفاصيل)
        
        Returns:
            bool: True إذا كان القيد صحيحاً
        """
        errors = cls.validate_journal_entry(entry)
        return len(errors) == 0
    
    @classmethod
    def get_validation_summary(cls, entry: JournalEntry) -> Dict[str, Any]:
        """
        الحصول على ملخص التحقق من القيد
        
        Returns:
            Dict: ملخص شامل للتحقق
        """
        errors = cls.validate_journal_entry(entry)
        
        return {
            "is_valid": len(errors) == 0,
            "error_count": len(errors),
            "errors": errors,
            "lines_count": len(entry.lines),
            "currencies": list(set(line.currency for line in entry.lines)),
            "accounts": list(set(str(line.account_code) for line in entry.lines)),
            "entry_id": str(entry.id) if entry.id else None,
            "entry_date": entry.date.isoformat() if entry.date else None,
            "is_posted": entry.is_posted if hasattr(entry, 'is_posted') else None,
        }
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        مسح التخزين المؤقت (إذا كان هناك أي كاش)
        """
        # لا يوجد كاش حالياً، ولكن هذه الدالة للاستخدام المستقبلي
        logger.debug("PostingValidator cache cleared")


# =============================================================================
# دوال مساعدة للاستخدام السريع
# =============================================================================

def validate_entry(entry: JournalEntry) -> List[str]:
    """
    دالة مساعدة للتحقق من قيد محاسبي
    
    Args:
        entry: القيد المراد التحقق منه
    
    Returns:
        List[str]: قائمة بأخطاء التحقق
    """
    return PostingValidator.validate_journal_entry(entry)


def is_valid_entry(entry: JournalEntry) -> bool:
    """
    دالة مساعدة للتحقق السريع من صحة القيد
    
    Args:
        entry: القيد المراد التحقق منه
    
    Returns:
        bool: True إذا كان القيد صحيحاً
    """
    return PostingValidator.is_valid_entry(entry)


# =============================================================================
# تصدير الكلاسات والدوال
# =============================================================================

__all__ = [
    "PostingValidator",
    "validate_entry",
    "is_valid_entry",
    "SUPPORTED_CURRENCIES",
    "CURRENCY_DECIMAL_PLACES",
]