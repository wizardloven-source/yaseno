# core/application/payments/__init__.py
"""Payments Application Layer - Commands, Queries, DTOs"""

from .commands import (
    CreatePaymentCommand,
    UpdatePaymentCommand,
    AddPaymentLineCommand,
    RemovePaymentLineCommand,
    ApprovePaymentCommand,
    RejectPaymentCommand,
    CompletePaymentCommand,
    CancelPaymentCommand,
    DeleteDraftPaymentCommand,
    GetPaymentQuery,
    ListPaymentsQuery,
    GetPaymentSummaryQuery,
    GetCustomerPaymentsQuery,
    GetSupplierPaymentsQuery,
)
from .dtos import (
    PaymentDTO,
    PaymentLineDTO,
    PaymentSummaryDTO,
    CreatePaymentDTO,
    UpdatePaymentDTO,
)
from .converters import (
    payment_to_dto,
    payment_line_to_dto,
    dto_to_payment,
)
from .services import PaymentService, PaymentAllocationService  # ✅ تصدير الخدمات

__all__ = [
    # Commands
    "CreatePaymentCommand",
    "UpdatePaymentCommand",
    "AddPaymentLineCommand",
    "RemovePaymentLineCommand",
    "ApprovePaymentCommand",
    "RejectPaymentCommand",
    "CompletePaymentCommand",
    "CancelPaymentCommand",
    "DeleteDraftPaymentCommand",
    # Queries
    "GetPaymentQuery",
    "ListPaymentsQuery",
    "GetPaymentSummaryQuery",
    "GetCustomerPaymentsQuery",
    "GetSupplierPaymentsQuery",
    # DTOs
    "PaymentDTO",
    "PaymentLineDTO",
    "PaymentSummaryDTO",
    "CreatePaymentDTO",
    "UpdatePaymentDTO",
    # Converters
    "payment_to_dto",
    "payment_line_to_dto",
    "dto_to_payment",
    # Services
    "PaymentService",
    "PaymentAllocationService",
]