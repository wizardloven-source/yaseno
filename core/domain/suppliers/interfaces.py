# core/domain/suppliers/interfaces.py
"""Repository Interface for Suppliers Context"""

from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal

from .entities import Supplier
from .value_objects import SupplierId, SupplierCode, SupplierStatus


class ISupplierRepository(ABC):
    @abstractmethod
    def save(self, supplier: Supplier) -> None:
        pass

    @abstractmethod
    def get_by_id(self, supplier_id: SupplierId) -> Optional[Supplier]:
        pass

    @abstractmethod
    def get_by_code(self, code: SupplierCode) -> Optional[Supplier]:
        pass

    @abstractmethod
    def list_all(
        self,
        status: Optional[SupplierStatus] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Supplier]:
        pass

    @abstractmethod
    def search(self, search_text: str, limit: int = 50) -> List[Supplier]:
        pass

    @abstractmethod
    def get_next_code(self, prefix: str = "S") -> str:
        pass

    @abstractmethod
    def delete(self, supplier_id: SupplierId, permanent: bool = False) -> bool:
        pass