# core/domain/funds/entities.py
"""
Fund Aggregate Root - كيان الصندوق النقدي (Professional Edition)
الإصدار المُصلح - v2.1.0

✅ لا يخزن الرصيد مباشرة - يُحسب من الحركات
✅ يدعم الرصيد المخزن مؤقتاً (cached balance) لتحسين الأداء
✅ يدعم العملات المتعددة ديناميكياً
✅ يدعم Optimistic Locking
✅ يدعم أحداث المجال (Domain Events)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
from typing import List, Optional, Any, Dict
from uuid import uuid4

from .value_objects import (
    FundId, FundCode, FundType, TransactionType, FundStatus,
    Money, FundLimits, TransactionId, TransferId, TransferStatus, DateRange
)
from .exceptions import (
    InsufficientFundsError,
    FundAlreadyActiveError,
    FundAlreadyInactiveError,
    FundClosedError,
    InvalidTransactionError,
    DailyLimitExceededError,
    MonthlyLimitExceededError,
    FundTransferError,
    SameFundTransferError,
    CurrencyMismatchError,
    InvalidAmountError
)
from .events import (
    FundCreatedEvent,
    FundUpdatedEvent,
    FundStatusChangedEvent,
    FundTransactionCreatedEvent,
    FundBalanceChangedEvent,
    FundTransferCompletedEvent
)


# =============================================================================
# ✅ الإصلاح 1: utc_now() الموحدة
# =============================================================================

def utc_now() -> datetime:
    """
    إرجاع توقيت UTC واعي للتدقيق.
    
    ✅ متوافق مع جميع إصدارات Python
    ✅ يستخدم timezone.utc مباشرة
    """
    return datetime.now(timezone.utc)


# =============================================================================
# ✅ الإصلاح 2: FundTransaction - إضافة @dataclass
# =============================================================================

@dataclass
class FundTransaction:
    """
    حركة الصندوق - Source of Truth
    كل تغيير في الرصيد يتم عبر هذا الكيان
    
    ✅ مصحح: إضافة @dataclass للتوافق مع الـ Repository
    """
    id: TransactionId
    fund_id: FundId
    transaction_type: TransactionType
    amount: Money
    balance_before: Money
    balance_after: Money
    reference_id: Optional[str]
    description: str
    created_at: datetime
    created_by: str
    metadata: dict = field(default_factory=dict)
    
    @property
    def is_inflow(self) -> bool:
        """هل الحركة تزيد الرصيد؟"""
        return self.transaction_type.is_inflow
    
    @property
    def is_outflow(self) -> bool:
        """هل الحركة تنقص الرصيد؟"""
        return self.transaction_type.is_outflow
    
    @property
    def net_effect(self) -> Money:
        """التأثير الصافي على الرصيد"""
        if self.is_inflow:
            return self.amount
        return Money(self.amount.amount * -1, self.amount.currency)
    
    @property
    def amount_formatted(self) -> str:
        """المبلغ المنسق للعرض"""
        if self.amount.currency == "LBP":
            return f"{self.amount.amount:,.0f} {self.amount.currency}"
        return f"{self.amount.amount:,.2f} {self.amount.currency}"
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل الحركة إلى قاموس للتسلسل"""
        return {
            'id': str(self.id.value),
            'fund_id': str(self.fund_id.value),
            'transaction_type': self.transaction_type.value,
            'amount': float(self.amount.amount),
            'currency': self.amount.currency,
            'balance_before': float(self.balance_before.amount),
            'balance_after': float(self.balance_after.amount),
            'reference_id': self.reference_id,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'metadata': self.metadata
        }


# =============================================================================
# ✅ Fund - AGGREGATE ROOT (محسّن)
# =============================================================================

