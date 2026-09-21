# api_routers/pos/dtos.py
"""
Point of Sale (POS) DTOs - نماذج الإدخال لنقطة البيع
"""
from decimal import Decimal
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class OpenSessionRequest(BaseModel):
    opening_cash: Decimal = Field(default=Decimal("0"), ge=0)
    terminal_id: Optional[str] = None
    device_id: Optional[str] = None
    warehouse_id: Optional[str] = None
    branch_id: Optional[str] = None
    notes: Optional[str] = None


class CloseSessionRequest(BaseModel):
    declared_cash: Decimal = Field(..., ge=0)
    tolerance: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None


class PosReceiptLineRequest(BaseModel):
    product_id: Optional[str] = None
    product_code: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None


class CreatePosReceiptRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    customer_id: Optional[str] = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    tender_type: str = Field(..., pattern="^(cash|card|credit|mixed)$")
    tenders: Optional[Dict[str, Decimal]] = None
    lines: List[PosReceiptLineRequest] = Field(..., min_length=1)
    fund_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    client_reference: Optional[str] = None
    device_id: Optional[str] = None
    notes: Optional[str] = None


class PosReturnLineRequest(BaseModel):
    product_id: Optional[str] = None
    product_code: Optional[str] = None
    quantity: Decimal = Field(..., gt=0)


class ReturnPosReceiptRequest(BaseModel):
    items: List[PosReturnLineRequest] = Field(..., min_length=1)
    refund_tender: str = Field(default="cash", pattern="^(cash|card|credit)$")
    reason: Optional[str] = None


class VoidPosReceiptRequest(BaseModel):
    reason: str = Field(..., min_length=1)


class SyncReceiptsRequest(BaseModel):
    receipts: List[CreatePosReceiptRequest] = Field(..., min_length=1)


class RegisterTerminalRequest(BaseModel):
    device_id: str = Field(..., min_length=1)
    terminal_name: Optional[str] = None
    default_warehouse_id: Optional[str] = None
    branch_id: Optional[str] = None