"""
Funds Services - خدمات الصناديق النقدية
"""

from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone

from core.domain.funds.entities import Fund, FundTransaction, FundTransfer
from core.domain.funds.value_objects import (
    FundId, FundCode, FundType, TransactionType, FundStatus,
    Money, TransferStatus
)
from core.domain.funds.interfaces import (
    IFundRepository, IFundTransactionRepository, IFundTransferRepository
)
from core.domain.accounting.interfaces import IUnitOfWork
from core.domain.shared.clock import get_clock


class FundService:
    """
    خدمة الصناديق النقدية - تدير عمليات الصناديق
    """
    
    def __init__(
        self,
        fund_repo: IFundRepository,
        movement_repo: IFundTransactionRepository,
        transfer_repo: IFundTransferRepository,
        uow: IUnitOfWork
    ):
        self._fund_repo = fund_repo
        self._movement_repo = movement_repo
        self._transfer_repo = transfer_repo
        self._uow = uow
        self._clock = get_clock()
    
    # =========================================================================
    # عمليات الصندوق الأساسية
    # =========================================================================
    
    def create_fund(
        self,
        code: str,
        name: str,
        account_code: str,
        fund_type: str = "main",
        currency: str = "USD",
        daily_limit: Decimal = Decimal('0'),
        monthly_limit: Decimal = Decimal('0'),
        min_balance_alert: Decimal = Decimal('0'),
        max_balance_alert: Decimal = Decimal('0'),
        opening_balance: Optional[Decimal] = None,
        created_by: str = "system"
    ) -> Fund:
        """إنشاء صندوق جديد"""
        fund = Fund.create(
            code=code,
            name=name,
            account_code=account_code,
            fund_type=FundType(fund_type),
            currency=currency,
            created_by=created_by,
            daily_limit=Money(daily_limit, currency),
            monthly_limit=Money(monthly_limit, currency),
            min_balance_alert=Money(min_balance_alert, currency),
            max_balance_alert=Money(max_balance_alert, currency),
            opening_balance=Money(opening_balance, currency) if opening_balance else None
        )
        
        self._fund_repo.save(fund)
        return fund
    
    def get_fund(self, fund_id: FundId) -> Optional[Fund]:
        """الحصول على صندوق"""
        return self._fund_repo.get_by_id(fund_id, include_transactions=True)
    
    def get_fund_by_code(self, code: FundCode) -> Optional[Fund]:
        """الحصول على صندوق بالكود"""
        return self._fund_repo.get_by_code(code, include_transactions=True)
    
    def list_funds(
        self,
        fund_type: Optional[FundType] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Fund]:
        """قائمة الصناديق"""
        return self._fund_repo.list_all(
            fund_type=fund_type,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
            include_balance=True
        )
    
    def update_fund(
        self,
        fund_id: FundId,
        name: Optional[str] = None,
        account_code: Optional[str] = None,
        currency: Optional[str] = None,
        daily_limit: Optional[Decimal] = None,
        monthly_limit: Optional[Decimal] = None,
        min_balance_alert: Optional[Decimal] = None,
        max_balance_alert: Optional[Decimal] = None,
        requires_approval: Optional[bool] = None,
        approval_threshold: Optional[Decimal] = None,
        updated_by: str = "system"
    ) -> Fund:
        """تحديث صندوق"""
        fund = self._fund_repo.get_by_id(fund_id)
        if not fund:
            raise ValueError(f"Fund {fund_id} not found")
        
        # تحديث البيانات
        fund.update(
            name=name,
            account_code=account_code,
            currency=currency,
            daily_limit=Money(daily_limit, fund.currency) if daily_limit is not None else None,
            monthly_limit=Money(monthly_limit, fund.currency) if monthly_limit is not None else None,
            min_balance_alert=Money(min_balance_alert, fund.currency) if min_balance_alert is not None else None,
            max_balance_alert=Money(max_balance_alert, fund.currency) if max_balance_alert is not None else None,
            requires_approval=requires_approval,
            approval_threshold=Money(approval_threshold, fund.currency) if approval_threshold is not None else None,
            updated_by=updated_by
        )
        
        self._fund_repo.save(fund)
        return fund
    
    def delete_fund(self, fund_id: FundId, permanent: bool = False, deleted_by: str = "system") -> bool:
        """حذف صندوق"""
        return self._fund_repo.delete(fund_id, permanent=permanent)
    
    # =========================================================================
    # عمليات الإيداع والسحب
    # =========================================================================
    
    def deposit(
        self,
        fund_id: FundId,
        amount: Decimal,
        reason: str,
        currency: Optional[str] = None,
        reference_id: Optional[str] = None,
        created_by: str = "system"
    ) -> FundTransaction:
        """إيداع في الصندوق"""
        fund = self._fund_repo.get_by_id(fund_id, include_transactions=True)
        if not fund:
            raise ValueError(f"Fund {fund_id} not found")
        
        # التحقق من العملة
        if currency and currency != fund.currency:
            raise ValueError(f"Currency mismatch: fund uses {fund.currency}, got {currency}")
        
        # تنفيذ الإيداع
        transaction = fund.deposit(
            amount=Money(amount, fund.currency),
            reason=reason,
            created_by=created_by,
            reference_id=reference_id
        )
        
        self._fund_repo.save(fund)
        return transaction
    
    def withdraw(
        self,
        fund_id: FundId,
        amount: Decimal,
        reason: str,
        currency: Optional[str] = None,
        reference_id: Optional[str] = None,
        created_by: str = "system"
    ) -> FundTransaction:
        """سحب من الصندوق"""
        fund = self._fund_repo.get_by_id(fund_id, include_transactions=True)
        if not fund:
            raise ValueError(f"Fund {fund_id} not found")
        
        # التحقق من العملة
        if currency and currency != fund.currency:
            raise ValueError(f"Currency mismatch: fund uses {fund.currency}, got {currency}")
        
        # تنفيذ السحب
        transaction = fund.withdraw(
            amount=Money(amount, fund.currency),
            reason=reason,
            created_by=created_by,
            reference_id=reference_id
        )
        
        self._fund_repo.save(fund)
        return transaction
    
    # =========================================================================
    # عمليات التحويل
    # =========================================================================
    
    def transfer(
        self,
        from_fund_id: FundId,
        to_fund_id: FundId,
        amount: Decimal,
        reason: str,
        from_currency: Optional[str] = None,
        to_currency: Optional[str] = None,
        auto_convert: bool = True,
        created_by: str = "system"
    ) -> FundTransfer:
        """تحويل بين صناديق"""
        if from_fund_id == to_fund_id:
            raise ValueError("Cannot transfer to the same fund")
        
        # الحصول على الصندوقين
        from_fund = self._fund_repo.get_by_id(from_fund_id, include_transactions=True)
        to_fund = self._fund_repo.get_by_id(to_fund_id, include_transactions=True)
        
        if not from_fund:
            raise ValueError(f"Source fund {from_fund_id} not found")
        if not to_fund:
            raise ValueError(f"Target fund {to_fund_id} not found")
        
        # التحقق من العملات
        from_currency = from_currency or from_fund.currency
        to_currency = to_currency or to_fund.currency
        
        # حساب سعر الصرف (تبسيط: 1:1 إذا كانت العملات متطابقة)
        exchange_rate = Decimal('1')
        if from_currency != to_currency:
            if not auto_convert:
                raise ValueError(
                    f"Cannot transfer between different currencies without auto-convert: "
                    f"{from_currency} -> {to_currency}"
                )
            # هنا يمكن إضافة منطق جلب سعر الصرف من خدمة العملات
            # مؤقتاً: استخدام سعر ثابت
            exchange_rate = Decimal('1')  # سيتم استبداله بسعر حقيقي
        
        # إنشاء التحويل
        transfer = FundTransfer.create(
            from_fund_id=from_fund.id,
            to_fund_id=to_fund.id,
            amount=Money(amount, from_currency),
            exchange_rate=exchange_rate,
            reason=reason,
            created_by=created_by
        )
        
        # تنفيذ التحويل (تبسيط: مباشر بدون موافقة)
        transfer.approve(created_by)
        
        # إنشاء القيد المحاسبي هنا إذا لزم الأمر
        
        self._transfer_repo.save(transfer)
        return transfer
    
    # =========================================================================
    # عمليات الاستعلام
    # =========================================================================
    
    def get_balance(self, fund_id: FundId, as_of: Optional[datetime] = None) -> Money:
        """الحصول على رصيد الصندوق"""
        fund = self._fund_repo.get_by_id(fund_id)
        if not fund:
            raise ValueError(f"Fund {fund_id} not found")
        
        if as_of:
            return fund.get_balance_at(as_of)
        return fund.current_balance
    
    def get_movements(
        self,
        fund_id: FundId,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        movement_type: Optional[TransactionType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundTransaction]:
        """الحصول على حركات الصندوق"""
        return self._movement_repo.get_by_date_range(
            fund_id=fund_id,
            from_date=from_date,
            to_date=to_date,
            transaction_type=movement_type,
            limit=limit,
            offset=offset
        )
    
    def get_transfers(
        self,
        from_fund_id: Optional[FundId] = None,
        to_fund_id: Optional[FundId] = None,
        status: Optional[TransferStatus] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[FundTransfer]:
        """الحصول على عمليات التحويل"""
        if from_fund_id and to_fund_id:
            return self._transfer_repo.get_by_funds(
                from_fund_id=from_fund_id,
                to_fund_id=to_fund_id,
                status=status,
                limit=limit,
                offset=offset
            )
        elif from_fund_id:
            return self._transfer_repo.get_by_fund(
                fund_id=from_fund_id,
                status=status,
                limit=limit
            )
        elif to_fund_id:
            return self._transfer_repo.get_by_fund(
                fund_id=to_fund_id,
                status=status,
                limit=limit
            )
        else:
            return self._transfer_repo.get_by_status(
                status=status or TransferStatus.PENDING,
                limit=limit
            )
    
    def get_statistics(self, fund_id: FundId) -> Dict[str, Any]:
        """الحصول على إحصائيات الصندوق"""
        fund = self._fund_repo.get_by_id(fund_id, include_transactions=True)
        if not fund:
            raise ValueError(f"Fund {fund_id} not found")
        
        transactions = fund.get_transactions()
        total_deposits = fund.get_total_deposits()
        total_withdrawals = fund.get_total_withdrawals()
        
        return {
            'fund_id': str(fund.id),
            'fund_code': fund.code.value,
            'fund_name': fund.name,
            'currency': fund.currency,
            'current_balance': float(fund.current_balance.amount),
            'total_deposits': float(total_deposits.amount),
            'total_withdrawals': float(total_withdrawals.amount),
            'net_flow': float(total_deposits.amount - total_withdrawals.amount),
            'transactions_count': len(transactions),
            'status': fund.status.value,
            'is_active': fund.is_active,
            'created_at': fund.created_at.isoformat() if fund.created_at else None,
            'updated_at': fund.updated_at.isoformat() if fund.updated_at else None,
        }