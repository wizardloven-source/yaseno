# core/application/sales/__init__.py
"""
Sales Module - Application Layer
معالجات الأوامر والاستعلامات لدورة المبيعات
"""

from .commands import (
    CreateQuotationCommand, UpdateQuotationCommand, SendQuotationCommand,
    AcceptQuotationCommand, RejectQuotationCommand, ConvertQuotationCommand,
    CreateOrderCommand, ConfirmOrderCommand, CancelOrderCommand,
    CreateDeliveryCommand, ScheduleDeliveryCommand, CompleteDeliveryCommand
)

from .handlers import (
    CreateQuotationHandler, UpdateQuotationHandler, SendQuotationHandler,
    AcceptQuotationHandler, RejectQuotationHandler, ConvertQuotationHandler,
    CreateOrderHandler, ConfirmOrderHandler, CancelOrderHandler,
    CreateDeliveryHandler, ScheduleDeliveryHandler, CompleteDeliveryHandler
)

from .queries import (
    GetQuotationQuery, GetOrderQuery, GetDeliveryQuery,
    ListQuotationsQuery, ListOrdersQuery, ListDeliveriesQuery
)

from .query_handlers import (
    GetQuotationHandler, GetOrderHandler, GetDeliveryHandler,
    ListQuotationsHandler, ListOrdersHandler, ListDeliveriesHandler
)

__all__ = [
    # Commands
    'CreateQuotationCommand', 'UpdateQuotationCommand', 'SendQuotationCommand',
    'AcceptQuotationCommand', 'RejectQuotationCommand', 'ConvertQuotationCommand',
    'CreateOrderCommand', 'ConfirmOrderCommand', 'CancelOrderCommand',
    'CreateDeliveryCommand', 'ScheduleDeliveryCommand', 'CompleteDeliveryCommand',
    
    # Command Handlers
    'CreateQuotationHandler', 'UpdateQuotationHandler', 'SendQuotationHandler',
    'AcceptQuotationHandler', 'RejectQuotationHandler', 'ConvertQuotationHandler',
    'CreateOrderHandler', 'ConfirmOrderHandler', 'CancelOrderHandler',
    'CreateDeliveryHandler', 'ScheduleDeliveryHandler', 'CompleteDeliveryHandler',
    
    # Queries
    'GetQuotationQuery', 'GetOrderQuery', 'GetDeliveryQuery',
    'ListQuotationsQuery', 'ListOrdersQuery', 'ListDeliveriesQuery',
    
    # Query Handlers
    'GetQuotationHandler', 'GetOrderHandler', 'GetDeliveryHandler',
    'ListQuotationsHandler', 'ListOrdersHandler', 'ListDeliveriesHandler'
]
