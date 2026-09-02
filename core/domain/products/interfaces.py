# core/domain/products/interfaces.py
"""
Repository Interfaces for Products Context
واجهات مستودع المنتجات - تحدد العقود بين Domain و Infrastructure
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from .entities import Product
from .value_objects import ProductId, ProductCode, ProductStatus


class IProductRepository(ABC):
    """
    واجهة مستودع المنتجات
    تحدد العمليات المتاحة على المنتجات دون الاهتمام بتفاصيل التنفيذ
    """
    
    @abstractmethod
    def save(self, product: Product) -> None:
        """
        حفظ المنتج (جديد أو محدث)
        """
        pass
    
    @abstractmethod
    def get_by_id(self, product_id: ProductId) -> Optional[Product]:
        """
        الحصول على منتج بواسطة المعرف
        """
        pass
    
    @abstractmethod
    def get_by_code(self, code: ProductCode) -> Optional[Product]:
        """
        الحصول على منتج بواسطة الكود
        """
        pass
    
    @abstractmethod
    def get_by_ids(self, product_ids: List[ProductId]) -> List[Product]:
        """
        الحصول على منتجات متعددة بواسطة المعرفات
        """
        pass
    
    @abstractmethod
    def list_all(
        self,
        include_inactive: bool = False,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Product]:
        """
        قائمة جميع المنتجات مع خيارات التصفية والترقيم
        """
        pass
    
    @abstractmethod
    def list_active(self, limit: int = 100, offset: int = 0) -> List[Product]:
        """
        قائمة المنتجات النشطة فقط
        """
        pass
    
    @abstractmethod
    def list_by_category(self, category: str, limit: int = 100) -> List[Product]:
        """
        قائمة المنتجات حسب التصنيف
        """
        pass
    
    @abstractmethod
    def list_by_status(self, status: ProductStatus, limit: int = 100) -> List[Product]:
        """
        قائمة المنتجات حسب الحالة
        """
        pass
    
    @abstractmethod
    def get_low_stock(self, threshold: Optional[int] = None, limit: int = 100) -> List[Product]:
        """
        قائمة المنتجات ذات المخزون المنخفض
        """
        pass
    
    @abstractmethod
    def get_out_of_stock(self, limit: int = 100) -> List[Product]:
        """
        قائمة المنتجات التي نفد مخزونها
        """
        pass
    
    @abstractmethod
    def search(
        self,
        search_text: str,
        category: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Product]:
        """
        البحث عن المنتجات بالكود أو الاسم أو الوصف
        """
        pass
    
    @abstractmethod
    def get_all_categories(self) -> List[str]:
        """
        الحصول على قائمة بجميع التصنيفات المستخدمة
        """
        pass
    
    @abstractmethod
    def count_all(self, include_inactive: bool = False, category: Optional[str] = None) -> int:
        """
        حساب عدد المنتجات
        """
        pass
    
    @abstractmethod
    def exists_by_code(self, code: ProductCode) -> bool:
        """
        التحقق من وجود منتج بكود معين
        """
        pass
    
    @abstractmethod
    def delete(self, product_id: ProductId) -> bool:
        """
        حذف منتج (حذف فعلي - استخدم بحذر)
        """
        pass
    
    @abstractmethod
    def get_next_code(self) -> str:
        """
        توليد كود منتج تلقائي (اختياري)
        """
        pass