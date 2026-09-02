# core/application/handlers/payments/__init__.py
"""Payments Handlers - معالجات أوامر واستعلامات الدفعات"""

# ========== Command Handlers ==========
from .create_payment_handler import CreatePaymentHandler
from .update_payment_handler import UpdatePaymentHandler
from .add_payment_line_handler import AddPaymentLineHandler
from .remove_payment_line_handler import RemovePaymentLineHandler
from .approve_payment_handler import ApprovePaymentHandler
from .reject_payment_handler import RejectPaymentHandler
from .complete_payment_handler import CompletePaymentHandler
from .cancel_payment_handler import CancelPaymentHandler
from .delete_draft_payment_handler import DeleteDraftPaymentHandler

# ✅ إضافة المعالجات الجديدة
from .allocate_payment_handler import AllocatePaymentHandler
from .reverse_allocation_handler import ReverseAllocationHandler

# ========== Query Handlers ==========
from .get_payment_query_handler import GetPaymentQueryHandler
from .list_payments_query_handler import ListPaymentsQueryHandler
from .get_payment_summary_query_handler import GetPaymentSummaryQueryHandler
from .get_customer_payments_query_handler import GetCustomerPaymentsQueryHandler
from .get_supplier_payments_query_handler import GetSupplierPaymentsQueryHandler
from .get_fund_payments_query_handler import GetFundPaymentsQueryHandler
from .get_payments_by_method_query_handler import GetPaymentsByMethodQueryHandler
from .get_payment_statistics_query_handler import GetPaymentStatisticsQueryHandler

# ✅ إضافة معالج الاستعلام الجديد
from .get_payment_allocations_query_handler import GetPaymentAllocationsQueryHandler

# ========== Event Handlers ==========
from .payment_completed_event_handler import PaymentCompletedEventHandler


__all__ = [
    # Command Handlers
    "CreatePaymentHandler",
    "UpdatePaymentHandler",
    "AddPaymentLineHandler",
    "RemovePaymentLineHandler",
    "ApprovePaymentHandler",
    "RejectPaymentHandler",
    "CompletePaymentHandler",
    "CancelPaymentHandler",
    "DeleteDraftPaymentHandler",
    "AllocatePaymentHandler",           # ✅ إضافة
    "ReverseAllocationHandler",         # ✅ إضافة
    
    # Query Handlers
    "GetPaymentQueryHandler",
    "ListPaymentsQueryHandler",
    "GetPaymentSummaryQueryHandler",
    "GetCustomerPaymentsQueryHandler",
    "GetSupplierPaymentsQueryHandler",
    "GetFundPaymentsQueryHandler",
    "GetPaymentsByMethodQueryHandler",
    "GetPaymentStatisticsQueryHandler",
    "GetPaymentAllocationsQueryHandler",  # ✅ إضافة
    
    # Event Handlers
    "PaymentCompletedEventHandler",
]