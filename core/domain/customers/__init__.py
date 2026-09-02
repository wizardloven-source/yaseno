# core/domain/customers/__init__.py
"""
Customers Bounded Context - Domain Layer
"""

from .entities import Customer
from .value_objects import CustomerId, CustomerCode, CustomerStatus, ContactInfo, Address
from .events import CustomerCreatedEvent, CustomerUpdatedEvent, CustomerDeletedEvent
from .exceptions import CustomerNotFoundError, DuplicateCustomerCodeError
from .interfaces import ICustomerRepository

__all__ = [
    "Customer",
    "CustomerId",
    "CustomerCode",
    "CustomerStatus",
    "ContactInfo",
    "Address",
    "CustomerCreatedEvent",
    "CustomerUpdatedEvent",
    "CustomerDeletedEvent",
    "CustomerNotFoundError",
    "DuplicateCustomerCodeError",
    "ICustomerRepository",
]