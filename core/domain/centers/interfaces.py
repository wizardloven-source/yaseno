# domain/centers/interfaces.py (ملف جديد)
"""Cost & Profit Centers Repository Interfaces"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date
from decimal import Decimal  # ✅ أضف هذا السطر

from .entities import Center, CenterAllocation
from .value_objects import CenterId, CenterCode, CenterType, CenterStatus, AllocationRule


class ICenterRepository(ABC):
    @abstractmethod
    def save(self, center: Center) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, center_id: CenterId) -> Optional[Center]:
        pass
    
    @abstractmethod
    def get_by_code(self, code: CenterCode) -> Optional[Center]:
        pass
    
    @abstractmethod
    def get_by_path(self, path: str) -> Optional[Center]:
        pass
    
    @abstractmethod
    def list_all(
        self,
        center_type: Optional[CenterType] = None,
        status: Optional[CenterStatus] = None,
        parent_code: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Center]:
        pass
    
    @abstractmethod
    def get_children(self, parent_code: str) -> List[Center]:
        pass
    
    @abstractmethod
    def get_tree(self, root_code: Optional[str] = None) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def get_center_with_children(self, code: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def search(self, search_text: str, limit: int = 50) -> List[Center]:
        pass
    
    @abstractmethod
    def exists_by_code(self, code: CenterCode) -> bool:
        pass
    
    @abstractmethod
    def delete(self, center_id: CenterId) -> bool:
        pass
    
    @abstractmethod
    def get_next_code(self, prefix: str = "C") -> str:
        pass


class IAllocationRepository(ABC):
    @abstractmethod
    def save(self, allocation: CenterAllocation) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, allocation_id: str) -> Optional[CenterAllocation]:
        pass
    
    @abstractmethod
    def list_by_center(
        self,
        center_code: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CenterAllocation]:
        pass
    
    @abstractmethod
    def list_by_period(
        self,
        from_date: date,
        to_date: date,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CenterAllocation]:
        pass
    
    @abstractmethod
    def get_total_allocated(
        self,
        center_code: str,
        from_date: date,
        to_date: date
    ) -> Decimal:
        pass
    
    @abstractmethod
    def delete(self, allocation_id: str) -> bool:
        pass


class IAllocationRuleRepository(ABC):
    @abstractmethod
    def save(self, rule: AllocationRule) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, rule_id: str) -> Optional[AllocationRule]:
        pass
    
    @abstractmethod
    def get_by_source_center(self, center_code: str) -> List[AllocationRule]:
        pass
    
    @abstractmethod
    def get_by_target_center(self, center_code: str) -> List[AllocationRule]:
        pass
    
    @abstractmethod
    def list_all(self, is_active: Optional[bool] = None) -> List[AllocationRule]:
        pass
    
    @abstractmethod
    def delete(self, rule_id: str) -> bool:
        pass