"""
YAseen ERP - Shared Pydantic Models
All request/response models used across routers
"""
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import date as date_type


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: Optional[List[str]] = None


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=10)
    remember_me: bool = False


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class JournalLineRequest(BaseModel):
    account_code: str = Field(..., min_length=3, max_length=20)
    debit: Decimal = Field(Decimal("0"), ge=0)
    credit: Decimal = Field(Decimal("0"), ge=0)
    description: Optional[str] = None
    currency: Optional[str] = None
    cost_center: Optional[str] = None
    profit_center: Optional[str] = None

    @field_validator("credit")
    @classmethod
    def validate_debit_credit(cls, v, info):
        values = info.data
        debit = values.get("debit", Decimal("0"))
        if debit > 0 and v > 0:
            raise ValueError("لا يمكن أن يكون هناك مدين ودائن في نفس الوقت")
        if debit == 0 and v == 0:
            raise ValueError("يجب أن يكون هناك مدين أو دائن")
        return v


class CreateJournalEntryRequest(BaseModel):
    date: date_type = Field(..., description="تاريخ القيد")
    description: str = Field(..., min_length=3, max_length=500)
    lines: List[JournalLineRequest] = Field(..., min_length=2)
    transaction_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_balanced(self) -> 'CreateJournalEntryRequest':
        total_debit = sum(line.debit for line in self.lines)
        total_credit = sum(line.credit for line in self.lines)
        if total_debit != total_credit:
            raise ValueError(f"القيد غير متوازن. مدين: {total_debit}, دائن: {total_credit}")
        return self


class CreateAccountRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=20, pattern=r"^\d+$")
    name: str = Field(..., min_length=2, max_length=100)
    account_type: str = Field(..., description="asset, liability, equity, revenue, expense")
    parent_code: Optional[str] = None
    description: Optional[str] = None
    currency: str = Field("USD", min_length=3, max_length=3)
    is_active: bool = True


class CreateCustomerRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=20)
    name: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    tax_number: Optional[str] = None
    credit_limit: Decimal = Field(Decimal("0"), ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    notes: Optional[str] = None


class CreateInvoiceRequest(BaseModel):
    customer_id: str
    customer_name: str
    currency: str = Field("USD", min_length=3, max_length=3)
    payment_type: str = "cash"
    payment_currency: str = "USD"
    site_id: Optional[str] = None
    site_name: Optional[str] = None
    fund_id: Optional[str] = None
    lines: List[dict] = Field(default_factory=list)
    notes: Optional[str] = None


class InvoiceLineRequest(BaseModel):
    product_code: str
    product_name: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    notes: Optional[str] = None


class PostInvoiceRequest(BaseModel):
    force: bool = False


class CancelInvoiceRequest(BaseModel):
    reason: Optional[str] = None


class ReturnInvoiceRequest(BaseModel):
    reason: str = Field(..., min_length=2)


class CreatePaymentRequest(BaseModel):
    payment_type: str
    payment_method: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    fund_id: str
    customer_id: Optional[str] = None
    supplier_id: Optional[str] = None
    invoice_id: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[date] = None


class TrialBalanceRequest(BaseModel):
    as_of_date: date
    include_zero_balance: bool = False
    currency: str = Field("USD", min_length=3, max_length=3)


class IncomeStatementRequest(BaseModel):
    start_date: date
    end_date: date
    currency: str = Field("USD", min_length=3, max_length=3)


class BalanceSheetRequest(BaseModel):
    as_of_date: date
    currency: str = Field("USD", min_length=3, max_length=3)


class CreateProductRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    unit_price: Decimal = Field(Decimal("0"), ge=0)
    tax_rate: Decimal = Field(Decimal("0"), ge=0, le=100)
    description: Optional[str] = None
    category: Optional[str] = None
    stock_quantity: int = Field(0, ge=0)
    low_stock_threshold: int = Field(10, ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)


class CreateSupplierRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    tax_number: Optional[str] = None
    credit_limit: Decimal = Field(Decimal("0"), ge=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    notes: Optional[str] = None


class PurchaseOrderLineRequest(BaseModel):
    product_code: str
    product_name: str
    quantity: Decimal = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)
    notes: Optional[str] = None


class CreatePurchaseOrderRequest(BaseModel):
    supplier_id: str = Field(..., min_length=1)
    supplier_name: Optional[str] = None
    currency: str = Field("USD", min_length=3, max_length=3)
    expected_delivery_date: Optional[date] = None
    notes: Optional[str] = None
    lines: List[PurchaseOrderLineRequest] = Field(..., min_length=1)


class CreateFundRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    account_code: str = Field(..., min_length=1, max_length=20)
    fund_type: str = "main"
    currency: str = Field("USD", min_length=3, max_length=3)
    opening_balance: Decimal = Field(Decimal("0"))


class FundTransactionRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    description: Optional[str] = None


class ReceivePurchaseOrderRequest(BaseModel):
    notes: Optional[str] = None


class PaymentReasonRequest(BaseModel):
    reason: str


class TransferFundsRequest(BaseModel):
    from_fund_id: str
    to_fund_id: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field("USD", min_length=3, max_length=3)
    description: Optional[str] = None


class CashFlowRequest(BaseModel):
    start_date: date
    end_date: date
    currency: str = Field("USD", min_length=3, max_length=3)


class StockMovementRequest(BaseModel):
    product_id: str
    movement_type: str
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)
    currency: str = "USD"
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None


