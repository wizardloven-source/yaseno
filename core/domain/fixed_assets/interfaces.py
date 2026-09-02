# core/domain/fixed_assets/interfaces.py
"""
Fixed Assets Repository Interfaces - واجهات مستودعات الأصول الثابتة
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date


class IFixedAssetRepository(ABC):
    """واجهة مستودع الأصول الثابتة"""

    @abstractmethod
    def save(self, asset) -> None:
        """حفظ أصل ثابت"""
        pass

    @abstractmethod
    def get_by_id(self, asset_id) -> Optional[Any]:
        """جلب أصل ثابت بالمعرّف"""
        pass

    @abstractmethod
    def get_by_code(self, code) -> Optional[Any]:
        """جلب أصل ثابت بالكود"""
        pass

    @abstractmethod
    def get_by_serial_number(self, serial_number: str) -> Optional[Any]:
        """جلب أصل ثابت بالرقم التسلسلي"""
        pass

    @abstractmethod
    def list_all(self, include_inactive: bool = False, limit: int = 100, offset: int = 0) -> List[Any]:
        """جلب قائمة الأصول الثابتة"""
        pass

    @abstractmethod
    def list_by_status(self, status, limit: int = 100) -> List[Any]:
        """جلب الأصول حسب الحالة"""
        pass

    @abstractmethod
    def list_by_asset_type(self, asset_type, include_inactive: bool = False, limit: int = 100) -> List[Any]:
        """جلب الأصول حسب النوع"""
        pass

    @abstractmethod
    def list_by_category(self, category: str, limit: int = 100) -> List[Any]:
        """جلب الأصول حسب الفئة"""
        pass

    @abstractmethod
    def get_depreciable_assets(self, as_of_date: date, limit: int = 100) -> List[Any]:
        """جلب الأصول القابلة للإهلاك"""
        pass

    @abstractmethod
    def get_fully_depreciated_assets(self, limit: int = 100) -> List[Any]:
        """جلب الأصول المكتملة الإهلاك"""
        pass

    @abstractmethod
    def search(self, search_text: str, asset_type=None, include_inactive: bool = False, limit: int = 50, offset: int = 0) -> List[Any]:
        """البحث في الأصول الثابتة"""
        pass

    @abstractmethod
    def delete(self, asset_id, permanent: bool = False) -> bool:
        """حذف أصل ثابت"""
        pass

    @abstractmethod
    def get_next_code(self, prefix: str = "A") -> str:
        """توليد الكود التالي"""
        pass

    @abstractmethod
    def count_all(self, asset_type=None, include_inactive: bool = False) -> int:
        """عدّ الأصول"""
        pass

    @abstractmethod
    def exists_by_code(self, code) -> bool:
        """التحقق من وجود كود"""
        pass

    @abstractmethod
    def get_assets_for_depreciation(self, as_of_date: date, limit: int = 100) -> List[Any]:
        """جلب الأصول المستحقة للإهلاك"""
        pass

    @abstractmethod
    def update_depreciation_schedule(self, asset_id, schedule: List[Any]) -> None:
        """تحديث جدول الإهلاك"""
        pass