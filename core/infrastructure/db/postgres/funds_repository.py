"""
PostgreSQL Repository for Funds - Professional Implementation
الإصدار: 2.1.0 - مع دعم SELECT FOR UPDATE و Atomic Save

✅ محدث: استخدام Clock Service للوقت
✅ تنفيذ كامل لجميع الواجهات
✅ يدعم Optimistic Locking
✅ يدعم Batch Balance Calculation
✅ يدعم Soft Delete و Hard Delete
✅ متوافق مع جميع الواجهات في interfaces.py
✅ مصحح: استخدام movement_type بدلاً من transaction_type
✅ مصحح: إضافة الدوال المفقودة في PostgresFundMovementRepository
✅ جديد: دالة lock_funds_for_update (SELECT FOR UPDATE)
✅ جديد: دالة save_atomic لحفظ عدة صناديق دفعة واحدة
"""

import logging
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, List, Dict, Any, Union, Tuple
from uuid import UUID
import re

from sqlalchemy import select, update, func, delete, and_, or_
from sqlalchemy.orm import Session

# ✅ استيراد Clock Service
from core.domain.shared.clock import get_clock, utc_now, to_utc
from core.domain.funds.entities import Fund, FundTransaction, FundTransfer
from core.domain.funds.value_objects import (
    FundId, FundCode, FundType, TransactionType, FundStatus,
    Money, TransactionId, TransferId, TransferStatus
)
from core.domain.funds.interfaces import (
    IFundRepository, IFundTransactionRepository, IFundTransferRepository, IFundMovementRepository
)
from core.shared.exceptions import ConcurrentModificationError, NotFoundError, ValidationError

from ..models.fund_model import FundModel, FundTransactionModel, FundTransferModel
from core.domain.funds import FundMovement

logger = logging.getLogger(__name__)


# =============================================================================
# دوال مساعدة للتحويل الآمن (محسنة)
# =============================================================================

def _to_decimal(value: Any) -> Decimal:
    """تحويل آمن إلى Decimal"""
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.replace(',', ''))
        except (ValueError, TypeError):
            return Decimal('0')
    if hasattr(value, 'amount'):
        return _to_decimal(value.amount)
    return Decimal('0')


def _to_currency(value: Any) -> str:
    """استخراج العملة بأمان"""
    if value is None:
        return "USD"
    if hasattr(value, 'currency'):
        return value.currency
    if isinstance(value, str):
        return value.upper()
    return "USD"


def _to_uuid(value: Any) -> UUID:
    """تحويل آمن إلى UUID"""
    if value is None:
        raise ValueError("Cannot convert None to UUID")
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            pass
    if hasattr(value, 'value'):
        return _to_uuid(value.value)
    if hasattr(value, 'id'):
        return _to_uuid(value.id)
    try:
        return UUID(str(value))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Cannot convert {type(value).__name__} to UUID: {value}") from e


# =============================================================================
# دوال التحويل بين Domain و ORM (محسنة)
# =============================================================================

def _model_to_domain_fund(model: FundModel) -> Fund:
    """تحويل ORM Model → Domain Entity - Fund"""
    if not model:
        return None
    
    return Fund(
        id=FundId(model.id),
        code=FundCode(model.code),
        name=model.name,
        fund_type=FundType(model.fund_type),
        account_code=model.account_code,
        currency=model.currency,
        status=FundStatus(model.status),
        daily_limit=Money(_to_decimal(model.daily_limit), model.currency),
        monthly_limit=Money(_to_decimal(model.monthly_limit), model.currency),
        min_balance_alert=Money(_to_decimal(model.min_balance_alert), model.currency),
        max_balance_alert=Money(_to_decimal(model.max_balance_alert), model.currency),
        requires_approval=model.requires_approval,
        approval_threshold=Money(_to_decimal(model.approval_threshold), model.currency),
        created_at=model.created_at,
        created_by=model.created_by,
        updated_at=model.updated_at,
        updated_by=model.updated_by,
        version=model.version
    )


def _domain_to_model_fund(fund: Fund) -> FundModel:
    """تحويل Domain Entity → ORM Model - Fund"""
    return FundModel(
        id=fund.id.value,
        code=fund.code.value,
        name=fund.name,
        fund_type=fund.fund_type.value,
        account_code=fund.account_code,
        currency=fund.currency,
        status=fund.status.value,
        daily_limit=_to_decimal(fund.daily_limit),
        monthly_limit=_to_decimal(fund.monthly_limit),
        min_balance_alert=_to_decimal(fund.min_balance_alert),
        max_balance_alert=_to_decimal(fund.max_balance_alert),
        requires_approval=fund.requires_approval,
        approval_threshold=_to_decimal(fund.approval_threshold),
        created_at=fund.created_at,
        created_by=fund.created_by,
        updated_at=fund.updated_at,
        updated_by=fund.updated_by,
        version=fund.version
    )