class PurchaseMovementRequest(BaseModel):
    product_id: str
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)
    currency: str = "USD"
    purchase_order_id: Optional[str] = None
    notes: Optional[str] = None


class SaleMovementRequest(BaseModel):
    product_id: str
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)
    currency: str = "USD"
    invoice_id: Optional[str] = None
    notes: Optional[str] = None


class AdjustmentMovementRequest(BaseModel):
    product_id: str
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)
    currency: str = "USD"
    adjustment_type: str  # increase or decrease
    notes: Optional[str] = None


class StockBatchRequest(BaseModel):
    product_id: str
    batch_number: str
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Decimal = Field(..., ge=0)
    currency: str = "USD"
    expiry_date: Optional[date] = None


class ConsumeBatchRequest(BaseModel):
    quantity: Decimal = Field(..., gt=0)


class StockTransferRequest(BaseModel):
    product_id: str
    from_site_id: str
    to_site_id: str
    quantity: Decimal = Field(..., gt=0)
    notes: Optional[str] = None


class CreateCurrencyRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=3)
    name: str = Field(..., min_length=2, max_length=100)
    symbol: Optional[str] = None
    decimal_places: int = 2
    is_base: bool = False


class UpdateCurrencyRequest(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimal_places: Optional[int] = None
    is_active: Optional[bool] = None


class SetExchangeRateRequest(BaseModel):
    target_currency_code: str = Field(..., min_length=3, max_length=3)
    rate: Decimal = Field(..., gt=0)
    effective_date: Optional[date] = None


class CreateSiteRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=2, max_length=200)
    site_type: str = "branch"
    address: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    notes: Optional[str] = None


class UpdateSiteRequest(BaseModel):
    name: Optional[str] = None
    site_type: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class CreateCenterRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=2, max_length=200)
    center_type: str = "cost"
    parent_code: Optional[str] = None
    description: Optional[str] = None


class UpdateCenterRequest(BaseModel):
    name: Optional[str] = None
    center_type: Optional[str] = None
    parent_code: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CreateAllocationRequest(BaseModel):
    center_code: str
    account_code: str
    percentage: Decimal = Field(..., gt=0, le=100)


