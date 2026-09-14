# core/application/handlers/sales_cycle/__init__.py
"""
Sales Cycle Handlers - معالجات دورة المبيعات

هذا المجلد يحتوي على جميع معالجات دورة المبيعات
(Commands و Queries) مقسمة حسب الوظيفة.
"""

from .quotation_handlers import (
    CreateQuotationHandler,
    UpdateQuotationHandler,
    SendQuotationHandler,
    AcceptQuotationHandler,
    RejectQuotationHandler,
    ConvertQuotationToOrderHandler,
)

__all__ = [
    # Quotation Handlers
    "CreateQuotationHandler",
    "UpdateQuotationHandler",
    "SendQuotationHandler",
    "AcceptQuotationHandler",
    "RejectQuotationHandler",
    "ConvertQuotationToOrderHandler",
]
"""
Sales Cycle Handlers - معالجات دورة المبيعات

هذا المجلد يحتوي على جميع معالجات دورة المبيعات
(Commands و Queries) مقسمة حسب الوظيفة.
"""

from .create_quotation_handler import CreateQuotationHandler
from .update_quotation_handler import UpdateQuotationHandler
from .get_quotation_handler import GetQuotationHandler
from .list_quotations_handler import ListQuotationsHandler
from .send_quotation_handler import SendQuotationHandler
from .accept_quotation_handler import AcceptQuotationHandler
from .reject_quotation_handler import RejectQuotationHandler
from .convert_to_order_handler import ConvertToOrderHandler
from .get_quotation_statistics_handler import GetQuotationStatisticsHandler

__all__ = [
    # Quotation Command Handlers
    "CreateQuotationHandler",
    "UpdateQuotationHandler",
    "SendQuotationHandler",
    "AcceptQuotationHandler",
    "RejectQuotationHandler",
    "ConvertToOrderHandler",
    
    # Quotation Query Handlers
    "GetQuotationHandler",
    "ListQuotationsHandler",
    "GetQuotationStatisticsHandler",
]
