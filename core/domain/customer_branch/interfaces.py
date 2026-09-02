# core/domain/customer_branch/interfaces.py
"""
Customer Branch Repository Interfaces - واجهات المستودع
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from .entities import CustomerBranch
from .value_objects import BranchId, BranchCode, BranchStatus


class ICustomerBranchRepository(ABC):
    """واجهة مستودع فروع العملاء"""
    
    @abstractmethod
    def save(self, branch: CustomerBranch) -> None:
        """حفظ فرع عميل"""
        pass
    
    @abstractmethod
    def get_by_id(self, branch_id: BranchId) -> Optional[CustomerBranch]:
        """الحصول على فرع بواسطة المعرف"""
        pass
    
    @abstractmethod
    def get_by_code(self, code: BranchCode) -> Optional[CustomerBranch]:
        """الحصول على فرع بواسطة الكود"""
        pass
    
    @abstractmethod
    def get_by_customer(
        self,
        customer_id: str,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[CustomerBranch]:
        """الحصول على فروع عميل معين"""
        pass
    
    @abstractmethod
    def get_default_branch(self, customer_id: str) -> Optional[CustomerBranch]:
        """الحصول على الفرع الافتراضي لعميل"""
        pass
    
    @abstractmethod
    def list_all(
        self,
        status: Optional[BranchStatus] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[CustomerBranch]:
        """قائمة جميع الفروع"""
        pass
    
    @abstractmethod
    def search(
        self,
        search_text: str,
        customer_id: Optional[str] = None,
        limit: int = 50
    ) -> List[CustomerBranch]:
        """البحث عن فروع"""
        pass
    
    @abstractmethod
    def get_next_code(self, prefix: str = "BR") -> str:
        """توليد كود فرع تلقائي"""
        pass
    
    @abstractmethod
    def delete(self, branch_id: BranchId, permanent: bool = False) -> bool:
        """حذف فرع"""
        pass
    
    @abstractmethod
    def exists_by_code(self, code: BranchCode) -> bool:
        """التحقق من وجود فرع بالكود"""
        pass
    
    @abstractmethod
    def count_by_customer(self, customer_id: str) -> int:
        """حساب عدد فروع العميل"""
        pass