# core/types/payment_enums.py
from enum import Enum, auto

class PaymentType(str, Enum):
    RECEIVE = "receive"
    PAY = "pay"
    TRANSFER = "transfer"

class PaymentMethod(str, Enum):
    CASH = "cash"
    CHECK = "check"
    TRANSFER = "transfer"
    CREDIT = "credit"
    CARD = "card"

class PaymentStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class DocumentType(str, Enum):
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    MANUAL = "manual"
    SALES_ORDER = "sales_order"
    DELIVERY_NOTE = "delivery_note"

class ReferenceType(str, Enum):
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"