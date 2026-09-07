# core/domain/sales/__init__.py
"""
Sales Module - Domain Layer
دورة المبيعات الكاملة: عروض الأسعار → أوامر البيع → إشعارات التسليم
"""

from .entities import SalesQuotation, QuotationItem, SalesOrder, OrderItem, DeliveryNote, DeliveryItem
from .value_objects import (
    QuotationId, QuotationNumber, QuotationStatus,
    OrderId, OrderNumber, OrderStatus,
    DeliveryId, DeliveryNumber, DeliveryStatus
)
from .events import (
    QuotationCreated, QuotationSent, QuotationAccepted, 
    QuotationRejected, QuotationConverted,
    OrderCreated, OrderConfirmed, OrderPicked, OrderPacked,
    OrderShipped, OrderDelivered, OrderCancelled,
    DeliveryCreated, DeliveryCompleted, DeliveryReturned
)
from .exceptions import (
    SalesDomainException, QuotationExpiredError,
    InvalidQuotationStatusError, InvalidOrderStatusError
)

__all__ = [
    # Entities
    'SalesQuotation', 'QuotationItem', 'SalesOrder', 'OrderItem', 'DeliveryNote', 'DeliveryItem',
    
    # Value Objects
    'QuotationId', 'QuotationNumber', 'QuotationStatus',
    'OrderId', 'OrderNumber', 'OrderStatus',
    'DeliveryId', 'DeliveryNumber', 'DeliveryStatus',
    
    # Events
    'QuotationCreated', 'QuotationSent', 'QuotationAccepted',
    'QuotationRejected', 'QuotationConverted',
    'OrderCreated', 'OrderConfirmed', 'OrderPicked', 'OrderPacked',
    'OrderShipped', 'OrderDelivered', 'OrderCancelled',
    'DeliveryCreated', 'DeliveryCompleted', 'DeliveryReturned',
    
    # Exceptions
    'SalesDomainException', 'QuotationExpiredError',
    'InvalidQuotationStatusError', 'InvalidOrderStatusError'
]
