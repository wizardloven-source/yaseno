# core/application/handlers/funds/transfer_funds_handler.py
"""
Transfer Funds Handler - معالج تحويل بين صندوقين
الإصدار المُصلح - v3.0.0

✅ محدث: استخدام Accounting Orchestrator المركزي
✅ محدث: SELECT FOR UPDATE مع ترتيب ثابت لمنع Deadlock
✅ محدث: Atomic Save لحفظ كلا الصندوقين دفعة واحدة
✅ محدث: التحقق من الإصدار قبل التحديث
✅ محدث: التراجع التلقائي عند التعارض
✅ محدث: دعم العملات المتعددة والتحويل التلقائي
✅ محدث: التخزين المؤقت لأسعار الصرف
✅ محدث: تحسين معالجة الأخطاء
✅ محدث: التحقق من صحة العملات
"""

import logging
from decimal import Decimal
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, Any, Optional, Tuple

from core.domain.funds.value_objects import (
    FundId, 
    TransactionType,
    TransferStatus,
    Money
)
from core.domain.funds.entities import FundTransfer
from core.domain.funds.exceptions import (
    FundNotFoundError, 
    FundAlreadyInactiveError, 
    InsufficientFundsError,
    SameFundTransferError,
    FundTransferError,
    CurrencyMismatchError
)
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.accounting.services import PostingEngine
from core.domain.accounting.entities import JournalEntry, JournalLine
from core.domain.shared.value_objects import AccountCode
from core.shared.exceptions import ConcurrentModificationError

# ✅ استيراد Accounting Orchestrator
from core.application.accounting.orchestrator import (
    AccountingOrchestrator,
    JournalEntryRequest,
    JournalEntryResult
)

# ✅ استيراد إعدادات العملات
try:
    from core.domain.shared.value_objects import CurrencySettings
except ImportError:
    class CurrencySettings:
        @staticmethod
        def get_decimal_places(currency: str) -> int:
            return 0 if currency == "LBP" else 2

from core.application.handlers.base_handler import BaseHandler
from core.application.security.authorization import UserContext, require_permission, Permission
from core.application.funds.commands import TransferBetweenFundsCommand
from core.application.funds.dtos import FundDTO
from core.application.funds.converters import fund_to_dto

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """الحصول على الوقت الحالي بتوقيت UTC"""
    return datetime.now(timezone.utc)


# =============================================================================
# ✅ TransferResult - نتيجة التحويل (محسّن)
# =============================================================================

class TransferResult:
    """نتيجة عملية التحويل"""
    
    def __init__(self):
        self.success: bool = False
        self.message: str = ""
        self.transfer_id: Optional[str] = None
        self.journal_entry_id: Optional[str] = None
        self.from_fund: Optional[FundDTO] = None
        self.to_fund: Optional[FundDTO] = None
        self.amount_from: float = 0.0
        self.amount_to: float = 0.0
        self.exchange_rate_used: float = 1.0
        self.from_balance_after: float = 0.0
        self.to_balance_after: float = 0.0
        self.errors: List[str] = list()
        self.warnings: List[str] = list()
        self.details: Dict[str, Any] = dict()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "transfer_id": self.transfer_id,
            "journal_entry_id": self.journal_entry_id,
            "from_fund": self.from_fund,
            "to_fund": self.to_fund,
            "amount_from": self.amount_from,
            "amount_to": self.amount_to,
            "exchange_rate_used": self.exchange_rate_used,
            "from_balance_after": self.from_balance_after,
            "to_balance_after": self.to_balance_after,
            "errors": self.errors,
            "warnings": self.warnings,
            "details": self.details,
            "locked_funds": True,
            "atomic_save": True,
        }
    
    def set_success(self, message: str):
        self.success = True
        self.message = message
    
    def set_error(self, message: str, error: Optional[str] = None):
        self.success = False
        self.message = message
        if error:
            self.errors.append(error)


# =============================================================================
# ✅ TransferFundsHandler - المعالج الرئيسي (محسّن)
# =============================================================================

