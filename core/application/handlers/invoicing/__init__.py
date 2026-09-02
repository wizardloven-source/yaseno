# core/application/handlers/invoicing/__init__.py

"""
Invoicing Handlers - Organized by use case

هذا المجلد يحتوي على جميع معالجات الفواتير (Commands و Queries)
كل Handler في ملف منفصل لتسهيل الصيانة والتطوير
"""

from .create_invoice_handler import CreateInvoiceHandler
from .add_invoice_line_handler import AddInvoiceLineHandler
from .update_invoice_line_handler import UpdateInvoiceLineHandler
from .remove_invoice_line_handler import RemoveInvoiceLineHandler
from .clear_invoice_lines_handler import ClearInvoiceLinesHandler
from .post_invoice_handler import PostInvoiceHandler
from .delete_draft_invoice_handler import DeleteDraftInvoiceHandler
from .get_invoice_query_handler import GetInvoiceQueryHandler
from .list_invoices_query_handler import ListInvoicesQueryHandler

# ✅ المعالجات الجديدة
from .cancel_invoice_handler import CancelInvoiceHandler
from .return_invoice_handler import ReturnInvoiceHandler
from .get_customer_invoices_query_handler import GetCustomerInvoicesQueryHandler
from .search_invoices_query_handler import SearchInvoicesQueryHandler
from .get_invoice_stats_query_handler import GetInvoiceStatsQueryHandler

__all__ = [
    # Command Handlers
    "CreateInvoiceHandler",
    "AddInvoiceLineHandler",
    "UpdateInvoiceLineHandler",
    "RemoveInvoiceLineHandler",
    "ClearInvoiceLinesHandler",
    "PostInvoiceHandler",
    "DeleteDraftInvoiceHandler",
    "CancelInvoiceHandler",
    "ReturnInvoiceHandler",
    
    # Query Handlers
    "GetInvoiceQueryHandler",
    "ListInvoicesQueryHandler",
    "GetCustomerInvoicesQueryHandler",
    "SearchInvoicesQueryHandler",
    "GetInvoiceStatsQueryHandler",
]