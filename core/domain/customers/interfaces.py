# core/domain/customers/interfaces.py
"""Repository Interface for Customers Context"""

from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal

from .entities import Customer
from .value_objects import CustomerId, CustomerCode, CustomerStatus


class ICustomerRepository(ABC):
    @abstractmethod
    def save(self, customer: Customer) -> None:
        pass

    @abstractmethod
    def get_by_id(self, customer_id: CustomerId) -> Optional[Customer]:
        pass

    @abstractmethod
    def get_by_code(self, code: CustomerCode) -> Optional[Customer]:
        pass

    @abstractmethod
    def list_all(
        self,
        status: Optional[CustomerStatus] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Customer]:
        pass

    @abstractmethod
    def search(self, search_text: str, limit: int = 50) -> List[Customer]:
        pass

    @abstractmethod
    def get_next_code(self, prefix: str = "C") -> str:
        pass

    @abstractmethod
    def delete(self, customer_id: CustomerId, permanent: bool = False) -> bool:
        pass