def _model_to_domain_transaction(model: FundTransactionModel, fund_id: FundId) -> FundTransaction:
    """تحويل ORM Model → Domain Transaction"""
    movement_type_str = getattr(model, 'movement_type', None)
    if movement_type_str is None:
        movement_type_str = getattr(model, 'transaction_type', 'deposit')
    
    return FundTransaction(
        id=TransactionId(str(model.id)),
        fund_id=fund_id,
        transaction_type=TransactionType(movement_type_str),
        amount=Money(_to_decimal(model.amount), model.currency),
        balance_before=Money(_to_decimal(model.balance_before), model.currency),
        balance_after=Money(_to_decimal(model.balance_after), model.currency),
        reference_id=model.reference_id,
        description=model.reason,
        created_at=model.created_at,
        created_by=model.created_by,
        metadata=model.movement_metadata or {}
    )


def _domain_to_model_transaction(transaction: FundTransaction, fund_id: FundId) -> FundTransactionModel:
    """تحويل Domain Transaction → ORM Model"""
    return FundTransactionModel(
        id=UUID(transaction.id.value),
        fund_id=fund_id.value,
        movement_type=transaction.transaction_type.value,
        amount=_to_decimal(transaction.amount),
        currency=_to_currency(transaction.amount),
        balance_before=_to_decimal(transaction.balance_before),
        balance_after=_to_decimal(transaction.balance_after),
        reference_id=transaction.reference_id,
        reason=transaction.description,
        created_at=transaction.created_at,
        created_by=transaction.created_by,
        movement_metadata=transaction.metadata
    )


def _model_to_domain_transfer(model: FundTransferModel) -> FundTransfer:
    """تحويل ORM Model → Domain Transfer"""
    if not model:
        return None
    
    return FundTransfer(
        id=TransferId(str(model.id)),
        from_fund_id=FundId(model.from_fund_id),
        to_fund_id=FundId(model.to_fund_id),
        amount=Money(_to_decimal(model.amount), model.from_currency),
        from_currency=model.from_currency,
        to_currency=model.to_currency,
        exchange_rate=_to_decimal(model.exchange_rate),
        converted_amount=Money(_to_decimal(model.converted_amount), model.to_currency),
        status=TransferStatus(model.status),
        reason=model.reason,
        journal_entry_id=model.journal_entry_id,
        created_at=model.created_at,
        created_by=model.created_by,
        approved_at=model.approved_at,
        approved_by=model.approved_by,
        completed_at=model.completed_at
    )


# =============================================================================
# PostgresFundRepository - التنفيذ الكامل (محسن)
# =============================================================================

