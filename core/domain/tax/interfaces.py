# core/domain/tax/interfaces.py
"""
Tax Interfaces - واجهات مستودع الضرائب
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import date

from .entities import TaxRule, TaxGroup, TaxExemption, TaxPeriod


class ITaxRepository(ABC):
    """واجهة مستودع القواعد الضريبية"""

    @abstractmethod
    def save(self, rule: TaxRule) -> None:
        """حفظ قاعدة ضريبية"""
        pass

    @abstractmethod
    def get_by_id(self, rule_id: str) -> Optional[TaxRule]:
        """الحصول على قاعدة بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[TaxRule]:
        """الحصول على قاعدة بواسطة الكود"""
        pass

    @abstractmethod
    def get_all(self, include_inactive: bool = False) -> List[TaxRule]:
        """الحصول على جميع القواعد"""
        pass

    @abstractmethod
    def get_active_rules(self) -> List[TaxRule]:
        """الحصول على القواعد النشطة فقط"""
        pass

    @abstractmethod
    def get_default_rule(self) -> Optional[TaxRule]:
        """الحصول على القاعدة الافتراضية"""
        pass

    @abstractmethod
    def get_by_date_range(self, start_date: date, end_date: date) -> List[TaxRule]:
        """الحصول على القواعد في نطاق زمني"""
        pass

    @abstractmethod
    def get_by_tax_type(self, tax_type: str) -> List[TaxRule]:
        """الحصول على القواعد حسب نوع الضريبة"""
        pass

    @abstractmethod
    def get_by_jurisdiction(self, jurisdiction: str) -> List[TaxRule]:
        """الحصول على القواعد حسب الجهة المختصة"""
        pass

    @abstractmethod
    def delete(self, rule_id: str) -> bool:
        """حذف قاعدة ضريبية"""
        pass

    @abstractmethod
    def count_active(self) -> int:
        """حساب عدد القواعد النشطة"""
        pass


class ITaxGroupRepository(ABC):
    """واجهة مستودع مجموعات الضرائب"""

    @abstractmethod
    def save(self, group: TaxGroup) -> None:
        """حفظ مجموعة ضرائب"""
        pass

    @abstractmethod
    def get_by_id(self, group_id: str) -> Optional[TaxGroup]:
        """الحصول على مجموعة بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[TaxGroup]:
        """الحصول على مجموعة بواسطة الكود"""
        pass

    @abstractmethod
    def get_all(self, include_inactive: bool = False) -> List[TaxGroup]:
        """الحصول على جميع المجموعات"""
        pass

    @abstractmethod
    def get_default_group(self) -> Optional[TaxGroup]:
        """الحصول على المجموعة الافتراضية"""
        pass

    @abstractmethod
    def delete(self, group_id: str) -> bool:
        """حذف مجموعة ضرائب"""
        pass


class ITaxExemptionRepository(ABC):
    """واجهة مستودع الإعفاءات الضريبية"""

    @abstractmethod
    def save(self, exemption: TaxExemption) -> None:
        """حفظ إعفاء ضريبي"""
        pass

    @abstractmethod
    def get_by_id(self, exemption_id: str) -> Optional[TaxExemption]:
        """الحصول على إعفاء بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[TaxExemption]:
        """الحصول على إعفاء بواسطة الكود"""
        pass

    @abstractmethod
    def get_all(self, include_inactive: bool = False) -> List[TaxExemption]:
        """الحصول على جميع الإعفاءات"""
        pass

    @abstractmethod
    def get_active_exemptions(self) -> List[TaxExemption]:
        """الحصول على الإعفاءات النشطة"""
        pass

    @abstractmethod
    def get_by_customer(self, customer_id: str) -> List[TaxExemption]:
        """الحصول على إعفاءات عميل معين"""
        pass

    @abstractmethod
    def get_by_product(self, product_code: str) -> List[TaxExemption]:
        """الحصول على إعفاءات منتج معين"""
        pass

    @abstractmethod
    def delete(self, exemption_id: str) -> bool:
        """حذف إعفاء ضريبي"""
        pass


class ITaxPeriodRepository(ABC):
    """واجهة مستودع الفترات الضريبية"""

    @abstractmethod
    def save(self, period: TaxPeriod) -> None:
        """حفظ فترة ضريبية"""
        pass

    @abstractmethod
    def get_by_id(self, period_id: str) -> Optional[TaxPeriod]:
        """الحصول على فترة بواسطة المعرف"""
        pass

    @abstractmethod
    def get_by_code(self, code: str) -> Optional[TaxPeriod]:
        """الحصول على فترة بواسطة الكود"""
        pass

    @abstractmethod
    def get_current_period(self) -> Optional[TaxPeriod]:
        """الحصول على الفترة الحالية"""
        pass

    @abstractmethod
    def get_by_date(self, dt: date) -> Optional[TaxPeriod]:
        """الحصول على الفترة التي تحتوي على تاريخ معين"""
        pass

    @abstractmethod
    def get_by_year(self, year: int) -> List[TaxPeriod]:
        """الحصول على فترات سنة معينة"""
        pass

    @abstractmethod
    def get_open_periods(self) -> List[TaxPeriod]:
        """الحصول على الفترات المفتوحة"""
        pass

    @abstractmethod
    def get_closed_periods(self) -> List[TaxPeriod]:
        """الحصول على الفترات المغلقة"""
        pass

    @abstractmethod
    def delete(self, period_id: str) -> bool:
        """حذف فترة ضريبية"""
        pass


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'ITaxRepository',
    'ITaxGroupRepository',
    'ITaxExemptionRepository',
    'ITaxPeriodRepository',
]