class UpdateUiSettingsRequest(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    direction: Optional[str] = None
    date_format: Optional[str] = None
    currency_display: Optional[str] = None


class UpdateAllSettingsRequest(BaseModel):
    company_name: Optional[str] = None
    company_email: Optional[str] = None
    company_phone: Optional[str] = None
    company_address: Optional[str] = None
    tax_number: Optional[str] = None
    fiscal_year_start: Optional[int] = None
    fiscal_year_end: Optional[int] = None
    base_currency: Optional[str] = None
    ui: Optional[UpdateUiSettingsRequest] = None


class CreateBranchRequest(BaseModel):
    code: str
    name: str
    customer_name: str
    customer_code: str = ""
    street: Optional[str] = None
    city: Optional[str] = None
    country: str = "LB"
    postal_code: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    contact_person: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    tax_number: Optional[str] = None
    is_default: bool = False
    notes: Optional[str] = None
    working_hours: Optional[str] = None
    branch_type: str = "store"


class UpdateBranchRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    site_id: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class SetDefaultBranchRequest(BaseModel):
    branch_id: str


class CreateFixedAssetRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=2, max_length=200)
    category: str
    purchase_date: date
    purchase_cost: Decimal = Field(..., gt=0)
    salvage_value: Decimal = Field(Decimal("0"), ge=0)
    useful_life_years: int = Field(..., gt=0)
    currency: str = "USD"
    description: Optional[str] = None
    location: Optional[str] = None
    account_code: Optional[str] = None
    depreciation_method: str = "straight_line"


class PostDepreciationRequest(BaseModel):
    period_end_date: date
    notes: Optional[str] = None


class DisposeFixedAssetRequest(BaseModel):
    disposal_date: date
    disposal_amount: Decimal = Field(..., ge=0)
    disposal_method: str
    notes: Optional[str] = None


class RunMonthlyDepreciationRequest(BaseModel):
    period_end_date: date
    notes: Optional[str] = None


class WorkflowStepRequest(BaseModel):
    step_order: int
    name: str
    approver_role: str
    required_approvals: int = 1


class CreateWorkflowRequest(BaseModel):
    name: str
    entity_type: str
    steps: List[WorkflowStepRequest]
    description: Optional[str] = None


class UpdateWorkflowRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[WorkflowStepRequest]] = None


class CreateApprovalRequestRequest(BaseModel):
    entity_type: str
    entity_id: str
    workflow_id: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None


class ApproveRequestRequest(BaseModel):
    comments: Optional[str] = None


class RejectRequestRequest(BaseModel):
    reason: str


class ActionRequestRequest(BaseModel):
    action: str
    comments: Optional[str] = None


class ReassignRequestRequest(BaseModel):
    reassigned_to: str
    reason: Optional[str] = None


class BatchRequestsRequest(BaseModel):
    request_ids: List[str]
    action: str  # approve or reject
    comments: Optional[str] = None
    reason: Optional[str] = None


class OpeningBalanceLineRequest(BaseModel):
    account_code: str
    debit: Decimal = Field(Decimal("0"), ge=0)
    credit: Decimal = Field(Decimal("0"), ge=0)
    currency: str = "USD"


class OpeningBalancesRequest(BaseModel):
    lines: List[OpeningBalanceLineRequest] = Field(..., min_length=1)
    notes: Optional[str] = None


class CreateRoleRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)


class UpdateRoleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class CreatePeriodRequest(BaseModel):
    name: str
    start_date: date
    end_date: date


class CloseYearRequest(BaseModel):
    closing_account_code: str
    notes: Optional[str] = None


class AllocatePaymentRequest(BaseModel):
    invoice_id: str
    amount: Decimal = Field(..., gt=0)


class CreateReconciliationRequest(BaseModel):
    account_code: str
    statement_date: date
    statement_balance: Decimal
    currency: str = "USD"
    notes: Optional[str] = None


class MatchPaymentRequest(BaseModel):
    payment_id: str
    reconciled_amount: Decimal = Field(..., ge=0)


class RevaluationRequest(BaseModel):
    as_of_date: date
    account_codes: Optional[List[str]] = None
    notes: Optional[str] = None


class BudgetLineRequest(BaseModel):
    account_code: str
    budget_amount: Decimal = Field(..., ge=0)
    currency: str = "USD"


class CreateBudgetRequest(BaseModel):
    name: str
    start_date: date
    end_date: date
    lines: List[BudgetLineRequest] = Field(..., min_length=1)
    notes: Optional[str] = None
