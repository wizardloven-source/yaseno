# domain/auth/interfaces.py (ملف جديد)
"""Repository Interfaces for Authentication & Authorization"""

from abc import ABC, abstractmethod
from typing import Optional, List

from .entities import User, Role, Permission
from .value_objects import UserId, RoleId, PermissionId


class IUserRepository(ABC):
    @abstractmethod
    def save(self, user: User) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, user_id: UserId) -> Optional[User]:
        pass
    
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def list_all(self, include_inactive: bool = False, limit: int = 100, offset: int = 0) -> List[User]:
        pass
    
    @abstractmethod
    def delete(self, user_id: UserId) -> bool:
        pass


class IRoleRepository(ABC):
    @abstractmethod
    def save(self, role: Role) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, role_id: RoleId) -> Optional[Role]:
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Role]:
        pass
    
    @abstractmethod
    def list_all(self, include_inactive: bool = False, limit: int = 100, offset: int = 0) -> List[Role]:
        pass
    
    @abstractmethod
    def delete(self, role_id: RoleId) -> bool:
        pass


class IPermissionRepository(ABC):
    @abstractmethod
    def save(self, permission: Permission) -> None:
        pass
    
    @abstractmethod
    def get_by_id(self, permission_id: PermissionId) -> Optional[Permission]:
        pass
    
    @abstractmethod
    def get_by_code(self, code: str) -> Optional[Permission]:
        pass
    
    @abstractmethod
    def list_all(self, category: Optional[str] = None, include_inactive: bool = False, limit: int = 100, offset: int = 0) -> List[Permission]:
        pass
    
    @abstractmethod
    def list_by_category(self, category: str) -> List[Permission]:
        pass
    
    @abstractmethod
    def delete(self, permission_id: PermissionId) -> bool:
        pass