@dataclass
class Fund:
    """
    AGGREGATE ROOT - الصندوق النقدي
    Professional Edition - لا يخزن الرصيد مباشرة
    
    ✅ محسّن: دعم العملات المتعددة ديناميكياً
    ✅ محسّن: تحسين معالجة الأخطاء
    ✅ محسّن: دعم الرصيد المخزن مؤقتاً
    """
    
    # === معلومات أساسية ===
    id: FundId = field(default_factory=FundId.generate)
    code: FundCode = field(default_factory=lambda: FundCode(""))
    name: str = ""
    fund_type: FundType = FundType.MAIN
    account_code: str = ""
    currency: str = "USD"
    status: FundStatus = FundStatus.ACTIVE
    
    # === حدود الصندوق ===
    daily_limit: Money = field(default_factory=lambda: Money.zero())
    monthly_limit: Money = field(default_factory=lambda: Money.zero())
    min_balance_alert: Money = field(default_factory=lambda: Money.zero())
    max_balance_alert: Money = field(default_factory=lambda: Money.zero())
    
    # === إعدادات إضافية ===
    requires_approval: bool = False
    approval_threshold: Money = field(default_factory=lambda: Money.zero())
    
    # === الحركات (مصدر الحقيقة) ===
    _transactions: List[FundTransaction] = field(default_factory=list, repr=False)
    
    # === ✅ الرصيد المخزن مؤقتاً (للاستخدام من Repository) ===
    _cached_balance: Optional[Money] = field(default=None, repr=False)
    
    # === أحداث المجال ===
    _events: List[Any] = field(default_factory=list, repr=False)
    
    # === Optimistic Locking ===
    version: int = 1
    
    # === بيانات التدقيق ===
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    updated_at: datetime = field(default_factory=utc_now)
    updated_by: str = ""
    
    # =========================================================================
    # ✅ دوال الرصيد المخزن مؤقتاً
    # =========================================================================
    
    def set_cached_balance(self, balance: Money) -> None:
        """
        تعيين رصيد مخزن مؤقتاً (للاستخدام من Repository)
        
        ✅ دالة جديدة: تسمح للـ Repository بتعيين رصيد محسوب مسبقاً
        
        Args:
            balance: الرصيد المحسوب
        """
        self._cached_balance = balance
    
    def get_cached_balance(self) -> Optional[Money]:
        """
        الحصول على الرصيد المخزن مؤقتاً
        
        Returns:
            Optional[Money]: الرصيد المخزن أو None
        """
        return self._cached_balance
    
    def has_cached_balance(self) -> bool:
        """
        التحقق من وجود رصيد مخزن مؤقتاً
        
        Returns:
            bool: True إذا كان هناك رصيد مخزن
        """
        return self._cached_balance is not None
    
    def clear_cached_balance(self) -> None:
        """مسح الرصيد المخزن مؤقتاً"""
        self._cached_balance = None
    
    # =========================================================================
    # ✅ دوال الرصيد المحسنة
    # =========================================================================
    
    @property
    def current_balance(self) -> Money:
        """
        الرصيد الحالي - يُحسب من آخر حركة أو من الرصيد المخزن مؤقتاً
        
        ✅ محسنة: تستخدم الرصيد المخزن مؤقتاً إذا كان موجوداً
        ✅ محسنة: تتحقق من تطابق العملة
        """
        # ✅ استخدام الرصيد المخزن مؤقتاً أولاً
        if self._cached_balance is not None:
            # التحقق من تطابق العملة
            if self._cached_balance.currency != self.currency:
                logger.warning(
                    f"Cached balance currency mismatch: {self._cached_balance.currency} vs {self.currency}"
                )
                self._cached_balance = None
            else:
                return self._cached_balance
        
        # حساب الرصيد من الحركات
        if not self._transactions:
            return Money.zero(self.currency)
        return self._transactions[-1].balance_after
    
    @property
    def balance(self) -> float:
        """الحصول على الرصيد كرقم عشري (للتوافق مع الكود القديم)"""
        return float(self.current_balance.amount)
    
    @property
    def balance_formatted(self) -> str:
        """الرصيد المنسق للعرض"""
        if self.currency == "LBP":
            return f"{self.balance:,.0f} {self.currency}"
        return f"{self.balance:,.2f} {self.currency}"
    
    # =========================================================================
    # الخصائص الأساسية
    # =========================================================================
    
    @property
    def is_active(self) -> bool:
        return self.status == FundStatus.ACTIVE
    
    @property
    def is_suspended(self) -> bool:
        return self.status == FundStatus.SUSPENDED
    
    @property
    def is_closed(self) -> bool:
        return self.status == FundStatus.CLOSED
    
    @property
    def can_transact(self) -> bool:
        """
        هل يمكن إجراء معاملات على هذا الصندوق؟
        
        ✅ محسّن: التحقق من جميع حالات الصندوق
        """
        return self.status == FundStatus.ACTIVE
    
    @property
    def transactions(self) -> List[FundTransaction]:
        """نسخة من الحركات (للقراءة فقط)"""
        return self._transactions.copy()
    
    @property
    def display_name(self) -> str:
        return f"{self.code.value} - {self.name}"
    
    @property
    def is_low_balance(self) -> bool:
        """التحقق من انخفاض الرصيد"""
        if self.min_balance_alert.is_zero():
            return False
        return self.current_balance.amount <= self.min_balance_alert.amount
    
    @property
    def is_high_balance(self) -> bool:
        """التحقق من ارتفاع الرصيد"""
        if self.max_balance_alert.is_zero():
            return False
        return self.current_balance.amount >= self.max_balance_alert.amount
    
    @property
    def total_transactions(self) -> int:
        """عدد الحركات"""
        return len(self._transactions)
    
    # =========================================================================
    # حساب الرصيد في وقت محدد
    # =========================================================================
    
    def get_balance_at(self, point_in_time: datetime) -> Money:
        """الرصيد في وقت محدد"""
        if not self._transactions:
            return Money.zero(self.currency)
        
        balance = Money.zero(self.currency)
        for tx in sorted(self._transactions, key=lambda x: x.created_at):
            if tx.created_at > point_in_time:
                break
            balance = tx.balance_after
        
        return balance
    
    def get_transactions_in_period(self, from_date: datetime, to_date: datetime) -> List[FundTransaction]:
        """الحركات في فترة زمنية محددة"""
        return [
            tx for tx in self._transactions
            if from_date <= tx.created_at <= to_date
        ]
    
    # =========================================================================
    # دالة المصنع
    # =========================================================================
    
    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        account_code: str,
        fund_type: FundType = FundType.MAIN,
        currency: str = "USD",
        created_by: str = "system",
        daily_limit: Optional[Money] = None,
        monthly_limit: Optional[Money] = None,
        min_balance_alert: Optional[Money] = None,
        max_balance_alert: Optional[Money] = None,
        opening_balance: Optional[Money] = None
    ) -> 'Fund':
        """
        إنشاء صندوق جديد مع رصيد افتتاحي اختياري
        
        ✅ محسّن: التحقق من صحة العملة
        """
        # ✅ التحقق من صحة العملة
        if currency not in ["USD", "EUR", "LBP", "GBP"]:
            logger.warning(f"Unusual currency: {currency}")
        
        fund = cls(
            code=FundCode(code),
            name=name,
            fund_type=fund_type,
            account_code=account_code,
            currency=currency,
            daily_limit=daily_limit or Money.zero(currency),
            monthly_limit=monthly_limit or Money.zero(currency),
            min_balance_alert=min_balance_alert or Money.zero(currency),
            max_balance_alert=max_balance_alert or Money.zero(currency),
            created_by=created_by,
            updated_by=created_by,
            version=1
        )
        
        # إضافة رصيد افتتاحي إذا كان موجوداً
        if opening_balance and opening_balance.amount > 0:
            fund.add_transaction(
                transaction_type=TransactionType.OPENING_BALANCE,
                amount=opening_balance,
                reference_id=None,
                description="رصيد افتتاحي",
                created_by=created_by
            )
        
        fund._events.append(FundCreatedEvent(
            fund_id=fund.id,
            fund_code=fund.code,
            fund_name=fund.name,
            fund_type=fund.fund_type,
            account_code=fund.account_code,
            currency=fund.currency,
            created_by=created_by
        ))
        
        return fund
    
    # =========================================================================
    # ✅ الطريقة الوحيدة لتغيير الرصيد (محسّنة)
    # =========================================================================
    
    def add_transaction(
        self,
        transaction_type: TransactionType,
        amount: Money,
        reference_id: Optional[str],
        description: str,
        created_by: str,
        metadata: Optional[dict] = None
    ) -> FundTransaction:
        """
        إضافة حركة جديدة - الطريقة الوحيدة لتغيير الرصيد
        
        ✅ محسّن: التحقق من صحة العملة
        ✅ محسّن: التحقق من حالة الصندوق
        ✅ محسّن: رسائل خطأ واضحة
        """
        # ✅ التحقق من حالة الصندوق
        if not self.can_transact:
            if self.is_closed:
                raise FundClosedError(self.code.value)
            elif self.is_suspended:
                raise ValueError(f"Fund {self.code.value} is suspended")
            else:
                raise ValueError(f"Fund {self.code.value} is not active (status: {self.status.value})")
        
        # ✅ التحقق من صحة العملة
        if amount.currency != self.currency:
            raise CurrencyMismatchError(
                fund_currency=self.currency,
                transaction_currency=amount.currency
            )
        
        # ✅ التحقق من صحة المبلغ
        if amount.amount <= 0:
            raise InvalidAmountError("Transaction amount must be positive")
        
        # حساب الرصيد الجديد
        current = self.current_balance
        new_balance = current + amount if transaction_type.is_inflow else current - amount
        
        if new_balance.amount < 0:
            raise InsufficientFundsError(
                self.code.value,
                float(current.amount),
                float(amount.amount)
            )
        
        # ✅ التحقق من الحدود اليومية والشهرية للسحوبات
        if transaction_type.is_outflow:
            today_withdrawn = self._get_today_withdrawals()
            if not self.daily_limit.is_zero():
                if (today_withdrawn + amount).amount > self.daily_limit.amount:
                    raise DailyLimitExceededError(
                        self.code.value,
                        float(self.daily_limit.amount),
                        float((today_withdrawn + amount).amount)
                    )
            
            month_withdrawn = self._get_month_withdrawals()
            if not self.monthly_limit.is_zero():
                if (month_withdrawn + amount).amount > self.monthly_limit.amount:
                    raise MonthlyLimitExceededError(
                        self.code.value,
                        float(self.monthly_limit.amount),
                        float((month_withdrawn + amount).amount)
                    )
        
        # إنشاء الحركة
        transaction = FundTransaction(
            id=TransactionId.generate(),
            fund_id=self.id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=current,
            balance_after=new_balance,
            reference_id=reference_id,
            description=description,
            created_at=utc_now(),
            created_by=created_by,
            metadata=metadata or {}
        )
        
        self._transactions.append(transaction)
        self.updated_at = utc_now()
        self.updated_by = created_by
        self.version += 1
        
        # ✅ مسح الرصيد المخزن مؤقتاً عند إضافة حركة جديدة
        self._cached_balance = None
        
        # أحداث المجال
        self._events.append(FundTransactionCreatedEvent(
            fund_code=self.code.value,
            transaction_id=transaction.id.value,
            transaction_type=transaction_type.value,
            amount=float(amount.amount),
            currency=amount.currency,
            balance_before=float(current.amount),
            balance_after=float(new_balance.amount),
            reference_id=reference_id,
            description=description,
            created_by=created_by
        ))
        
        self._events.append(FundBalanceChangedEvent(
            fund_code=self.code.value,
            old_balance=float(current.amount),
            new_balance=float(new_balance.amount),
            currency=self.currency,
            changed_by=created_by
        ))
        
        return transaction
    
    # =========================================================================
    # عمليات الإيداع والسحب (محسّنة)
    # =========================================================================
    
    def deposit(
        self,
        amount: Money,
        reason: str,
        created_by: str,
        reference_id: Optional[str] = None
    ) -> FundTransaction:
        """إيداع مبلغ في الصندوق"""
        return self.add_transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            reference_id=reference_id,
            description=reason,
            created_by=created_by
        )
    
    def withdraw(
        self,
        amount: Money,
        reason: str,
        created_by: str,
        reference_id: Optional[str] = None
    ) -> FundTransaction:
        """سحب مبلغ من الصندوق"""
        return self.add_transaction(
            transaction_type=TransactionType.WITHDRAWAL,
            amount=amount,
            reference_id=reference_id,
            description=reason,
            created_by=created_by
        )
    
    def transfer_out(
        self,
        amount: Money,
        to_fund_code: str,
        reason: str,
        created_by: str,
        transfer_id: Optional[str] = None
    ) -> FundTransaction:
        """تحويل صادر إلى صندوق آخر"""
        return self.add_transaction(
            transaction_type=TransactionType.TRANSFER_OUT,
            amount=amount,
            reference_id=transfer_id,
            description=f"تحويل إلى {to_fund_code} - {reason}",
            created_by=created_by
        )
    
    def transfer_in(
        self,
        amount: Money,
        from_fund_code: str,
        reason: str,
        created_by: str,
        transfer_id: Optional[str] = None
    ) -> FundTransaction:
        """تحويل وارد من صندوق آخر"""
        return self.add_transaction(
            transaction_type=TransactionType.TRANSFER_IN,
            amount=amount,
            reference_id=transfer_id,
            description=f"تحويل من {from_fund_code} - {reason}",
            created_by=created_by
        )
    
    def adjust_balance(
        self,
        amount: Money,
        reason: str,
        created_by: str,
        reference_id: Optional[str] = None
    ) -> FundTransaction:
        """تعديل الرصيد (تسوية)"""
        return self.add_transaction(
            transaction_type=TransactionType.ADJUSTMENT,
            amount=amount,
            reference_id=reference_id,
            description=f"تسوية: {reason}",
            created_by=created_by
        )
    
    # =========================================================================
    # دوال حساب السحوبات
    # =========================================================================
    
    def _get_today_withdrawals(self) -> Money:
        """إجمالي السحوبات اليوم"""
        today = utc_now().date()
        total = Decimal('0')
        
        for tx in self._transactions:
            if tx.transaction_type.is_outflow and tx.created_at.date() == today:
                total += tx.amount.amount
        
        return Money(total, self.currency)
    
    def _get_month_withdrawals(self) -> Money:
        """إجمالي السحوبات في الشهر الحالي"""
        now = utc_now()
        total = Decimal('0')
        
        for tx in self._transactions:
            if (tx.transaction_type.is_outflow and 
                tx.created_at.year == now.year and 
                tx.created_at.month == now.month):
                total += tx.amount.amount
        
        return Money(total, self.currency)
    
    def get_total_deposits(self, from_date: Optional[datetime] = None) -> Money:
        """إجمالي الإيداعات"""
        total = Decimal('0')
        for tx in self._transactions:
            if tx.transaction_type.is_inflow:
                if from_date is None or tx.created_at >= from_date:
                    total += tx.amount.amount
        return Money(total, self.currency)
    
    def get_total_withdrawals(self, from_date: Optional[datetime] = None) -> Money:
        """إجمالي السحوبات"""
        total = Decimal('0')
        for tx in self._transactions:
            if tx.transaction_type.is_outflow:
                if from_date is None or tx.created_at >= from_date:
                    total += tx.amount.amount
        return Money(total, self.currency)
    
    # =========================================================================
    # عمليات إدارة الصندوق
    # =========================================================================
    
    def activate(self, activated_by: str) -> None:
        """تنشيط الصندوق"""
        if self.is_active:
            raise FundAlreadyActiveError(self.code.value)
        
        old_status = self.status
        self.status = FundStatus.ACTIVE
        self.updated_at = utc_now()
        self.updated_by = activated_by
        self.version += 1
        
        self._events.append(FundStatusChangedEvent(
            fund_id=self.id,
            fund_code=self.code,
            old_status=old_status.value,
            new_status=self.status.value,
            changed_by=activated_by
        ))
    
    def suspend(self, suspended_by: str, reason: Optional[str] = None) -> None:
        """تعليق الصندوق مؤقتاً"""
        if self.is_suspended:
            return
        
        old_status = self.status
        self.status = FundStatus.SUSPENDED
        self.updated_at = utc_now()
        self.updated_by = suspended_by
        self.version += 1
        
        self._events.append(FundStatusChangedEvent(
            fund_id=self.id,
            fund_code=self.code,
            old_status=old_status.value,
            new_status=self.status.value,
            changed_by=suspended_by,
            reason=reason
        ))
    
    def close(self, closed_by: str, reason: Optional[str] = None) -> None:
        """إغلاق الصندوق نهائياً"""
        if self.is_closed:
            return
        
        old_status = self.status
        self.status = FundStatus.CLOSED
        self.updated_at = utc_now()
        self.updated_by = closed_by
        self.version += 1
        
        self._events.append(FundStatusChangedEvent(
            fund_id=self.id,
            fund_code=self.code,
            old_status=old_status.value,
            new_status=self.status.value,
            changed_by=closed_by,
            reason=reason
        ))
    
    def soft_delete(self, deleted_by: str, reason: Optional[str] = None) -> None:
        """حذف ناعم (تعطيل الصندوق)"""
        if self.is_closed:
            return
        
        old_status = self.status
        self.status = FundStatus.CLOSED
        self.updated_at = utc_now()
        self.updated_by = deleted_by
        self.version += 1
        
        self._events.append(FundStatusChangedEvent(
            fund_id=self.id,
            fund_code=self.code,
            old_status=old_status.value,
            new_status=self.status.value,
            changed_by=deleted_by,
            reason=reason or "Soft delete"
        ))
    
    def update(
        self,
        name: Optional[str] = None,
        account_code: Optional[str] = None,
        currency: Optional[str] = None,
        daily_limit: Optional[Money] = None,
        monthly_limit: Optional[Money] = None,
        min_balance_alert: Optional[Money] = None,
        max_balance_alert: Optional[Money] = None,
        requires_approval: Optional[bool] = None,
        approval_threshold: Optional[Money] = None,
        updated_by: str = ""
    ) -> None:
        """تحديث بيانات الصندوق"""
        changes = {}
        
        if name and name != self.name:
            changes['name'] = {'old': self.name, 'new': name}
            self.name = name
        
        if account_code and account_code != self.account_code:
            changes['account_code'] = {'old': self.account_code, 'new': account_code}
            self.account_code = account_code
        
        if currency and currency != self.currency:
            changes['currency'] = {'old': self.currency, 'new': currency}
            self.currency = currency
        
        if daily_limit is not None and daily_limit != self.daily_limit:
            changes['daily_limit'] = {'old': float(self.daily_limit.amount), 'new': float(daily_limit.amount)}
            self.daily_limit = daily_limit
        
        if monthly_limit is not None and monthly_limit != self.monthly_limit:
            changes['monthly_limit'] = {'old': float(self.monthly_limit.amount), 'new': float(monthly_limit.amount)}
            self.monthly_limit = monthly_limit
        
        if min_balance_alert is not None and min_balance_alert != self.min_balance_alert:
            changes['min_balance_alert'] = {'old': float(self.min_balance_alert.amount), 'new': float(min_balance_alert.amount)}
            self.min_balance_alert = min_balance_alert
        
        if max_balance_alert is not None and max_balance_alert != self.max_balance_alert:
            changes['max_balance_alert'] = {'old': float(self.max_balance_alert.amount), 'new': float(max_balance_alert.amount)}
            self.max_balance_alert = max_balance_alert
        
        if requires_approval is not None and requires_approval != self.requires_approval:
            changes['requires_approval'] = {'old': self.requires_approval, 'new': requires_approval}
            self.requires_approval = requires_approval
        
        if approval_threshold is not None and approval_threshold != self.approval_threshold:
            changes['approval_threshold'] = {'old': float(self.approval_threshold.amount), 'new': float(approval_threshold.amount)}
            self.approval_threshold = approval_threshold
        
        if changes:
            self.updated_at = utc_now()
            self.updated_by = updated_by
            self.version += 1
            
            self._events.append(FundUpdatedEvent(
                fund_id=self.id,
                fund_code=self.code,
                changes=changes,
                updated_by=updated_by
            ))
    
    # =========================================================================
    # أحداث المجال
    # =========================================================================
    
    def pull_events(self) -> List[Any]:
        """استخراج الأحداث المتراكمة"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def add_event(self, event: Any) -> None:
        """إضافة حدث (للاستخدام في الـ Repository)"""
        self._events.append(event)
    
    # =========================================================================
    # دوال مساعدة للحركات
    # =========================================================================
    
    def get_transactions(self) -> List[FundTransaction]:
        """الحصول على جميع الحركات"""
        return self._transactions.copy()
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[FundTransaction]:
        """البحث عن حركة بالمعرف"""
        for tx in self._transactions:
            if tx.id.value == transaction_id:
                return tx
        return None
    
    def get_last_transaction(self) -> Optional[FundTransaction]:
        """الحصول على آخر حركة"""
        if not self._transactions:
            return None
        return self._transactions[-1]
    
    def get_transactions_by_type(self, transaction_type: TransactionType) -> List[FundTransaction]:
        """الحصول على الحركات حسب النوع"""
        return [tx for tx in self._transactions if tx.transaction_type == transaction_type]
    
    def get_transactions_by_reference(self, reference_id: str) -> List[FundTransaction]:
        """الحصول على الحركات حسب المرجع"""
        return [tx for tx in self._transactions if tx.reference_id == reference_id]
    
    # =========================================================================
    # دوال التقارير
    # =========================================================================
    
    def get_summary(self) -> Dict[str, Any]:
        """الحصول على ملخص الصندوق"""
        return {
            'id': str(self.id.value),
            'code': self.code.value,
            'name': self.name,
            'currency': self.currency,
            'balance': float(self.current_balance.amount),
            'balance_formatted': self.balance_formatted,
            'status': self.status.value,
            'is_active': self.is_active,
            'total_transactions': len(self._transactions),
            'total_deposits': float(self.get_total_deposits().amount),
            'total_withdrawals': float(self.get_total_withdrawals().amount),
            'daily_limit': float(self.daily_limit.amount),
            'monthly_limit': float(self.monthly_limit.amount),
            'min_balance_alert': float(self.min_balance_alert.amount),
            'max_balance_alert': float(self.max_balance_alert.amount),
            'version': self.version,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_by': self.created_by,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by
        }
    
    # =========================================================================
    # التحقق من الصلاحية
    # =========================================================================
    
    def can_deposit(self, amount: Money) -> bool:
        """التحقق من إمكانية الإيداع"""
        if not self.is_active:
            return False
        if amount.currency != self.currency:
            return False
        if amount.amount <= 0:
            return False
        return True
    
    def can_withdraw(self, amount: Money) -> bool:
        """التحقق من إمكانية السحب"""
        if not self.is_active:
            return False
        if amount.currency != self.currency:
            return False
        if amount.amount <= 0:
            return False
        if self.current_balance.amount < amount.amount:
            return False
        return True
    
    def can_transfer(self, amount: Money) -> bool:
        """التحقق من إمكانية التحويل"""
        return self.can_withdraw(amount)
    
    # =========================================================================
    # دالة التمثيل النصي
    # =========================================================================
    
    def __repr__(self) -> str:
        return (
            f"Fund(id={self.id}, code={self.code}, name={self.name}, "
            f"balance={self.current_balance}, status={self.status.value}, "
            f"version={self.version})"
        )


# =============================================================================
# ✅ FundTransfer - عملية تحويل بين صندوقين (محسّن)
# =============================================================================

@dataclass
class FundTransfer:
    """
    AGGREGATE ROOT - عملية تحويل بين صندوقين
    تضمن سلامة العملية كاملة (من + إلى + قيد محاسبي)
    
    ✅ مصحح: إضافة @dataclass للتوافق مع الـ Repository
    ✅ محسّن: التحقق من صحة البيانات
    """
    id: TransferId
    from_fund_id: FundId
    to_fund_id: FundId
    amount: Money
    from_currency: str
    to_currency: str
    exchange_rate: Decimal
    converted_amount: Money
    status: TransferStatus
    reason: str
    journal_entry_id: Optional[str] = None
    created_at: datetime = field(default_factory=utc_now)
    created_by: str = ""
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    _events: List[Any] = field(default_factory=list, repr=False)
    
    @classmethod
    def create(
        cls,
        from_fund_id: FundId,
        to_fund_id: FundId,
        amount: Money,
        exchange_rate: Decimal,
        reason: str,
        created_by: str
    ) -> 'FundTransfer':
        """إنشاء تحويل جديد"""
        if from_fund_id == to_fund_id:
            raise SameFundTransferError(str(from_fund_id))
        if amount.amount <= 0:
            raise ValueError("Transfer amount must be positive")
        if exchange_rate <= 0:
            raise ValueError("Exchange rate must be positive")
        
        from_currency = amount.currency
        to_currency = from_currency
        
        converted_amount = Money(amount.amount * exchange_rate, to_currency)
        
        transfer = cls(
            id=TransferId.generate(),
            from_fund_id=from_fund_id,
            to_fund_id=to_fund_id,
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
            exchange_rate=exchange_rate,
            converted_amount=converted_amount,
            status=TransferStatus.PENDING,
            reason=reason,
            created_by=created_by
        )
        return transfer
    
    def approve(self, approved_by: str) -> None:
        """الموافقة على التحويل"""
        if self.status != TransferStatus.PENDING:
            raise FundTransferError(f"Cannot approve transfer in status '{self.status.value}'")
        self.status = TransferStatus.APPROVED
        self.approved_at = utc_now()
        self.approved_by = approved_by
    
    def complete(self, journal_entry_id: str) -> None:
        """إكمال التحويل بعد ترحيل القيد المحاسبي"""
        if self.status != TransferStatus.APPROVED:
            raise FundTransferError(f"Cannot complete transfer in status '{self.status.value}'")
        self.status = TransferStatus.COMPLETED
        self.completed_at = utc_now()
        self.journal_entry_id = journal_entry_id
        
        self._events.append(FundTransferCompletedEvent(
            transfer_id=self.id.value,
            from_fund=str(self.from_fund_id),
            to_fund=str(self.to_fund_id),
            amount=float(self.amount.amount),
            from_currency=self.from_currency,
            to_currency=self.to_currency,
            exchange_rate=float(self.exchange_rate),
            converted_amount=float(self.converted_amount.amount),
            journal_entry_id=journal_entry_id
        ))
    
    def fail(self, reason: str) -> None:
        """فشل التحويل"""
        if self.status not in [TransferStatus.PENDING, TransferStatus.APPROVED]:
            raise FundTransferError(f"Cannot fail transfer in status '{self.status.value}'")
        self.status = TransferStatus.FAILED
    
    def cancel(self, cancelled_by: str) -> None:
        """إلغاء التحويل"""
        if self.status in [TransferStatus.COMPLETED, TransferStatus.CANCELLED]:
            raise FundTransferError(f"Cannot cancel transfer in status '{self.status.value}'")
        self.status = TransferStatus.CANCELLED
    
    def pull_events(self) -> List[Any]:
        events = self._events.copy()
        self._events.clear()
        return events
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل التحويل إلى قاموس للتسلسل"""
        return {
            'id': str(self.id.value),
            'from_fund_id': str(self.from_fund_id.value),
            'to_fund_id': str(self.to_fund_id.value),
            'amount': float(self.amount.amount),
            'currency': self.amount.currency,
            'from_currency': self.from_currency,
            'to_currency': self.to_currency,
            'exchange_rate': float(self.exchange_rate),
            'converted_amount': float(self.converted_amount.amount),
            'status': self.status.value,
            'reason': self.reason,
            'journal_entry_id': self.journal_entry_id,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'approved_by': self.approved_by,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def __repr__(self) -> str:
        return (
            f"FundTransfer(id={self.id}, from={self.from_fund_id}, to={self.to_fund_id}, "
            f"amount={self.amount}, status={self.status.value})"
        )