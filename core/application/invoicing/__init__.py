# core/application/invoicing/__init__.py (معدل - بدون استيراد Handlers)

"""
Invoicing Application Layer - DTOs, Commands, and Converters only
"""

from .commands import (
    # Commands
    CreateInvoiceCommand,
    AddInvoiceLineCommand,
    PostInvoiceCommand,
    UpdateInvoiceLineCommand,
    RemoveInvoiceLineCommand,
    ClearInvoiceLinesCommand,
    DeleteDraftInvoiceCommand,
    RestoreDraftInvoiceCommand,
    # Queries
    GetInvoiceQuery,
    ListInvoicesQuery,
    GetCustomerInvoicesQuery,
    GetInvoiceStatsQuery,
    SearchInvoicesQuery,
)
from .dtos import InvoiceDTO, InvoiceLineDTO, CreateInvoiceDTO
from .converters import (
    invoice_to_dto, 
    line_to_dto, 
    lines_to_journal_lines,
    dto_to_invoice
)

# ❌ لا نستورد Handlers من هنا لتجنب الاستيراد الدائري
# يتم استيراد Handlers مباشرة من core.application.handlers.invoicing

__all__ = [
    # Commands
    "CreateInvoiceCommand",
    "AddInvoiceLineCommand",
    "PostInvoiceCommand",
    "UpdateInvoiceLineCommand",
    "RemoveInvoiceLineCommand",
    "ClearInvoiceLinesCommand",
    "DeleteDraftInvoiceCommand",
    "RestoreDraftInvoiceCommand",
    # Queries
    "GetInvoiceQuery",
    "ListInvoicesQuery",
    "GetCustomerInvoicesQuery",
    "GetInvoiceStatsQuery",
    "SearchInvoicesQuery",
    # DTOs
    "InvoiceDTO",
    "InvoiceLineDTO",
    "CreateInvoiceDTO",
    # Converters
    "invoice_to_dto",
    "line_to_dto",
    "lines_to_journal_lines",
    "dto_to_invoice",
]