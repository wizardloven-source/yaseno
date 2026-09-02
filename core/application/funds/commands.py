# core/application/funds/commands.py
"""
Commands and Queries for Funds Module
✅ مصحح: استخدام FundId بدلاً من str للحفاظ على سلامة النوع
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from decimal import Decimal
from uuid import UUID

# ✅ استيراد FundId من Domain Layer
from core.domain.funds.value_objects import FundId


# ========== COMMANDS ==========

@dataclass(frozen=True)
class CreateFundCommand:
    """أمر إنشاء صندوق جديد"""
    code: str
    name: str
    account_code: str
    fund_type: str = "main"
    currency: str = "USD"
    daily_limit: Decimal = Decimal('0')
    monthly_limit: Decimal = Decimal('0')
    min_balance_alert: Decimal = Decimal('0')
    max_balance_alert: Decimal = Decimal('0')
    opening_balance: Optional[Decimal] = None
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateFundCommand:
    """أمر تحديث صندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    name: Optional[str] = None
    account_code: Optional[str] = None
    currency: Optional[str] = None
    daily_limit: Optional[Decimal] = None
    monthly_limit: Optional[Decimal] = None
    min_balance_alert: Optional[Decimal] = None
    max_balance_alert: Optional[Decimal] = None
    requires_approval: Optional[bool] = None
    approval_threshold: Optional[Decimal] = None
    updated_by: str = "system"
    version: int = 1


@dataclass(frozen=True)
class DeleteFundCommand:
    """أمر حذف صندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    permanent: bool = False
    deleted_by: str = "system"


@dataclass(frozen=True)
class ActivateFundCommand:
    """أمر تنشيط صندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    activated_by: str = "system"


@dataclass(frozen=True)
class DeactivateFundCommand:
    """أمر تعطيل صندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    reason: Optional[str] = None
    deactivated_by: str = "system"


@dataclass(frozen=True)
class DepositToFundCommand:
    """أمر إيداع في صندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    amount: Decimal
    reason: str
    currency: Optional[str] = None
    reference_id: Optional[str] = None
    exchange_rate_used: Optional[Decimal] = None
    created_by: str = "system"


@dataclass(frozen=True)
class WithdrawFromFundCommand:
    """أمر سحب من صندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    amount: Decimal
    reason: str
    currency: Optional[str] = None
    reference_id: Optional[str] = None
    exchange_rate_used: Optional[Decimal] = None
    created_by: str = "system"


@dataclass(frozen=True)
class TransferBetweenFundsCommand:
    """أمر تحويل بين صندوقين"""
    from_fund_id: FundId  # ✅ تغيير من str إلى FundId
    to_fund_id: FundId    # ✅ تغيير من str إلى FundId
    amount: Decimal
    reason: str
    from_currency: Optional[str] = None
    to_currency: Optional[str] = None
    auto_convert: bool = True
    created_by: str = "system"


# ========== QUERIES ==========

@dataclass(frozen=True)
class GetFundQuery:
    """استعلام لجلب صندوق بواسطة المعرف"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    include_balance: bool = True
    include_movements: bool = False
    movements_limit: int = 50


@dataclass(frozen=True)
class GetFundByCodeQuery:
    """استعلام لجلب صندوق بواسطة الكود"""
    code: str
    include_balance: bool = True
    include_movements: bool = False


@dataclass(frozen=True)
class GetFundBalanceQuery:
    """استعلام لجلب رصيد الصندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    as_of_date: Optional[datetime] = None
    include_history: bool = False


@dataclass(frozen=True)
class ListFundsQuery:
    """استعلام لجلب قائمة الصناديق"""
    fund_type: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    include_inactive: bool = False
    include_balance: bool = True
    search_term: Optional[str] = None
    sort_by: str = "code"
    sort_desc: bool = False
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetFundMovementsQuery:
    """استعلام لجلب حركات الصندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    movement_type: Optional[str] = None
    transaction_type: Optional[str] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    reference_id: Optional[str] = None
    sort_by: str = "created_at"
    sort_desc: bool = True
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class GetFundStatisticsQuery:
    """استعلام لجلب إحصائيات الصندوق"""
    fund_id: FundId  # ✅ تغيير من str إلى FundId
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    include_daily_breakdown: bool = False


@dataclass(frozen=True)
class ListFundTransfersQuery:
    """استعلام لجلب قائمة التحويلات بين الصناديق"""
    from_fund_id: Optional[FundId] = None  # ✅ تغيير من str إلى FundId
    to_fund_id: Optional[FundId] = None    # ✅ تغيير من str إلى FundId
    status: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    created_by: Optional[str] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class SearchFundsQuery:
    """استعلام للبحث في الصناديق"""
    search_term: str
    fund_type: Optional[str] = None
    status: Optional[str] = None
    include_inactive: bool = False
    limit: int = 50


# ========== ALIASES FOR BACKWARD COMPATIBILITY ==========

# للتوافق مع الكود القديم
GetFundBalanceCommand = GetFundBalanceQuery


# ========== EXPORTS ==========

__all__ = [
    # Commands
    "CreateFundCommand",
    "UpdateFundCommand",
    "DeleteFundCommand",
    "ActivateFundCommand",
    "DeactivateFundCommand",
    "DepositToFundCommand",
    "WithdrawFromFundCommand",
    "TransferBetweenFundsCommand",
    
    # Queries
    "GetFundQuery",
    "GetFundByCodeQuery",
    "GetFundBalanceQuery",
    "ListFundsQuery",
    "GetFundMovementsQuery",
    "GetFundStatisticsQuery",
    "ListFundTransfersQuery",
    "SearchFundsQuery",
    
    # Aliases
    "GetFundBalanceCommand",
]