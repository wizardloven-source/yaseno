# core/application/customer_branch/services.py
"""
Customer Branch Service - خدمة فروع العملاء (واجهة التكامل)
"""

from typing import Optional, List
from uuid import UUID

from core.domain.customer_branch.entities import CustomerBranch
from core.domain.customer_branch.value_objects import BranchId, BranchCode
from core.domain.customer_branch.interfaces import ICustomerBranchRepository

from .dtos import CustomerBranchDTO
from .converters import branch_to_dto


class CustomerBranchService:
    """
    خدمة فروع العملاء - نقطة الوصول الرئيسية للنظام
    
    هذه الخدمة هي الواجهة الوحيدة التي يتفاعل معها باقي النظام.
    كل التفاصيل الداخلية مخفية خلف هذه الواجهة.
    """
    
    def __init__(self, repository: ICustomerBranchRepository):
        self._repo = repository
    
    # =========================================================================
    # عمليات القراءة
    # =========================================================================
    
    def get_branch(self, branch_id: str) -> Optional[CustomerBranchDTO]:
        """الحصول على فرع بواسطة المعرف"""
        branch = self._repo.get_by_id(BranchId.from_string(branch_id))
        return branch_to_dto(branch) if branch else None
    
    def get_branch_by_code(self, code: str) -> Optional[CustomerBranchDTO]:
        """الحصول على فرع بواسطة الكود"""
        branch = self._repo.get_by_code(BranchCode(code))
        return branch_to_dto(branch) if branch else None
    
    def get_customer_branches(
        self,
        customer_id: str,
        include_inactive: bool = False
    ) -> List[CustomerBranchDTO]:
        """الحصول على فروع عميل معين"""
        branches = self._repo.get_by_customer(
            customer_id=customer_id,
            include_inactive=include_inactive
        )
        return [branch_to_dto(b) for b in branches]
    
    def get_default_branch(self, customer_id: str) -> Optional[CustomerBranchDTO]:
        """الحصول على الفرع الافتراضي لعميل"""
        branch = self._repo.get_default_branch(customer_id)
        return branch_to_dto(branch) if branch else None
    
    def search_branches(self, search_text: str, customer_id: Optional[str] = None) -> List[CustomerBranchDTO]:
        """البحث عن فروع"""
        branches = self._repo.search(search_text, customer_id)
        return [branch_to_dto(b) for b in branches]
    
    # =========================================================================
    # عمليات الكتابة
    # =========================================================================
    
    def create_branch(self, branch: CustomerBranch) -> CustomerBranchDTO:
        """إنشاء فرع جديد"""
        self._repo.save(branch)
        return branch_to_dto(branch)
    
    def update_branch(self, branch: CustomerBranch) -> CustomerBranchDTO:
        """تحديث فرع"""
        self._repo.save(branch)
        return branch_to_dto(branch)
    
    def delete_branch(self, branch_id: str, permanent: bool = False) -> bool:
        """حذف فرع"""
        return self._repo.delete(BranchId.from_string(branch_id), permanent)
    
    def set_default_branch(self, branch_id: str, customer_id: str) -> bool:
        """تعيين فرع كافتراضي"""
        # 1. إلغاء تعيين الفرع الافتراضي الحالي
        current_default = self._repo.get_default_branch(customer_id)
        if current_default:
            current_default.unset_default("system")
            self._repo.save(current_default)
        
        # 2. تعيين الفرع الجديد كافتراضي
        branch = self._repo.get_by_id(BranchId.from_string(branch_id))
        if not branch:
            return False
        
        branch.set_as_default("system")
        self._repo.save(branch)
        return True
    
    # =========================================================================
    # دوال مساعدة للتكامل مع الفواتير
    # =========================================================================
    
    def get_branch_for_invoice(self, customer_id: str, branch_id: Optional[str] = None) -> Optional[CustomerBranchDTO]:
        """
        الحصول على فرع العميل المناسب للفاتورة
        
        إذا تم تحديد branch_id، يتم استخدامه.
        وإلا يتم استخدام الفرع الافتراضي للعميل.
        """
        if branch_id:
            return self.get_branch(branch_id)
        
        return self.get_default_branch(customer_id)
    
    def get_branch_display_name(self, branch_id: str) -> str:
        """الحصول على الاسم المعروض للفرع"""
        branch = self.get_branch(branch_id)
        return branch.display_name if branch else ""
    
    def get_branch_full_address(self, branch_id: str) -> str:
        """الحصول على العنوان الكامل للفرع"""
        branch = self.get_branch(branch_id)
        return branch.full_address if branch else ""