class TransferFundsHandler(BaseHandler[TransferBetweenFundsCommand, dict]):
    """
    معالج تحويل بين صندوقين - النسخة النهائية المتكاملة مع Atomic Save
    
    مسؤولياته:
        1. التحقق من وجود الصندوقين ونشاطهما
        2. 🔒 قفل الصندوقين باستخدام SELECT FOR UPDATE (بترتيب ثابت)
        3. التحقق من كفاية الرصيد
        4. إنشاء كيان التحويل
        5. ✅ إنشاء القيد المحاسبي عبر Accounting Orchestrator
        6. ✅ تحديث كلا الصندوقين مع Optimistic Locking
        7. 💾 حفظ ذري (Atomic Save) لكلا الصندوقين
        8. التراجع التلقائي عند أي تعارض
        9. دعم العملات المتعددة والتحويل التلقائي
        10. التخزين المؤقت لأسعار الصرف
    
    حالات الخطأ المحتملة:
        - FundNotFoundError: أحد الصندوقين غير موجود
        - FundAlreadyInactiveError: أحد الصندوقين غير نشط
        - InsufficientFundsError: رصيد غير كافٍ
        - SameFundTransferError: تحويل من وإلى نفس الصندوق
        - FundTransferError: خطأ عام في التحويل
        - ConcurrentModificationError: تعديل متزامن
        - CurrencyMismatchError: عملات غير متطابقة
    """
    
    def __init__(
        self,
        uow: IUnitOfWork,
        accounting_orchestrator: AccountingOrchestrator,
        posting_engine: PostingEngine = None
    ):
        super().__init__(uow)
        self._orchestrator = accounting_orchestrator
        self._posting_engine = posting_engine
        
        # ✅ التخزين المؤقت لأسعار الصرف
        self._exchange_rate_cache: Dict[str, Decimal] = {}
    
    # =========================================================================
    # ✅ دوال التحقق (Validation) - محسّنة
    # =========================================================================
    
    def _validate_funds(
        self,
        from_fund_id: FundId,
        to_fund_id: FundId
    ) -> Tuple[Any, Any]:
        """
        التحقق من الصندوقين وقفلهما بترتيب ثابت
        
        🔒 يقفل الصندوقين بترتيب ثابت حسب المعرف لمنع Deadlock
        
        Returns:
            Tuple[Fund, Fund]: (from_fund, to_fund)
        
        Raises:
            FundNotFoundError: إذا لم يتم العثور على أحد الصندوقين
            FundAlreadyInactiveError: إذا كان أحد الصندوقين غير نشط
            SameFundTransferError: إذا كان التحويل من وإلى نفس الصندوق
            FundTransferError: إذا فشل القفل
        """
        # التحقق من أن الصندوقين مختلفان
        if from_fund_id == to_fund_id:
            raise SameFundTransferError(str(from_fund_id))
        
        # التحقق من صحة المعرفات
        if not isinstance(from_fund_id, FundId) or not isinstance(to_fund_id, FundId):
            raise FundTransferError("معرف صندوق غير صالح")
        
        # ✅ قفل الصندوقين بترتيب ثابت (لمنع Deadlock)
        fund_ids = [from_fund_id, to_fund_id]
        sorted_ids = sorted([str(fid) for fid in fund_ids])
        
        try:
            # ✅ استخدام order_by لضمان ترتيب ثابت
            funds = self._uow.funds.lock_funds_for_update(
                [FundId.from_string(sid) for sid in sorted_ids]
            )
        except ValueError as e:
            raise FundNotFoundError(str(e))
        except Exception as e:
            logger.error(f"Error locking funds: {e}", exc_info=True)
            raise FundTransferError(f"فشل قفل الصناديق: {str(e)}")
        
        # خريطة للوصول السريع للصناديق المقفلة
        fund_map = {str(f.id): f for f in funds}
        
        from_fund = fund_map.get(str(from_fund_id))
        to_fund = fund_map.get(str(to_fund_id))
        
        if not from_fund or not to_fund:
            missing = str(from_fund_id) if not from_fund else str(to_fund_id)
            raise FundNotFoundError(missing)
        
        # التحقق من نشاط الصندوقين
        if not from_fund.is_active:
            raise FundAlreadyInactiveError(from_fund.code.value)
        if not to_fund.is_active:
            raise FundAlreadyInactiveError(to_fund.code.value)
        
        return from_fund, to_fund
    
    def _validate_balance(
        self,
        fund: Any,
        amount: Money
    ) -> None:
        """
        التحقق من كفاية الرصيد
        
        Args:
            fund: كائن الصندوق
            amount: المبلغ المراد تحويله
        
        Raises:
            InsufficientFundsError: إذا كان الرصيد غير كافٍ
        """
        # ✅ استخدام الرصيد المحسوب من الحركات
        current_balance = fund.current_balance.amount
        
        if current_balance < amount.amount:
            raise InsufficientFundsError(
                fund.code.value,
                float(current_balance),
                float(amount.amount)
            )
    
    def _validate_currency(
        self,
        from_currency: str,
        to_currency: str,
        auto_convert: bool
    ) -> None:
        """
        التحقق من صحة العملات
        
        Args:
            from_currency: عملة المصدر
            to_currency: عملة الهدف
            auto_convert: هل يُسمح بالتحويل التلقائي؟
        
        Raises:
            CurrencyMismatchError: إذا كانت العملات غير متطابقة ولا يُسمح بالتحويل
        """
        if from_currency == to_currency:
            return
        
        if not auto_convert:
            raise CurrencyMismatchError(
                fund_currency=from_currency,
                transaction_currency=to_currency
            )
        
        # التحقق من أن العملات مدعومة
        if not CurrencySettings.is_valid(from_currency):
            raise ValueError(f"عملة المصدر غير مدعومة: {from_currency}")
        if not CurrencySettings.is_valid(to_currency):
            raise ValueError(f"عملة الهدف غير مدعومة: {to_currency}")
    
    # =========================================================================
    # ✅ الحصول على سعر الصرف مع التخزين المؤقت
    # =========================================================================
    
    @lru_cache(maxsize=128)
    def _get_cached_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """الحصول على سعر الصرف مع التخزين المؤقت"""
        if from_currency == to_currency:
            return Decimal('1')
        
        cache_key = f"{from_currency}_{to_currency}"
        if cache_key in self._exchange_rate_cache:
            return self._exchange_rate_cache[cache_key]
        
        try:
            rate = self._get_exchange_rate_from_db(from_currency, to_currency)
            self._exchange_rate_cache[cache_key] = rate
            return rate
        except Exception as e:
            logger.error(f"Error getting exchange rate: {e}")
            raise FundTransferError(f"فشل الحصول على سعر الصرف: {str(e)}")
    
    def _get_exchange_rate_from_db(self, from_currency: str, to_currency: str) -> Decimal:
        """الحصول على سعر الصرف من قاعدة البيانات"""
        try:
            from core.infrastructure.db.postgres.settings_repository import SettingsRepository
            repo = SettingsRepository()
            
            # USD → LBP
            if from_currency == "USD" and to_currency == "LBP":
                rate_str = repo.get("usd_buy_rate", "13000")
                return Decimal(rate_str)
            
            # LBP → USD
            elif from_currency == "LBP" and to_currency == "USD":
                rate_str = repo.get("usd_sell_rate", "13100")
                rate = Decimal(rate_str)
                if rate <= 0:
                    raise ValueError(f"Invalid exchange rate: {rate}")
                return Decimal('1') / rate
            
            # عبر USD كعملة وسيطة
            else:
                rate_to_usd = self._get_exchange_rate_from_db(from_currency, "USD")
                rate_from_usd = self._get_exchange_rate_from_db("USD", to_currency)
                return rate_to_usd * rate_from_usd
                
        except Exception as e:
            logger.error(f"Error getting exchange rate from DB: {e}")
            raise FundTransferError(f"فشل الحصول على سعر الصرف: {str(e)}")
    
    def _handle_exchange_rate(
        self,
        amount: Money,
        from_currency: str,
        to_currency: str,
        auto_convert: bool
    ) -> Tuple[Decimal, Decimal]:
        """
        التعامل مع أسعار الصرف
        
        Args:
            amount: المبلغ الأصلي
            from_currency: عملة المصدر
            to_currency: عملة الهدف
            auto_convert: هل يُسمح بالتحويل التلقائي؟
        
        Returns:
            Tuple[Decimal, Decimal]: (سعر الصرف, المبلغ المحول)
        
        Raises:
            FundTransferError: إذا فشل الحصول على سعر الصرف
        """
        exchange_rate = Decimal('1')
        converted_amount = amount.amount
        
        if from_currency != to_currency:
            if not auto_convert:
                raise FundTransferError(
                    f"لا يمكن التحويل من {from_currency} إلى {to_currency} مباشرة. "
                    "يرجى تفعيل التحويل التلقائي."
                )
            
            # ✅ الحصول على سعر الصرف من الكاش
            exchange_rate = self._get_cached_exchange_rate(from_currency, to_currency)
            converted_amount = amount.amount * exchange_rate
            
            logger.info(
                f"Auto conversion: {amount.amount} {from_currency} → "
                f"{converted_amount} {to_currency} (rate: {exchange_rate})"
            )
        
        return exchange_rate, converted_amount
    
    # =========================================================================
    # ✅ بناء طلب القيد المحاسبي (محسّن)
    # =========================================================================
    
    def _build_journal_entry_request(
        self,
        transfer: FundTransfer,
        from_fund: Any,
        to_fund: Any,
        converted_amount: Decimal
    ) -> JournalEntryRequest:
        """
        بناء طلب قيد محاسبي من التحويل
        
        ✅ يدعم التحويل بين عملات مختلفة
        ✅ يستخدم حسابات الصندوق الصحيحة
        ✅ يسجل سعر الصرف المستخدم
        
        Args:
            transfer: كائن التحويل
            from_fund: الصندوق المصدر
            to_fund: الصندوق الهدف
            converted_amount: المبلغ المحول
        
        Returns:
            JournalEntryRequest: طلب القيد المحاسبي
        """
        lines = []
        
        # الحصول على حسابات الصندوقين
        from_account_code = AccountCode(from_fund.account_code)
        to_account_code = AccountCode(to_fund.account_code)
        
        # 1. سطر المدين: حساب الصندوق المستلم
        lines.append({
            "account_code": to_account_code.code,
            "debit": float(converted_amount),
            "currency": transfer.to_currency
        })
        
        # 2. سطر الدائن: حساب الصندوق المرسل
        lines.append({
            "account_code": from_account_code.code,
            "credit": float(transfer.amount.amount),
            "currency": transfer.from_currency
        })
        
        # بناء الطلب
        return JournalEntryRequest(
            entity_type="fund_transfer",
            entity_id=str(transfer.id.value),
            description=(
                f"تحويل نقدي من صندوق {from_fund.code.value} إلى صندوق {to_fund.code.value} - "
                f"{transfer.reason} (سعر الصرف: {transfer.exchange_rate})"
            ),
            lines=lines,
            date=utc_now(),
            transaction_type="transfer",
            created_by=transfer.created_by,
            reference_number=str(transfer.id.value),
            metadata={
                "transfer_id": str(transfer.id.value),
                "from_fund_id": str(from_fund.id.value),
                "from_fund_code": from_fund.code.value,
                "from_fund_name": from_fund.name,
                "to_fund_id": str(to_fund.id.value),
                "to_fund_code": to_fund.code.value,
                "to_fund_name": to_fund.name,
                "amount_from": float(transfer.amount.amount),
                "amount_to": float(converted_amount),
                "from_currency": transfer.from_currency,
                "to_currency": transfer.to_currency,
                "exchange_rate": float(transfer.exchange_rate),
                "reason": transfer.reason,
                "status": transfer.status.value,
                "cost_center": getattr(from_fund, 'cost_center', None),
                "profit_center": getattr(from_fund, 'profit_center', None),
            }
        )
    
    # =========================================================================
    # ✅ المعالج الرئيسي - المحسّن بالكامل
    # =========================================================================
    
    @require_permission(Permission.MODIFY_DRAFT)
    def handle(self, command: TransferBetweenFundsCommand, user_context: UserContext = None) -> dict:
        """
        معالج تحويل بين صندوقين مع SELECT FOR UPDATE و Atomic Save
        
        🔒 يقفل الصندوقين بترتيب ثابت لمنع Deadlock
        💾 يحفظ كلا الصندوقين في معاملة واحدة ذرية
        ✅ يستخدم Accounting Orchestrator لإنشاء القيد المحاسبي
        ✅ التراجع التلقائي عند أي تعارض
        ✅ دعم العملات المتعددة والتحويل التلقائي
        
        Args:
            command: أمر التحويل
            user_context: سياق المستخدم
        
        Returns:
            dict: نتيجة التحويل
        
        Raises:
            SameFundTransferError: تحويل من وإلى نفس الصندوق
            FundNotFoundError: أحد الصندوقين غير موجود
            FundAlreadyInactiveError: أحد الصندوقين غير نشط
            InsufficientFundsError: رصيد غير كافٍ
            FundTransferError: خطأ عام في التحويل
            ConcurrentModificationError: تعديل متزامن
            CurrencyMismatchError: عملات غير متطابقة
        """
        # ========== 0. إعداد سياق المستخدم ==========
        ctx = user_context or UserContext(
            user_id=command.created_by,
            username="System",
            roles=set()
        )
        
        result = TransferResult()
        
        with self._uow:
            try:
                # ✅ ربط الـ Orchestrator ومحرك الترحيل بجلسة الـ UoW الحالية
                # (نفس إصلاح الفواتير: منع deadlock بين جلسة الحاوية وجلسة الـ UoW)
                orchestrator = self._orchestrator
                orchestrator._uow = self._uow
                if self._posting_engine is not None:
                    engine = self._posting_engine
                    engine._journal_repo = self._uow.journal_entries
                    engine._ledger_repo = self._uow.ledger
                    engine._period_repo = self._uow.periods
                    engine._account_repo = self._uow.accounts
                    engine._uow = self._uow

                # ========== 1. التحقق من الصندوقين ==========
                from_fund, to_fund = self._validate_funds(
                    command.from_fund_id,
                    command.to_fund_id
                )
                
                # ========== 2. إعداد المبلغ ==========
                amount_money = Money(
                    amount=Decimal(str(command.amount)),
                    currency=command.from_currency or from_fund.currency
                )
                
                if amount_money.amount <= 0:
                    raise ValueError("مبلغ التحويل يجب أن يكون أكبر من صفر")
                
                # ========== 3. التحقق من كفاية الرصيد ==========
                self._validate_balance(from_fund, amount_money)
                
                # ========== 4. التعامل مع العملات ==========
                from_currency = command.from_currency or from_fund.currency
                to_currency = command.to_currency or to_fund.currency
                
                self._validate_currency(from_currency, to_currency, command.auto_convert)
                
                exchange_rate, converted_amount = self._handle_exchange_rate(
                    amount=amount_money,
                    from_currency=from_currency,
                    to_currency=to_currency,
                    auto_convert=command.auto_convert
                )
                
                # ========== 5. إنشاء كيان التحويل ==========
                transfer = FundTransfer.create(
                    from_fund_id=from_fund.id,
                    to_fund_id=to_fund.id,
                    amount=amount_money,
                    exchange_rate=exchange_rate,
                    reason=command.reason or "تحويل بين الصناديق",
                    created_by=ctx.user_id
                )
                transfer.approve(ctx.user_id)
                
                # ========== 6. إنشاء القيد المحاسبي ==========
                try:
                    journal_request = self._build_journal_entry_request(
                        transfer=transfer,
                        from_fund=from_fund,
                        to_fund=to_fund,
                        converted_amount=converted_amount
                    )
                    
                    orchestrator_result = self._orchestrator.create_journal_entry(
                        request=journal_request,
                        posted_by=ctx.user_id
                    )
                    
                    if not orchestrator_result.success:
                        raise FundTransferError(
                            f"فشل إنشاء القيد المحاسبي: {orchestrator_result.message}\n"
                            f"الأخطاء: {', '.join(orchestrator_result.errors)}"
                        )
                    
                    journal_entry_id = orchestrator_result.journal_entry_id
                    logger.info(f"Journal entry created for transfer {transfer.id}: {journal_entry_id}")
                    
                except Exception as e:
                    logger.error(f"Error creating journal entry: {e}", exc_info=True)
                    raise FundTransferError(f"فشل إنشاء القيد المحاسبي: {str(e)}")
                
                # ========== 7. إكمال التحويل ==========
                transfer.complete(journal_entry_id)
                
                # ========== 8. إضافة الحركات (في الذاكرة) ==========
                from_fund.transfer_out(
                    amount=amount_money,
                    to_fund_code=to_fund.code.value,
                    reason=command.reason or "تحويل بين الصناديق",
                    created_by=ctx.user_id,
                    transfer_id=str(transfer.id.value)
                )
                
                to_fund.transfer_in(
                    amount=Money(converted_amount, to_currency),
                    from_fund_code=from_fund.code.value,
                    reason=command.reason or "تحويل بين الصناديق",
                    created_by=ctx.user_id,
                    transfer_id=str(transfer.id.value)
                )
                
                # ========== 9. حفظ جميع التغييرات دفعة واحدة ==========
                try:
                    # ✅ حفظ كلا الصندوقين في معاملة واحدة
                    self._uow.funds.save_atomic([from_fund, to_fund])
                    
                    # حفظ التحويل
                    if hasattr(self._uow, 'fund_transfers'):
                        self._uow.fund_transfers.save(transfer)
                    
                    # جمع الأحداث
                    if hasattr(self._uow, 'collect_events'):
                        self._uow.collect_events(transfer.pull_events())
                        self._uow.collect_events(from_fund.pull_events())
                        self._uow.collect_events(to_fund.pull_events())
                    
                    # Commit
                    self._commit()
                    
                    logger.info(
                        f"✅ Transfer completed: {from_fund.code.value} → {to_fund.code.value} "
                        f"({amount_money.amount} {from_currency})"
                    )
                    
                except ConcurrentModificationError as e:
                    self._uow.rollback()
                    logger.warning(f"Concurrent modification: {e}")
                    raise FundTransferError(
                        f"تعارض في التحديث: {e.entity_type} {e.entity_id}. "
                        "الرجاء إعادة المحاولة."
                    ) from e
                except Exception as e:
                    self._uow.rollback()
                    logger.error(f"Error saving transfer: {e}", exc_info=True)
                    raise FundTransferError(f"فشل حفظ التغييرات: {str(e)}")
                
                # ========== 10. إعداد النتيجة ==========
                result.set_success(f"تم تحويل {amount_money.amount:,.2f} {from_currency} بنجاح")
                result.transfer_id = str(transfer.id.value)
                result.journal_entry_id = transfer.journal_entry_id
                result.from_fund = fund_to_dto(from_fund)
                result.to_fund = fund_to_dto(to_fund)
                result.amount_from = float(amount_money.amount)
                result.amount_to = float(converted_amount)
                result.exchange_rate_used = float(exchange_rate)
                result.from_balance_after = float(from_fund.current_balance.amount)
                result.to_balance_after = float(to_fund.current_balance.amount)
                result.details = {
                    "orchestrator_result": {
                        "success": orchestrator_result.success,
                        "journal_entry_id": orchestrator_result.journal_entry_id,
                        "posted": orchestrator_result.posted,
                    },
                    "locked_funds": True,
                    "atomic_save": True,
                    "auto_converted": from_currency != to_currency,
                }
                
                return result.to_dict()
                
            except SameFundTransferError as e:
                self._uow.rollback()
                result.set_error(str(e), str(e))
                return result.to_dict()
                
            except FundNotFoundError as e:
                self._uow.rollback()
                result.set_error(f"الصندوق غير موجود: {e.fund_id}", str(e))
                return result.to_dict()
                
            except FundAlreadyInactiveError as e:
                self._uow.rollback()
                result.set_error(f"الصندوق غير نشط: {e.fund_code}", str(e))
                return result.to_dict()
                
            except InsufficientFundsError as e:
                self._uow.rollback()
                result.set_error(
                    f"الرصيد غير كافٍ في صندوق {e.fund_code}. "
                    f"الرصيد: {e.balance:,.2f}، المطلوب: {e.requested:,.2f}",
                    str(e)
                )
                return result.to_dict()
                
            except (CurrencyMismatchError, ValueError) as e:
                self._uow.rollback()
                result.set_error(str(e), str(e))
                return result.to_dict()
                
            except ConcurrentModificationError as e:
                self._uow.rollback()
                result.set_error(
                    f"تعارض في التحديث: {e.entity_type} {e.entity_id}. الرجاء إعادة المحاولة.",
                    str(e)
                )
                result.details["concurrent_modification"] = True
                return result.to_dict()
                
            except FundTransferError as e:
                self._uow.rollback()
                result.set_error(str(e), str(e))
                return result.to_dict()
                
            except Exception as e:
                self._uow.rollback()
                logger.error(f"Unexpected error: {e}", exc_info=True)
                result.set_error(f"خطأ غير متوقع: {str(e)}", str(e))
                return result.to_dict()
    
    # =========================================================================
    # ✅ دوال مساعدة للتحقق من الصندوقين (للاختبارات)
    # =========================================================================
    
    def get_fund_balances(self, fund_id: str) -> Dict[str, Any]:
        """الحصول على معلومات رصيد الصندوق (للاختبار)"""
        with self._uow:
            fund = self._uow.funds.get_by_id(FundId.from_string(fund_id))
            if not fund:
                return {"error": f"Fund {fund_id} not found"}
            
            return {
                "fund_id": str(fund.id),
                "fund_code": fund.code.value,
                "fund_name": fund.name,
                "currency": fund.currency,
                "balance": float(fund.current_balance.amount),
                "balance_formatted": fund.balance_formatted,
                "transactions_count": len(fund.transactions),
                "is_active": fund.is_active,
                "version": fund.version,
            }
    
    def clear_exchange_rate_cache(self) -> None:
        """مسح التخزين المؤقت لأسعار الصرف"""
        self._get_cached_exchange_rate.cache_clear()
        self._exchange_rate_cache.clear()
        logger.info("Exchange rate cache cleared")