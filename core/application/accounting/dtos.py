# core/application/accounting/dtos.py

"""
Data Transfer Objects (DTOs) for the Accounting Application Layer
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any


# ============================================================
# ✅ إضافة JournalLineDTO (المطلوب)
# ============================================================

@dataclass
class JournalLineDTO:
    """
    DTO لسطر قيد محاسبي - يستخدم في الطلبات والاستجابات
    
    Attributes:
        account_code: كود الحساب
        debit: مبلغ المدين
        credit: مبلغ الدائن
        description: وصف السطر (اختياري)
        currency: العملة
    """
    account_code: str
    debit: Decimal
    credit: Decimal
    description: Optional[str] = None
    currency: str = "USD"
    
    @property
    def amount(self) -> Decimal:
        """المبلغ الصافي (موجب للمدين، سالب للدائن)"""
        if self.debit > 0:
            return self.debit
        return -self.credit
    
    @property
    def is_debit(self) -> bool:
        return self.debit > 0
    
    @property
    def is_credit(self) -> bool:
        return self.credit > 0


# ============================================================
# Journal Entry DTOs (الموجودة)
# ============================================================

@dataclass
class JournalLineResponseDTO:
    """سطر قيد محاسبي - DTO للاستجابة"""
    line_id: str
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    description: Optional[str] = None
    currency: str = "USD"
    
    @property
    def amount(self) -> Decimal:
        if self.debit > 0:
            return self.debit
        return -self.credit
    
    @property
    def is_debit(self) -> bool:
        return self.debit > 0
    
    @property
    def is_credit(self) -> bool:
        return self.credit > 0


@dataclass
class JournalEntryResponseDTO:
    """قيد محاسبي - DTO للاستجابة"""
    id: str
    date: datetime
    description: str
    is_posted: bool
    total_debit: Decimal
    total_credit: Decimal
    lines: List[JournalLineResponseDTO]
    version: int
    created_at: datetime
    created_by: str
    notes: Optional[str] = None
    posted_at: Optional[datetime] = None
    posted_by: Optional[str] = None
    reversed_entry_id: Optional[str] = None
    reverses_entry_id: Optional[str] = None
    currency: str = "USD"
    
    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debit - self.total_credit) < Decimal('0.01')
    
    @property
    def line_count(self) -> int:
        return len(self.lines)


@dataclass
class CreateJournalEntryDTO:
    """بيانات إنشاء قيد محاسبي"""
    date: datetime
    description: str
    lines: List[Dict[str, Any]]
    transaction_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    created_by: str = "system"


@dataclass
class UpdateJournalEntryDTO:
    """بيانات تحديث قيد محاسبي"""
    entry_id: str
    version: int
    description: Optional[str] = None
    lines: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    updated_by: str = "system"


# ============================================================
# Balance DTOs
# ============================================================

@dataclass
class AccountBalanceResponseDTO:
    """رصيد حساب - DTO"""
    account_code: str
    account_name: str
    balance: Decimal
    currency: str
    as_of_date: datetime
    total_debit: Decimal = Decimal('0')
    total_credit: Decimal = Decimal('0')
    
    @property
    def balance_formatted(self) -> str:
        return f"{self.balance:,.2f} {self.currency}"


@dataclass
class TrialBalanceResponseDTO:
    """ميزان المراجعة - DTO"""
    as_of_date: datetime
    currency: str
    accounts: List[AccountBalanceResponseDTO]
    total_debits: Decimal
    total_credits: Decimal
    is_balanced: bool
    difference: Decimal
    account_count: int


# ============================================================
# Account DTOs
# ============================================================

@dataclass
class AccountDTO:
    """حساب محاسبي - DTO"""
    code: str
    name: str
    account_type: str
    is_active: bool
    currency: str
    parent_code: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1


@dataclass
class CreateAccountDTO:
    """بيانات إنشاء حساب"""
    code: str
    name: str
    account_type: str
    currency: str = "USD"
    parent_code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


@dataclass
class UpdateAccountDTO:
    """بيانات تحديث حساب"""
    name: str
    account_type: str
    is_active: bool
    currency: str
    parent_code: Optional[str] = None
    description: Optional[str] = None
    version: int = 1


# ============================================================
# Fiscal Period DTOs
# ============================================================

@dataclass
class FiscalPeriodDTO:
    """فترة مالية - DTO"""
    id: str
    name: str
    start_date: datetime
    end_date: datetime
    is_closed: bool = False
    closed_at: Optional[datetime] = None
    closed_by: Optional[str] = None


# ============================================================
# Error DTOs
# ============================================================

@dataclass
class ErrorResponseDTO:
    """استجابة خطأ - DTO"""
    success: bool = False
    message: str = ""
    errors: List[str] = field(default_factory=list)
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "errors": self.errors,
            "error_code": self.error_code,
            "details": self.details,
        }
    
    @classmethod
    def from_exception(cls, exception: Exception, message: Optional[str] = None) -> 'ErrorResponseDTO':
        return cls(
            success=False,
            message=message or str(exception),
            errors=[str(exception)],
            details={"exception_type": exception.__class__.__name__}
        )


# ============================================================
# Validation Helpers
# ============================================================

def validate_create_journal_entry_dto(dto: CreateJournalEntryDTO) -> List[str]:
    """التحقق من صحة CreateJournalEntryDTO"""
    errors = []
    
    if not dto.date:
        errors.append("Date is required")
    
    if not dto.description or len(dto.description.strip()) < 3:
        errors.append("Description must be at least 3 characters")
    
    if not dto.lines or len(dto.lines) < 2:
        errors.append("At least 2 journal lines are required")
    
    total_debit = Decimal('0')
    total_credit = Decimal('0')
    
    for i, line in enumerate(dto.lines):
        if 'account_code' not in line:
            errors.append(f"Line {i+1}: account_code is required")
        
        debit = Decimal(str(line.get('debit', 0)))
        credit = Decimal(str(line.get('credit', 0)))
        
        if debit < 0 or credit < 0:
            errors.append(f"Line {i+1}: Amounts cannot be negative")
        
        if debit > 0 and credit > 0:
            errors.append(f"Line {i+1}: Cannot have both debit and credit")
        
        if debit == 0 and credit == 0:
            errors.append(f"Line {i+1}: Must have either debit or credit")
        
        total_debit += debit
        total_credit += credit
    
    if total_debit != total_credit:
        errors.append(f"Entry unbalanced: Debit={total_debit}, Credit={total_credit}")
    
    return errors


# ============================================================
# __all__ Export
# ============================================================

__all__ = [
    # ✅ Journal Line DTO (جديد)
    "JournalLineDTO",
    
    # Journal Entry DTOs
    "JournalLineResponseDTO",
    "JournalEntryResponseDTO",
    "CreateJournalEntryDTO",
    "UpdateJournalEntryDTO",
    
    # Balance DTOs
    "AccountBalanceResponseDTO",
    "TrialBalanceResponseDTO",
    
    # Account DTOs
    "AccountDTO",
    "CreateAccountDTO",
    "UpdateAccountDTO",
    
    # Fiscal Period DTOs
    "FiscalPeriodDTO",
    
    # Error DTOs
    "ErrorResponseDTO",
    
    # Validation
    "validate_create_journal_entry_dto",
]