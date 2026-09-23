# core/domain/projects/interfaces.py (ملف جديد)
"""Projects Repository Interfaces - واجهات مستودع المشاريع"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from decimal import Decimal

from .entities import Project
from .value_objects import ProjectId, ProjectCode, ProjectStatus


class IProjectRepository(ABC):
    """واجهة مستودع المشاريع"""

    @abstractmethod
    def save(self, project: Project) -> None:
        pass

    @abstractmethod
    def get_by_id(self, project_id: ProjectId) -> Optional[Project]:
        pass

    @abstractmethod
    def get_by_code(self, code: ProjectCode) -> Optional[Project]:
        pass

    @abstractmethod
    def list_all(
        self,
        status: Optional[ProjectStatus] = None,
        search: Optional[str] = None,
        customer_id: Optional[str] = None,
        manager_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Project]:
        pass

    @abstractmethod
    def search(self, search_text: str, limit: int = 50) -> List[Project]:
        pass

    @abstractmethod
    def exists_by_code(self, code: ProjectCode) -> bool:
        pass

    @abstractmethod
    def delete(self, project_id: ProjectId) -> bool:
        pass

    @abstractmethod
    def get_next_code(self, prefix: str = "PRJ") -> str:
        """توليد كود تلقائي للمشروع"""
        pass

    @abstractmethod
    def overview(self) -> Dict[str, Any]:
        """إحصائيات عامة عن المشاريع (عدد/ميزانيات/مصروفات حسب الحالة)"""
        pass