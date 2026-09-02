from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from core.domain.shared.value_objects import BaseDomainEvent

@dataclass(frozen=True)
class CurrencyCreatedEvent(BaseDomainEvent):
    currency_id: UUID
    code: str
    name: str
    created_by: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_event_name(self) -> str:
        return "currency.created"

@dataclass(frozen=True)
class CurrencyUpdatedEvent(BaseDomainEvent):
    currency_id: UUID
    code: str
    old_name: str
    new_name: str
    updated_by: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_event_name(self) -> str:
        return "currency.updated"

@dataclass(frozen=True)
class ExchangeRateUpdatedEvent(BaseDomainEvent):
    from_currency: str
    to_currency: str
    new_rate: float
    updated_by: str
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_event_name(self) -> str:
        return "currency.exchange_rate_updated"