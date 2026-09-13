# core/application/sales/__init__.py
"""
Sales Module - Application Layer
معالجات الأوامر والاستعلامات لدورة المبيعات
"""

from .commands import (
    CreateQuotationCommand, UpdateQuotationCommand, SendQuotationCommand,
    AcceptQuotationCommand, RejectQuotationCommand, ConvertQuotationCommand,
    CreateOrderCommand, ConfirmOrderCommand, CancelOrderCommand,
    CreateDeliveryCommand, ScheduleDeliveryCommand, CompleteDeliveryCommand,
    # Sales Return Commands
    CreateSalesReturnCommand, SubmitSalesReturnCommand, ApproveSalesReturnCommand,
    RejectSalesReturnCommand, ReceiveSalesReturnCommand, InspectSalesReturnCommand,
    CompleteSalesReturnCommand, CancelSalesReturnCommand, ReturnItemCommand
)

from .handlers import (
    CreateQuotationHandler, UpdateQuotationHandler, SendQuotationHandler,
    AcceptQuotationHandler, RejectQuotationHandler, ConvertQuotationHandler,
    CreateOrderHandler, ConfirmOrderHandler, CancelOrderHandler,
    CreateDeliveryHandler, ScheduleDeliveryHandler, CompleteDeliveryHandler,
    # Sales Return Handlers
    CreateSalesReturnHandler, SubmitSalesReturnHandler, ApproveSalesReturnHandler,
    RejectSalesReturnHandler, ReceiveSalesReturnHandler, InspectSalesReturnHandler,
    CompleteSalesReturnHandler, CancelSalesReturnHandler
)

# Queries will be added later if needed
# from .queries import (...)
# from .query_handlers import (...)

__all__ = [
    # Commands
    'CreateQuotationCommand', 'UpdateQuotationCommand', 'SendQuotationCommand',
    'AcceptQuotationCommand', 'RejectQuotationCommand', 'ConvertQuotationCommand',
    'CreateOrderCommand', 'ConfirmOrderCommand', 'CancelOrderCommand',
    'CreateDeliveryCommand', 'ScheduleDeliveryCommand', 'CompleteDeliveryCommand',
    
    # Sales Return Commands
    'CreateSalesReturnCommand', 'SubmitSalesReturnCommand', 'ApproveSalesReturnCommand',
    'RejectSalesReturnCommand', 'ReceiveSalesReturnCommand', 'InspectSalesReturnCommand',
    'CompleteSalesReturnCommand', 'CancelSalesReturnCommand', 'ReturnItemCommand',
    
    # Command Handlers
    'CreateQuotationHandler', 'UpdateQuotationHandler', 'SendQuotationHandler',
    'AcceptQuotationHandler', 'RejectQuotationHandler', 'ConvertQuotationHandler',
    'CreateOrderHandler', 'ConfirmOrderHandler', 'CancelOrderHandler',
    'CreateDeliveryHandler', 'ScheduleDeliveryHandler', 'CompleteDeliveryHandler',
    
    # Sales Return Handlers
    'CreateSalesReturnHandler', 'SubmitSalesReturnHandler', 'ApproveSalesReturnHandler',
    'RejectSalesReturnHandler', 'ReceiveSalesReturnHandler', 'InspectSalesReturnHandler',
    'CompleteSalesReturnHandler', 'CancelSalesReturnHandler'
]