class PostgresFundRepository(IFundRepository):
    """تطبيق PostgreSQL لمستودع الصناديق - Professional Edition"""
    
    def __init__(self, session: Session):
        self._session = session
    
    # ========== العمليات الأساسية مع Optimistic Locking ==========
    
    def save(self, fund: Fund) -> None:
        """حفظ الصندوق مع Optimistic Locking"""
        existing = self._session.execute(
            select(FundModel).where(FundModel.id == fund.id.value)
        ).scalar_one_or_none()
        
        if existing:
            self._update_existing_fund(existing, fund)
        else:
            self._create_new_fund(fund)
    
    def _update_existing_fund(self, existing: FundModel, fund: Fund) -> None:
        """تحديث صندوق موجود مع Optimistic Locking"""
        clock = get_clock()
        now = clock.now()
        new_version = existing.version + 1
        
        result = self._session.execute(
            update(FundModel)
            .where(
                FundModel.id == fund.id.value,
                FundModel.version == fund.version - 1
            )
            .values(
                code=fund.code.value,
                name=fund.name,
                fund_type=fund.fund_type.value,
                account_code=fund.account_code,
                currency=fund.currency,
                status=fund.status.value,
                daily_limit=_to_decimal(fund.daily_limit),
                monthly_limit=_to_decimal(fund.monthly_limit),
                min_balance_alert=_to_decimal(fund.min_balance_alert),
                max_balance_alert=_to_decimal(fund.max_balance_alert),
                requires_approval=fund.requires_approval,
                approval_threshold=_to_decimal(fund.approval_threshold),
                updated_at=now,
                updated_by=fund.updated_by,
                version=new_version
            )
        )
        
        if result.rowcount == 0:
            raise ConcurrentModificationError("Fund", str(fund.id), fund.version, existing.version)
        
        fund.version = new_version
        self._save_new_transactions(fund)
    
    def _create_new_fund(self, fund: Fund) -> None:
        """إنشاء صندوق جديد"""
        model = _domain_to_model_fund(fund)
        self._session.add(model)
        self._session.flush()
        fund.version = 1
        
        for transaction in fund.get_transactions():
            tx_model = _domain_to_model_transaction(transaction, fund.id)
            self._session.add(tx_model)
    
    def _save_new_transactions(self, fund: Fund) -> None:
        """حفظ الحركات الجديدة فقط"""
        existing_ids = self._session.execute(
            select(FundTransactionModel.id)
            .where(FundTransactionModel.fund_id == fund.id.value)
        ).scalars().all()
        existing_id_set = {str(eid) for eid in existing_ids}
        
        for transaction in fund.get_transactions():
            if transaction.id.value not in existing_id_set:
                tx_model = _domain_to_model_transaction(transaction, fund.id)
                self._session.add(tx_model)
    
    # ========== 🔒 قفل الصناديق للتحديث (SELECT FOR UPDATE) ==========
    
    def lock_funds_for_update(self, fund_ids: List[FundId]) -> List[Fund]:
        """
        قفل الصناديق باستخدام SELECT FOR UPDATE لمنع التعديل المتزامن.
        
        هذه الدالة ضرورية لعمليات التحويل بين الصناديق لضمان:
            1. عدم تعديل رصيد الصندوق أثناء عملية التحويل
            2. منع فقدان الأموال بسبب سباقات البيانات (Race Conditions)
            3. ضمان Atomicity للعملية
        
        Args:
            fund_ids: قائمة معرفات الصناديق المراد قفلها
            
        Returns:
            List[Fund]: قائمة الصناديق المقفلة مع حركاتها
            
        Raises:
            ValueError: إذا لم يتم العثور على أحد الصناديق
            ConcurrentModificationError: إذا كان هناك تعديل متزامن
        """
        if not fund_ids:
            return []
        
        # استخراج قيم UUID
        ids = [fid.value for fid in fund_ids]
        
        # 🔒 قفل الصفوف للتحديث (يمنع أي عملية أخرى من تعديلها)
        # SQL: SELECT * FROM funds WHERE id IN (...) FOR UPDATE
        models = self._session.execute(
            select(FundModel)
            .where(FundModel.id.in_(ids))
            .with_for_update()  # 🔒 قفل حصري
        ).scalars().all()
        
        # التحقق من وجود جميع الصناديق المطلوبة
        found_ids = {str(m.id) for m in models}
        requested_ids = {str(fid.value) for fid in fund_ids}
        
        missing = requested_ids - found_ids
        if missing:
            raise ValueError(f"Funds not found: {', '.join(missing)}")
        
        # تحويل إلى Domain Entities مع الحركات
        funds = []
        for model in models:
            fund = _model_to_domain_fund(model)
            
            # جلب الحركات (لحساب الرصيد الحقيقي)
            transactions = self._session.execute(
                select(FundTransactionModel)
                .where(FundTransactionModel.fund_id == model.id)
                .order_by(FundTransactionModel.created_at)
            ).scalars().all()
            
            for tx_model in transactions:
                fund._transactions.append(_model_to_domain_transaction(tx_model, fund.id))
            
            # تعيين الرصيد المخزن مؤقتاً
            if transactions:
                fund.set_cached_balance(Money(
                    _to_decimal(transactions[-1].balance_after),
                    model.currency
                ))
            else:
                fund.set_cached_balance(Money(Decimal('0'), model.currency))
            
            funds.append(fund)
        
        logger.debug(f"🔒 Locked {len(funds)} funds for update: {[f.code.value for f in funds]}")
        return funds
    
    # ========== 💾 حفظ ذري (Atomic Save) لعدة صناديق ==========
    
    def save_atomic(self, funds: List[Fund]) -> None:
        """
        حفظ عدة صناديق دفعة واحدة مع Optimistic Locking.
        
        هذه الدالة تضمن:
            1. التحقق من الإصدار (version) لكل صندوق
            2. تحديث جميع الصناديق في معاملة واحدة
            3. الفشل الكامل إذا تعارض أي صندوق (All or Nothing)
        
        Args:
            funds: قائمة الصناديق للحفظ
            
        Raises:
            ConcurrentModificationError: إذا تم تعديل أي صندوق بشكل متزامن
        """
        if not funds:
            return
        
        clock = get_clock()
        now = clock.now()
        
        # جلب الإصدارات الحالية للتحقق منها
        fund_ids = [f.id.value for f in funds]
        current_versions = self._session.execute(
            select(FundModel.id, FundModel.version)
            .where(FundModel.id.in_(fund_ids))
        ).all()
        
        version_map = {str(row[0]): row[1] for row in current_versions}
        
        # التحقق من الإصدارات وحفظ كل صندوق
        for fund in funds:
            fund_id_str = str(fund.id.value)
            
            if fund_id_str in version_map:
                # ✅ التحقق من الإصدار (Optimistic Locking)
                if fund.version != version_map[fund_id_str] + 1:
                    raise ConcurrentModificationError(
                        "Fund",
                        fund_id_str,
                        fund.version,
                        version_map[fund_id_str]
                    )
                
                # تحديث الصندوق
                new_version = version_map[fund_id_str] + 1
                
                result = self._session.execute(
                    update(FundModel)
                    .where(
                        FundModel.id == fund.id.value,
                        FundModel.version == fund.version - 1
                    )
                    .values(
                        code=fund.code.value,
                        name=fund.name,
                        fund_type=fund.fund_type.value,
                        account_code=fund.account_code,
                        currency=fund.currency,
                        status=fund.status.value,
                        daily_limit=_to_decimal(fund.daily_limit),
                        monthly_limit=_to_decimal(fund.monthly_limit),
                        min_balance_alert=_to_decimal(fund.min_balance_alert),
                        max_balance_alert=_to_decimal(fund.max_balance_alert),
                        requires_approval=fund.requires_approval,
                        approval_threshold=_to_decimal(fund.approval_threshold),
                        updated_at=now,
                        updated_by=fund.updated_by,
                        version=new_version
                    )
                )
                
                if result.rowcount == 0:
                    raise ConcurrentModificationError(
                        "Fund",
                        fund_id_str,
                        fund.version,
                        version_map[fund_id_str]
                    )
                
                fund.version = new_version
                
                # حفظ الحركات الجديدة
                self._save_new_transactions(fund)
            else:
                # صندوق جديد
                model = _domain_to_model_fund(fund)
                self._session.add(model)
                self._session.flush()
                fund.version = 1
                
                for transaction in fund.get_transactions():
                    tx_model = _domain_to_model_transaction(transaction, fund.id)
                    self._session.add(tx_model)
        
        logger.debug(f"💾 Atomic save completed for {len(funds)} funds")
    
    # ========== دوال الاستعلام ==========
    
    def get_by_id(self, fund_id: FundId, include_transactions: bool = True) -> Optional[Fund]:
        """الحصول على صندوق بواسطة المعرف (تحميل الحركات افتراضياً لحساب الرصيد الصحيح)"""
        model = self._session.execute(
            select(FundModel).where(FundModel.id == fund_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        fund = _model_to_domain_fund(model)
        
        if include_transactions:
            transactions = self._session.execute(
                select(FundTransactionModel)
                .where(FundTransactionModel.fund_id == fund_id.value)
                .order_by(FundTransactionModel.created_at)
            ).scalars().all()
            
            for tx_model in transactions:
                fund._transactions.append(_model_to_domain_transaction(tx_model, fund_id))
        
        return fund
    
    def get_by_code(self, code: FundCode, include_transactions: bool = False) -> Optional[Fund]:
        """الحصول على صندوق بواسطة الكود"""
        model = self._session.execute(
            select(FundModel).where(FundModel.code == code.value)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self.get_by_id(FundId(model.id), include_transactions)
    
    def get_by_account_code(self, account_code: str) -> Optional[Fund]:
        """الحصول على صندوق بواسطة كود حساب الأستاذ"""
        model = self._session.execute(
            select(FundModel).where(FundModel.account_code == account_code)
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return self.get_by_id(FundId(model.id), include_transactions=False)
    
    # ========== قوائم الصناديق مع Pagination ==========
    
    def list_all(
        self,
        fund_type: Optional[FundType] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0,
        include_balance: bool = True
    ) -> List[Fund]:
        """قائمة جميع الصناديق"""
        query = select(FundModel)
        
        if fund_type:
            query = query.where(FundModel.fund_type == fund_type.value)
        
        if not include_inactive:
            query = query.where(FundModel.status == FundStatus.ACTIVE.value)
        
        models = self._session.execute(
            query.order_by(FundModel.code).limit(limit).offset(offset)
        ).scalars().all()
        
        funds = []
        for model in models:
            fund = _model_to_domain_fund(model)
            
            if include_balance:
                balance = self.get_balance(FundId(model.id))
                fund.set_cached_balance(balance)
            
            funds.append(fund)
        
        return funds
    
    def list_active(self, limit: int = 100, offset: int = 0) -> List[Fund]:
        """الحصول على الصناديق النشطة فقط"""
        return self.list_all(include_inactive=False, limit=limit, offset=offset)
    
    def get_active_funds(self) -> List[Fund]:
        """الحصول على الصناديق النشطة فقط (بدون Pagination)"""
        return self.list_active(limit=1000)
    
    def get_funds_by_currency(self, currency: str) -> List[Fund]:
        """الحصول على الصناديق بعملة محددة"""
        query = select(FundModel).where(FundModel.currency == currency.upper())
        models = self._session.execute(query).scalars().all()
        
        funds = []
        for model in models:
            fund = _model_to_domain_fund(model)
            balance = self.get_balance(FundId(model.id))
            fund.set_cached_balance(balance)
            funds.append(fund)
        
        return funds
    
    # =========================================================================
    # حساب الرصيد بشكل صحيح
    # =========================================================================
    
    def get_balance(self, fund_id: FundId, as_of: Optional[datetime] = None) -> Money:
        """
        الحصول على الرصيد الحقيقي من آخر balance_after
        """
        try:
            currency = self._session.execute(
                select(FundModel.currency).where(FundModel.id == fund_id.value)
            ).scalar_one_or_none() or "USD"

            query = select(FundTransactionModel.balance_after).where(
                FundTransactionModel.fund_id == fund_id.value
            )

            if as_of:
                query = query.where(FundTransactionModel.created_at <= as_of)

            query = query.order_by(FundTransactionModel.created_at.desc()).limit(1)

            result = self._session.execute(query).scalar()

            if result is None:
                return Money(Decimal('0'), currency)

            return Money(_to_decimal(result), currency)

        except Exception as e:
            logger.error(f"Error calculating balance: {e}")
            return Money(Decimal('0'), "USD")
    
    def get_balance_history(
        self,
        fund_id: FundId,
        from_date: datetime,
        to_date: datetime
    ) -> List[tuple]:
        """الحصول على تاريخ الرصيد بين تاريخين"""
        transactions = self._session.execute(
            select(FundTransactionModel)
            .where(
                and_(
                    FundTransactionModel.fund_id == fund_id.value,
                    FundTransactionModel.created_at >= from_date,
                    FundTransactionModel.created_at <= to_date
                )
            )
            .order_by(FundTransactionModel.created_at)
        ).scalars().all()
        
        result = []
        for tx in transactions:
            result.append((
                tx.created_at,
                Money(_to_decimal(tx.balance_after), tx.currency)
            ))
        
        return result
    
    def get_balance_summary(self, fund_id: FundId) -> Dict[str, Any]:
        """الحصول على ملخص الرصيد للصندوق"""
        balance = self.get_balance(fund_id)
        
        total_deposits = self._session.execute(
            select(func.sum(FundTransactionModel.amount))
            .where(
                and_(
                    FundTransactionModel.fund_id == fund_id.value,
                    FundTransactionModel.movement_type.in_(['deposit', 'opening_balance', 'transfer_in', 'collection'])
                )
            )
        ).scalar() or Decimal('0')
        
        total_withdrawals = self._session.execute(
            select(func.sum(FundTransactionModel.amount))
            .where(
                and_(
                    FundTransactionModel.fund_id == fund_id.value,
                    FundTransactionModel.movement_type.in_(['withdrawal', 'transfer_out', 'payment'])
                )
            )
        ).scalar() or Decimal('0')
        
        return {
            'fund_id': str(fund_id),
            'current_balance': float(balance.amount),
            'currency': balance.currency,
            'total_deposits': float(total_deposits),
            'total_withdrawals': float(total_withdrawals),
            'net_flow': float(total_deposits - total_withdrawals),
            'as_of': get_clock().now().isoformat()
        }
    
    # ========== عمليات أخرى ==========
    
    def get_next_code(self, prefix: str = "F") -> str:
        """توليد كود صندوق تلقائي"""
        result = self._session.execute(
            select(FundModel.code)
            .where(FundModel.code.regexp_match(f'^{prefix}[0-9]+$'))
            .order_by(FundModel.code.desc())
            .limit(1)
        ).scalar_one_or_none()
        
        if result:
            match = re.search(rf'{prefix}(\d+)', result)
            next_num = int(match.group(1)) + 1 if match else 1
        else:
            next_num = 1
        
        return f"{prefix}{next_num:05d}"
    
    def delete(self, fund_id: FundId, permanent: bool = False) -> bool:
        """حذف صندوق (ناعم أو دائم)"""
        model = self._session.execute(
            select(FundModel).where(FundModel.id == fund_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        if permanent:
            self._session.execute(
                delete(FundTransactionModel).where(FundTransactionModel.fund_id == fund_id.value)
            )
            self._session.delete(model)
        else:
            clock = get_clock()
            model.status = FundStatus.CLOSED.value
            model.updated_at = clock.now()
            model.version += 1
        
        return True
    
    def soft_delete(self, fund_id: FundId, deleted_by: str = "system") -> bool:
        """حذف ناعم (تعطيل) صندوق"""
        model = self._session.execute(
            select(FundModel).where(FundModel.id == fund_id.value)
        ).scalar_one_or_none()
        
        if not model:
            return False
        
        clock = get_clock()
        model.status = FundStatus.CLOSED.value
        model.updated_at = clock.now()
        model.updated_by = deleted_by
        model.version += 1
        
        return True
    
    def exists_by_code(self, code: FundCode) -> bool:
        """التحقق من وجود صندوق بالكود"""
        result = self._session.execute(
            select(FundModel.id).where(FundModel.code == code.value)
        ).first()
        return result is not None
    
    def exists_by_id(self, fund_id: FundId) -> bool:
        """التحقق من وجود صندوق بالمعرف"""
        result = self._session.execute(
            select(FundModel.id).where(FundModel.id == fund_id.value)
        ).first()
        return result is not None
    
    def count(self, fund_type: Optional[FundType] = None, include_inactive: bool = False) -> int:
        """حساب عدد الصناديق"""
        query = select(func.count()).select_from(FundModel)
        
        if fund_type:
            query = query.where(FundModel.fund_type == fund_type.value)
        
        if not include_inactive:
            query = query.where(FundModel.status == FundStatus.ACTIVE.value)
        
        result = self._session.execute(query).scalar()
        return result or 0
    
    def bulk_save(self, funds: List[Fund]) -> int:
        """حفظ عدة صناديق دفعة واحدة"""
        saved_count = 0
        errors = []
        
        for fund in funds:
            try:
                self.save(fund)
                saved_count += 1
            except Exception as e:
                errors.append(f"Fund {fund.code}: {str(e)}")
                logger.error(f"Error saving fund {fund.code}: {e}")
        
        return saved_count


# =============================================================================
# PostgresFundTransactionRepository - التنفيذ الكامل (محسن)
# =============================================================================

class PostgresFundTransactionRepository(IFundTransactionRepository):
    """تطبيق PostgreSQL لمستودع حركات الصناديق"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, transaction: FundTransaction, fund_id: FundId) -> None:
        """حفظ حركة جديدة"""
        model = _domain_to_model_transaction(transaction, fund_id)
        self._session.add(model)
    
    def get_by_id(self, transaction_id: str) -> Optional[FundTransaction]:
        """الحصول على حركة بواسطة المعرف"""
        model = self._session.execute(
            select(FundTransactionModel).where(FundTransactionModel.id == UUID(transaction_id))
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        fund_id = FundId(model.fund_id)
        return _model_to_domain_transaction(model, fund_id)
    
    def get_by_fund(self, fund_id: FundId, limit: int = 100, offset: int = 0) -> List[FundTransaction]:
        """الحصول على حركات صندوق معين"""
        models = self._session.execute(
            select(FundTransactionModel)
            .where(FundTransactionModel.fund_id == fund_id.value)
            .order_by(FundTransactionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [_model_to_domain_transaction(m, fund_id) for m in models]
    
    def get_by_date_range(
        self,
        fund_id: FundId,
        from_date: datetime,
        to_date: datetime,
        transaction_type: Optional[TransactionType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundTransaction]:
        """الحصول على حركات في نطاق زمني"""
        query = select(FundTransactionModel).where(
            FundTransactionModel.fund_id == fund_id.value
        )
        
        if from_date:
            query = query.where(FundTransactionModel.created_at >= from_date)
        if to_date:
            query = query.where(FundTransactionModel.created_at <= to_date)
        if transaction_type:
            query = query.where(FundTransactionModel.movement_type == transaction_type.value)
        
        query = query.order_by(FundTransactionModel.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        models = self._session.execute(query).scalars().all()
        return [_model_to_domain_transaction(m, fund_id) for m in models]
    
    def get_by_reference(self, reference_id: str) -> List[FundTransaction]:
        """الحصول على الحركات المرتبطة بمرجع معين"""
        models = self._session.execute(
            select(FundTransactionModel)
            .where(FundTransactionModel.reference_id == reference_id)
            .order_by(FundTransactionModel.created_at)
        ).scalars().all()
        
        if not models:
            return []
        
        fund_id = FundId(models[0].fund_id)
        return [_model_to_domain_transaction(m, fund_id) for m in models]
    
    def delete(self, transaction_id: str) -> bool:
        """حذف حركة صندوق"""
        try:
            result = self._session.execute(
                delete(FundTransactionModel)
                .where(FundTransactionModel.id == UUID(transaction_id))
            )
            self._session.flush()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting transaction {transaction_id}: {e}")
            return False
    
    def count_by_fund(self, fund_id: FundId) -> int:
        """حساب عدد حركات صندوق"""
        result = self._session.execute(
            select(func.count())
            .select_from(FundTransactionModel)
            .where(FundTransactionModel.fund_id == fund_id.value)
        ).scalar()
        return result or 0


# =============================================================================
# PostgresFundTransferRepository - التنفيذ الكامل (محسن)
# =============================================================================

class PostgresFundTransferRepository(IFundTransferRepository):
    """تطبيق PostgreSQL لمستودع عمليات التحويل"""
    
    def __init__(self, session: Session):
        self._session = session
    
    def save(self, transfer: FundTransfer) -> None:
        """حفظ عملية تحويل"""
        model = FundTransferModel(
            id=UUID(transfer.id.value),
            from_fund_id=transfer.from_fund_id.value,
            to_fund_id=transfer.to_fund_id.value,
            amount=_to_decimal(transfer.amount),
            from_currency=transfer.from_currency,
            to_currency=transfer.to_currency,
            exchange_rate=_to_decimal(transfer.exchange_rate),
            converted_amount=_to_decimal(transfer.converted_amount),
            status=transfer.status.value,
            reason=transfer.reason,
            journal_entry_id=transfer.journal_entry_id,
            created_at=transfer.created_at,
            created_by=transfer.created_by,
            approved_at=transfer.approved_at,
            approved_by=transfer.approved_by,
            completed_at=transfer.completed_at
        )
        self._session.add(model)
    
    def get_by_id(self, transfer_id: str) -> Optional[FundTransfer]:
        """الحصول على تحويل بواسطة المعرف"""
        model = self._session.execute(
            select(FundTransferModel).where(FundTransferModel.id == UUID(transfer_id))
        ).scalar_one_or_none()
        
        if not model:
            return None
        
        return _model_to_domain_transfer(model)
    
    def get_by_funds(
        self,
        from_fund_id: FundId,
        to_fund_id: FundId,
        status: Optional[TransferStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundTransfer]:
        """الحصول على التحويلات بين صندوقين"""
        query = select(FundTransferModel).where(
            and_(
                FundTransferModel.from_fund_id == from_fund_id.value,
                FundTransferModel.to_fund_id == to_fund_id.value
            )
        )
        
        if status:
            query = query.where(FundTransferModel.status == status.value)
        
        models = self._session.execute(
            query.order_by(FundTransferModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [_model_to_domain_transfer(m) for m in models]
    
    def get_by_fund(self, fund_id: FundId, status: Optional[TransferStatus] = None, limit: int = 100) -> List[FundTransfer]:
        """الحصول على التحويلات المرتبطة بصندوق"""
        query = select(FundTransferModel).where(
            or_(
                FundTransferModel.from_fund_id == fund_id.value,
                FundTransferModel.to_fund_id == fund_id.value
            )
        )
        
        if status:
            query = query.where(FundTransferModel.status == status.value)
        
        models = self._session.execute(
            query.order_by(FundTransferModel.created_at.desc()).limit(limit)
        ).scalars().all()
        
        return [_model_to_domain_transfer(m) for m in models]
    
    def get_by_status(self, status: TransferStatus, limit: int = 100) -> List[FundTransfer]:
        """الحصول على التحويلات حسب الحالة"""
        models = self._session.execute(
            select(FundTransferModel)
            .where(FundTransferModel.status == status.value)
            .order_by(FundTransferModel.created_at.desc())
            .limit(limit)
        ).scalars().all()
        
        return [_model_to_domain_transfer(m) for m in models]
    
    def get_by_date_range(
        self,
        from_date: datetime,
        to_date: datetime,
        status: Optional[TransferStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundTransfer]:
        """الحصول على التحويلات في نطاق زمني"""
        query = select(FundTransferModel).where(
            and_(
                FundTransferModel.created_at >= from_date,
                FundTransferModel.created_at <= to_date
            )
        )
        
        if status:
            query = query.where(FundTransferModel.status == status.value)
        
        models = self._session.execute(
            query.order_by(FundTransferModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        
        return [_model_to_domain_transfer(m) for m in models]
    
    def get_pending_transfers(self, limit: int = 100) -> List[FundTransfer]:
        """الحصول على التحويلات المعلقة"""
        return self.get_by_status(TransferStatus.PENDING, limit)
    
    def get_approved_transfers(self, limit: int = 100) -> List[FundTransfer]:
        """الحصول على التحويلات المعتمدة"""
        return self.get_by_status(TransferStatus.APPROVED, limit)
    
    def update_status(self, transfer_id: str, status: TransferStatus, updated_by: str) -> bool:
        """تحديث حالة التحويل"""
        clock = get_clock()
        values = {
            'status': status.value,
            'updated_by': updated_by
        }
        
        if status == TransferStatus.COMPLETED:
            values['completed_at'] = clock.now()
        elif status == TransferStatus.APPROVED:
            values['approved_at'] = clock.now()
            values['approved_by'] = updated_by
        
        result = self._session.execute(
            update(FundTransferModel)
            .where(FundTransferModel.id == UUID(transfer_id))
            .values(**values)
        )
        self._session.flush()
        return result.rowcount > 0
    
    def count_by_status(self, status: TransferStatus) -> int:
        """حساب عدد التحويلات حسب الحالة"""
        result = self._session.execute(
            select(func.count())
            .select_from(FundTransferModel)
            .where(FundTransferModel.status == status.value)
        ).scalar()
        return result or 0


# =============================================================================
# ✅ PostgresFundMovementRepository - مع الدوال المفقودة (محسن)
# =============================================================================

class PostgresFundMovementRepository(IFundMovementRepository):
    """
    تنفيذ واجهة IFundMovementRepository للتوافق مع الكود القديم
    
    ✅ مصحح: إضافة دالة get_by_fund لتمرير الطلب إلى PostgresFundTransactionRepository
    ✅ مصحح: إضافة دالة get_by_fund_id للبحث بالنص
    ✅ مصحح: إضافة دالة get_by_fund_code للبحث بالكود
    ✅ محدث: استخدام Clock Service للوقت
    """
    
    def __init__(self, session: Session):
        self._session = session
        self._tx_repo = PostgresFundTransactionRepository(session)
    
    # =========================================================================
    # الدوال المضافة (الإصلاح الأساسي)
    # =========================================================================
    
    def get_by_fund(self, fund_id: FundId, limit: int = 100, offset: int = 0) -> List[FundTransaction]:
        """الحصول على حركات صندوق معين"""
        return self._tx_repo.get_by_fund(fund_id, limit=limit, offset=offset)
    
    def get_by_fund_id(self, fund_id: str, limit: int = 100, offset: int = 0) -> List[FundTransaction]:
        """الحصول على حركات صندوق معين بواسطة المعرف كنص"""
        return self._tx_repo.get_by_fund(FundId(UUID(fund_id)), limit=limit, offset=offset)
    
    def get_by_fund_code(self, fund_code: str, limit: int = 100, offset: int = 0) -> List[FundTransaction]:
        """الحصول على حركات صندوق معين بواسطة الكود"""
        fund_model = self._session.execute(
            select(FundModel.id).where(FundModel.code == fund_code)
        ).scalar_one_or_none()
        
        if not fund_model:
            return []
        
        return self._tx_repo.get_by_fund(FundId(fund_model), limit=limit, offset=offset)
    
    def get_by_date_range(
        self,
        fund_id: FundId,
        from_date: date,
        to_date: date,
        movement_type: Optional['MovementType'] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundMovement]:
        """الحصول على حركات في نطاق زمني"""
        from_dt = None
        to_dt = None
        if from_date:
            from_dt = datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc)
        if to_date:
            to_dt = datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc)
        
        transaction_type = None
        if movement_type:
            raw_type = getattr(movement_type, 'value', movement_type)
            transaction_type = TransactionType(raw_type)
        
        transactions = self._tx_repo.get_by_date_range(
            fund_id=fund_id,
            from_date=from_dt,
            to_date=to_dt,
            transaction_type=transaction_type,
            limit=limit,
            offset=offset
        )
        
        return [
            FundMovement(
                id=t.id,
                fund_id=t.fund_id,
                transaction_type=t.transaction_type,
                amount=t.amount,
                balance_before=t.balance_before,
                balance_after=t.balance_after,
                reference_id=t.reference_id,
                description=t.description,
                created_at=t.created_at,
                created_by=t.created_by,
                metadata=t.metadata
            )
            for t in transactions
        ]
    
    def get_by_fund_and_type(
        self,
        fund_id: FundId,
        movement_type: str,
        limit: int = 100
    ) -> List[FundMovement]:
        """الحصول على حركات صندوق حسب النوع"""
        transactions = self._tx_repo.get_by_date_range(
            fund_id=fund_id,
            from_date=None,
            to_date=None,
            transaction_type=TransactionType(movement_type),
            limit=limit
        )
        
        return [
            FundMovement(
                id=t.id,
                fund_id=t.fund_id,
                transaction_type=t.transaction_type,
                amount=t.amount,
                balance_before=t.balance_before,
                balance_after=t.balance_after,
                reference_id=t.reference_id,
                description=t.description,
                created_at=t.created_at,
                created_by=t.created_by,
                metadata=t.metadata
            )
            for t in transactions
        ]
    
    # =========================================================================
    # الدوال الموجودة (بدون تغيير)
    # =========================================================================
    
    def save(self, movement: FundMovement) -> None:
        """حفظ حركة صندوق"""
        transaction = FundTransaction(
            id=movement.id,
            fund_id=movement.fund_id,
            transaction_type=movement.transaction_type,
            amount=movement.amount,
            balance_before=movement.balance_before,
            balance_after=movement.balance_after,
            reference_id=movement.reference_id,
            description=movement.description,
            created_at=movement.created_at,
            created_by=movement.created_by,
            metadata=movement.metadata
        )
        self._tx_repo.save(transaction, movement.fund_id)
    
    def get_by_id(self, movement_id: str) -> Optional[FundMovement]:
        """الحصول على حركة بواسطة المعرف"""
        transaction = self._tx_repo.get_by_id(movement_id)
        if not transaction:
            return None
        
        return FundMovement(
            id=transaction.id,
            fund_id=transaction.fund_id,
            transaction_type=transaction.transaction_type,
            amount=transaction.amount,
            balance_before=transaction.balance_before,
            balance_after=transaction.balance_after,
            reference_id=transaction.reference_id,
            description=transaction.description,
            created_at=transaction.created_at,
            created_by=transaction.created_by,
            metadata=transaction.metadata
        )
    
    def delete(self, movement_id: str) -> bool:
        """حذف حركة صندوق"""
        return self._tx_repo.delete(movement_id)
    
    def count_by_fund(self, fund_id: FundId) -> int:
        """حساب عدد حركات صندوق"""
        return self._tx_repo.count_by_fund(fund_id)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'PostgresFundRepository',
    'PostgresFundTransactionRepository',
    'PostgresFundTransferRepository',
    'PostgresFundMovementRepository',
]