# core/application/payments/dtos.py
"""
Data Transfer Objects for Payments Module
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


@dataclass(frozen=True)
class PaymentLineDTO:
    """سطر دفعة - DTO"""
    line_id: str
    reference_type: str
    reference_id: str
    amount: Decimal
    currency: str
    total: Decimal
    notes: str = ""

    @property
    def amount_formatted(self) -> str:
        if self.currency == "LBP":
            return f"{self.amount:,.0f} {self.currency}"
        return f"{self.amount:,.2f} {self.currency}"


@dataclass(frozen=True)
class PaymentDTO:
    """دفعة - DTO كامل"""
    id: str
    code: str
    date: datetime
    payment_type: str
    payment_method: str
    amount: Decimal
    currency: str
    customer_id: Optional[str]
    customer_name: Optional[str]
    supplier_id: Optional[str]
    supplier_name: Optional[str]
    fund_id: Optional[str]
    fund_code: Optional[str]
    status: str
    lines: List[PaymentLineDTO]
    notes: str
    reference_type: Optional[str]
    reference_id: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    completed_by: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    version: int
    
    # ✅ إضافة حقل معرف القيد المحاسبي
    journal_entry_id: Optional[str] = None

    @property
    def amount_formatted(self) -> str:
        if self.currency == "LBP":
            return f"{self.amount:,.0f} {self.currency}"
        return f"{self.amount:,.2f} {self.currency}"

    @property
    def display_name(self) -> str:
        if self.customer_name:
            return f"{self.code} - {self.customer_name}"
        if self.supplier_name:
            return f"{self.code} - {self.supplier_name}"
        return str(self.code)

    @property
    def is_completed(self) -> bool:
        return self.status == "completed"

    @property
    def is_draft(self) -> bool:
        return self.status == "draft"


@dataclass(frozen=True)
class PaymentSummaryDTO:
    """ملخص الدفعات - DTO"""
    total_received: Decimal
    total_paid: Decimal
    net_balance: Decimal
    total_count: int
    pending_count: int
    completed_count: int
    cancelled_count: int
    currency: str = "USD"

    @property
    def total_received_formatted(self) -> str:
        if self.currency == "LBP":
            return f"{self.total_received:,.0f} {self.currency}"
        return f"{self.total_received:,.2f} {self.currency}"

    @property
    def total_paid_formatted(self) -> str:
        if self.currency == "LBP":
            return f"{self.total_paid:,.0f} {self.currency}"
        return f"{self.total_paid:,.2f} {self.currency}"

    @property
    def net_balance_formatted(self) -> str:
        if self.currency == "LBP":
            return f"{self.net_balance:,.0f} {self.currency}"
        return f"{self.net_balance:,.2f} {self.currency}"


@dataclass(frozen=True)
class CreatePaymentDTO:
    """بيانات إنشاء دفعة جديدة"""
    payment_type: str
    amount: Decimal
    currency: str = "USD"
    payment_method: str = "cash"
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    supplier_id: Optional[str] = None
    supplier_name: Optional[str] = None
    fund_id: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: str = ""


@dataclass(frozen=True)
class UpdatePaymentDTO:
    """بيانات تحديث دفعة"""
    payment_id: str
    notes: Optional[str] = None
    payment_method: Optional[str] = None
    fund_id: Optional[str] = None
    version: int = 1