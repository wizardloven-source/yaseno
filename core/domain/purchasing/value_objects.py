from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4


class PurchaseOrderStatus(Enum):
    DRAFT = "draft"
    POSTED = "posted"
    CANCELLED = "cancelled"
    PARTIALLY_RECEIVED = "partially_received"
    FULLY_RECEIVED = "fully_received"


class PaymentTerms(Enum):
    CASH = "cash"
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"


# ========== ✅ Value Objects for Purchase Returns ==========

class PurchaseReturnStatus(Enum):
    """حالات إرجاع المشتريات"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    SHIPPED = "shipped"
    RECEIVED_BY_SUPPLIER = "received_by_supplier"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class DebitNoteStatus(Enum):
    """حالات مذكرة المدين"""
    DRAFT = "draft"
    ISSUED = "issued"
    POSTED = "posted"
    APPLIED = "applied"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class PurchaseReturnId:
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            if isinstance(self.value, str):
                object.__setattr__(self, 'value', UUID(self.value))
            else:
                raise ValueError("PurchaseReturnId must be UUID or UUID string")
    
    @classmethod
    def generate(cls) -> "PurchaseReturnId":
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "PurchaseReturnId":
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class PurchaseReturnNumber:
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("Purchase return number cannot be empty")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DebitNoteId:
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            if isinstance(self.value, str):
                object.__setattr__(self, 'value', UUID(self.value))
            else:
                raise ValueError("DebitNoteId must be UUID or UUID string")
    
    @classmethod
    def generate(cls) -> "DebitNoteId":
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "DebitNoteId":
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class DebitNoteNumber:
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("Debit note number cannot be empty")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PurchaseOrderNumber:
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value.strip()) == 0:
            raise ValueError("Purchase order number cannot be empty")
    
    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PurchaseOrderId:
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            if isinstance(self.value, str):
                object.__setattr__(self, 'value', UUID(self.value))
            else:
                raise ValueError("PurchaseOrderId must be UUID or UUID string")
    
    @classmethod
    def generate(cls) -> "PurchaseOrderId":
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "PurchaseOrderId":
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)