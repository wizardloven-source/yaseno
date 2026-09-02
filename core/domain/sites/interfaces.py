# core/domain/sites/interfaces.py
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from .entities import Site
from .value_objects import SiteCode, SiteType


class ISiteRepository(ABC):
    @abstractmethod
    def save(self, site: Site) -> None:
        pass

    @abstractmethod
    def get_by_id(self, site_id: UUID) -> Optional[Site]:
        pass

    @abstractmethod
    def get_by_code(self, code: SiteCode) -> Optional[Site]:
        pass

    @abstractmethod
    def get_default_site(self) -> Optional[Site]:
        pass

    @abstractmethod
    def list_all(
        self,
        site_type: Optional[SiteType] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Site]:
        pass

    @abstractmethod
    def search(self, search_text: str, limit: int = 50) -> List[Site]:
        pass

    @abstractmethod
    def get_next_code(self, prefix: str = "S") -> str:
        pass

    @abstractmethod
    def delete(self, site_id: UUID, permanent: bool = False) -> bool:
        pass