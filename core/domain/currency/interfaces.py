from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from .entities import Currency
from .value_objects import CurrencyCode

class ICurrencyRepository(ABC):
    @abstractmethod
    def save(self, currency: Currency) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, currency_id: UUID) -> Optional[Currency]:
        pass
    
    @abstractmethod
    def get_by_code(self, code: CurrencyCode) -> Optional[Currency]:
        pass
    
    @abstractmethod
    def get_all(self, include_inactive: bool = False) -> List[Currency]:
        pass
    
    @abstractmethod
    def get_base_currency(self) -> Optional[Currency]:
        pass
    
    @abstractmethod
    def delete(self, currency_id: UUID) -> bool:
        pass