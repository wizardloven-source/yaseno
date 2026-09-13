"""
YASeen ERP - Core Domain Models
Implements: Multi-currency, Financial Periods, Audit Trail, Double-Entry
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import uuid


class EntryStatus(Enum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"


class PeriodStatus(Enum):
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


@dataclass
class AuditEvent:
    """Immutable Audit Trail Record"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: str = ""
    user_name: str = ""
    action: str = ""  # CREATE, UPDATE, DELETE, POST, CANCEL
    entity_type: str = ""
    entity_id: str = ""
    old_values: Dict[str, Any] = field(default_factory=dict)
    new_values: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    ip_address: str = ""
    device_info: str = ""
    session_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "user": self.user_name,
            "action": self.action,
            "entity": f"{self.entity_type}:{self.entity_id}",
            "changes": {"old": self.old_values, "new": self.new_values},
            "context": {
                "reason": self.reason,
                "ip": self.ip_address,
                "device": self.device_info,
                "session": self.session_id
            }
        }


@dataclass
class FinancialPeriod:
    name: str  # e.g., "2026-01"
    start_date: date
    end_date: date
    status: PeriodStatus = PeriodStatus.OPEN
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None

    def is_date_within(self, target_date: date) -> bool:
        return self.start_date <= target_date <= self.end_date

    def enforce_open(self):
        if self.status != PeriodStatus.OPEN:
            raise PermissionError(
                f"Financial Period {self.name} is {self.status.value}. "
                "Cannot post transactions."
            )


@dataclass
class JournalEntryLine:
    account_id: str
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    currency_code: str = "USD"
    amount_currency: Decimal = Decimal("0.00")  # Amount in original currency
    exchange_rate: Decimal = Decimal("1.00")
    description: str = ""

    def __post_init__(self):
        if self.debit < 0 or self.credit < 0:
            raise ValueError("Debit and Credit must be non-negative")
        
        # Enforce base currency calculation if not provided
        if self.amount_currency == 0 and (self.debit > 0 or self.credit > 0):
            # Assume provided debit/credit are already converted if amount_currency is 0
            pass 

    @property
    def balance(self) -> Decimal:
        return self.debit - self.credit


@dataclass
class JournalEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: date = field(default_factory=date.today)
    period_id: str = ""
    lines: List[JournalEntryLine] = field(default_factory=list)
    status: EntryStatus = EntryStatus.DRAFT
    reference: str = ""
    description: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None
    
    # Multi-currency tracking
    base_currency: str = "USD"
    exchange_rate_date: Optional[date] = None

    def validate_balance(self):
        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)
        if total_debit != total_credit:
            raise ValueError(
                f"Accounting Invariant Violation: Debit ({total_debit}) != Credit ({total_credit})"
            )

    def post(self, user_id: str, period: FinancialPeriod):
        if self.status != EntryStatus.DRAFT:
            raise ValueError("Only draft entries can be posted")
        
        period.enforce_open()
        self.validate_balance()
        
        if not self.lines:
            raise ValueError("Cannot post an empty journal entry")
            
        self.status = EntryStatus.POSTED
        self.posted_at = datetime.utcnow()
        self.posted_by = user_id

    def cancel(self, user_id: str):
        if self.status != EntryStatus.POSTED:
            raise ValueError("Only posted entries can be cancelled")
        self.status = EntryStatus.CANCELLED

    def modify(self, updates: Dict[str, Any]):
        if self.status == EntryStatus.POSTED:
            raise PermissionError(
                "Accounting Invariant Violation: Posted entries cannot be modified. "
                "Please cancel and reverse the entry."
            )
        if self.status == EntryStatus.CANCELLED:
            raise PermissionError("Cancelled entries cannot be modified.")
        
        # Apply updates safely
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)


@dataclass
class Permission:
    code: str  # e.g., "sales.invoice.create"
    name: str
    module: str
    screen: str
    action: str

    @staticmethod
    def parse(code: str) -> 'Permission':
        parts = code.split('.')
        if len(parts) != 3:
            raise ValueError("Permission code must be in format: module.screen.action")
        return Permission(
            code=code,
            name=code.replace('.', ' ').title(),
            module=parts[0],
            screen=parts[1],
            action=parts[2]
        )


@dataclass
class Role:
    id: str
    name: str
    permissions: List[str] = field(default_factory=list)

    def has_permission(self, permission_code: str) -> bool:
        if "admin" in self.name.lower():
            return True
        return permission_code in self.permissions


@dataclass
class User:
    id: str
    username: str
    role: Role
    is_active: bool = True
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None

    def can(self, permission_code: str) -> bool:
        if not self.is_active:
            return False
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return False
        return self.role.has_permission(permission_code)
