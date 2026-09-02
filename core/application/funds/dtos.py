# core/application/funds/dtos.py
"""
Data Transfer Objects for Funds Module
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


@dataclass(frozen=True)
class FundMovementDTO:
    """حركة صندوق - DTO"""
    id: str
    fund_id: str
    movement_type: str
    amount: float
    currency: str
    balance_after: float
    reason: str
    created_at: datetime
    created_by: str
    reference_id: Optional[str] = None
    exchange_rate_used: Optional[float] = None
    from_fund_code: Optional[str] = None
    to_fund_code: Optional[str] = None
    
    @property
    def amount_formatted(self) -> str:
        if self.currency == "LBP":
            return f"{abs(self.amount):,.0f} {self.currency}"
        return f"{abs(self.amount):,.2f} {self.currency}"
    
    @property
    def is_deposit(self) -> bool:
        return self.movement_type == "deposit"
    
    @property
    def is_withdraw(self) -> bool:
        return self.movement_type == "withdraw"


@dataclass(frozen=True)
class FundDTO:
    """صندوق - DTO كامل"""
    id: str
    code: str
    name: str
    fund_type: str
    account_code: str
    currency: str
    balance: float
    status: str
    daily_limit: float
    monthly_limit: float
    min_balance_alert: float
    max_balance_alert: float
    requires_approval: bool
    approval_threshold: float
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    version: int
    is_active: bool
    movements: List[FundMovementDTO] = None
    
    @property
    def balance_formatted(self) -> str:
        if self.currency == "LBP":
            return f"{self.balance:,.0f} {self.currency}"
        return f"{self.balance:,.2f} {self.currency}"
    
    @property
    def display_name(self) -> str:
        return f"{self.code} - {self.name}"
    
    @property
    def is_over_daily_limit(self, amount: float) -> bool:
        if self.daily_limit <= 0:
            return False
        return amount > self.daily_limit
    
    @property
    def is_low_balance(self) -> bool:
        if self.min_balance_alert <= 0:
            return False
        return self.balance <= self.min_balance_alert
    
    @property
    def is_high_balance(self) -> bool:
        if self.max_balance_alert <= 0:
            return False
        return self.balance >= self.max_balance_alert


@dataclass(frozen=True)
class FundSummaryDTO:
    """ملخص الصناديق - DTO"""
    total_funds: int
    active_funds: int
    inactive_funds: int
    total_balance_usd: float
    total_balance_lbp: float
    funds_by_currency: dict
    
    def to_dict(self) -> dict:
        return {
            'total_funds': self.total_funds,
            'active_funds': self.active_funds,
            'inactive_funds': self.inactive_funds,
            'total_balance_usd': self.total_balance_usd,
            'total_balance_lbp': self.total_balance_lbp,
            'funds_by_currency': self.funds_by_currency,
        }


@dataclass(frozen=True)
class CreateFundDTO:
    """بيانات إنشاء صندوق جديد"""
    code: str
    name: str
    account_code: str
    fund_type: str = "main"
    currency: str = "USD"
    daily_limit: float = 0.0
    monthly_limit: float = 0.0
    min_balance_alert: float = 0.0
    max_balance_alert: float = 0.0
    created_by: str = "system"


@dataclass(frozen=True)
class UpdateFundDTO:
    """بيانات تحديث صندوق"""
    fund_id: str
    name: Optional[str] = None
    account_code: Optional[str] = None
    currency: Optional[str] = None
    daily_limit: Optional[float] = None
    monthly_limit: Optional[float] = None
    min_balance_alert: Optional[float] = None
    max_balance_alert: Optional[float] = None
    updated_by: str = "system"
    version: int = 1